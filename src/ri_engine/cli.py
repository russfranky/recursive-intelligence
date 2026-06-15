from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ri_engine.client_view import (
    build_client_summary,
    expert_mode_enabled,
    load_template,
    print_client_result,
    print_demo_summary,
    print_templates,
    print_welcome,
    template_to_metadata,
)
from ri_engine.engine import RecursiveIntelligenceEngine
from ri_engine.models import RunConfig
from ri_engine.resilient_llm import wrap_provider
from ri_engine.terminal_ui import make_console, print_run_intro
from ri_engine.visualizer import ProcessVisualizer

console = make_console()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        print_welcome(console)
        return 0

    if args.command == "templates":
        print_templates(console)
        return 0

    if args.command == "demo":
        return _run_demo(args)

    if args.command == "expert":
        return _run_expert(args)

    if args.command == "improve":
        return _run_improve(args)

    if args.command == "runbook":
        return _run_runbook(args)

    if args.command == "real-world":
        from ri_engine.real_world_test import main_prep, main_run
        if args.rw_command == "prep" or args.rw_command is None:
            return main_prep(force=getattr(args, "force", False))
        if args.rw_command == "run":
            return main_run(
                config_path=getattr(args, "config", None),
                provider=getattr(args, "provider", None),
                expert=getattr(args, "expert", False),
                quiet=getattr(args, "quiet", False),
            )
        return 0

    # Expert / internal commands
    if args.command == "improve-prompts":
        from ri_engine.improve_prompts import improve_until_converged
        summary = improve_until_converged(max_rounds=args.max_rounds)
        if expert_mode_enabled(args):
            print(f"\nDone: {summary['rounds_run']} rounds, converged={summary['converged']}")
        else:
            console.print(Panel(
                f"System tuning complete after {summary['rounds_run']} rounds.",
                title="Done",
                border_style="green",
            ))
        return 0

    if args.command == "substantial-gains":
        from ri_engine.substantial_gains import main as gains_main
        return gains_main()

    if args.command == "benchmark":
        return _run_demo(args)

    if args.command == "register-proof":
        from ri_engine.register_benchmark import main as register_main
        return register_main()

    if args.command == "pool-linguistic-registry":
        from ri_engine.pool_linguistic_registry import main as pool_main
        return pool_main()

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ri-engine",
        description="Prompt Improvement Studio — turn rough AI prompts into production-ready ones.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  ri-engine improve --seed prompt.txt --goal \"When this works, the AI will …\"\n"
            "  ri-engine improve --template code-review\n"
            "  ri-engine improve --seed prompt.txt --goal \"…\" --until-plateau --runbook\n"
            "  ri-engine demo\n"
            "  ri-engine expert benchmark\n"
            "\n"
            "Expert mode: add --expert for raw VSR report fields."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    # --- Mainstream commands ---
    sub.add_parser("templates", help="List ready-to-use prompt templates")

    improve = sub.add_parser("improve", help="Improve a prompt automatically")
    improve.add_argument(
        "--template", "-t",
        type=str,
        help="Use a ready-made template (see: ri-engine templates)",
    )
    improve.add_argument("--config", "-c", type=str, help="Path to a config file")
    improve.add_argument("--seed", "-s", type=str, help="Your starting prompt (text or .txt/.md file)")
    improve.add_argument(
        "--goal", "-g",
        type=str,
        help="What you want the prompt to achieve (required with --seed)",
    )
    improve.add_argument(
        "--rounds",
        type=int,
        default=5,
        help="How many improvement rounds to run (default: 5)",
    )
    improve.add_argument("--output", "-o", type=str, help="Save your improved prompt summary (JSON)")
    improve.add_argument(
        "--provider",
        choices=["mock", "openai", "anthropic"],
        default="mock",
        help="AI backend (default: mock — works offline, no API key)",
    )
    improve.add_argument("--quiet", "-q", action="store_true", help="Hide progress animation")
    improve.add_argument("--expert", action="store_true", help="Show technical details")
    improve.add_argument(
        "--until-plateau",
        action="store_true",
        help="Run multiple improvement cycles until fitness plateaus",
    )
    improve.add_argument(
        "--max-cycles",
        type=int,
        default=10,
        help="Max outer cycles when using --until-plateau (default: 10)",
    )
    improve.add_argument(
        "--plateau-threshold",
        type=float,
        default=0.01,
        help="Stop when fitness gain per cycle stays below this (default: 0.01)",
    )
    improve.add_argument(
        "--plateau-window",
        type=int,
        default=2,
        help="Consecutive low-gain cycles required to stop (default: 2)",
    )
    improve.add_argument(
        "--continue",
        dest="continue_session",
        action="store_true",
        help="Resume from output/improvement_session.json",
    )
    improve.add_argument(
        "--runbook",
        action="store_true",
        help="After plateau, approve the final prompt to runbook/RUNBOOK.md",
    )
    improve.add_argument(
        "--runbook-name",
        type=str,
        default="",
        help="Name for the runbook entry (default: template id or custom-prompt)",
    )
    improve.add_argument(
        "--runbook-dir",
        type=str,
        default="",
        help="Custom runbook directory (default: runbook/ at project root)",
    )
    improve.add_argument(
        "--share-traits",
        action="store_true",
        help="Export trait JSON bundle to output/traits/ (patterns only, no raw prompts)",
    )
    improve.add_argument(
        "--force-goal",
        action="store_true",
        help="Skip objective clarity kickback (expert)",
    )

    runbook = sub.add_parser("runbook", help="Browse and compile approved prompts for the next AI")
    rb_sub = runbook.add_subparsers(dest="runbook_command")
    rb_sub.add_parser("list", help="List approved runbook entries")
    rb_sub.add_parser("compile", help="Recompile runbook/RUNBOOK.md")
    rb_show = rb_sub.add_parser("show", help="Show one entry by name or id")
    rb_show.add_argument("name", type=str, help="Entry name or id")

    demo = sub.add_parser("demo", help="See proof: weak prompts improved across 6 business scenarios")
    demo.add_argument("--expert", action="store_true", help="Show technical benchmark output")

    rw = sub.add_parser("real-world", help="Prep and run a real-world production test")
    rw_sub = rw.add_subparsers(dest="rw_command")
    rw_prep = rw_sub.add_parser("prep", help="Validate system and scaffold test session")
    rw_prep.add_argument("--force", action="store_true", help="Reset active.yaml from template")
    rw_run = rw_sub.add_parser("run", help="Run the active real-world test session")
    rw_run.add_argument("--config", "-c", type=str, help="Session YAML (default: config/real_world/active.yaml)")
    rw_run.add_argument("--provider", choices=["mock", "openai", "anthropic"], help="Override session provider")
    rw_run.add_argument("--quiet", "-q", action="store_true")
    rw_run.add_argument("--expert", action="store_true")

    # --- Expert commands (hidden from casual --help via separate group) ---
    expert = sub.add_parser("expert", help="Advanced / technical commands")
    expert_sub = expert.add_subparsers(dest="expert_command")

    for name, help_text in [
        ("benchmark", "Run full use-case benchmark"),
        ("register-proof", "Plain vs Latinate register A/B proof"),
        ("pool-linguistic-registry", "Rebuild language-style registry"),
        ("macro-registry", "Show internal macro trait pool stats"),
        ("improve-prompts", "Evolve operator system prompts"),
        ("substantial-gains", "Diagnose plateau and unlock gains"),
        ("meta-recursive", "Metaprompt self-improvements then evolve two rounds"),
        ("meta-recursive-loop", "Run meta-recursive loops until plateau"),
    ]:
        p = expert_sub.add_parser(name, help=help_text)
        p.add_argument("--max-rounds", type=int, default=20)
        p.set_defaults(command=name)

    # Legacy: allow `ri-engine improve-prompts` at top level for backward compatibility
    legacy = sub.add_parser("improve-prompts", help=argparse.SUPPRESS)
    legacy.add_argument("--max-rounds", type=int, default=20)
    legacy.add_argument("--expert", action="store_true")

    for hidden in ("benchmark", "register-proof", "pool-linguistic-registry", "substantial-gains"):
        p = sub.add_parser(hidden, help=argparse.SUPPRESS)
        p.add_argument("--expert", action="store_true")
        if hidden == "improve-prompts":
            p.add_argument("--max-rounds", type=int, default=20)

    # Legacy top-level flags for backward compatibility
    parser.add_argument("--config", "-c", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--seed", "-s", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--objective", "-o", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--generations", "-g", type=int, default=5, help=argparse.SUPPRESS)
    parser.add_argument("--population", "-p", type=int, default=6, help=argparse.SUPPRESS)
    parser.add_argument("--survivors", type=int, default=2, help=argparse.SUPPRESS)
    parser.add_argument("--provider", choices=["mock", "openai", "anthropic"], default="mock", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--no-membrane", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--quiet", "-q", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-visual", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--simulate-errors", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--expert", action="store_true", help=argparse.SUPPRESS)

    return parser


def _run_expert(args: argparse.Namespace) -> int:
    cmd = getattr(args, "expert_command", None)
    if not cmd:
        console.print("[yellow]Usage: ri-engine expert <benchmark|register-proof|...>[/yellow]")
        return 1
    args.command = cmd
    args.expert = True
    if cmd == "benchmark":
        return _run_demo(args)
    if cmd == "improve-prompts":
        from ri_engine.improve_prompts import improve_until_converged
        summary = improve_until_converged(max_rounds=getattr(args, "max_rounds", 20))
        print(f"\nDone: {summary['rounds_run']} rounds, converged={summary['converged']}")
        return 0
    if cmd == "substantial-gains":
        from ri_engine.substantial_gains import main as gains_main
        return gains_main()
    if cmd == "register-proof":
        from ri_engine.register_benchmark import main as register_main
        return register_main()
    if cmd == "pool-linguistic-registry":
        from ri_engine.pool_linguistic_registry import main as pool_main
        return pool_main()
    if cmd == "macro-registry":
        return _run_macro_registry()
    if cmd == "meta-recursive":
        from ri_engine.meta_recursive import main as meta_main
        return meta_main()
    if cmd == "meta-recursive-loop":
        from ri_engine.meta_recursive import run_meta_recursive_loops
        run_meta_recursive_loops(max_loops=getattr(args, "max_rounds", 15))
        return 0
    return 1


def _finalize_client_prompt(config: RunConfig, report: dict) -> dict:
    """Produce a clean, copy-ready prompt without evolution artifacts."""
    from ri_engine.llm_provider import MockLLMProvider
    from ri_engine.prompt_synthesizer import finalize_prompt

    gate = report.get("linguistic_gate", {})
    leaning = gate.get("leaning") or config.metadata.get("linguistic_leaning", "plain")
    membrane = ""
    if config.enable_membrane_bridge:
        membrane = MockLLMProvider()._bridge(config.objective)
    report = dict(report)
    report["best_prompt"] = finalize_prompt(
        config.seed_prompt,
        config.objective,
        "constraint_first",
        membrane,
        leaning=leaning,
    )
    return report


def _check_objective_clarity(args: argparse.Namespace, config: RunConfig) -> int | None:
    """Return exit code 2 if goal is too vague; else None."""
    if getattr(args, "force_goal", False) or getattr(args, "template", None):
        return None
    if getattr(args, "continue_session", False):
        return None
    from ri_engine.objective_clarity import assess_objective

    meta = dict(config.metadata or {})
    check = assess_objective(config.objective, metadata=meta)
    if check.blocked:
        console.print("[yellow]Goal needs a clearer desired outcome[/yellow]\n")
        console.print(check.kickback_message)
        return 2
    if not check.ready:
        console.print(f"[dim]Goal clarity {check.clarity_score}/100 — proceeding; tip: start with "
                      f'"When this works, the AI will …"[/dim]\n')
    return None


def _run_improve(args: argparse.Namespace) -> int:
    expert = expert_mode_enabled(args)
    until_plateau = getattr(args, "until_plateau", False) or getattr(args, "continue_session", False)

    if until_plateau:
        return _run_improve_until_plateau(args, expert=expert)

    use_visual = not args.quiet and not expert

    try:
        config = _resolve_config(args)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    if clarity_exit := _check_objective_clarity(args, config):
        return clarity_exit

    if not expert:
        template = getattr(args, "template", "") or ""
        print_run_intro(console, template=template, rounds=getattr(args, "rounds", 5))

    from ri_engine.llm_provider import create_provider

    visualizer: ProcessVisualizer | None = None
    if use_visual:
        visualizer = ProcessVisualizer(config, provider=args.provider, simple_mode=True)
        visualizer.start()

    observer = visualizer if visualizer else None
    base_provider = create_provider(args.provider)
    llm = wrap_provider(base_provider, observer=observer)
    engine = RecursiveIntelligenceEngine(llm, observer=observer)

    try:
        report = engine.run(config)
    finally:
        if visualizer:
            visualizer.stop()

    report = _finalize_client_prompt(config, report)

    out_path = Path(args.output) if args.output else None
    if expert:
        _print_expert_report(console, report)
        if out_path:
            out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            console.print(f"\n[green]Technical report: {out_path}[/green]")
    else:
        client_path = out_path or Path("output") / "your_improved_prompt.json"
        print_client_result(console, report, output_path=client_path)

    return 0


def _run_improve_until_plateau(args: argparse.Namespace, *, expert: bool) -> int:
    from ri_engine.api import ImproveResult, improve_until_plateau
    from ri_engine.llm_provider import create_provider
    from ri_engine.terminal_ui import print_plateau_complete, print_plateau_cycle, print_run_intro

    use_visual = not args.quiet and not expert
    max_cycles = getattr(args, "max_cycles", 10)
    template_id = getattr(args, "template", "") or ""

    try:
        if getattr(args, "continue_session", False):
            seed = ""
            objective = ""
            improve_kwargs: dict = {"provider": args.provider, "template": template_id}
        else:
            config = _resolve_config(args)
            if clarity_exit := _check_objective_clarity(args, config):
                return clarity_exit
            seed = config.seed_prompt
            objective = config.objective
            improve_kwargs = {
                "provider": args.provider,
                "template": template_id,
                "max_generations": config.max_generations,
                "population_size": config.population_size,
                "survivors_count": config.survivors_count,
                "enable_membrane_bridge": config.enable_membrane_bridge,
                "metadata": config.metadata,
                "domains": config.domains,
                "fitness_weights": config.fitness_weights or None,
            }
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    if not expert:
        print_run_intro(
            console,
            template=template_id,
            rounds=max_cycles,
            mode="improve",
        )
        if getattr(args, "continue_session", False):
            console.print("[accent.dim]resuming saved session[/]")
            console.print()

    previous_fitness: float | None = None
    last_config: RunConfig | None = None

    def run_cycle(current_prompt: str) -> ImproveResult:
        nonlocal previous_fitness, last_config
        if getattr(args, "continue_session", False) and not objective:
            from ri_engine.session_state import load_session

            session = load_session(Path("output") / "improvement_session.json")
            if not session:
                raise ValueError("No session to continue")
            cfg_objective = session.objective
            cfg_meta = session.metadata
        else:
            cfg_objective = objective
            cfg_meta = improve_kwargs.get("metadata", {})

        cycle_config = RunConfig(
            seed_prompt=current_prompt,
            objective=cfg_objective,
            max_generations=improve_kwargs.get("max_generations", getattr(args, "rounds", 5)),
            population_size=improve_kwargs.get("population_size", 6),
            survivors_count=improve_kwargs.get("survivors_count", 2),
            enable_membrane_bridge=improve_kwargs.get("enable_membrane_bridge", True),
            domains=improve_kwargs.get("domains", []),
            fitness_weights=improve_kwargs.get("fitness_weights") or {},
            metadata=cfg_meta,
        )
        last_config = cycle_config

        visualizer: ProcessVisualizer | None = None
        if use_visual:
            visualizer = ProcessVisualizer(cycle_config, provider=args.provider, simple_mode=True)
            visualizer.start()

        observer = visualizer if visualizer else None
        base_provider = create_provider(args.provider)
        llm = wrap_provider(base_provider, observer=observer)
        engine = RecursiveIntelligenceEngine(llm, observer=observer)
        try:
            report = engine.run(cycle_config)
        finally:
            if visualizer:
                visualizer.stop()

        report = _finalize_client_prompt(cycle_config, report)
        return ImproveResult.from_report(report, improved_prompt=report["best_prompt"])

    def on_cycle(cycle: int, total: int, result: ImproveResult) -> None:
        nonlocal previous_fitness
        if not expert:
            print_plateau_cycle(
                console,
                cycle=cycle,
                max_cycles=total,
                fitness=result.fitness,
                previous_fitness=previous_fitness,
            )
            console.print()
        previous_fitness = result.fitness

    runbook_dir = getattr(args, "runbook_dir", "") or None
    try:
        plateau_result = improve_until_plateau(
            seed,
            objective,
            max_cycles=max_cycles,
            plateau_threshold=getattr(args, "plateau_threshold", 0.01),
            plateau_window=getattr(args, "plateau_window", 2),
            continue_from_session=getattr(args, "continue_session", False),
            approve_to_runbook=getattr(args, "runbook", False),
            runbook_name=getattr(args, "runbook_name", ""),
            runbook_dir=runbook_dir,
            share_traits=getattr(args, "share_traits", False),
            on_cycle=on_cycle,
            cycle_runner=run_cycle,
            **improve_kwargs,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    final_report = plateau_result.final.report
    if last_config:
        final_report = dict(final_report)
        final_report["best_prompt"] = plateau_result.final.improved_prompt

    out_path = Path(args.output) if args.output else None
    if expert:
        _print_expert_report(console, final_report)
        console.print(
            f"\n[bold]Plateau:[/bold] {plateau_result.cycles_run} cycles · "
            f"reason={plateau_result.plateau_reason}"
        )
        if out_path:
            out_path.write_text(json.dumps(plateau_result.to_dict(), indent=2), encoding="utf-8")
    else:
        if not expert:
            print_plateau_complete(
                console,
                cycles_run=plateau_result.cycles_run,
                plateau_reason=plateau_result.plateau_reason,
                fitness=plateau_result.final.fitness,
                runbook_path=str(plateau_result.runbook_path or ""),
            )
        if plateau_result.trait_export_path:
            console.print(f"[dim]Traits exported: {plateau_result.trait_export_path}[/dim]")
        client_path = out_path or Path("output") / "your_improved_prompt.json"
        print_client_result(console, final_report, output_path=client_path)
        if plateau_result.session_path:
            console.print(f"[dim]Session saved: {plateau_result.session_path}[/dim]")
            console.print("[dim]Resume: ri-engine improve --continue --until-plateau[/dim]")

    return 0


def _run_runbook(args: argparse.Namespace) -> int:
    from ri_engine.runbook import compile_runbook, default_runbook_dir, get_entry, list_entries
    from ri_engine.terminal_ui import print_brand_bar

    base = Path(getattr(args, "runbook_dir", "") or default_runbook_dir())
    cmd = getattr(args, "runbook_command", None) or "list"

    print_brand_bar(console, subtitle="runbook")

    if cmd == "list":
        entries = list_entries(base)
        if not entries:
            console.print("\n[muted]No approved prompts yet.[/muted]")
            console.print(
                "Run: [accent]ri-engine improve -t customer-support --until-plateau --runbook[/]"
            )
            return 0
        table = Table(show_header=True, header_style="accent", box=None)
        table.add_column("name")
        table.add_column("fitness", justify="right")
        table.add_column("cycles", justify="right")
        table.add_column("approved")
        for e in entries:
            table.add_row(e.name, f"{e.fitness:.1%}", str(e.cycles), e.approved_at[:10])
        console.print()
        console.print(table)
        compiled = base / "RUNBOOK.md"
        console.print(f"\n[dim]Compiled for next AI: {compiled}[/dim]")
        return 0

    if cmd == "compile":
        path = compile_runbook(base)
        console.print(f"\n[green]Compiled:[/green] {path}")
        return 0

    if cmd == "show":
        entry = get_entry(args.name, base)
        if not entry:
            console.print(f"[red]No entry matching {args.name!r}[/red]")
            return 1
        console.print(Panel(
            entry.prompt,
            title=f"[accent]{entry.name}[/] — {entry.fitness:.1%}",
            border_style="white",
        ))
        console.print(f"[dim]Objective:[/dim] {entry.objective}")
        return 0

    console.print("[yellow]Usage: ri-engine runbook list|show|compile[/yellow]")
    return 1


def _run_macro_registry() -> int:
    from ri_engine.macro_registry import registry_summary
    from ri_engine.terminal_ui import print_brand_bar

    print_brand_bar(console, subtitle="macro trait registry")
    summary = registry_summary()
    console.print(f"\n[dim]Path:[/dim] {summary['path']}")
    console.print(f"[dim]Objective classes:[/dim] {summary['classes']}\n")
    if not summary["entries"]:
        console.print("[muted]No macro traits recorded yet. Run improve cycles to populate.[/muted]")
        return 0
    table = Table(show_header=True, header_style="accent", box=None)
    table.add_column("class")
    table.add_column("runs", justify="right")
    table.add_column("best", justify="right")
    table.add_column("traits", justify="right")
    table.add_column("top patterns")
    for cls, info in summary["entries"].items():
        table.add_row(
            cls,
            str(info["selection_runs"]),
            f"{info['best_fitness']:.0%}",
            str(info["trait_count"]),
            ", ".join(info["top_traits"]) or "—",
        )
    console.print(table)
    return 0


def _run_demo(args: argparse.Namespace) -> int:
    from ri_engine.benchmark import run_benchmark

    if not expert_mode_enabled(args):
        print_run_intro(console, mode="demo", rounds=6)

    summary = run_benchmark(client_mode=not expert_mode_enabled(args))
    if expert_mode_enabled(args):
        return 0
    print_demo_summary(console, summary)
    return 0


def _resolve_config(args: argparse.Namespace) -> RunConfig:
    if getattr(args, "template", None):
        data = load_template(args.template)
        meta = template_to_metadata(data)
        return RunConfig(
            seed_prompt=data["seed_prompt"],
            objective=data["objective"],
            max_generations=data.get("max_generations", getattr(args, "rounds", 5)),
            population_size=data.get("population_size", 6),
            survivors_count=data.get("survivors_count", 2),
            convergence_threshold=data.get("convergence_threshold", 0.03),
            convergence_window=data.get("convergence_window", 2),
            variation_temperature=data.get("variation_temperature", 0.75),
            enable_membrane_bridge=data.get("enable_membrane_bridge", True),
            domains=data.get("domains", []),
            fitness_weights=data.get("fitness_weights", {}),
            output_path=data.get("output_path"),
            metadata=meta,
        )

    if getattr(args, "config", None):
        return RecursiveIntelligenceEngine.load_config(args.config)

    seed_arg = getattr(args, "seed", None)
    goal = getattr(args, "goal", None) or getattr(args, "objective", None)
    if seed_arg and goal:
        seed = _load_text(seed_arg)
        return RunConfig(
            seed_prompt=seed,
            objective=goal,
            max_generations=getattr(args, "rounds", None) or getattr(args, "generations", 5),
            population_size=getattr(args, "population", 6),
            survivors_count=getattr(args, "survivors", 2),
            enable_membrane_bridge=not getattr(args, "no_membrane", False),
            output_path=getattr(args, "output", None),
            metadata={"apply_linguistic_gate": True},
        )

    raise ValueError(
        "Tell us what to improve:\n"
        "  ri-engine improve --template <name>\n"
        "  ri-engine improve --config my_task.yaml\n"
        "  ri-engine improve --seed prompt.txt --goal \"What you want it to do\""
    )


def _load_text(value: str) -> str:
    path = Path(value)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return value


def _print_expert_report(console: Console, report: dict) -> None:
    table = Table(title="Fitness Trajectory")
    table.add_column("Gen", justify="right")
    table.add_column("Fitness", justify="right")
    for entry in report.get("fitness_trajectory", []):
        table.add_row(str(entry["generation"]), f"{entry['fitness']:.4f}")
    console.print(table)
    meta = report["meta"]
    status = "converged" if meta["converged"] else "max generations"
    console.print(
        f"\n[bold]Result:[/bold] {meta['generations_run']} generations ({status}) · "
        f"best fitness = {report.get('best_fitness', 0):.4f}"
    )
    if gate := report.get("linguistic_gate"):
        console.print(f"[dim]Linguistic gate: {gate}[/dim]")
    console.print(Panel(report.get("best_prompt", ""), title="Best Prompt (Technical)"))


# Backward compatibility: `ri-engine --config foo.yaml` without subcommand
def _legacy_main(argv: list[str]) -> int | None:
    """Handle legacy invocations without subcommands."""
    if not argv:
        return None
    if argv[0] in {
        "improve", "demo", "templates", "expert", "real-world", "runbook",
        "improve-prompts", "benchmark", "register-proof",
        "pool-linguistic-registry", "substantial-gains",
    }:
        return None
    if any(a.startswith("-") for a in argv[:3]) or Path(argv[0]).suffix in (".yaml", ".yml"):
        patched = ["improve"] + argv
        return main(patched)
    return None


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv:
        print_welcome(console)
        sys.exit(0)
    legacy = _legacy_main(argv)
    sys.exit(legacy if legacy is not None else main(argv))
