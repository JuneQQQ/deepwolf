"""Tests for the self-play arena."""

from __future__ import annotations

from deepwolf.agents.random_agent import RandomAgent
from deepwolf.arena.runner import Arena


def test_arena_runs_every_game_and_totals_add_up():
    arena = Arena(7, lambda pid, _: RandomAgent(pid), n_games=12, base_seed=0)
    report = arena.run()
    assert report.n_games == 12
    assert report.village_wins + report.werewolf_wins == 12
    assert abs(report.village_win_rate + report.werewolf_win_rate - 1.0) < 1e-9
    assert report.avg_days >= 1.0


def test_arena_reports_role_and_agent_breakdowns():
    arena = Arena(7, lambda pid, _: RandomAgent(pid), n_games=8, base_seed=100)
    report = arena.run()
    survival = report.role_survival()
    assert {"werewolf", "seer", "doctor", "villager"} <= set(survival)
    assert all(0.0 <= rate <= 1.0 for rate in survival.values())
    assert report.agent_win_rate()["random"] >= 0.0


def test_arena_is_reproducible_for_a_base_seed():
    def run():
        return Arena(7, lambda pid, _: RandomAgent(pid), n_games=6, base_seed=5).run()

    a, b = run(), run()
    assert (a.village_wins, a.werewolf_wins, a.total_days) == (
        b.village_wins, b.werewolf_wins, b.total_days,
    )


def test_arena_progress_hook_is_called():
    seen: list[tuple[int, int]] = []
    Arena(6, lambda pid, _: RandomAgent(pid), n_games=4).run(progress=lambda d, t: seen.append((d, t)))
    assert seen == [(1, 4), (2, 4), (3, 4), (4, 4)]


def test_report_render_is_a_string():
    report = Arena(7, lambda pid, _: RandomAgent(pid), n_games=3).run()
    text = report.render()
    assert "Village win rate" in text and "Role survival" in text
