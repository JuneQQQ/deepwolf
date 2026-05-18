"""Round-trip test for the JSON transcript export."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from deepwolf.agents.random_agent import RandomAgent
from deepwolf.game.engine import GameEngine
from deepwolf.game.events import EventType
from deepwolf.game.state import GameConfig, GameResult
from deepwolf.game.transcript import to_json, write


def _play(seed: int = 42) -> GameResult:
    config = GameConfig.standard(7, seed=seed)
    return GameEngine(config, lambda pid, _: RandomAgent(pid)).run()


def test_to_json_is_serialisable():
    result = _play()
    data = to_json(result)
    # Must survive a full JSON round-trip without error.
    text = json.dumps(data)
    reloaded = json.loads(text)
    assert reloaded["winner"] in ("village", "werewolves")
    assert reloaded["days"] >= 1
    assert len(reloaded["players"]) == 7
    assert len(reloaded["events"]) > 0


def test_player_fields():
    data = to_json(_play())
    for p in data["players"]:
        assert isinstance(p["id"], int)
        assert isinstance(p["name"], str)
        assert p["role"] in ("villager", "werewolf", "seer", "doctor")
        assert p["faction"] in ("village", "werewolves")
        assert isinstance(p["alive"], bool)


def test_event_fields():
    data = to_json(_play())
    valid_types = {e.value for e in EventType}
    for event in data["events"]:
        assert event["type"] in valid_types
        assert isinstance(event["day"], int)
        assert isinstance(event["text"], str)
        assert isinstance(event["public"], bool)
        assert isinstance(event["visible_to"], list)


def test_visible_to_is_sorted_list():
    """frozenset must become a sorted list, not stay a set."""
    data = to_json(_play())
    for event in data["events"]:
        vt = event["visible_to"]
        assert isinstance(vt, list)
        assert vt == sorted(vt)


def test_write_creates_valid_file():
    result = _play()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "transcript.json"
        write(result, path)
        assert path.exists()
        reloaded = json.loads(path.read_text())
        assert reloaded["winner"] == result.winner.value
        assert reloaded["days"] == result.days
        assert len(reloaded["players"]) == len(result.players)
        assert len(reloaded["events"]) == len(result.events)


def test_round_trip_preserves_data():
    """to_json -> json.dumps -> json.loads gives identical output."""
    data = to_json(_play(seed=7))
    text = json.dumps(data, indent=2)
    reloaded = json.loads(text)
    assert data == reloaded
