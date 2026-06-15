from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from rich.align import Align
from rich.box import MINIMAL, ROUNDED, SIMPLE
from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from ri_engine.events import EventKind, RunEvent
from ri_engine.models import RunConfig
from ri_engine.terminal_ui import BRAND, hint_bar, make_console, phase_quip


PHASES = ("membrane", "variation", "selection", "retention", "converge")
PHASE_LABELS_EXPERT = {
    "membrane": "Membrane Bridge",
    "variation": "Variation",
    "selection": "Selection",
    "retention": "Retention",
    "converge": "Convergence",
}
PHASE_LABELS_SIMPLE = {
    "membrane": "Fresh ideas",
    "variation": "New versions",
    "selection": "Pick the best",
    "retention": "Keep winners",
    "converge": "Finish up",
}
PHASE_LABELS = PHASE_LABELS_EXPERT


@dataclass
class VisualState:
    generation: int = 0
    max_generations: int = 1
    phase: str = "init"
    phase_progress: float = 0.0
    overall_progress: float = 0.0
    best_fitness: float = 0.0
    fitness_delta: float = 0.0
    population_size: int = 0
    survivors_count: int = 0
    variants_done: int = 0
    variants_total: int = 0
    eliminated: int = 0
    retries: int = 0
    errors: int = 0
    warnings: int = 0
    learnings: deque[str] = field(default_factory=lambda: deque(maxlen=8))
    issues: deque[str] = field(default_factory=lambda: deque(maxlen=8))
    agent_tasks: deque[str] = field(default_factory=lambda: deque(maxlen=6))
    event_log: deque[tuple[str, str, str]] = field(default_factory=lambda: deque(maxlen=40))
    fitness_history: list[float] = field(default_factory=list)
    active_agent: str = ""
    provider: str = "mock"
    converged: bool = False
    pulse: int = 0
    status_quip: str = ""


