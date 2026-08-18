"""unix-compound CLI — terminal plugin for ri-engine.

Commands:
  unix-compound start "domain"
  unix-compound lock
  unix-compound step
  unix-compound run
  unix-compound sidecar
  unix-compound status
  unix-compound export
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ri_engine.terminal_ui import hint_bar, make_console, print_brand_bar
from ri_engine.unix_compound import (
    PLUGIN_VERSION,
    load_session,
    lock_goal,
    propose_again,
    render_sequence_block,
    render_sidecar,
    render_success_block,
    run_until_idle,
    save_session,
    start,
    step,
)


def _console() -> Console:
    return make_console()


def _session_path(args: argparse.Namespace) -> Path | None:
    if getattr(args, "session", None):
        return Path(args.session)
    return None


def _need_session(args: argparse.Namespace):
    session = load_session(_session_path(args))
    if session is None:
        raise FileNotFoundError(
            'No session. Start one: unix-compound start "your domain"'
        )
    return session


def _print_state(console: Console, session) -> None:
    print_brand_bar(console, subtitle="unix-compound", right=f"v{PLUGIN_VERSION}")
    console.print()
    console.print(Panel(render_sidecar(session), title="sidecar", border_style="white"))
    block = render_success_block(session)
    if block:
        console.print(Panel(block, title="goal", border_style="cyan"))
    seq = render_sequence_block(session)
    if seq:
        console.print(Panel(seq, title="sequence", border_style="cyan"))
    if session.baseline and session.decision == "terminate":
        b = session.baseline
        console.print(
            f"[dim]baseline:[/dim] oneshot={b.get('fitness')}  "
            f"modular={b.get('modular_fitness')}  winner={b.get('winner')}"
        )
    console.print()
    console.print(hint_bar([
        "start:new",
        "lock:confirm goal",
        "step:one phase",
        "run:until idle",
        "sidecar:print only",
    ]))


def cmd_start(args: argparse.Namespace) -> int:
    console = _console()
    domain = (args.domain or "").strip()
    if not domain:
        console.print('[red]Need a domain.[/red] Example: unix-compound start "daily operating system ≤15 min"')
        return 1
    session = start(domain, path=_session_path(args))
    if args.lock:
        session = lock_goal(session, path=_session_path(args))
        if args.run:
            session = run_until_idle(session, path=_session_path(args))
    _print_state(console, session)
    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    console = _console()
    try:
        session = _need_session(args)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    if args.edit:
        session.criteria = []
        from ri_engine.unix_compound import Criterion
        for line in args.edit:
            session.criteria.append(Criterion(text=line.strip()))
    session = lock_goal(session, provisional=bool(args.provisional), path=_session_path(args))
    if args.run:
        session = run_until_idle(session, path=_session_path(args))
    _print_state(console, session)
    return 0


def cmd_propose(args: argparse.Namespace) -> int:
    console = _console()
    try:
        session = _need_session(args)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    session = propose_again(session, path=_session_path(args))
    _print_state(console, session)
    return 0


def cmd_step(args: argparse.Namespace) -> int:
    console = _console()
    try:
        session = _need_session(args)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    if session.phase == "goal" and not session.goal_locked:
        console.print("[yellow]Goal is not locked.[/yellow] Run: unix-compound lock")
        _print_state(console, session)
        return 2
    session = step(session, path=_session_path(args))
    _print_state(console, session)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    console = _console()
    try:
        session = _need_session(args)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    if session.phase == "goal" and not session.goal_locked:
        if args.yes or args.lock:
            session = lock_goal(session, path=_session_path(args))
        else:
            console.print("[yellow]Goal is not locked.[/yellow] Re-run with --yes to lock proposed criteria.")
            _print_state(console, session)
            return 2
    session = run_until_idle(session, max_steps=args.max_steps, path=_session_path(args))
    _print_state(console, session)
    return 0


def cmd_sidecar(args: argparse.Namespace) -> int:
    console = _console()
    try:
        session = _need_session(args)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(render_sidecar(session))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    console = _console()
    try:
        session = _need_session(args)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    if args.json:
        print(json.dumps({
            "phase": session.phase,
            "decision": session.decision,
            "goal_locked": session.goal_locked,
            "goal_progress": list(session.goal_progress()),
            "coverage": session.coverage(),
            "modules": [m.name for m in session.modules],
            "residuals": session.residuals,
        }, indent=2))
        return 0
    _print_state(console, session)
    table = Table(title="modules", box=None, show_header=True, header_style="accent")
    table.add_column("status")
    table.add_column("name")
    table.add_column("fitness", justify="right")
    table.add_column("purpose")
    for m in session.modules:
        fit = f"{m.fitness:.2f}" if m.fitness is not None else "—"
        table.add_row(m.status, m.name, fit, m.purpose)
    if session.modules:
        console.print()
        console.print(table)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    console = _console()
    try:
        session = _need_session(args)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    dest = Path(args.output) if args.output else Path("output") / "unix-compound-export.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    save_session(session, dest)
    console.print(f"[green]exported[/green] {dest}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--session",
        type=str,
        help="Session JSON path (default: output/unix-compound-session.json)",
    )
    parser = argparse.ArgumentParser(
        prog="unix-compound",
        description="Recursive modular process: goal → skeleton → sequence? → build → check → sidecar → next",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parent],
        epilog=(
            "Examples:\n"
            "  unix-compound start \"daily operating system ≤15 min\"\n"
            "  unix-compound lock --run\n"
            "  unix-compound start \"clean up my prompt library\" --lock --run\n"
            "  ri-engine compound start \"help me get healthier\" --lock --run\n"
        ),
    )
    sub = parser.add_subparsers(dest="command")

    start_p = sub.add_parser("start", help="Start a new run from a domain", parents=[parent])
    start_p.add_argument("domain", nargs="?", default="", help="Domain to decompose")
    start_p.add_argument("--lock", action="store_true", help="Lock proposed criteria immediately")
    start_p.add_argument("--run", action="store_true", help="After lock, run until idle")

    lock_p = sub.add_parser("lock", help="Lock proposed success criteria", parents=[parent])
    lock_p.add_argument("--provisional", action="store_true", help="Mark as provisional lock")
    lock_p.add_argument("--run", action="store_true", help="Run the rest of the process after lock")
    lock_p.add_argument("--edit", action="append", help="Replace criteria (repeatable)")

    sub.add_parser("propose", help="Propose a new criteria set (auto-locks as provisional on 2nd try)", parents=[parent])
    sub.add_parser("step", help="Advance one process phase", parents=[parent])

    run_p = sub.add_parser("run", help="Run until terminate or human lock required", parents=[parent])
    run_p.add_argument("--yes", "-y", action="store_true", help="Lock proposed criteria if still open")
    run_p.add_argument("--lock", action="store_true", help="Same as --yes")
    run_p.add_argument("--max-steps", type=int, default=40)

    sub.add_parser("sidecar", help="Print only the terminal markdown sidecar", parents=[parent])
    status_p = sub.add_parser("status", help="Show current session", parents=[parent])
    status_p.add_argument("--json", action="store_true")

    export_p = sub.add_parser("export", help="Write session JSON", parents=[parent])
    export_p.add_argument("-o", "--output", type=str, default="")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        print_brand_bar(_console(), subtitle="unix-compound", right=f"v{PLUGIN_VERSION}")
        _console().print()
        _console().print("start a domain, lock success, then run.")
        _console().print()
        _console().print(hint_bar([
            'start "daily OS ≤15 min"',
            "lock --run",
            "sidecar",
        ]))
        return 0
    dispatch = {
        "start": cmd_start,
        "lock": cmd_lock,
        "propose": cmd_propose,
        "step": cmd_step,
        "run": cmd_run,
        "sidecar": cmd_sidecar,
        "status": cmd_status,
        "export": cmd_export,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
