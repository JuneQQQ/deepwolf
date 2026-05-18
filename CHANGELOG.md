# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Arena leaderboard** ([#4](https://github.com/JuneQQQ/deepwolf/issues/4)) —
  `deepwolf.arena.leaderboard` and a `deepwolf leaderboard` command rank agents
  fairly: each competitor plays both sides of a fixed reference match-up under
  identical seeds. Exports a Markdown table.

### Planned
- Additional roles: Cupid.

## [0.2.0] — 2026-05-18

### Added
- **Hunter role** ([#1](https://github.com/JuneQQQ/deepwolf/issues/1)) — a
  villager who, the moment they die (lynched or killed at night), takes one
  living player down with them. Chained Hunter deaths resolve correctly, and
  the copilot treats a Hunter's victim as a confirmed role.
- **JSON transcript export** ([#3](https://github.com/JuneQQQ/deepwolf/issues/3))
  — the `deepwolf.game.transcript` module and a `--transcript PATH` flag on
  `deepwolf simulate` write a finished game as a versioned, machine-readable
  JSON record (players, full event log, winner).
- **Witch role** ([#2](https://github.com/JuneQQQ/deepwolf/issues/2)) — a
  villager with two one-time potions. Each night the Witch learns who the
  werewolves attacked and may spend a healing potion to save them and/or a
  poison potion to kill any player. The night phase now resolves multiple
  simultaneous deaths.

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

[Unreleased]: https://github.com/JuneQQQ/deepwolf/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/JuneQQQ/deepwolf/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/JuneQQQ/deepwolf/releases/tag/v0.1.0
