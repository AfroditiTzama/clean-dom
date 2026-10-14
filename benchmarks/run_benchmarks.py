"""Run local clean-dom benchmarks against the committed synthetic fixtures."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Callable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from benchmarks.semantics import (
    evaluate_semantic_retention,
    expectations_for_variant,
)
from clean_dom import DOMCleaner

FIXTURE_DIR = PROJECT_ROOT / "benchmarks" / "fixtures"
MANIFEST_PATH = PROJECT_ROOT / "benchmarks" / "fixtures.json"

CleanerFactory = Callable[[], DOMCleaner]

VARIANTS: dict[str, CleanerFactory] = {
    "default": DOMCleaner,
    "agent": lambda: DOMCleaner.preset("agent"),
    "deduplication": lambda: DOMCleaner(deduplicate_repeated_sections=True),
}


def _percentile(values: Sequence[float], percentile: float) -> float:
    """Return the nearest-rank percentile for a non-empty sample."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def _load_fixtures(selected: Sequence[str]) -> list[tuple[dict, str]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = {entry["filename"]: entry for entry in manifest}
    filenames = selected or list(entries)
    fixtures = []
    for filename in filenames:
        if filename not in entries:
            raise ValueError(f"Unknown fixture: {filename}")
        path = FIXTURE_DIR / filename
        fixtures.append((entries[filename], path.read_text(encoding="utf-8")))
    return fixtures


def _run_variant(
    html: str,
    cleaner_factory: CleanerFactory,
    iterations: int,
    expectations: dict,
    fixture_filename: str,
    variant: str,
) -> dict[str, float | int | str]:
    cleaner = cleaner_factory()
    # Warm tokenizer and parser paths outside the timed samples.
    cleaner.clean_with_report(html, tokenizer="tiktoken")

    elapsed_seconds = []
    result = None
    for _ in range(iterations):
        started = time.perf_counter()
        result = cleaner.clean_with_report(html, tokenizer="tiktoken")
        elapsed_seconds.append(time.perf_counter() - started)

    assert result is not None
    stats = result.stats
    assert stats.input_tokens is not None
    assert stats.output_tokens is not None
    semantic_metrics = evaluate_semantic_retention(result.cleaned_html, expectations)
    missing = semantic_metrics["missing_semantics"]
    if missing:
        raise ValueError(
            f"{fixture_filename} / {variant} lost required semantics: "
            + "; ".join(missing)
            + f". {expectations.get('notes', '')}"
        )
    return {
        "raw_chars": stats.input_chars,
        "cleaned_chars": stats.output_chars,
        "char_reduction_percent": stats.char_reduction_percent,
        "raw_tokens": stats.input_tokens,
        "cleaned_tokens": stats.output_tokens,
        "token_reduction_percent": stats.token_reduction_percent or 0.0,
        "semantic_retention_percent": semantic_metrics["semantic_retention_percent"],
        "required_counts": (
            "{required_text_preserved}/{required_text_total} text, "
            "{required_href_preserved}/{required_href_total} href, "
            "{required_attributes_preserved}/{required_attributes_total} attrs"
        ).format(**semantic_metrics),
        "optional_counts": (
            "{optional_text_preserved}/{optional_text_total} text, "
            "{optional_href_preserved}/{optional_href_total} href"
        ).format(**semantic_metrics),
        "median_ms": statistics.median(elapsed_seconds) * 1000,
        "p95_ms": _percentile(elapsed_seconds, 0.95) * 1000,
    }


def _format_table(rows: Sequence[dict[str, str | float | int]]) -> str:
    headers = (
        "Fixture",
        "Variant",
        "Raw chars",
        "Clean chars",
        "Char ↓",
        "Raw tokens",
        "Clean tokens",
        "Token ↓",
        "Retention",
        "Required kept",
        "Optional kept",
        "Median ms",
        "P95 ms",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        lines.append(
            "| {fixture} | {variant} | {raw_chars} | {cleaned_chars} | "
            "{char_reduction_percent:.1f}% | {raw_tokens} | {cleaned_tokens} | "
            "{token_reduction_percent:.1f}% | {semantic_retention_percent:.1f}% | "
            "{required_counts} | {optional_counts} | {median_ms:.2f} | {p95_ms:.2f} |".format(
                **row
            )
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iterations",
        type=int,
        default=7,
        help="Timed runs per fixture and variant (default: 7).",
    )
    parser.add_argument(
        "--fixture",
        action="append",
        default=[],
        help="Run one fixture by filename; repeat to select several.",
    )
    args = parser.parse_args(argv)
    if args.iterations < 1:
        parser.error("--iterations must be at least 1")

    try:
        fixtures = _load_fixtures(args.fixture)
        rows = []
        for fixture, html in fixtures:
            filename = fixture["filename"]
            for variant, cleaner_factory in VARIANTS.items():
                expectations = expectations_for_variant(fixture, variant)
                metrics = _run_variant(
                    html,
                    cleaner_factory,
                    args.iterations,
                    expectations,
                    filename,
                    variant,
                )
                rows.append({"fixture": filename, "variant": variant, **metrics})
    except ImportError as exc:
        parser.exit(2, f"{exc}\nInstall token support with: uv sync --extra tokens\n")
    except ValueError as exc:
        parser.error(str(exc))

    print(
        f"Iterations per case: {args.iterations}; local fixture data only; no network access."
    )
    print(_format_table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
