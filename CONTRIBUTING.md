# Contributing to deepwolf

Thanks for your interest — contributions of every size are welcome, from
typo fixes to whole new roles.

## Getting set up

```bash
git clone https://github.com/JuneQQQ/deepwolf.git
cd deepwolf
pip install -e ".[dev]"
pytest          # everything should be green
```

No API key is needed: the test suite and `--provider mock` run fully offline.

## Before you open a pull request

Run the same three checks CI runs:

```bash
ruff check .            # lint + import order
mypy deepwolf           # static types
pytest --cov=deepwolf   # tests
```

All three must pass. New behaviour needs a test.

## Project layout

| Layer | Package | Responsibility |
|-------|---------|----------------|
| Rules | `deepwolf/game` | The referee — roles, events, state, engine. Pure, no I/O. |
| Agents | `deepwolf/agents` | Player policies (`RandomAgent`, `LLMAgent`). |
| LLM | `deepwolf/llm` | Provider abstraction and the offline mock. |
| Copilot | `deepwolf/copilot` | The explainable human advisor. |
| Arena | `deepwolf/arena` | Batch self-play and benchmarking. |
| CLI | `deepwolf/cli.py` | The only layer that touches the console. |

Keep the boundaries: the `game` layer must never import `agents`, and only
`cli.py` may do console I/O.

## Design principles

1. **The engine is a pure rules machine.** It validates everything; an agent
   can play badly but can never corrupt a game.
2. **The event log is the single source of truth.** A `PlayerView` is a filter
   over it — never leak information a player should not have.
3. **Determinism matters.** Anything seeded must be reproducible. Add a test
   that proves it.
4. **The copilot stays explainable.** Every number it shows must come with a
   reason a human can read.

## Good first issues

Look for the [`good first issue`](https://github.com/JuneQQQ/deepwolf/labels/good%20first%20issue)
label. Adding a new role (Witch, Hunter, Cupid) is a great self-contained
contribution — see `deepwolf/game/roles.py`.

## Commit style

Short, imperative subject lines (`add Hunter role`, `fix tie-break in arena`).
Reference the issue number when there is one.

## Code of conduct

Be kind and constructive. We assume good faith and expect the same in return.
