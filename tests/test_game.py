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
    assert roles.count(Role.HUNTER) == 1
    assert roles.count(Role.WITCH) == 1


def test_small_games_omit_the_special_roles():
    roles = standard_setup(4)
    assert roles.count(Role.HUNTER) == 0  # not enough village seats


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


def test_hunter_is_a_villager_with_no_night_action():
    assert Role.HUNTER.faction is Faction.VILLAGE
    assert Role.HUNTER.has_night_action is False


class _FixedVoter(RandomAgent):
    """Votes for a shared target id so a test can engineer a lynch."""

    target_id = -1

    def vote(self, view):
        if _FixedVoter.target_id in view.others_alive():
            return _FixedVoter.target_id
        return super().vote(view)


def test_hunter_fires_a_revenge_shot_on_death():
    from deepwolf.game.events import EventType

    config = GameConfig(
        roles=[Role.WEREWOLF, Role.HUNTER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER],
        seed=1,
    )
    engine = GameEngine(config, lambda pid, _: _FixedVoter(pid))
    hunter_id = next(p.id for p in engine.state.players if p.role is Role.HUNTER)
    _FixedVoter.target_id = hunter_id

    result = engine.run()

    shots = [e for e in result.events if e.type is EventType.HUNTER_SHOT]
    assert shots, "the Hunter died but never fired"
    shot = shots[0]
    assert shot.actor == hunter_id
    # the Hunter's victim must really be dead
    assert not result.players[shot.target].alive
    _FixedVoter.target_id = -1


def test_witch_role_is_a_villager_with_a_night_action():
    assert Role.WITCH.faction is Faction.VILLAGE
    assert Role.WITCH.has_night_action is True


class _WitchScript(RandomAgent):
    """Scripts the werewolf target and the Witch's potions for tests."""

    wolf_target = -1
    witch_heal = False
    witch_poison = -1

    def night_action(self, view):
        if (
            view.me_role is Role.WEREWOLF
            and _WitchScript.wolf_target in view.others_alive()
        ):
            return _WitchScript.wolf_target
        return super().night_action(view)

    def witch_turn(self, view, victim, can_heal, can_poison):
        heal = can_heal and _WitchScript.witch_heal
        poison = None
        if can_poison and _WitchScript.witch_poison in view.others_alive():
            poison = _WitchScript.witch_poison
        return (heal, poison)


def test_witch_healing_potion_cancels_the_night_kill():
    from deepwolf.game.events import EventType

    config = GameConfig(
        roles=[Role.WEREWOLF, Role.WITCH, Role.VILLAGER, Role.VILLAGER], seed=2
    )
    engine = GameEngine(config, lambda pid, _: _WitchScript(pid))
    victim = next(p.id for p in engine.state.players if p.role is Role.VILLAGER)
    _WitchScript.wolf_target = victim
    _WitchScript.witch_heal = True
    _WitchScript.witch_poison = -1

    result = engine.run()

    assert any(
        e.type is EventType.QUIET_NIGHT and e.day == 1 for e in result.events
    ), "the Witch healed the victim but a death was still announced"


def test_witch_poison_potion_kills_its_target():
    config = GameConfig(
        roles=[Role.WEREWOLF, Role.WITCH, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER],
        seed=5,
    )
    engine = GameEngine(config, lambda pid, _: _WitchScript(pid))
    villagers = [p.id for p in engine.state.players if p.role is Role.VILLAGER]
    _WitchScript.wolf_target = villagers[0]
    _WitchScript.witch_heal = False
    _WitchScript.witch_poison = villagers[1]

    result = engine.run()

    poisoned = result.players[villagers[1]]
    assert not poisoned.alive
    assert poisoned.death_day == 1
    assert poisoned.death_cause == "poisoned by the Witch"
