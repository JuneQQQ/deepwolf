# Architecture

deepwolf is built in five layers. Dependencies point strictly downward — an
upper layer may import a lower one, never the reverse.

```
  cli            deepwolf/cli.py        the only layer that does console I/O
   │
   ├── arena     deepwolf/arena         batches games, aggregates statistics
   │
   ├── copilot   deepwolf/copilot       the explainable human advisor
   │
   ├── agents    deepwolf/agents        player policies (random, llm)
   │      │
   │      └── llm  deepwolf/llm         provider abstraction + offline mock
   │
   └── game      deepwolf/game          the rules engine — pure, no I/O
```

## The game layer

The referee. It has four parts:

- **`roles.py`** — `Role`, `Faction`, and `standard_setup()` which deals a
  balanced table.
- **`events.py`** — `Event`, the atomic unit of everything that happens. An
  event carries its own visibility (`public`, or a `visible_to` set).
- **`state.py`** — `GameState` (the referee's full picture), `PlayerView` (a
  filtered picture for one player), and `build_view()` which produces the
  latter from the former.
- **`engine.py`** — `GameEngine`, which runs the night/day loop, consults
  agents, validates every decision and decides the winner.

Two invariants make the engine trustworthy:

1. **The event log is the single source of truth.** Player views, transcripts
   and the copilot are all *derived* from it.
2. **Every agent decision is validated.** An illegal target — out of range, a
   dead player, a hallucinated id — is silently replaced with a random legal
   one. A buggy agent can play badly; it can never corrupt a game.

## The agent layer

An `Agent` controls one seat. It is asked three things — `night_action`,
`speak`, `vote` — and only ever sees a `PlayerView`. `RandomAgent` is the
baseline; `LLMAgent` wraps a provider and is hardened against malformed model
output.

## The LLM layer

A `provider` turns chat messages into text. `OpenAICompatProvider` speaks the
OpenAI `/chat/completions` dialect that every major endpoint exposes.
`MockProvider` answers offline and deterministically by reading the
machine-readable `[[ACTION ...]]` trailer that prompts carry.

## The copilot layer

`advise()` takes a human's `PlayerView` and returns ranked werewolf
suspicions plus a recommended vote. The estimate is a transparent heuristic
(prior → confirmed facts → voting-behaviour nudges → renormalisation), with an
optional LLM second opinion layered on top.

## The arena layer

`Arena` runs many seeded games with one agent configuration and aggregates the
outcomes into an `ArenaReport`. Because every game is seeded, a benchmark is
fully reproducible.

## Determinism

A `GameConfig.seed` flows into a single `random.Random` on the `GameState`.
Role dealing, tie-breaks and `RandomAgent` all draw from it. Given the same
seed and the same (deterministic) agents, a game replays event-for-event —
which is what makes the arena a real benchmark and bugs reproducible.