class ProcessVisualizer:
    """Real-time progress display — friendly by default, technical in expert mode."""

    def __init__(
        self,
        config: RunConfig,
        provider: str = "mock",
        *,
        simple_mode: bool = True,
    ) -> None:
        self.config = config
        self.simple_mode = simple_mode
        self.console = make_console()
        self.state = VisualState(
            max_generations=config.max_generations,
            population_size=config.population_size,
            survivors_count=config.survivors_count,
            variants_total=config.population_size,
            provider=provider,
        )
        self._live: Live | None = None
        self._tick = 0
        self._started = time.monotonic()

    def start(self) -> None:
        self._live = Live(
            self.render(),
            console=self.console,
            refresh_per_second=10,
            transient=False,
        )
        self._live.start()

    def stop(self) -> None:
        if self._live:
            self._live.stop()
            self._live = None
        self.console.print()
        self.console.print(self.render_summary())

    def refresh(self) -> None:
        self._tick += 1
        self.state.pulse = self._tick % 4
        if self._live:
            self._live.update(self.render())

    def on_event(self, event: RunEvent) -> None:
        self._apply_event(event)
        self.refresh()

    def _phase_labels(self) -> dict[str, str]:
        return PHASE_LABELS_SIMPLE if self.simple_mode else PHASE_LABELS_EXPERT

    def _apply_event(self, event: RunEvent) -> None:
        s = self.state
        kind = event.kind
        msg = event.message

        if event.progress is not None:
            s.overall_progress = event.progress
        if event.generation:
            s.generation = event.generation
        if event.phase:
            s.phase = event.phase

        icon, style = self._event_style(kind)
        if kind == EventKind.INFO and self.simple_mode and "linguistic gate" in msg.lower():
            leaning = event.data.get("leaning", "")
            friendly = {
                "plain": "Using clear, everyday language",
                "conversational": "Using a friendly, natural tone",
                "latinate": "Using formal professional tone",
                "mixed": "Plain words + expert terms where needed",
                "technical": "Using specialist vocabulary",
                "neutral": "Optimizing for clarity",
            }.get(leaning, "Matched best writing style for your task")
            self._log("✓", "green", friendly)
        else:
            self._log(icon, style, msg)

        if kind == EventKind.RUN_START:
            s.phase = "init"
            s.overall_progress = 0.0

        elif kind == EventKind.GENERATION_START:
            s.phase = "membrane" if self.config.enable_membrane_bridge and s.generation > 1 else "variation"
            s.variants_done = 0
            s.eliminated = 0
            s.phase_progress = 0.0

        elif kind == EventKind.PHASE_START:
            s.phase = event.phase
            s.phase_progress = 0.0
            s.active_agent = event.data.get("agent", self._phase_labels().get(event.phase, event.phase))
            if self.simple_mode:
                s.status_quip = phase_quip(event.phase, seed=s.generation)

            if event.phase == "variation":
                s.variants_done = 0
                s.variants_total = event.data.get("total", s.variants_total)

        elif kind == EventKind.PHASE_COMPLETE:
            s.phase_progress = 100.0

        elif kind == EventKind.AGENT_TASK:
            task = event.data.get("task", msg)
            s.active_agent = event.data.get("agent", s.active_agent)
            s.agent_tasks.appendleft(task)

        elif kind == EventKind.VARIANT_SPAWN:
            s.agent_tasks.appendleft(f"mutate · {event.data.get('strategy', '?')}")

        elif kind == EventKind.VARIANT_COMPLETE:
            s.variants_done += 1
            pct = s.variants_done / max(s.variants_total, 1) * 100
            s.phase_progress = pct
            self._update_overall(event)

        elif kind == EventKind.VARIANT_FALLBACK:
            s.warnings += 1
            s.issues.appendleft(msg)

        elif kind == EventKind.SCORE:
            fitness = event.data.get("fitness")
            if fitness is not None:
                prev = s.best_fitness
                if fitness > s.best_fitness:
                    s.fitness_delta = fitness - prev
                    s.best_fitness = fitness

        elif kind == EventKind.ELIMINATE:
            s.eliminated += 1

        elif kind == EventKind.SURVIVE:
            fitness = event.data.get("fitness", 0)
            if fitness >= s.best_fitness:
                s.best_fitness = fitness

        elif kind == EventKind.LEARNING:
            s.learnings.appendleft(msg)

        elif kind == EventKind.MEMBRANE:
            s.learnings.appendleft(f"⬡ {msg[:90]}")

        elif kind == EventKind.RETRY:
            s.retries += 1
            s.issues.appendleft(msg)

        elif kind == EventKind.ERROR:
            s.errors += 1
            s.issues.appendleft(msg)

        elif kind == EventKind.WARNING:
            s.warnings += 1
            s.issues.appendleft(msg)

        elif kind == EventKind.CONVERGENCE:
            s.converged = event.data.get("converged", False)
            s.phase = "converge"

        elif kind == EventKind.GENERATION_COMPLETE:
            fitness = event.data.get("best_fitness")
            if fitness is not None:
                s.fitness_history.append(fitness)
                s.best_fitness = fitness
            self._update_overall(event)

        elif kind == EventKind.RUN_COMPLETE:
            s.overall_progress = 100.0
            s.phase = "done"
            if self.simple_mode:
                s.status_quip = phase_quip("done", seed=s.generation)

    def _update_overall(self, event: RunEvent) -> None:
        if event.progress is not None:
            self.state.overall_progress = event.progress
        else:
            gen = max(self.state.generation, 1)
            phase_idx = PHASES.index(self.state.phase) if self.state.phase in PHASES else 0
            phase_frac = (phase_idx + self.state.phase_progress / 100) / len(PHASES)
            self.state.overall_progress = min(
                99.0,
                ((gen - 1) + phase_frac) / self.state.max_generations * 100,
            )

    def _log(self, icon: str, style: str, msg: str) -> None:
        short = msg if len(msg) <= 72 else msg[:69] + "…"
        self.state.event_log.appendleft((icon, style, short))

    @staticmethod
    def _event_style(kind: EventKind) -> tuple[str, str]:
        mapping = {
            EventKind.RUN_START: ("▶", "bold cyan"),
            EventKind.RUN_COMPLETE: ("✓", "bold green"),
            EventKind.GENERATION_START: ("◎", "bold blue"),
            EventKind.GENERATION_COMPLETE: ("◉", "blue"),
            EventKind.PHASE_START: ("→", "cyan"),
            EventKind.PHASE_COMPLETE: ("←", "dim cyan"),
            EventKind.AGENT_TASK: ("⚙", "white"),
            EventKind.VARIANT_SPAWN: ("+", "dim white"),
            EventKind.VARIANT_COMPLETE: ("·", "dim green"),
            EventKind.VARIANT_FALLBACK: ("⚠", "yellow"),
            EventKind.SCORE: ("%", "magenta"),
            EventKind.ELIMINATE: ("✕", "red"),
            EventKind.SURVIVE: ("♦", "green"),
            EventKind.LEARNING: ("◈", "bright_blue"),
            EventKind.MEMBRANE: ("⬡", "bright_cyan"),
            EventKind.RETRY: ("↻", "yellow"),
            EventKind.ERROR: ("✗", "bold red"),
            EventKind.WARNING: ("!", "yellow"),
            EventKind.CONVERGENCE: ("≈", "bright_green"),
            EventKind.INFO: ("·", "dim"),
        }
        return mapping.get(kind, ("·", "dim"))

    def render(self) -> Layout:
        if self.simple_mode:
            return self._render_stream_layout()
        return self._render_dashboard_layout()

    def _render_stream_layout(self) -> Layout:
        """Grok-inspired: brand bar, live stream, slim stats, footer quip."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="stream"),
            Layout(name="stats", size=3),
            Layout(name="footer", size=3),
        )
        layout["header"].update(self._stream_header())
        layout["stream"].update(self._event_stream())
        layout["stats"].update(self._stream_stats())
        layout["footer"].update(self._stream_footer())
        return layout

    def _render_dashboard_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
        layout["body"].split_row(
            Layout(name="left", ratio=3),
            Layout(name="right", ratio=2),
        )
        layout["left"].split_column(
            Layout(name="pipeline", size=5),
            Layout(name="stream"),
        )
        layout["right"].split_column(
            Layout(name="stats", size=14),
            Layout(name="learnings", size=10),
            Layout(name="issues", size=10),
        )

        layout["header"].update(self._header())
        layout["pipeline"].update(self._pipeline())
        layout["stream"].update(self._event_stream())
        layout["stats"].update(self._stats_panel())
        layout["learnings"].update(self._learnings_panel())
        layout["issues"].update(self._issues_panel())
        layout["footer"].update(self._footer())
        return layout

    def _stream_header(self) -> Panel:
        s = self.state
        elapsed = time.monotonic() - self._started
        title = Text.assemble(
            (BRAND, "brand"),
            ("  ·  ", "muted"),
            (f"round {s.generation}/{s.max_generations}", "accent"),
            ("  ·  ", "muted"),
            (f"{elapsed:.0f}s", "muted"),
        )
        bar = Progress(
            SpinnerColumn(style="white"),
            BarColumn(bar_width=48, complete_style="white", finished_style="success"),
            TaskProgressColumn(),
            expand=True,
        )
        bar.add_task("evolving", total=100, completed=s.overall_progress)
        return Panel(Group(title, bar), box=MINIMAL, border_style="white", padding=(0, 1))

    def _stream_stats(self) -> Panel:
        s = self.state
        line = Text.assemble(
            ("quality ", "muted"),
            (f"{s.best_fitness:.0%}" if s.best_fitness else "—", "success"),
            ("  ·  ", "muted"),
            ("versions ", "muted"),
            (f"{s.variants_done}/{s.variants_total}", "prompt"),
            ("  ·  ", "muted"),
            ("culled ", "muted"),
            (str(s.eliminated), "warn" if s.eliminated else "muted"),
        )
        if s.fitness_history:
            line.append("  ·  ", style="muted")
            line.append(self._sparkline(s.fitness_history), style="accent.dim")
        return Panel(line, box=MINIMAL, border_style="dim white", padding=(0, 1))

    def _stream_footer(self) -> Panel:
        s = self.state
        quip = Text(s.status_quip or phase_quip(s.phase, seed=s.generation), style="quip")
        hints = hint_bar(["Ctrl+C: stop", "--quiet", "--expert"])
        return Panel(Group(quip, hints), box=MINIMAL, border_style="dim white", padding=(0, 1))

    def _header(self) -> Panel:
        s = self.state
        elapsed = time.monotonic() - self._started
        if self.simple_mode:
            title = Text("Prompt Improvement Studio", style="bold")
            subtitle = Text.assemble(
                ("Improving your prompt", "dim"),
                ("  ·  ", "dim"),
                (f"round {s.generation}/{s.max_generations}", "cyan"),
                ("  ·  ", "dim"),
                (f"{elapsed:.0f}s", "dim"),
            )
            task_label = "progress"
        else:
            title = Text("Recursive Intelligence Engine", style="bold")
            subtitle = Text.assemble(
                ("Variation → Selection → Retention", "dim"),
                ("  ·  ", "dim"),
                (f"gen {s.generation}/{s.max_generations}", "cyan"),
                ("  ·  ", "dim"),
                (f"{s.provider}", "dim italic"),
                ("  ·  ", "dim"),
                (f"{elapsed:.1f}s", "dim"),
            )
            task_label = "evolution"
        bar = Progress(
            SpinnerColumn(style="cyan"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40, complete_style="cyan", finished_style="green"),
            TaskProgressColumn(),
            expand=True,
        )
        bar.add_task(task_label, total=100, completed=s.overall_progress)
        return Panel(
            Group(Align.center(title), Align.center(subtitle), bar),
            box=ROUNDED,
            border_style="dim cyan",
        )

    def _pipeline(self) -> Panel:
        s = self.state
        labels = self._phase_labels()
        dots = [" ", "·", "∙", "●"]
        pulse = dots[s.pulse]

        cells = []
        for phase in PHASES:
            label = labels[phase]
            if s.phase == phase:
                cells.append(Text(f" {pulse} {label} ", style="bold cyan reverse"))
            elif phase in PHASES[: PHASES.index(s.phase)] if s.phase in PHASES else False:
                cells.append(Text(f" ✓ {label} ", style="dim green"))
            else:
                cells.append(Text(f"   {label} ", style="dim"))

        pipeline = Text.assemble(*[c for pair in zip(cells, [Text(" → ", style="dim")] * len(cells)) for c in pair][:-1])

        phase_bar = Progress(
            TextColumn("[dim]{task.description}"),
            BarColumn(bar_width=30, complete_style="blue", finished_style="green"),
            TaskProgressColumn(),
            expand=True,
        )
        phase_bar.add_task(
            labels.get(s.phase, s.phase),
            total=100,
            completed=s.phase_progress,
        )

        agent_line = Text()
        if s.active_agent:
            agent_line = Text.assemble(("agent: ", "dim"), (s.active_agent, "italic white"))

        return Panel(
            Group(pipeline, phase_bar, agent_line),
            title="Improvement Steps" if self.simple_mode else "VSR Pipeline",
            border_style="dim",
            box=ROUNDED,
        )

    def _event_stream(self) -> Panel:
        rows = Table(show_header=False, box=SIMPLE, padding=(0, 1), expand=True)
        rows.add_column("log", ratio=1)

        for icon, style, msg in list(self.state.event_log)[:18]:
            rows.add_row(Text.assemble((f"{icon} ", style), (msg, "dim white")))

        if not self.state.event_log:
            rows.add_row(Text("awaiting events…", style="dim italic"))

        return Panel(rows, title="live" if self.simple_mode else "Live Process Stream", border_style="dim white" if self.simple_mode else "dim", box=MINIMAL if self.simple_mode else ROUNDED)

    def _stats_panel(self) -> Panel:
        s = self.state
        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("k", style="dim")
        table.add_column("v")

        cull_pct = (s.eliminated / max(s.population_size, 1)) * 100
        variant_pct = (s.variants_done / max(s.variants_total, 1)) * 100
        survive_pct = (s.survivors_count / max(s.population_size, 1)) * 100

        table.add_row("quality score" if self.simple_mode else "best fitness", f"[green]{s.best_fitness:.1%}[/]" if s.best_fitness else "—")
        table.add_row("improvement" if self.simple_mode else "Δ fitness", f"[cyan]+{s.fitness_delta:.1%}[/]" if s.fitness_delta else "—")
        table.add_row("versions tried" if self.simple_mode else "variants", f"{s.variants_done}/{s.variants_total}  [dim]({variant_pct:.0f}%)[/]")
        table.add_row("ruled out" if self.simple_mode else "eliminated", f"[red]{s.eliminated}[/]  [dim]({cull_pct:.0f}%)[/]")
        table.add_row("kept" if self.simple_mode else "survivors", f"[green]{s.survivors_count}[/]  [dim]({survive_pct:.0f}%)[/]")
        table.add_row("retries", f"[yellow]{s.retries}[/]" if s.retries else "0")
        table.add_row("errors", f"[red]{s.errors}[/]" if s.errors else "0")
        table.add_row("warnings", f"[yellow]{s.warnings}[/]" if s.warnings else "0")

        if s.fitness_history:
            spark = self._sparkline(s.fitness_history)
            table.add_row("trajectory", spark)

        return Panel(table, title="Your Results" if self.simple_mode else "Metrics", border_style="dim", box=ROUNDED)

    def _learnings_panel(self) -> Panel:
        lines = [Text(f"◈ {ln}", style="bright_blue") for ln in list(self.state.learnings)[:5]]
        body: RenderableType = Group(*lines) if lines else Text("no learnings yet", style="dim italic")
        return Panel(body, title="Improvements Made" if self.simple_mode else "Lineage Learnings", border_style="dim blue", box=ROUNDED)

    def _issues_panel(self) -> Panel:
        lines = []
        for item in list(self.state.issues)[:5]:
            style = "yellow" if "retry" in item.lower() else "red"
            lines.append(Text(f"! {item}", style=style))
        body: RenderableType = Group(*lines) if lines else Text("no issues", style="dim green")
        return Panel(body, title="Issues · Retries · Failures", border_style="dim", box=ROUNDED)

    def _footer(self) -> Panel:
        s = self.state
        tasks = list(s.agent_tasks)[:4]
        task_cols = Columns(
            [Text(f"⚙ {t}", style="dim") for t in tasks] or [Text("idle", style="dim italic")],
            expand=True,
        )
        labels = self._phase_labels()
        status = "Done improving" if s.converged and self.simple_mode else (
            "converged" if s.converged else labels.get(s.phase, s.phase)
        )
        return Panel(
            Group(
                task_cols,
                Align.center(Text(f"status: {status}  ·  {s.overall_progress:.0f}% complete", style="dim")),
            ),
            box=SIMPLE,
            border_style="dim",
        )

    def render_summary(self) -> Panel:
        s = self.state
        elapsed = time.monotonic() - self._started
        if self.simple_mode:
            lines = [
                Text.assemble(("quality ", "muted"), (f"{s.best_fitness:.0%}", "success")),
                Text.assemble(("rounds ", "muted"), (f"{s.generation}/{s.max_generations}", "prompt")),
                Text.assemble(("time ", "muted"), (f"{elapsed:.0f}s", "prompt")),
                Text(phase_quip("done", seed=s.generation), style="quip"),
            ]
            if s.fitness_history:
                lines.insert(3, Text.assemble(("trajectory ", "muted"), (self._sparkline(s.fitness_history), "accent.dim")))
            return Panel(Group(*lines), title=f"{BRAND} · complete", border_style="white", box=MINIMAL)
        lines = [
            f"Generations: {s.generation}/{s.max_generations}",
            f"Best fitness: {s.best_fitness:.1%}",
            f"Eliminated: {s.eliminated} variants · Retries: {s.retries} · Errors: {s.errors}",
            f"Learnings captured: {len(s.learnings)}",
            f"Elapsed: {elapsed:.1f}s · {'converged' if s.converged else 'completed'}",
        ]
        if s.fitness_history:
            lines.append(f"Progress: {self._sparkline(s.fitness_history)}")
        return Panel("\n".join(lines), title="Run Complete", border_style="green", box=ROUNDED)

    @staticmethod
    def _sparkline(values: list[float], width: int = 24) -> str:
        if not values:
            return ""
        chars = "▁▂▃▄▅▆▇█"
        mn, mx = min(values), max(values)
        span = mx - mn or 1e-9
        sampled = values[-width:]
        return "".join(chars[min(int((v - mn) / span * (len(chars) - 1)), len(chars) - 1)] for v in sampled)
