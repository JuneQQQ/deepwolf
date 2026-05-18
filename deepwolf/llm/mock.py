"""An offline provider for tests, CI and zero-setup demos.

:class:`MockProvider` never touches the network. It reads the machine-readable
``[[ACTION ...]]`` trailer that :mod:`deepwolf.prompts.templates` appends to
every request and answers with a valid, well-formed JSON decision. With a fixed
seed it is fully deterministic, so a whole self-play game is reproducible.
"""

from __future__ import annotations

import json
import random
import re

from deepwolf.llm.provider import LLMProvider

_ACTION_RE = re.compile(r"\[\[ACTION kind=(\w+) candidates=([\d,]*)\]\]")

_STATEMENTS = [
    "P{x} has been dodging the hard questions — that reads wolfy to me.",
    "Something about P{x}'s vote yesterday doesn't add up.",
    "I'd rather hear P{x} explain themselves before I commit my vote.",
    "P{x} is steering us a little too eagerly. I'm watching them.",
    "I think P{x} is village, honestly. Let's not waste the day on them.",
]


class MockProvider(LLMProvider):
    """A deterministic, network-free stand-in for a real LLM."""

    name = "mock"

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def complete(self, messages: list[dict[str, str]]) -> str:
        user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        match = _ACTION_RE.search(user)
        if match is None:
            return json.dumps({"statement": "I have nothing to add right now."})

        kind = match.group(1)
        candidates = [int(x) for x in match.group(2).split(",") if x]
        if kind == "speak":
            return json.dumps({"statement": self._statement(candidates)})

        choice = self.rng.choice(candidates) if candidates else 0
        return json.dumps({"choice": choice, "reasoning": "mock heuristic pick."})

    def _statement(self, candidates: list[int]) -> str:
        if not candidates:
            return "I'll keep my read to myself for now."
        return self.rng.choice(_STATEMENTS).format(x=self.rng.choice(candidates))
