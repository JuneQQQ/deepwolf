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
