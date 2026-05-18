"""JSON transcript export for completed games.

Serialises a :class:`GameResult` into a plain JSON-compatible dict that can be
written to disk for analysis, replay or sharing.  Handles the tricky bits —
``frozenset``, ``Enum`` and dataclass fields — so callers get clean output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from deepwolf.game.events import Event
from deepwolf.game.state import GameResult, Player


def _serialise_event(event: Event) -> dict[str, Any]:
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


def _serialise_player(player: Player) -> dict[str, Any]:
    return {
        "id": player.id,
        "name": player.name,
        "role": player.role.value,
        "faction": player.faction.value,
        "alive": player.alive,
        "death_day": player.death_day,
        "death_cause": player.death_cause,
    }


def to_json(result: GameResult) -> dict[str, Any]:
    """Convert a finished game into a JSON-serialisable dict."""
    return {
        "winner": result.winner.value,
        "days": result.days,
        "players": [_serialise_player(p) for p in result.players],
        "events": [_serialise_event(e) for e in result.events],
    }


def write(result: GameResult, path: str | Path) -> None:
    """Serialise *result* and write it to *path* as pretty-printed JSON."""
    data = to_json(result)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
