"""Export a finished game as a structured JSON transcript.

A transcript is a self-contained, machine-readable record of one game: the
players with their roles revealed, the full event log, and the winner. It is
useful for replay, offline analysis, attaching to a bug report, or feeding past
games into an arena leaderboard.

The format is versioned via the ``schema`` field so consumers can evolve
safely. The current schema is ``deepwolf.transcript/v1``.
"""

from __future__ import annotations

import json
from pathlib import Path

from deepwolf.game.events import Event, EventType
from deepwolf.game.roles import Faction
from deepwolf.game.state import GameResult

SCHEMA = "deepwolf.transcript/v1"


class Transcript:
    """A loaded transcript ready for replay."""

    def __init__(self, data: dict) -> None:
        self.schema: str = data.get("schema", "")
        self.winner: str = data["winner"]
        self.days: int = data["days"]
        self.players: list[dict] = data["players"]
        self.events: list[Event] = [_event_from_json(e) for e in data["events"]]

    @property
    def winner_label(self) -> str:
        return "the Village" if self.winner == Faction.VILLAGE.value else "the Werewolves"


def _event_from_json(raw: dict) -> Event:
    """Reconstruct an :class:`Event` from a transcript dict entry."""
    return Event(
        type=EventType(raw["type"]),
        day=raw["day"],
        phase=raw["phase"],
        text=raw["text"],
        actor=raw.get("actor"),
        target=raw.get("target"),
        public=raw.get("public", True),
        visible_to=frozenset(raw.get("visible_to", ())),
        data=raw.get("data", {}),
    )


def load(path: str | Path) -> Transcript:
    """Read a transcript JSON file and return a :class:`Transcript`."""
    return Transcript(json.loads(Path(path).read_text(encoding="utf-8")))


def event_to_json(event: Event) -> dict:
    """Serialise one :class:`Event` to a JSON-safe dict."""
    return {
        "type": event.type.value,
        "day": event.day,
        "phase": event.phase,
        "text": event.text,
        "actor": event.actor,
        "target": event.target,
        "public": event.public,
        "visible_to": sorted(event.visible_to),
        "data": event.data,
    }


def to_json(result: GameResult) -> dict:
    """Build a JSON-safe transcript dict from a finished game."""
    return {
        "schema": SCHEMA,
        "winner": result.winner.value,
        "days": result.days,
        "players": [
            {
                "id": p.id,
                "name": p.name,
                "role": p.role.value,
                "faction": p.faction.value,
                "alive": p.alive,
                "death_day": p.death_day,
                "death_cause": p.death_cause,
            }
            for p in result.players
        ],
        "events": [event_to_json(e) for e in result.events],
    }


def dumps(result: GameResult, *, indent: int | None = 2) -> str:
    """Return the transcript of ``result`` as a JSON string."""
    return json.dumps(to_json(result), indent=indent, ensure_ascii=False)


def save(result: GameResult, path: str | Path) -> Path:
    """Write the transcript of ``result`` to ``path`` and return that path."""
    out = Path(path)
    out.write_text(dumps(result) + "\n", encoding="utf-8")
    return out
