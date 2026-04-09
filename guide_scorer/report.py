"""Rich terminal report for guide-scorer."""
from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import DimensionResult, GuideScoreResult

console = Console()

_GRADE_COLORS = {"A": "green", "B": "cyan", "C": "yellow", "D": "red", "F": "bright_red"}
_SCORE_BAR_WIDTH = 20


def _score_bar(score: float, width: int = _SCORE_BAR_WIDTH) -> str:
    filled = int(score / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[dim]{bar}[/dim]"


def _score_color(score: float) -> str:
    if score >= 85:
        return "green"
    if score >= 70:
        return "cyan"
    if score >= 55:
        return "yellow"
    if score >= 40:
        return "red"
    return "bright_red"


def print_score_report(result: GuideScoreResult, filepath: str = "") -> None:
    """Print a formatted score report to the terminal."""
    grade_color = _GRADE_COLORS.get(result.grade, "white")
    score_color = _score_color(result.overall_score)

    # --- Header panel ---
    header_lines = []
    if filepath:
        header_lines.append(f"[dim]File:[/dim] {filepath}")
    header_lines.append(
        f"[bold]Overall Score:[/bold] "
        f"[{score_color}]{result.overall_score:.1f}/100[/{score_color}]  "
        f"Grade: [{grade_color}][bold]{result.grade}[/bold][/{grade_color}]"
    )
    header_lines.append(
        f"[dim]Questions: {result.question_count}  ·  "
        f"Probes: {result.probe_count}  ·  "
        f"Sections: {result.section_count}"
        + (f"  ·  Session: {result.session_minutes} min" if result.session_minutes else "")
        + "[/dim]"
    )

    console.print(
        Panel(
            "\n".join(header_lines),
            title="[bold]guide-scorer[/bold]",
            border_style="dim",
            padding=(0, 2),
        )
    )

    # --- Narrative (LLM) ---
    if result.narrative:
        console.print(
            Panel(
                f"[italic]{result.narrative}[/italic]",
                title="[dim]LLM Narrative[/dim]",
                border_style="dim blue",
                padding=(0, 2),
            )
        )

    # --- Dimensions table ---
    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold dim",
        padding=(0, 1),
    )
    table.add_column("Dimension", min_width=22)
    table.add_column("Score", justify="right", min_width=7)
    table.add_column("Weight", justify="right", min_width=7)
    table.add_column("Bar", min_width=22)
    table.add_column("Issues", min_width=8, justify="right")

    for dim in result.dimensions:
        color = _score_color(dim.score)
        table.add_row(
            dim.name,
            f"[{color}]{dim.score:.0f}[/{color}]",
            f"{int(dim.weight * 100)}%",
            _score_bar(dim.score),
            str(len(dim.issues)) if dim.issues else "[green]–[/green]",
        )

    console.print(table)

    # --- Per-dimension details ---
    for dim in result.dimensions:
        _print_dimension_detail(dim)


def _print_dimension_detail(dim: DimensionResult) -> None:
    color = _score_color(dim.score)
    lines: list[str] = []

    if dim.rationale:
        lines.append(f"[italic dim]{dim.rationale}[/italic dim]")

    if dim.issues:
        lines.append("[yellow]Issues:[/yellow]")
        for issue in dim.issues:
            lines.append(f"  [yellow]▸[/yellow] {issue}")

    if dim.suggestions:
        lines.append("[cyan]Suggestions:[/cyan]")
        for sug in dim.suggestions:
            lines.append(f"  [cyan]→[/cyan] {sug}")

    if not lines:
        return

    console.print(
        Panel(
            "\n".join(lines),
            title=f"[{color}]{dim.name}[/{color}] [{color}]{dim.score:.0f}/100[/{color}]",
            border_style="dim",
            padding=(0, 2),
        )
    )
