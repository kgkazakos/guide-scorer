"""Click CLI for guide-scorer."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from .models import LLMBackend
from .report import print_score_report
from .scorer import GuideScorer

console = Console()
_scorer = GuideScorer()


def _load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        console.print(f"[red]Error reading {path}: {exc}[/red]")
        sys.exit(1)


def _run_llm(result, text: str, backend: str, api_key: Optional[str]):
    from .llm import enrich_with_llm

    backend_enum = LLMBackend(backend)
    try:
        enrich_with_llm(result, text, backend_enum, api_key)
    except ImportError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[yellow]LLM enrichment failed: {exc}[/yellow]")


@click.group()
@click.version_option(package_name="guide-scorer")
def cli() -> None:
    """guide-scorer — Score discussion guides across 8 research quality dimensions."""


@cli.command()
@click.argument("guide_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--llm-backend",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default=None,
    help="Enable LLM narrative enrichment via DSPy.",
)
@click.option("--api-key", default=None, help="API key (overrides environment variable).")
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON.")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None, help="Write JSON to file.")
def score(
    guide_file: Path,
    llm_backend: Optional[str],
    api_key: Optional[str],
    output_json: bool,
    output: Optional[Path],
) -> None:
    """Score a single discussion GUIDE_FILE."""
    text = _load_text(guide_file)
    result = _scorer.score(text)

    if llm_backend:
        _run_llm(result, text, llm_backend, api_key)

    if output_json or output:
        data = result.to_dict()
        data["file"] = str(guide_file)
        serialised = json.dumps(data, indent=2)
        if output:
            output.write_text(serialised, encoding="utf-8")
            console.print(f"[green]Results written to {output}[/green]")
        else:
            click.echo(serialised)
    else:
        print_score_report(result, filepath=str(guide_file))


@cli.command()
@click.argument("guide_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--pattern", default="*.txt", show_default=True, help="File glob pattern.")
@click.option(
    "--llm-backend",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default=None,
    help="Enable LLM narrative enrichment via DSPy.",
)
@click.option("--api-key", default=None, help="API key (overrides environment variable).")
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON array.")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None, help="Write JSON to file.")
def batch(
    guide_dir: Path,
    pattern: str,
    llm_backend: Optional[str],
    api_key: Optional[str],
    output_json: bool,
    output: Optional[Path],
) -> None:
    """Score all guides matching PATTERN inside GUIDE_DIR."""
    files = sorted(guide_dir.glob(pattern))
    if not files:
        console.print(f"[yellow]No files matching '{pattern}' found in {guide_dir}[/yellow]")
        sys.exit(0)

    results = []
    for f in files:
        text = _load_text(f)
        result = _scorer.score(text)
        if llm_backend:
            _run_llm(result, text, llm_backend, api_key)
        results.append((f, result))

    if output_json or output:
        batch_data = []
        for f, r in results:
            d = r.to_dict()
            d["file"] = str(f)
            batch_data.append(d)
        serialised = json.dumps(batch_data, indent=2)
        if output:
            output.write_text(serialised, encoding="utf-8")
            console.print(f"[green]Results written to {output}[/green]")
        else:
            click.echo(serialised)
    else:
        # Summary table
        from rich import box
        from rich.table import Table

        table = Table(box=box.SIMPLE_HEAD, header_style="bold dim")
        table.add_column("File")
        table.add_column("Score", justify="right")
        table.add_column("Grade", justify="center")
        table.add_column("Questions", justify="right")

        grade_colors = {"A": "green", "B": "cyan", "C": "yellow", "D": "red", "F": "bright_red"}
        for f, r in results:
            gc = grade_colors.get(r.grade, "white")
            table.add_row(
                f.name,
                f"{r.overall_score:.1f}",
                f"[{gc}]{r.grade}[/{gc}]",
                str(r.question_count),
            )

        console.print(table)
        console.print(f"\n[dim]Scored {len(results)} guide(s) from {guide_dir}[/dim]")


def main() -> None:
    cli()
