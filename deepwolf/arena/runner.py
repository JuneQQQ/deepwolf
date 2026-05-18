"""The self-play arena.

The arena runs many games under identical rules and aggregates the outcomes
into an :class:`ArenaReport`. It is how deepwolf answers questions like *"do
LLM werewolves beat random villagers?"* or *"which model survives longest as
the seer?"* — every game is seeded, so a benchmark is reproducible.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from deepwolf.agents.base import Agent
from deepwolf.game.engine import AgentFactory, GameEngine
from deepwolf.game.roles import Faction, Role
from deepwolf.game.state import GameConfig

ProgressHook = Callable[[int, int], None]  # (completed, total)


@dataclass
class ArenaReport:
    """Aggregated results of an arena run."""

    n_games: int = 0
    n_players: int = 0
    village_wins: int = 0
    werewolf_wins: int = 0
    total_days: int = 0
    # role -> [appearances, survivals]
    role_stats: dict[str, list[int]] = field(default_factory=dict)
    # agent name -> [games played, games won]
    agent_stats: dict[str, list[int]] = field(default_factory=dict)

    @property
    def village_win_rate(self) -> float:
        return self.village_wins / self.n_games if self.n_games else 0.0

    @property
    def werewolf_win_rate(self) -> float:
        return self.werewolf_wins / self.n_games if self.n_games else 0.0

    @property
    def avg_days(self) -> float:
        return self.total_days / self.n_games if self.n_games else 0.0

    def role_survival(self) -> dict[str, float]:
        return {
            role: (s / a if a else 0.0)
            for role, (a, s) in sorted(self.role_stats.items())
        }

    def agent_win_rate(self) -> dict[str, float]:
        return {
            name: (w / g if g else 0.0)
            for name, (g, w) in sorted(self.agent_stats.items())
        }

    def render(self) -> str:
        """A plain-text summary, suitable for logs or a terminal without rich."""
        lines = [
            f"Arena: {self.n_games} games, {self.n_players} players each",
            f"  Village win rate   : {self.village_win_rate:6.1%}",
            f"  Werewolf win rate  : {self.werewolf_win_rate:6.1%}",
            f"  Average game length: {self.avg_days:6.1f} days",
            "  Role survival:",
        ]
        for role, rate in self.role_survival().items():
            lines.append(f"    {role:<10}: {rate:6.1%}")
        if self.agent_stats:
            lines.append("  Agent win rate:")
            for name, rate in self.agent_win_rate().items():
                lines.append(f"    {name:<10}: {rate:6.1%}")
        return "\n".join(lines)


class Arena:
    """Runs a batch of seeded games with one agent configuration."""

    def __init__(
        self,
        n_players: int,
        agent_factory: AgentFactory,
        *,
        n_games: int = 50,
        base_seed: int = 0,
        discussion_rounds: int = 1,
    ) -> None:
        self.n_players = n_players
        self.agent_factory = agent_factory
        self.n_games = n_games
        self.base_seed = base_seed
        self.discussion_rounds = discussion_rounds

    def run(self, progress: ProgressHook | None = None) -> ArenaReport:
        report = ArenaReport(n_games=self.n_games, n_players=self.n_players)
        for i in range(self.n_games):
            config = GameConfig.standard(
                self.n_players,
                seed=self.base_seed + i,
                discussion_rounds=self.discussion_rounds,
            )
            seats: dict[int, Agent] = {}

            def recording_factory(pid: int, role: Role, _seats=seats) -> Agent:
                agent = self.agent_factory(pid, role)
                _seats[pid] = agent
                return agent

            result = GameEngine(config, recording_factory).run()
            self._record(report, result, seats)
            if progress is not None:
                progress(i + 1, self.n_games)
        return report

    @staticmethod
    def _record(report: ArenaReport, result: object, seats: dict[int, Agent]) -> None:
        report.total_days += result.days  # type: ignore[attr-defined]
        if result.winner is Faction.VILLAGE:  # type: ignore[attr-defined]
            report.village_wins += 1
        else:
            report.werewolf_wins += 1
        for player in result.players:  # type: ignore[attr-defined]
            stats = report.role_stats.setdefault(player.role.value, [0, 0])
            stats[0] += 1
            if player.alive:
                stats[1] += 1
            agent = seats.get(player.id)
            if agent is not None:
                a_stats = report.agent_stats.setdefault(agent.name, [0, 0])
                a_stats[0] += 1
                if player.faction is result.winner:  # type: ignore[attr-defined]
                    a_stats[1] += 1
