#!/usr/bin/env python3
"""Build a compact summary table of finalist run results.

Reads (in priority order):
  1. outputs/finalist_rerun_results.json    (master accumulated results)
  2. runs/finalist_rerun_results.json       (alternate location)
  3. runs/finalist_*/metrics.json           (per-run metric files; fallback)

Emits:
  outputs/proposal_support/finalist_results_table.csv
  outputs/proposal_support/finalist_results_table.md

If no usable finalist results are found, fails gracefully and reports
exactly which expected files are missing.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "proposal_support"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CSV_PATH = OUT_DIR / "finalist_results_table.csv"
MD_PATH = OUT_DIR / "finalist_results_table.md"

CANDIDATES = [
    ROOT / "outputs" / "finalist_rerun_results.json",
    ROOT / "runs" / "finalist_rerun_results.json",
]


def _load_master() -> list | None:
    for p in CANDIDATES:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    print(f"[ok] loaded master results from {p.relative_to(ROOT)} ({len(data)} runs)")
                    return data
            except Exception as e:
                print(f"[warn] failed to read {p}: {e}")
    return None


def _load_per_run() -> list:
    runs_dir = ROOT / "runs"
    rows = []
    if not runs_dir.exists():
        return rows
    for p in sorted(runs_dir.glob("finalist_*/metrics.json")):
        try:
            rows.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[warn] failed to read {p}: {e}")
    if rows:
        print(f"[ok] fell back to {len(rows)} per-run metrics files")
    return rows


def _missing_report():
    print("\n[fail] no usable finalist results found.")
    print("Expected one of:")
    for p in CANDIDATES:
        print(f"  - {p.relative_to(ROOT)} {'(missing)' if not p.exists() else '(present but unreadable)'}")
    print(f"  - {(ROOT / 'runs').relative_to(ROOT)}/finalist_*/metrics.json  "
          f"(found {len(list((ROOT / 'runs').glob('finalist_*/metrics.json'))) if (ROOT / 'runs').exists() else 0} files)")
    print("\nRun scripts/18_finalist_rerun.py to produce them.")


def _format_metric(v, prec=4):
    if isinstance(v, (int, float)):
        return f"{v:.{prec}f}"
    return "n/a"


def main():
    results = _load_master()
    if not results:
        results = _load_per_run()
    if not results:
        _missing_report()
        sys.exit(1)

    df = pd.DataFrame(results)
    keep = [c for c in [
        "run_name", "model", "prompt_version", "temperature", "seed", "n_comments",
        "jsd_stance", "wasserstein_time", "mmd_semantic",
        "grounded_pct", "weakly_grounded_pct", "ungrounded_pct",
        "elapsed_s",
    ] if c in df.columns]
    df = df[keep].copy()

    sort_cols = [c for c in ["mmd_semantic", "jsd_stance"] if c in df.columns]
    if sort_cols:
        df_sorted = df.copy()
        df_sorted["_mmd_sort"] = pd.to_numeric(df_sorted.get("mmd_semantic"), errors="coerce")
        df_sorted = df_sorted.sort_values("_mmd_sort", na_position="last").drop(columns="_mmd_sort")
    else:
        df_sorted = df

    df_sorted.to_csv(CSV_PATH, index=False)
    print(f"[ok] wrote {CSV_PATH.relative_to(ROOT)} ({len(df_sorted)} rows)")

    lines = ["# Finalist Results Table",
             "",
             f"Auto-generated from {len(df_sorted)} finalist runs.",
             "Lower is better for JSD, Wasserstein, and MMD.",
             ""]
    headers = ["run_name", "model", "prompt", "tau", "seed", "n", "JSD", "Wass(h)", "MMD", "Gnd%", "Ung%"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for _, r in df_sorted.iterrows():
        lines.append("| " + " | ".join([
            str(r.get("run_name", "")),
            str(r.get("model", "")),
            str(r.get("prompt_version", "")),
            str(r.get("temperature", "")),
            str(r.get("seed", "")),
            str(r.get("n_comments", "")),
            _format_metric(r.get("jsd_stance")),
            _format_metric(r.get("wasserstein_time"), 2),
            _format_metric(r.get("mmd_semantic"), 5),
            _format_metric(r.get("grounded_pct"), 1),
            _format_metric(r.get("ungrounded_pct"), 1),
        ]) + " |")
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote {MD_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
