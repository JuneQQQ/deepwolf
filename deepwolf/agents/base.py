"""The agent interface.

An :class:`Agent` controls exactly one seat at the table. The engine hands it a
:class:`~deepwolf.game.state.PlayerView` and asks for a decision; the agent must
never see anything the view does not contain. Implementations live alongside
this module: :class:`~deepwolf.agents.random_agent.RandomAgent` (a baseline)
and :class:`~deepwolf.agents.llm_agent.LLMAgent` (an LLM-driven player).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from deepwolf.game.state import PlayerView


class Agent(ABC):
    """A single player's decision-making policy."""

    #: short identifier used in arena reports
    name: str = "agent"

    def __init__(self, player_id: int) -> None:
        self.player_id = player_id

    @abstractmethod
    def night_action(self, view: PlayerView) -> int:
        """Return the player id this agent's night ability should target.

        Called once per night for werewolves, the seer and the doctor. The
        meaning of the target depends on ``view.me_role``.
        """

    @abstractmethod
    def speak(self, view: PlayerView) -> str:
        """Return a short daytime statement addressed to the village."""

    @abstractmethod
    def vote(self, view: PlayerView) -> int:
        """Return the player id this agent votes to lynch."""

    def dying_shot(self, view: PlayerView) -> int:
        """Return a player id to take down with a dying Hunter's revenge.

        Only called when this agent's Hunter has just died. The default is a
        random living player; LLM and human agents override it. It is concrete,
        not abstract, so existing agents need no change.
        """
        pool = view.others_alive() or list(view.living_ids)
        return view.rng.choice(pool)

    def bid(self, view: PlayerView) -> tuple[int, str]:
        """Return ``(priority, reason)`` — a bid for the discussion floor.

        Only called in the ``bidding`` discussion mode. ``priority`` is clamped
        to 0-10 by the engine; ``reason`` is a short public justification. The
        default is a neutral bid; LLM and human agents override it.
        """
        return (5, "")

    def witch_turn(
        self,
        view: PlayerView,
        victim: int | None,
        can_heal: bool,
        can_poison: bool,
    ) -> tuple[bool, int | None]:
        """Return ``(use_heal, poison_target)`` for the Witch's night.

        ``victim`` is who the werewolves attacked (``None`` if they did not, or
        the Witch cannot know). ``can_heal`` / ``can_poison`` say which one-time
        potions are still available. Only called for a living Witch. Concrete,
        so existing agents need no change; the default uses no potions.
        """
        return (False, None)
