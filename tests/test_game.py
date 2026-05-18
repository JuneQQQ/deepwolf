"""Tests for the rules engine: roles, setups and full games."""

from __future__ import annotations

import pytest

from deepwolf.agents.llm_agent import LLMAgent
from deepwolf.agents.random_agent import RandomAgent
from deepwolf.game.engine import GameEngine
from deepwolf.game.roles import Faction, Role, standard_setup
from deepwolf.game.state import GameConfig
from deepwolf.llm.mock import MockProvider


def test_standard_setup_is_balanced():
    roles = standard_setup(7)
    assert len(roles) == 7
    assert roles.count(Role.WEREWOLF) == 2
    assert roles.count(Role.SEER) == 1
    assert roles.count(Role.DOCTOR) == 1


def test_standard_setup_rejects_tiny_games():
    with pytest.raises(ValueError):
        standard_setup(3)


def test_role_factions():
    assert Role.WEREWOLF.faction is Faction.WEREWOLVES
    assert Role.SEER.faction is Faction.VILLAGE
    assert Role.DOCTOR.faction is Faction.VILLAGE


def test_game_runs_to_a_decisive_winner():
    config = GameConfig.standard(7, seed=42)
    result = GameEngine(config, lambda pid, _: RandomAgent(pid)).run()
    assert result.winner in (Faction.VILLAGE, Faction.WEREWOLVES)
    assert result.days >= 1
    # exactly one faction can still win
    living_wolves = sum(1 for p in result.players if p.alive and p.faction is Faction.WEREWOLVES)
    living_village = sum(1 for p in result.players if p.alive and p.faction is Faction.VILLAGE)
    if result.winner is Faction.VILLAGE:
        assert living_wolves == 0
    else:
        assert living_wolves >= living_village


def test_games_are_reproducible():
    def play(seed: int):
        config = GameConfig.standard(7, seed=seed)
        provider = MockProvider(seed=0)
        return GameEngine(config, lambda pid, _: LLMAgent(pid, provider)).run()

    a, b = play(7), play(7)
    assert a.winner is b.winner
    assert a.days == b.days
    assert [e.text for e in a.events] == [e.text for e in b.events]


class _RogueAgent(RandomAgent):
    """Always returns illegal player ids to stress the engine's validation."""

    def night_action(self, view):
        return 999

    def vote(self, view):
        return -1


def test_illegal_agent_moves_cannot_corrupt_a_game():
    config = GameConfig.standard(6, seed=1)
    result = GameEngine(config, lambda pid, _: _RogueAgent(pid)).run()
    assert result.winner in (Faction.VILLAGE, Faction.WEREWOLVES)


def test_config_rejects_mismatched_names():
    with pytest.raises(ValueError):
        GameConfig(roles=standard_setup(5), player_names=["only", "two"])
