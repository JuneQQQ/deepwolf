# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned
- Additional roles: Witch, Hunter, Cupid.
- JSON transcript export for completed games.
- A model leaderboard built from arena runs.

## [0.1.0] — 2026-05-18

Initial public release.

### Added
- **Rules engine** — a strict, seeded referee with a night/day cycle and the
  Villager, Werewolf, Seer and Doctor roles. Every game is reproducible from a
  seed, and illegal agent moves are validated away.
- **Event log + player views** — a single-source-of-truth event log; each
  `PlayerView` is a visibility-filtered slice of it.
- **Agents** — a `RandomAgent` baseline and an `LLMAgent` that is robust to
  malformed model output (it always degrades to a legal move).
- **LLM provider layer** — a vendor-neutral, OpenAI-compatible provider plus a
  deterministic offline `MockProvider`.
- **Self-play arena** — batch runner with faction win rates, role survival and
  per-agent win rates.
- **Human copilot** — an explainable werewolf-suspicion model with an optional
  LLM second opinion.
- **CLI** — `deepwolf simulate`, `deepwolf arena` and `deepwolf play`.
- Test suite (33 tests), CI across Python 3.10–3.12, and full docs.

[Unreleased]: https://github.com/JuneQQQ/deepwolf/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/JuneQQQ/deepwolf/releases/tag/v0.1.0
