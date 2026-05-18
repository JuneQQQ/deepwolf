"""The werewolf referee.

The engine is intentionally a *pure rules machine*: it deals roles, runs the
night/day cycle, validates every agent decision and decides the winner. It
never reasons about the game — that is the agents' job. Any decision an agent
returns that is illegal is quietly replaced with a random legal one, so a
buggy or hallucinating agent can never corrupt a game.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from deepwolf.game.events import Event, EventType
from deepwolf.game.roles import Faction, Role
from deepwolf.game.state import (
    GameConfig,
    GameResult,
    GameState,
    Phase,
    Player,
    PlayerView,
    build_view,
)

if TYPE_CHECKING:
    from deepwolf.agents.base import Agent

AgentFactory = Callable[[int, Role], "Agent"]
Observer = Callable[[Event], None]


class GameEngine:
    """Runs a single game of werewolf from deal to winner."""

    def __init__(
        self,
        config: GameConfig,
        agent_factory: AgentFactory,
        observer: Observer | None = None,
    ) -> None:
        self.config = config
        self.agent_factory = agent_factory
        self.observer = observer
        self.state = GameState.new(config)
        self.agents: dict[int, Agent] = {}

    # ------------------------------------------------------------------ run
    def run(self) -> GameResult:
        """Play the whole game and return its result."""
        self._setup()
        while not self.state.is_over:
            self.state.day += 1
            if self.state.day > self.config.max_days:
                self._declare_by_headcount()
                break
            self._night_phase()
            if self._check_winner():
                break
            self._day_phase()
            if self._check_winner():
                break
        return GameResult(
            winner=self.state.winner or Faction.VILLAGE,
            days=self.state.day,
            players=self.state.players,
            events=self.state.events,
        )

    # --------------------------------------------------------------- setup
    def _setup(self) -> None:
        s = self.state
        roster = ", ".join(str(p) for p in s.players)
        role_counts = _role_count_map(s.players)
        summary = ", ".join(f"{n}x {role}" for role, n in sorted(role_counts.items()))
        self._emit(Event(
            EventType.GAME_START, 0, "setup",
            f"A game of werewolf begins. Players: {roster}. "
            f"Roles in play: {summary}.",
            data={"role_counts": role_counts, "n_players": len(s.players)},
        ))
        for p in s.players:
            self._emit(Event(
                EventType.ROLE_ASSIGNED, 0, "setup",
                f"You are the {p.role.value}.",
                public=False, visible_to=frozenset({p.id}),
                data={"role": p.role.value},
            ))
        pack = [p.id for p in s.players if p.role is Role.WEREWOLF]
        for wolf_id in pack:
            self._emit(Event(
                EventType.PACK_REVEAL, 0, "setup",
                "You recognise your fellow werewolves.",
                public=False, visible_to=frozenset({wolf_id}),
                data={"pack": pack},
            ))
        self.agents = {p.id: self.agent_factory(p.id, p.role) for p in s.players}

    # --------------------------------------------------------------- night
    def _night_phase(self) -> None:
        s = self.state
        s.phase = Phase.NIGHT
        self._emit(Event(
            EventType.NIGHT_FALLS, s.day, "night",
            f"Night {s.day} falls. The village sleeps.",
        ))

        victim = self._werewolf_target()
        self._seer_inspection()
        protected = self._doctor_protection()

        if victim is not None and victim != protected:
            self._kill(victim, "killed by werewolves")
            reveal = self._role_reveal(victim)
            self._emit(Event(
                EventType.DEATH_ANNOUNCED, s.day, "night",
                f"At dawn the village finds {s.name(victim)} (P{victim}) dead."
                + reveal[0],
                target=victim, data=reveal[1],
            ))
            self._process_hunter(victim)
        else:
            saved = protected is not None and protected == victim
            self._emit(Event(
                EventType.QUIET_NIGHT, s.day, "night",
                "The village wakes to find everyone alive."
                + (" The doctor's vigil paid off." if saved else ""),
            ))

    def _werewolf_target(self) -> int | None:
        s = self.state
        wolves = s.living_with_role(Role.WEREWOLF)
        if not wolves:
            return None
        legal = s.living_ids()
        tally: dict[int, int] = {}
        for wolf in wolves:
            choice = self._ask_target(wolf, "kill", legal)
            tally[choice] = tally.get(choice, 0) + 1
        victim = _argmax_random(tally, s.rng)
        pack_ids = frozenset(w.id for w in wolves)
        self._emit(Event(
            EventType.WEREWOLF_TARGET, s.day, "night",
            f"The pack marks {s.name(victim)} (P{victim}) for death.",
            target=victim, public=False, visible_to=pack_ids,
        ))
        return victim

    def _seer_inspection(self) -> None:
        s = self.state
        seers = s.living_with_role(Role.SEER)
        if not seers:
            return
        seer = seers[0]
        legal = [pid for pid in s.living_ids() if pid != seer.id]
        target = self._ask_target(seer, "inspect", legal)
        is_wolf = s.player(target).role is Role.WEREWOLF
        verdict = "a werewolf" if is_wolf else "not a werewolf"
        self._emit(Event(
            EventType.SEER_RESULT, s.day, "night",
            f"Your inspection reveals {s.name(target)} (P{target}) is {verdict}.",
            target=target, public=False, visible_to=frozenset({seer.id}),
            data={"is_wolf": is_wolf},
        ))

    def _doctor_protection(self) -> int | None:
        s = self.state
        doctors = s.living_with_role(Role.DOCTOR)
        if not doctors:
            return None
        doctor = doctors[0]
        target = self._ask_target(doctor, "protect", s.living_ids())
        self._emit(Event(
            EventType.DOCTOR_PROTECT, s.day, "night",
            f"You watch over {s.name(target)} (P{target}) tonight.",
            target=target, public=False, visible_to=frozenset({doctor.id}),
        ))
        return target

    # ----------------------------------------------------------------- day
    def _day_phase(self) -> None:
        s = self.state
        s.phase = Phase.DAY_DISCUSSION
        self._emit(Event(
            EventType.DAY_BREAKS, s.day, "day",
            f"Day {s.day}: the village gathers to debate.",
        ))
        for _ in range(self.config.discussion_rounds):
            for pid in s.living_ids():
                self._collect_statement(pid)

        s.phase = Phase.DAY_VOTE
        tally: dict[int, int] = {}
        for pid in s.living_ids():
            choice = self._collect_vote(pid)
            tally[choice] = tally.get(choice, 0) + 1

        lynched = _plurality_or_none(tally)
        if lynched is None:
            self._emit(Event(
                EventType.NO_LYNCH, s.day, "day",
                "The vote is split. Nobody is lynched today.",
            ))
        else:
            self._kill(lynched, "lynched by the village")
            reveal = self._role_reveal(lynched)
            self._emit(Event(
                EventType.LYNCH, s.day, "day",
                f"The village votes to lynch {s.name(lynched)} (P{lynched})."
                + reveal[0],
                target=lynched, data=reveal[1],
            ))
            self._process_hunter(lynched)

    def _collect_statement(self, player_id: int) -> None:
        s = self.state
        view = build_view(s, player_id, Phase.DAY_DISCUSSION)
        try:
            text = self.agents[player_id].speak(view).strip()
        except Exception as exc:  # noqa: BLE001 - agents must never crash a game
            text = f"(stays quiet — {type(exc).__name__})"
        text = text or "(says nothing)"
        if len(text) > 800:
            text = text[:797] + "..."
        self._emit(Event(
            EventType.STATEMENT, s.day, "day",
            f"{s.name(player_id)} (P{player_id}): {text}",
            actor=player_id, data={"statement": text},
        ))

    def _collect_vote(self, player_id: int) -> int:
        s = self.state
        legal = [pid for pid in s.living_ids() if pid != player_id]
        view = build_view(s, player_id, Phase.DAY_VOTE)
        choice = self._validate(self.agents[player_id].vote, view, legal)
        self._emit(Event(
            EventType.VOTE_CAST, s.day, "day",
            f"{s.name(player_id)} (P{player_id}) votes for "
            f"{s.name(choice)} (P{choice}).",
            actor=player_id, target=choice,
        ))
        return choice

    # ------------------------------------------------------------- helpers
    def _ask_target(self, actor: Player, action: str, legal: list[int]) -> int:
        view = build_view(self.state, actor.id, Phase.NIGHT)
        return self._validate(self.agents[actor.id].night_action, view, legal)

    def _validate(
        self,
        decide: Callable[[PlayerView], int],
        view: PlayerView,
        legal: list[int],
    ) -> int:
        """Run an agent decision, falling back to a random legal target."""
        try:
            choice = decide(view)
        except Exception:  # noqa: BLE001 - never let an agent crash the game
            choice = -1
        if choice not in legal:
            choice = view.rng.choice(legal)
        return choice

    def _kill(self, player_id: int, cause: str) -> None:
        player = self.state.player(player_id)
        player.alive = False
        player.death_day = self.state.day
        player.death_cause = cause

    def _role_reveal(self, player_id: int) -> tuple[str, dict]:
        """Optional public role reveal appended to a death event."""
        if not self.config.reveal_role_on_death:
            return "", {}
        role = self.state.player(player_id).role
        return f" They were the {role.value}.", {"role": role.value}

    def _process_hunter(self, player_id: int) -> None:
        """If the player who just died is the Hunter, fire their revenge shot.

        The shot is resolved immediately and may itself kill another Hunter, so
        the method recurses. Win conditions are re-checked by the phase loop
        once the whole chain has resolved.
        """
        s = self.state
        if s.player(player_id).role is not Role.HUNTER:
            return
        targets = s.living_ids()
        if not targets:
            return
        view = build_view(s, player_id, s.phase)
        try:
            choice = self.agents[player_id].dying_shot(view)
        except Exception:  # noqa: BLE001 - an agent error must not crash a game
            choice = -1
        if choice not in targets:
            choice = s.rng.choice(targets)
        self._kill(choice, "shot by the dying Hunter")
        reveal = self._role_reveal(choice)
        self._emit(Event(
            EventType.HUNTER_SHOT, s.day, s.phase.value,
            f"With their dying breath, {s.name(player_id)} (P{player_id}) "
            f"shoots {s.name(choice)} (P{choice})." + reveal[0],
            actor=player_id, target=choice, data=reveal[1],
        ))
        self._process_hunter(choice)  # a shot Hunter shoots back

    def _check_winner(self) -> bool:
        winner = _winner(self.state)
        if winner is None:
            return False
        self.state.winner = winner
        self.state.phase = Phase.GAME_OVER
        self._emit(Event(
            EventType.GAME_OVER, self.state.day, "end",
            f"The game is over after {self.state.day} day(s). "
            f"{winner.label} win.",
            data={"winner": winner.value},
        ))
        return True

    def _declare_by_headcount(self) -> None:
        s = self.state
        wolves = len(s.living_in_faction(Faction.WEREWOLVES))
        village = len(s.living_in_faction(Faction.VILLAGE))
        s.winner = Faction.WEREWOLVES if wolves > village else Faction.VILLAGE
        s.phase = Phase.GAME_OVER
        self._emit(Event(
            EventType.GAME_OVER, s.day, "end",
            f"The game reaches the day limit. {s.winner.label} win on headcount.",
            data={"winner": s.winner.value},
        ))

    def _emit(self, event: Event) -> None:
        self.state.emit(event)
        if self.observer is not None:
            self.observer(event)


# ---------------------------------------------------------------- functions
def _winner(state: GameState) -> Faction | None:
    """Return the winning faction, or ``None`` if the game continues."""
    wolves = len(state.living_in_faction(Faction.WEREWOLVES))
    village = len(state.living_in_faction(Faction.VILLAGE))
    if wolves == 0:
        return Faction.VILLAGE
    if wolves >= village:
        return Faction.WEREWOLVES
    return None


def _argmax_random(tally: dict[int, int], rng: object) -> int:
    """Key with the highest count; ties broken with ``rng``."""
    best = max(tally.values())
    top = sorted(k for k, v in tally.items() if v == best)
    return top[0] if len(top) == 1 else rng.choice(top)  # type: ignore[attr-defined]


def _plurality_or_none(tally: dict[int, int]) -> int | None:
    """Key with a strict plurality, or ``None`` on a tie or empty tally."""
    if not tally:
        return None
    best = max(tally.values())
    top = [k for k, v in tally.items() if v == best]
    return top[0] if len(top) == 1 else None


def _role_count_map(players: list[Player]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in players:
        counts[p.role.value] = counts.get(p.role.value, 0) + 1
    return counts
