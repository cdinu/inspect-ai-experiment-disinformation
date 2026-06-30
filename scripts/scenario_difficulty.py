#!/usr/bin/env python
"""Rank scenarios by difficulty across every run/model in an Inspect log directory.

Inspect's interactive viewer (``inspect view``) shows one log at a time. This
script uses the Inspect analysis API (``samples_df`` / ``evals_df``) to pool all
logs into one row-per-sample table and aggregate by scenario id, so you can see
which scenario is hardest across models and task variants.

Difficulty = mean model-graded score per scenario, with C=1.0, P=0.5, I=0.0,
pooled across every model and task in the log directory. Lower mean = harder.

Examples:
    uv run python scripts/scenario_difficulty.py
    uv run python scripts/scenario_difficulty.py --task pressure --by-model
    uv run python scripts/scenario_difficulty.py --top 15 --csv difficulty.csv
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import pandas as pd
from inspect_ai.analysis import evals_df, samples_df
from inspect_ai.scorer import value_to_float

STATS_START = "<!-- STATS:START -->"
STATS_END = "<!-- STATS:END -->"


def load_runs(log_dir: str, task: str | None = None) -> pd.DataFrame:
    """One row per sample-run, with scenario id, model, task, and numeric score."""
    to_float = value_to_float()  # C -> 1.0, P -> 0.5, I -> 0.0
    samples = samples_df(log_dir)
    evals = evals_df(log_dir)[["eval_id", "model", "task_name"]]
    runs = samples.merge(evals, on="eval_id", how="left")
    if task:
        runs = runs[runs["task_name"].str.contains(task, case=False, na=False)]
    runs["score"] = runs["score_model_graded_qa"].map(lambda value: to_float(str(value)))
    return runs


def rank(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to one row per scenario id, sorted hardest first."""
    grouped = runs.groupby("id").agg(
        runs=("score", "size"),
        models=("model", "nunique"),
        mean_score=("score", "mean"),
        solved_rate=("score", lambda col: (col == 1.0).mean()),
    )
    return grouped.sort_values(["mean_score", "solved_rate"])


def difficulty_text(runs: pd.DataFrame, top: int = 0) -> str:
    """Plain-text difficulty table with a one-line summary header, hardest first."""
    if runs.empty:
        return "No evaluation runs found yet."
    ranking = rank(runs)
    shown = ranking.head(top) if top else ranking
    header = (
        f"Hardest scenarios — {len(runs)} runs, {runs['model'].nunique()} models, "
        f"{runs['task_name'].nunique()} task(s). Lower mean_score = harder."
    )
    if top and len(ranking) > top:
        header += f" Showing the {top} hardest of {len(ranking)}."
    return f"{header}\n\n{shown.round(3).to_string()}"


def inject_html(runs: pd.DataFrame, path: Path, top: int = 0) -> int:
    """Replace the <pre> between the STATS markers in an HTML file with the table."""
    pre = f'<pre class="stats">{html.escape(difficulty_text(runs, top))}</pre>'
    block = f"{STATS_START}\n{pre}\n{STATS_END}"
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(STATS_START) + r".*?" + re.escape(STATS_END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"{path}: missing '{STATS_START} ... {STATS_END}' markers")
    path.write_text(pattern.sub(lambda _: block, text), encoding="utf-8")
    print(f"Injected difficulty table into {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", default="logs")
    parser.add_argument("--task", default=None, help="substring filter on task name, e.g. pressure")
    parser.add_argument("--top", type=int, default=0, help="show only the N hardest (0 = all)")
    parser.add_argument(
        "--by-model", action="store_true", help="also print a scenario x model pivot"
    )
    parser.add_argument("--csv", type=Path, default=None, help="write the full ranking to CSV")
    parser.add_argument(
        "--html-into",
        type=Path,
        default=None,
        help=f"inject the table into an HTML file between {STATS_START} and {STATS_END}",
    )
    args = parser.parse_args(argv)

    runs = load_runs(args.log_dir, args.task)

    if args.html_into is not None:
        # Tolerate an empty log dir here so the publish step never fails the bundle.
        return inject_html(runs, args.html_into, args.top)

    if runs.empty:
        print(
            f"No samples found in {args.log_dir!r}"
            + (f" for task ~ {args.task!r}." if args.task else ".")
        )
        return 1

    ranking = rank(runs)
    pd.set_option("display.max_rows", None, "display.width", 140)
    shown = ranking.head(args.top) if args.top else ranking
    print(
        f"Scenario difficulty (lower mean_score = harder) over {len(runs)} runs, "
        f"{runs['model'].nunique()} models, {runs['task_name'].nunique()} task(s):\n"
    )
    print(shown.round(3).to_string())

    if args.csv:
        ranking.round(4).to_csv(args.csv)
        print(f"\nWrote {args.csv}")

    if args.by_model:
        pivot = runs.pivot_table(index="id", columns="model", values="score", aggfunc="mean")
        print("\nScenario x model mean score (hardest first):\n")
        print(pivot.loc[ranking.index].round(2).to_string())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
