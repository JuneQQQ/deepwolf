"""The ``deepwolf`` command-line interface.

Three sub-commands:

* ``simulate`` — watch a full self-play game as a transcript;
* ``arena``    — benchmark agents over many seeded games;
* ``play``     — sit at the table yourself, with the copilot at your side.

The CLI is the only part of deepwolf that does console I/O; the library layers
stay pure and importable.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import Any

from deepwolf import __version__
from deepwolf.agents.base import Agent
from deepwolf.agents.llm_agent import LLMAgent
from deepwolf.agents.random_agent import RandomAgent
from deepwolf.arena.runner import Arena, ArenaReport
from deepwolf.copilot.advisor import Advice, advise
from deepwolf.game.engine import GameEngine
from deepwolf.game.events import Event, EventType
from deepwolf.game.roles import Faction, Role
from deepwolf.game.state import GameConfig, GameResult, PlayerView
from deepwolf.i18n import LANGUAGES, Translator, pick
from deepwolf.llm.mock import MockProvider
from deepwolf.llm.provider import LLMConfig, LLMProvider, OpenAICompatProvider

try:  # rich makes the output pleasant but is not load-bearing
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    _RICH = True
except ImportError:  # pragma: no cover
    _RICH = False

AGENT_KINDS = ("mock", "random", "llm")


# --------------------------------------------------------------- console glue
class _Plain:
    """A minimal stand-in for rich.Console when rich is not installed."""

    def print(self, *args: object, **_: object) -> None:
        print(*[_strip(a) for a in args])

    def rule(self, title: str = "", **_: object) -> None:
        print(f"--- {_strip(title)} ---")

    def input(self, prompt: str = "") -> str:
        return input(_strip(prompt))


def _strip(obj: object) -> str:
    return str(obj)


def _console() -> Any:
    return Console() if _RICH else _Plain()


# ------------------------------------------------------------------ providers
def build_provider(name: str, seed: int = 0) -> LLMProvider:
    """Resolve a ``--provider`` value into a concrete provider."""
    if name == "mock":
        return MockProvider(seed=seed)
    if name == "env":
        return OpenAICompatProvider(LLMConfig.from_env())
    raise ValueError(f"unknown provider {name!r} (use 'mock' or 'env')")


def make_agent_factory(
    village: str, werewolf: str, provider: LLMProvider
) -> Callable[[int, Role], Agent]:
    """Build an agent factory assigning a kind to each faction."""

    def factory(player_id: int, role: Role) -> Agent:
        kind = werewolf if role is Role.WEREWOLF else village
        if kind == "random":
            return RandomAgent(player_id)
        return LLMAgent(player_id, provider)

    return factory


# ------------------------------------------------------------------- human
class HumanAgent(Agent):
    """A seat driven by a person at the keyboard, backed by the copilot."""

    name = "human"

    def __init__(
        self, player_id: int, console: Any, copilot: LLMProvider | None = None
    ) -> None:
        super().__init__(player_id)
        self.console = console
        self.copilot = copilot

    def night_action(self, view: PlayerView) -> int:
        prompt, candidates = _night_prompt(view)
        self._banner(view, "NIGHT")
        return self._ask(view, candidates, prompt)

    def speak(self, view: PlayerView) -> str:
        self._banner(view, "DISCUSSION")
        _show_copilot(self.console, advise(view, self.copilot))
        text = self.console.input("[bold]Your statement>[/bold] " if _RICH else "Your statement> ")
        return text.strip() or "(I have nothing to say.)"

    def vote(self, view: PlayerView) -> int:
        self._banner(view, "VOTE")
        _show_copilot(self.console, advise(view, self.copilot))
        return self._ask(view, view.others_alive(), "Who do you vote to lynch?")

    def dying_shot(self, view: PlayerView) -> int:
        self._banner(view, "DYING SHOT")
        _show_copilot(self.console, advise(view, self.copilot))
        pool = view.others_alive() or list(view.living_ids)
        return self._ask(view, pool, "You are the dying Hunter — who do you shoot?")

    def witch_turn(
        self, view: PlayerView, victim: int | None, can_heal: bool, can_poison: bool
    ) -> tuple[bool, int | None]:
        self._banner(view, "WITCH")
        if victim is not None:
            self.console.print(f"  The werewolves attacked {view.name(victim)} (P{victim}).")
        else:
            self.console.print("  You sense no werewolf attack you could counter.")
        heal = False
        if can_heal and victim is not None:
            answer = self.console.input(f"  Use your HEALING potion on P{victim}? [y/N] ")
            heal = answer.strip().lower().startswith("y")
        poison: int | None = None
        if can_poison:
            answer = self.console.input(
                "  POISON potion — enter a player id to kill, or blank to skip: "
            )
            raw = answer.strip().lstrip("Pp")
            if raw.isdigit() and int(raw) in view.others_alive():
                poison = int(raw)
        return (heal, poison)

    def bid(self, view: PlayerView) -> tuple[int, str]:
        self._banner(view, "BID")
        raw = self.console.input(
            pick(view.lang, "  Bid for the floor [0-10]: ", "  为发言权竞价 [0-10]：")
        ).strip()
        priority = int(raw) if raw.isdigit() else 5
        reason = self.console.input(
            pick(view.lang, "  reason (optional)> ", "  理由（可选）> ")
        ).strip()
        return (max(0, min(10, priority)), reason)

    def _banner(self, view: PlayerView, phase: str) -> None:
        self.console.rule(f"You are {view.me_name} (P{view.me_id}) — {view.me_role.value} — {phase}")
        for note in view.private_notes:
            self.console.print(f"  • {note}")

    def _ask(self, view: PlayerView, candidates: list[int], prompt: str) -> int:
        options = ", ".join(f"P{c}={view.name(c)}" for c in candidates)
        self.console.print(prompt)
        self.console.print(f"  choices: {options}")
        while True:
            raw = self.console.input("> ").strip().lstrip("Pp")
            if raw.isdigit() and int(raw) in candidates:
                return int(raw)
            self.console.print("  invalid — enter one of the listed player ids.")


def _night_prompt(view: PlayerView) -> tuple[str, list[int]]:
    if view.me_role is Role.WEREWOLF:
        return "Choose a player for the pack to eliminate.", view.others_alive()
    if view.me_role is Role.SEER:
        return "Choose a player to inspect.", view.others_alive()
    if view.me_role is Role.DOCTOR:
        return "Choose a player to protect (you may pick yourself).", list(view.living_ids)
    return "You have no night action.", list(view.living_ids)


# ------------------------------------------------------------------ commands
def cmd_simulate(args: argparse.Namespace) -> int:
    console = _console()
    provider = build_provider(args.provider, seed=args.model_seed)
    config = GameConfig.standard(
        args.players, seed=args.seed, discussion_rounds=args.rounds, lang=args.lang,
        discussion_mode="bidding" if args.bidding else "ordered",
    )

    def factory(player_id: int, role: Role) -> Agent:
        return LLMAgent(player_id, provider)

    console.rule(f"deepwolf simulate — {args.players} players, seed {args.seed}")
    result = GameEngine(config, factory, observer=lambda e: _print_event(console, e)).run()
    _print_outcome(console, result, args.lang)
    if args.transcript:
        from deepwolf.game.transcript import save

        path = save(result, args.transcript)
        console.print(f"transcript written to {path}")
    return 0


def cmd_arena(args: argparse.Namespace) -> int:
    console = _console()
    provider = build_provider(args.provider, seed=args.model_seed)
    factory = make_agent_factory(args.villagers, args.werewolves, provider)
    arena = Arena(
        args.players,
        factory,
        n_games=args.games,
        base_seed=args.seed,
        discussion_rounds=args.rounds,
    )

    console.rule(f"deepwolf arena — {args.games} games")
    console.print(
        f"villagers: {args.villagers}   werewolves: {args.werewolves}   "
        f"provider: {args.provider}\n"
    )

    def progress(done: int, total: int) -> None:
        end = "\n" if done == total else "\r"
        print(f"  running games... {done}/{total}", end=end, flush=True)

    report = arena.run(progress=progress)
    _print_report(console, report)
    return 0


def cmd_play(args: argparse.Namespace) -> int:
    console = _console()
    config = GameConfig.standard(
        args.players, seed=args.seed, discussion_rounds=args.rounds, lang=args.lang,
        discussion_mode="bidding" if args.bidding else "ordered",
    )
    seat = args.seat if args.seat is not None else (args.seed % args.players)
    bot_provider = build_provider("mock", seed=args.seed)
    copilot = build_provider("env") if args.copilot_llm else None

    def factory(player_id: int, role: Role) -> Agent:
        if player_id == seat:
            return HumanAgent(player_id, console, copilot)
        return LLMAgent(player_id, bot_provider)

    console.rule(f"deepwolf play — you are seat P{seat}")
    console.print("Public events scroll below; your private prompts appear in panels.\n")
    try:
        result = GameEngine(
            config, factory, observer=lambda e: _print_public(console, e)
        ).run()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]game abandoned[/dim]" if _RICH else "\ngame abandoned")
        return 130
    _print_outcome(console, result, args.lang)
    won = result.winner is config_faction(result, seat)
    msg = (
        pick(args.lang, "You won!", "你赢了！")
        if won
        else pick(args.lang, "You lost.", "你输了。")
    )
    console.print(f"\n[bold]{msg}[/bold]" if _RICH else f"\n{msg}")
    return 0


def config_faction(result: GameResult, seat: int) -> Faction:
    return result.players[seat].faction  # type: ignore[attr-defined]


def cmd_leaderboard(args: argparse.Namespace) -> int:
    from deepwolf.arena.leaderboard import Leaderboard

    console = _console()

    def make_random(player_id: int) -> Agent:
        return RandomAgent(player_id)

    mock = MockProvider(seed=args.model_seed)

    def make_mock(player_id: int) -> Agent:
        return LLMAgent(player_id, mock)

    competitors: dict[str, object] = {"random": make_random, "mock-llm": make_mock}
    if args.provider == "env":
        provider = build_provider("env")

        def make_llm(player_id: int) -> Agent:
            return LLMAgent(player_id, provider)

        competitors[args.model or "llm"] = make_llm

    board = Leaderboard(
        args.players, competitors, make_random,  # type: ignore[arg-type]
        reference_name="random", n_games=args.games, base_seed=args.seed,
    )
    console.rule(f"deepwolf leaderboard — {args.games} games per side")

    def progress(done: int, total: int) -> None:
        end = "\n" if done == total else "\r"
        print(f"  evaluating competitors... {done}/{total}", end=end, flush=True)

    report = board.run(progress=progress)
    _print_leaderboard(console, report)
    if args.markdown:
        from pathlib import Path

        Path(args.markdown).write_text(report.to_markdown() + "\n", encoding="utf-8")
        console.print(f"markdown table written to {args.markdown}")
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    from deepwolf.copilot.calibration import evaluate_copilot

    console = _console()
    console.rule(f"deepwolf calibrate — {args.games} games")

    def progress(done: int, total: int) -> None:
        end = "\n" if done == total else "\r"
        print(f"  evaluating the copilot... {done}/{total}", end=end, flush=True)

    report = evaluate_copilot(
        args.players, args.games, base_seed=args.seed, progress=progress
    )
    _print_calibration(console, report)
    if args.markdown:
        from pathlib import Path

        Path(args.markdown).write_text(report.to_markdown() + "\n", encoding="utf-8")
        console.print(f"markdown report written to {args.markdown}")
    return 0


# -------------------------------------------------------------- rendering
_STYLE = {
    EventType.GAME_START: "bold cyan",
    EventType.NIGHT_FALLS: "blue",
    EventType.DAY_BREAKS: "yellow",
    EventType.DEATH_ANNOUNCED: "red",
    EventType.LYNCH: "red",
    EventType.HUNTER_SHOT: "bold red",
    EventType.QUIET_NIGHT: "green",
    EventType.SPEAK_BID: "dim cyan",
    EventType.STATEMENT: "white",
    EventType.GAME_OVER: "bold green",
}


def _print_event(console: Any, event: Event) -> None:
    """Spectator view — show everything, dimming secrets."""
    style = _STYLE.get(event.type, "dim" if not event.public else "white")
    tag = "" if event.public else "[secret] "
    if _RICH:
        console.print(f"[{style}]{tag}{event.text}[/{style}]")
    else:
        console.print(f"{tag}{event.text}")


def _print_public(console: Any, event: Event) -> None:
    """Player view — only public events reach the table."""
    if event.public:
        _print_event(console, event)


def _print_outcome(console: Any, result: GameResult, lang: str = "en") -> None:
    tr = Translator(lang)
    console.rule(pick(lang, "result", "对局结果"))
    rows = []
    for p in result.players:
        status = (
            pick(lang, "survived", "存活")
            if p.alive
            else pick(lang, f"died day {p.death_day}", f"第 {p.death_day} 天死亡")
        )
        rows.append(f"  P{p.id} {p.name:<8} {tr.role_name(p.role):<9} — {status}")
    body = "\n".join(rows)
    title = pick(
        lang,
        f"{tr.faction_label(result.winner)} win",
        f"{tr.faction_label(result.winner)}获胜",
    )
    if _RICH:
        console.print(Panel(body, title=title, border_style="green"))
    else:
        console.print(f"{title}\n{body}")


def _print_report(console: Any, report: ArenaReport) -> None:
    if not _RICH:
        console.print(report.render())  # type: ignore[attr-defined]
        return
    table = Table(title="Arena report", show_header=True, header_style="bold")
    table.add_column("metric")
    table.add_column("value", justify="right")
    table.add_row("games", str(report.n_games))
    table.add_row("village win rate", f"{report.village_win_rate:.1%}")
    table.add_row("werewolf win rate", f"{report.werewolf_win_rate:.1%}")
    table.add_row("avg game length", f"{report.avg_days:.1f} days")
    console.print(table)

    roles = Table(title="role survival", header_style="bold")
    roles.add_column("role")
    roles.add_column("survival", justify="right")
    for role, rate in report.role_survival().items():
        roles.add_row(role, f"{rate:.1%}")
    console.print(roles)

    if report.agent_stats:
        agents = Table(title="agent win rate", header_style="bold")
        agents.add_column("agent")
        agents.add_column("win rate", justify="right")
        for name, rate in report.agent_win_rate().items():
            agents.add_row(name, f"{rate:.1%}")
        console.print(agents)


def _print_leaderboard(console: Any, report: Any) -> None:
    if not _RICH:
        console.print(report.render())
        return
    table = Table(
        title=f"Leaderboard — {report.games_per_side} games/side vs '{report.reference}'",
        header_style="bold",
    )
    table.add_column("#", justify="right")
    table.add_column("agent")
    table.add_column("score", justify="right")
    table.add_column("as werewolf", justify="right")
    table.add_column("as village", justify="right")
    for rank, e in enumerate(report.entries, 1):
        table.add_row(
            str(rank), e.name, f"{e.score:.1%}",
            f"{e.werewolf_win_rate:.1%}", f"{e.village_win_rate:.1%}",
        )
    console.print(table)


def _print_calibration(console: Any, report: Any) -> None:
    if not _RICH:
        console.print(report.render())
        return
    metrics = Table(
        title=f"Copilot calibration — {report.n_games} games, "
        f"{report.n_predictions} predictions",
        header_style="bold",
    )
    metrics.add_column("metric")
    metrics.add_column("value", justify="right")
    metrics.add_row("base rate (werewolves)", f"{report.base_rate:.1%}")
    metrics.add_row("Brier score (0 = perfect)", f"{report.brier_score:.4f}")
    metrics.add_row("baseline (base-rate) Brier", f"{report.baseline_brier:.4f}")
    metrics.add_row("Brier skill score (1 = perfect)", f"{report.skill_score:.4f}")
    metrics.add_row("reliability — calibration error", f"{report.reliability:.4f}")
    metrics.add_row("resolution — discrimination", f"{report.resolution:.4f}")
    metrics.add_row("uncertainty", f"{report.uncertainty:.4f}")
    console.print(metrics)

    diagram = Table(title="reliability diagram", header_style="bold")
    diagram.add_column("predicted bin")
    diagram.add_column("mean predicted", justify="right")
    diagram.add_column("observed werewolf rate", justify="right")
    diagram.add_column("calibration gap", justify="right")
    diagram.add_column("count", justify="right")
    for b in report.bins:
        diagram.add_row(
            f"{b.low:.0%}-{b.high:.0%}",
            f"{b.mean_predicted:.1%}",
            f"{b.observed_rate:.1%}",
            f"{b.gap:+.1%}",
            str(b.count),
        )
    console.print(diagram)


def _show_copilot(console: Any, advice: Advice) -> None:
    if _RICH:
        table = Table(title="🐺 copilot — werewolf suspicion", header_style="bold")
        table.add_column("player")
        table.add_column("suspicion", justify="right")
        table.add_column("why")
        for s in advice.suspicions:
            bar = "█" * round(s.score * 10)
            table.add_row(
                f"P{s.player_id} {s.name}",
                f"{s.percent:3d}% {bar}",
                "; ".join(s.reasons),
            )
        console.print(table)
    else:
        console.print("copilot — werewolf suspicion:")
        for s in advice.suspicions:
            console.print(f"  P{s.player_id} {s.name}: {s.percent}% — {'; '.join(s.reasons)}")
    console.print(f"  recommendation: {advice.rationale}")
    if advice.llm_note:
        console.print(f"  llm note: {advice.llm_note}")


# ---------------------------------------------------------------------- main
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deepwolf",
        description="An LLM werewolf engine: self-play arena and human copilot.",
    )
    parser.add_argument("--version", action="version", version=f"deepwolf {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sim = sub.add_parser("simulate", help="watch one self-play game")
    sim.add_argument("--players", type=int, default=7)
    sim.add_argument("--seed", type=int, default=1)
    sim.add_argument("--rounds", type=int, default=1, help="discussion rounds per day")
    sim.add_argument("--provider", default="mock", help="'mock' (offline) or 'env'")
    sim.add_argument("--model-seed", type=int, default=0)
    sim.add_argument(
        "--transcript", metavar="PATH", default=None,
        help="write a JSON transcript of the game to PATH",
    )
    sim.add_argument(
        "--lang", choices=LANGUAGES, default="en",
        help="game language: en (English) or zh (中文)",
    )
    sim.add_argument(
        "--bidding", action="store_true",
        help="agents bid for the discussion floor instead of fixed order",
    )
    sim.set_defaults(func=cmd_simulate)

    arena = sub.add_parser("arena", help="benchmark agents over many games")
    arena.add_argument("--players", type=int, default=7)
    arena.add_argument("--games", type=int, default=20)
    arena.add_argument("--seed", type=int, default=0)
    arena.add_argument("--rounds", type=int, default=1)
    arena.add_argument("--provider", default="mock")
    arena.add_argument("--model-seed", type=int, default=0)
    arena.add_argument("--villagers", choices=AGENT_KINDS, default="mock")
    arena.add_argument("--werewolves", choices=AGENT_KINDS, default="mock")
    arena.set_defaults(func=cmd_arena)

    play = sub.add_parser("play", help="play a game yourself with the copilot")
    play.add_argument("--players", type=int, default=7)
    play.add_argument("--seed", type=int, default=1)
    play.add_argument("--rounds", type=int, default=1)
    play.add_argument("--seat", type=int, default=None, help="which seat you take")
    play.add_argument(
        "--copilot-llm", action="store_true",
        help="add an LLM second opinion (needs DEEPWOLF_* env vars)",
    )
    play.add_argument(
        "--lang", choices=LANGUAGES, default="en",
        help="game language: en (English) or zh (中文)",
    )
    play.add_argument(
        "--bidding", action="store_true",
        help="agents bid for the discussion floor instead of fixed order",
    )
    play.set_defaults(func=cmd_play)

    board = sub.add_parser("leaderboard", help="rank agents against a reference")
    board.add_argument("--players", type=int, default=7)
    board.add_argument("--games", type=int, default=20, help="games per side")
    board.add_argument("--seed", type=int, default=0)
    board.add_argument("--provider", default="mock", help="'mock' or 'env'")
    board.add_argument("--model-seed", type=int, default=0)
    board.add_argument(
        "--model", default=None, help="label for the --provider env competitor",
    )
    board.add_argument(
        "--markdown", metavar="PATH", default=None,
        help="also write the ranking as a Markdown table",
    )
    board.set_defaults(func=cmd_leaderboard)

    cal = sub.add_parser(
        "calibrate", help="measure how well-calibrated the copilot's probabilities are"
    )
    cal.add_argument("--players", type=int, default=7)
    cal.add_argument("--games", type=int, default=40)
    cal.add_argument("--seed", type=int, default=0)
    cal.add_argument(
        "--markdown", metavar="PATH", default=None,
        help="also write the calibration report as Markdown",
    )
    cal.set_defaults(func=cmd_calibrate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"deepwolf: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
