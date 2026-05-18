"""Prompt construction for LLM-driven agents.

These helpers turn a :class:`~deepwolf.game.state.PlayerView` into chat
messages. The format is deliberately stable: every decision request ends with a
machine-readable ``[[ACTION ...]]`` trailer, which lets the offline
:class:`~deepwolf.llm.mock.MockProvider` answer without a real model.
"""

from __future__ import annotations

from deepwolf.game.events import EventType
from deepwolf.game.state import PlayerView

# Decision kinds understood by both the LLM agent and the mock provider.
KIND_KILL = "kill"
KIND_INSPECT = "inspect"
KIND_PROTECT = "protect"
KIND_VOTE = "vote"
KIND_SPEAK = "speak"
KIND_SHOOT = "shoot"

_ASK = {
    KIND_KILL: "It is night. As a werewolf, choose one living player for the "
               "pack to eliminate. Pick someone whose loss hurts the village.",
    KIND_INSPECT: "It is night. As the Seer, choose one living player to "
                  "inspect. You will learn if they are a werewolf.",
    KIND_PROTECT: "It is night. As the Doctor, choose one living player to "
                  "protect from the werewolves tonight.",
    KIND_VOTE: "It is the daytime vote. Choose one living player to lynch. "
               "Vote to advance your faction's win condition.",
    KIND_SPEAK: "It is the daytime discussion. Make a short statement (2-4 "
                "sentences) to the village. Push your faction's agenda — "
                "share real reads if that helps you, or mislead if you must.",
    KIND_SHOOT: "You are the Hunter and you have just died. As your final "
                "act, choose one living player to shoot — aim at whoever you "
                "most believe is a werewolf.",
}


def system_message(view: PlayerView) -> str:
    """The standing instructions for a player: rules, role and objective."""
    role = view.me_role
    return (
        "You are playing a game of Werewolf (Mafia), a game of social "
        "deduction. The Village wins when every werewolf is dead. The "
        "Werewolves win when they equal or outnumber the remaining villagers.\n\n"
        f"You are {view.me_name} (P{view.me_id}). Your secret role is "
        f"{role.value.upper()}.\n{role.summary}\n\n"
        "Play to win. Reason carefully about who is lying. Werewolves should "
        "blend in and misdirect; villagers should compare claims and voting "
        "patterns. Keep statements concise and in character. Never reveal "
        "information you could not plausibly know."
    )


def decision_request(view: PlayerView, kind: str, candidates: list[int]) -> str:
    """The user message asking the agent for one concrete decision."""
    parts = [
        f"=== Day {view.day} — {view.phase.value} ===",
        _players_block(view),
        _secret_block(view),
        _log_block(view),
        _ASK[kind],
        _candidates_line(view, candidates),
        _format_instructions(kind),
        f"[[ACTION kind={kind} candidates={','.join(map(str, candidates))}]]",
    ]
    return "\n\n".join(p for p in parts if p)


def _players_block(view: PlayerView) -> str:
    rows = []
    for p in view.players:
        tag = "alive" if p.alive else "DEAD"
        me = "  <- you" if p.id == view.me_id else ""
        rows.append(f"  P{p.id} {p.name}: {tag}{me}")
    return "Players:\n" + "\n".join(rows)


def _secret_block(view: PlayerView) -> str:
    if not view.private_notes:
        return ""
    return "What only you know:\n" + "\n".join(f"  - {n}" for n in view.private_notes)


def _log_block(view: PlayerView) -> str:
    lines = []
    for e in view.events:
        if e.type in (EventType.ROLE_ASSIGNED, EventType.PACK_REVEAL):
            continue  # already surfaced in the secret block
        prefix = "  " if e.public else "  [secret] "
        lines.append(prefix + e.text)
    if not lines:
        return "Game log: (nothing has happened yet)"
    return "Game log:\n" + "\n".join(lines)


def _candidates_line(view: PlayerView, candidates: list[int]) -> str:
    named = ", ".join(f"{view.name(c)} (P{c})" for c in candidates)
    return f"Your legal choices are: {named}."


def _format_instructions(kind: str) -> str:
    if kind == KIND_SPEAK:
        return (
            'Respond with ONLY a JSON object: {"statement": "<your words>"}. '
            "No other text."
        )
    return (
        'Respond with ONLY a JSON object: '
        '{"choice": <player id as integer>, "reasoning": "<one sentence>"}. '
        "The choice MUST be one of the legal player ids above. No other text."
    )
