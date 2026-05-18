"""A baseline agent that plays uniformly at random.

It exists for two reasons: it is the control group every arena benchmark
measures LLM agents against, and it lets the whole engine be exercised in
tests without touching a network.
"""

from __future__ import annotations

from deepwolf.agents.base import Agent
from deepwolf.game.state import PlayerView

_FILLER = [
    "I don't have anything solid yet. Let's hear from the others.",
    "Hard to read this table. I'll keep watching.",
    "Someone here is lying, but I can't prove who.",
    "I'm keeping my vote open for now.",
    "We should focus on whoever is being too quiet.",
]


class RandomAgent(Agent):
    """Picks uniformly among legal options. No memory, no strategy."""

    name = "random"

    def night_action(self, view: PlayerView) -> int:
        return view.rng.choice(self._pool(view))

    def vote(self, view: PlayerView) -> int:
        return view.rng.choice(self._pool(view))

    def speak(self, view: PlayerView) -> str:
        return view.rng.choice(_FILLER)

    def witch_turn(
        self, view: PlayerView, victim: int | None, can_heal: bool, can_poison: bool
    ) -> tuple[bool, int | None]:
        heal = can_heal and view.rng.random() < 0.5
        poison: int | None = None
        if can_poison and view.rng.random() < 0.3 and view.others_alive():
            poison = view.rng.choice(view.others_alive())
        return (heal, poison)

    @staticmethod
    def _pool(view: PlayerView) -> list[int]:
        return view.others_alive() or list(view.living_ids)
