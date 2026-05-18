"""deepwolf — an LLM werewolf engine.

deepwolf does two things with the game of Werewolf (Mafia):

* **self-play arena** — LLM agents play each other so you can benchmark how
  well a model reasons, deceives and deduces under hidden information;
* **human copilot** — an explainable advisor that estimates who the werewolves
  are and recommends your vote while *you* play.

The public API is re-exported here; see the README for usage.
"""

from deepwolf.agents.base import Agent
from deepwolf.agents.llm_agent import LLMAgent
from deepwolf.agents.random_agent import RandomAgent
from deepwolf.arena.runner import Arena, ArenaReport
from deepwolf.copilot.advisor import Advice, Suspicion, advise
from deepwolf.game.engine import GameEngine
from deepwolf.game.roles import Faction, Role
from deepwolf.game.state import GameConfig, GameResult, PlayerView
from deepwolf.i18n import LANGUAGES, Translator
from deepwolf.llm.mock import MockProvider
from deepwolf.llm.provider import LLMConfig, LLMProvider, OpenAICompatProvider

__version__ = "0.2.0"

__all__ = [
    "Agent",
    "LLMAgent",
    "RandomAgent",
    "Arena",
    "ArenaReport",
    "Advice",
    "Suspicion",
    "advise",
    "GameEngine",
    "Faction",
    "Role",
    "GameConfig",
    "GameResult",
    "PlayerView",
    "LANGUAGES",
    "Translator",
    "MockProvider",
    "LLMConfig",
    "LLMProvider",
    "OpenAICompatProvider",
    "__version__",
]
