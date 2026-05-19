"""Tests for JSON transcript export."""

from __future__ import annotations

import json

from deepwolf.agents.random_agent import RandomAgent
from deepwolf.game.engine import GameEngine
from deepwolf.game.events import EventType
from deepwolf.game.state import GameConfig
from deepwolf.game.transcript import SCHEMA, Transcript, dumps, load, save, to_json


def _finished_game():
    config = GameConfig.standard(7, seed=3)
    return GameEngine(config, lambda pid, _: RandomAgent(pid)).run()


def test_to_json_has_the_expected_shape():
    t = to_json(_finished_game())
    assert t["schema"] == SCHEMA
    assert t["winner"] in ("village", "werewolves")
    assert len(t["players"]) == 7
    assert all({"id", "name", "role", "faction", "alive"} <= set(p) for p in t["players"])
    assert t["events"]
    assert all("type" in e and "day" in e for e in t["events"])


def test_transcript_round_trips_through_json():
    t = to_json(_finished_game())
    # if any non-JSON type leaked (Enum, frozenset, ...) this would raise or differ
    assert json.loads(json.dumps(t)) == t


def test_dumps_produces_valid_json():
    parsed = json.loads(dumps(_finished_game()))
    assert parsed["schema"] == SCHEMA
    assert isinstance(parsed["events"], list)


def test_save_writes_a_readable_file(tmp_path):
    path = save(_finished_game(), tmp_path / "game.json")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema"] == SCHEMA
    assert data["days"] >= 1


def test_load_reconstructs_events(tmp_path):
    result = _finished_game()
    path = save(result, tmp_path / "game.json")
    transcript = load(path)
    assert isinstance(transcript, Transcript)
    assert transcript.winner == result.winner.value
    assert transcript.days == result.days
    assert len(transcript.players) == len(result.players)
    assert len(transcript.events) == len(result.events)
    for loaded, original in zip(transcript.events, result.events, strict=True):
        assert loaded.type is original.type
        assert loaded.day == original.day
        assert loaded.text == original.text
        assert loaded.public == original.public


def test_round_trip_simulate_save_load(tmp_path):
    """Simulate -> save -> load -> verify events match exactly."""
    result = _finished_game()
    path = save(result, tmp_path / "rt.json")
    transcript = load(path)
    # every event text must survive the round trip
    original_texts = [e.text for e in result.events]
    loaded_texts = [e.text for e in transcript.events]
    assert original_texts == loaded_texts
    # event types must be proper EventType enums, not strings
    assert all(isinstance(e.type, EventType) for e in transcript.events)


def test_replay_cli_runs_without_error(tmp_path):
    """End-to-end: simulate, save, replay via CLI entry point."""
    from deepwolf.cli import main

    path = save(_finished_game(), tmp_path / "replay.json")
    exit_code = main(["replay", str(path)])
    assert exit_code == 0
