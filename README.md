# 🐺 deepwolf

**An LLM werewolf engine — agent self-play arena and an explainable human copilot.**

[![CI](https://github.com/JuneQQQ/deepwolf/actions/workflows/ci.yml/badge.svg)](https://github.com/JuneQQQ/deepwolf/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**English** | [中文](README.zh-CN.md)

Werewolf (a.k.a. Mafia) is a game of **hidden information, persuasion and
deception** — exactly the things that are hard to measure in a language model
and hard to do well as a human. `deepwolf` turns the game into two tools:

- 🤖 **a self-play arena** — LLM agents play full games against each other under
  a strict, seeded rules engine, so you can *benchmark* how well a model
  reasons, lies and deduces under uncertainty;
- 🧭 **a human copilot** — an *explainable* advisor that estimates who the
  werewolves are and recommends your vote while **you** play.

Everything runs offline out of the box (a deterministic mock model ships with
the package); point it at any OpenAI-compatible endpoint for the real thing.

---

## Why this exists

Most LLM benchmarks are single-turn and fully observable. Werewolf is neither:
a player must track *who said what*, reason about *why* they said it, maintain
a consistent lie across many turns, and update beliefs from votes and deaths.
`deepwolf` makes that measurable — and makes the same belief-tracking available
to a human as a copilot.

## Features

- ♟️ **A strict, seeded rules engine.** Night/day cycle with Werewolf, Seer,
  Doctor, Hunter and Witch abilities. Every game is reproducible from a seed; an
  illegal or hallucinated agent move can never corrupt a game.
- 🌏 **Bilingual.** The whole game — event log, roles, agent speech, the CLI —
  runs in English or Simplified Chinese. Just add `--lang zh`.
- 🔌 **Vendor-neutral LLMs.** Any OpenAI-compatible endpoint — OpenAI,
  DeepSeek, Xiaomi MiMo, Groq, OpenRouter, a local server. Change one env var.
- 🧪 **Offline by default.** A deterministic `MockProvider` plays full games
  with zero network and zero keys — great for CI and for trying it out.
- 📊 **A benchmarking arena.** Run hundreds of seeded games and get faction win
  rates, role survival and per-agent win rates.
- 🧭 **An explainable copilot.** Not a black box: a transparent Bayesian-flavoured
  belief model you can read, optionally augmented by an LLM second opinion.

## Install

```bash
git clone https://github.com/JuneQQQ/deepwolf.git
cd deepwolf
pip install -e ".[dev]"
```

## Quickstart

Watch a full game play itself — **no API key needed**:

```bash
deepwolf simulate --players 7 --seed 1
deepwolf simulate --players 7 --seed 1 --lang zh                # play in Chinese
deepwolf simulate --players 7 --seed 1 --transcript game.json   # + JSON record
```

Benchmark agents over many seeded games, or rank them on a leaderboard:

```bash
deepwolf arena --games 50 --players 7 --villagers mock --werewolves random
deepwolf leaderboard --games 30 --players 7 --markdown board.md
```

Sit at the table yourself, with the copilot advising every vote:

```bash
deepwolf play --players 7
```

## Connecting a real model

`deepwolf` talks the OpenAI `/chat/completions` dialect. Copy `.env.example` to
`.env` and fill it in:

```bash
DEEPWOLF_PROVIDER=mimo            # or: openai, deepseek, groq, openrouter
DEEPWOLF_API_KEY=sk-...
DEEPWOLF_MODEL=mimo-v2-flash
# DEEPWOLF_BASE_URL=...           # set this instead of PROVIDER for custom endpoints
```

Then run any command with `--provider env`:

```bash
deepwolf simulate --provider env
deepwolf arena --provider env --villagers llm --werewolves llm --games 10
```

For custom endpoints (a corporate gateway, a local llama.cpp / vLLM / Ollama
server) and troubleshooting, see [`docs/providers.md`](docs/providers.md).

## How it works

```
          ┌─────────────┐   PlayerView   ┌──────────────┐
          │  GameEngine  │ ─────────────▶ │    Agent     │
          │  (referee)   │ ◀───────────── │ random / llm │
          └─────────────┘    decision     └──────────────┘
                 │                               │
            event log                       LLMProvider
                 │                         (mock / OpenAI-compat)
        ┌────────┴────────┐
        ▼                 ▼
     Arena            Copilot.advise()
  (benchmark)       (belief model + LLM)
```

The **event log** is the single source of truth. A `PlayerView` is just a
*filtered* log — an agent physically cannot see a secret it was not party to.
See [`docs/architecture.md`](docs/architecture.md) for the full design.

## Library usage

```python
from deepwolf import GameConfig, GameEngine, LLMAgent, MockProvider

provider = MockProvider(seed=0)
config = GameConfig.standard(n_players=7, seed=1)
result = GameEngine(config, lambda pid, role: LLMAgent(pid, provider)).run()

print(result.winner.label, "win in", result.days, "days")
```

The copilot, standalone:

```python
from deepwolf.copilot import advise
advice = advise(player_view)          # heuristic only
for s in advice.suspicions:
    print(f"P{s.player_id} {s.name}: {s.percent}%  ({'; '.join(s.reasons)})")
print(advice.rationale)
```

## The copilot's belief model

The copilot is deliberately **not** a black box. For each living player it
estimates `P(werewolf)`:

1. start from the prior `unknown werewolves / unknown players`;
2. harden to `0` or `1` for anything *confirmed* — a seer result, a revealed
   corpse, a known packmate;
3. nudge the rest from public voting: helping lynch a confirmed werewolf looks
   clean, pushing a confirmed villager looks bad;
4. renormalise so the suspicions sum to the werewolves still at large.

Every number comes with the reasons that produced it. An optional LLM pass adds
a natural-language read of the *statements* the heuristic ignores.

## Roadmap

See [CHANGELOG.md](CHANGELOG.md) and the [issue tracker](https://github.com/JuneQQQ/deepwolf/issues).
Near-term: more roles (Cupid) and richer copilot belief modelling.

## Contributing

Contributions are very welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
Good first issues are labelled [`good first issue`](https://github.com/JuneQQQ/deepwolf/labels/good%20first%20issue).

## License

[MIT](LICENSE) © 2026 the deepwolf contributors.
