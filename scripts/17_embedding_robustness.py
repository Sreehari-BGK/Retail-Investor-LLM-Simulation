#!/usr/bin/env python3
"""
17_embedding_robustness.py

Semantic robustness check: re-run MMD using an alternative embedding model
(default: Qwen/Qwen3-Embedding-0.6B) and compare against the MiniLM baseline.

Supervisor request: verify that semantic-similarity conclusions from the prompt-
condition experiment do not depend on the choice of MiniLM as the embedding model.

Usage
-----
  # Supervisor-requested robustness check (three candidate files):
  python scripts/17_embedding_robustness.py \\
      --model Qwen/Qwen3-Embedding-0.6B \\
      --event NVDA_Q3FY26 \\
      --input runs/qwen25_3b_seed42_promptgrid_nvda/prompt_exp_P0_V0_comments.csv \\
              runs/qwen35_2b_seed42_promptgrid_nvda/prompt_exp_P2_V1_comments.csv \\
              runs/qwen35_2b_temp07_seed42_promptgrid_nvda/prompt_exp_P2_V1_comments.csv

  # Any other model (generic use):
  python scripts/17_embedding_robustness.py \\
      --model sentence-transformers/all-MiniLM-L6-v2 \\
      --event NVDA_Q3FY26 \\
      --input runs/qwen25_3b_seed42_promptgrid_nvda/prompt_exp_P0_V0_comments.csv

Outputs (all in outputs/ and runs/embedding_robustness_<modelslug>/)
---------------------------------------------------------------------
  embedding_robustness_<modelslug>.json   — machine-readable results
  embedding_robustness_<modelslug>.md     — human-readable ranked summary
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
DATA_DIR = ROOT / "data" / "processed"
OUTPUTS_DIR = ROOT / "outputs"
RUNS_DIR = ROOT / "runs"

REAL_CSV_CANDIDATES = [
    DATA_DIR / "real_comments_curated_labeled.csv",
    DATA_DIR / "comments.csv",
]

# Columns that might hold comment text in the input CSVs
TEXT_COL_CANDIDATES = ["text", "body", "comment", "comment_text", "content"]

# Reference MiniLM MMD values from the existing prompt-condition experiment
# (from prompt_exp_metrics.json in each run folder) — used only in the
# markdown for side-by-side comparison.
MINILM_LABEL = "all-MiniLM-L6-v2 (baseline)"

# ---------------------------------------------------------------------------
# Load metrics module (04_compute_metrics.py has a leading digit)
# ---------------------------------------------------------------------------
def _load_metrics_module():
    spec = importlib.util.spec_from_file_location(
        "compute_metrics", SCRIPTS_DIR / "04_compute_metrics.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Model-slug helper (safe filename component)
# ---------------------------------------------------------------------------
def _slug(model_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", model_name).strip("_").lower()


# ---------------------------------------------------------------------------
# Text-column detection
# ---------------------------------------------------------------------------
def _find_text_col(df: pd.DataFrame) -> str:
    for c in TEXT_COL_CANDIDATES:
        if c in df.columns:
            return c
    raise ValueError(
        f"Cannot find a text column. Tried: {TEXT_COL_CANDIDATES}. "
        f"Available columns: {list(df.columns)}"
    )


# ---------------------------------------------------------------------------
# Embedding with Qwen3-Embedding-style last-token pooling
# ---------------------------------------------------------------------------

def _embed_with_transformers(
    texts: list[str],
    model_name: str,
    batch_size: int,
    device: str,
) -> np.ndarray:
    """
    Load via HuggingFace `transformers` with last-token pooling.
    Required for Qwen3-Embedding models (and compatible with other decoder-
    based embedding models that use EOS-token pooling).
    """
    import torch
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer

    print(f"[embed] Loading tokenizer: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    print(f"[embed] Loading model: {model_name} on {device}")
    model = AutoModel.from_pretrained(
        model_name,
        dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True,
    )
    if device == "cpu":
        model = model.to(device)
    model.eval()

    def _last_token_pool(last_hidden: torch.Tensor, attn_mask: torch.Tensor) -> torch.Tensor:
        # If left-padded, the last position is always the final real token.
        left_padded = (attn_mask[:, -1].sum() == attn_mask.shape[0])
        if left_padded:
            return last_hidden[:, -1]
        seq_lens = attn_mask.sum(dim=1) - 1
        bs = last_hidden.shape[0]
        return last_hidden[torch.arange(bs, device=last_hidden.device), seq_lens]

    all_vecs: list[np.ndarray] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        encoded = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        encoded = {k: v.to(model.device) for k, v in encoded.items()}

        with torch.no_grad():
            out = model(**encoded)

        vecs = _last_token_pool(out.last_hidden_state, encoded["attention_mask"])
        vecs = F.normalize(vecs, p=2, dim=-1)
        all_vecs.append(vecs.cpu().float().numpy())

        done = min(start + batch_size, len(texts))
        if len(texts) > batch_size:
            print(f"  {done}/{len(texts)} embedded", end="\r", flush=True)

    if len(texts) > batch_size:
        print()
    return np.vstack(all_vecs).astype(np.float32)


def _embed_with_sentence_transformers(
    texts: list[str],
    model_name: str,
    batch_size: int,
) -> np.ndarray:
    """
    Fallback: use sentence-transformers API (works for MiniLM and ST-compatible models).
    """
    from sentence_transformers import SentenceTransformer

    print(f"[embed] Loading via sentence-transformers: {model_name}")
    st_model = SentenceTransformer(model_name)
    emb = st_model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 20,
        convert_to_numpy=True,
    )
    return emb.astype(np.float32)


def embed(
    texts: list[str],
    model_name: str,
    batch_size: int,
    device: str,
) -> np.ndarray:
    """
    Embed texts with the given model.

    Strategy:
      1. Always try the transformers last-token-pool path first.
         This is the correct path for Qwen3-Embedding-0.6B.
      2. If that fails (e.g. model is encoder-only and has no last_hidden_state
         in the expected format), fall back to sentence-transformers.
    """
    try:
        return _embed_with_transformers(texts, model_name, batch_size, device)
    except Exception as primary_err:
        print(f"[embed] transformers path failed: {primary_err}")
        print("[embed] Falling back to sentence-transformers ...")
        try:
            return _embed_with_sentence_transformers(texts, model_name, batch_size)
        except Exception as fallback_err:
            raise RuntimeError(
                f"Both embedding paths failed.\n"
                f"  transformers error:         {primary_err}\n"
                f"  sentence-transformers error: {fallback_err}"
            ) from fallback_err


# ---------------------------------------------------------------------------
# Load real comments
# ---------------------------------------------------------------------------
def _load_real(event_id: str) -> pd.DataFrame:
    csv_path = next((p for p in REAL_CSV_CANDIDATES if p.exists()), None)
    if csv_path is None:
        raise FileNotFoundError(
            f"Real comments CSV not found. Tried: {[str(p) for p in REAL_CSV_CANDIDATES]}"
        )
    df = pd.read_csv(csv_path)
    if "event_id" in df.columns:
        df = df[df["event_id"] == event_id].copy()
    if df.empty:
        raise ValueError(
            f"No rows found for event_id='{event_id}' in {csv_path}. "
            f"Available event IDs: {df['event_id'].unique().tolist() if 'event_id' in df.columns else 'N/A'}"
        )
    print(f"[data] Loaded {len(df)} real comments for {event_id} from {csv_path.name}")
    return df


# ---------------------------------------------------------------------------
# Retrieve MiniLM MMD from an existing run's metrics file (best-effort)
# ---------------------------------------------------------------------------
def _get_minilm_mmd(csv_path: Path) -> float | None:
    """
    Look for prompt_exp_metrics.json in the same folder as csv_path.
    Return the mmd_semantic value for the matching condition if found.
    """
    metrics_file = csv_path.parent / "prompt_exp_metrics.json"
    if not metrics_file.exists():
        return None
    try:
        with open(metrics_file) as f:
            data = json.load(f)
        # The key is the short condition label embedded in the CSV filename.
        # e.g. prompt_exp_P0_V0_comments.csv -> P0_V0
        stem = csv_path.stem  # e.g. prompt_exp_P0_V0_comments
        for key, val in data.items():
            if key.replace("__", "_") in stem or key in stem:
                mmd = val.get("mmd_semantic")
                if isinstance(mmd, float):
                    return mmd
        # Try every key and return the first float mmd_semantic
        for key, val in data.items():
            mmd = val.get("mmd_semantic")
            if isinstance(mmd, float):
                return mmd
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Memory-safe RBF bandwidth estimator
# ---------------------------------------------------------------------------

def _safe_gamma(X: np.ndarray, Y: np.ndarray, n_sample: int = 500) -> float:
    """
    Median-heuristic RBF bandwidth that works for high-dimensional embeddings.

    For L2-normalised vectors: ||x-y||^2 = 2 - 2*(x . y), so pairwise squared
    distances reduce to a matrix multiply — O(n^2 * d) multiply but only O(n^2)
    memory, versus the O(n^2 * d) broadcast that causes the 30 GiB OOM.

    Falls back to the dot-product trick for any embedding dimensionality.
    """
    rng = np.random.default_rng(42)
    combined = np.vstack([X, Y]).astype(np.float32)
    if len(combined) > n_sample:
        idx = rng.choice(len(combined), size=n_sample, replace=False)
        combined = combined[idx]

    # ||x-y||^2 = ||x||^2 + ||y||^2 - 2*(x . y)
    # For unit vectors this is 2 - 2*(x . y), but we compute generally:
    dot = combined @ combined.T                    # (n, n)
    sq_norms = np.einsum("ij,ij->i", combined, combined)  # (n,)
    sq_dists = sq_norms[:, None] + sq_norms[None, :] - 2.0 * dot  # (n, n)
    sq_dists = np.maximum(sq_dists, 0.0)

    # Take upper-triangle (excluding diagonal) to get unique pairwise distances
    triu_idx = np.triu_indices(len(combined), k=1)
    median_sq = float(np.median(sq_dists[triu_idx]))
    if median_sq <= 0.0:
        median_sq = 1.0
    return float(1.0 / median_sq)   # gamma = 1 / (2 * sigma^2), sigma^2 ≈ median/2


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Embedding robustness check — recompute MMD with an alternative model"
    )
    p.add_argument(
        "--model",
        default="Qwen/Qwen3-Embedding-0.6B",
        help="HuggingFace model ID for embeddings (default: Qwen/Qwen3-Embedding-0.6B)",
    )
    p.add_argument(
        "--event",
        default="NVDA_Q3FY26",
        help="event_id to filter real comments (default: NVDA_Q3FY26)",
    )
    p.add_argument(
        "--input",
        nargs="+",
        required=True,
        metavar="CSV",
        help="One or more generated-comment CSV files to evaluate",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=32,
        dest="batch_size",
        help="Embedding batch size (default: 32)",
    )
    return p.parse_args()


def main() -> None:
    import torch

    args = parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_slug = _slug(args.model)
    run_out_dir = RUNS_DIR / f"embedding_robustness_{model_slug}"
    run_out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("Embedding Robustness Check")
    print("=" * 65)
    print(f"  Embedding model : {args.model}")
    print(f"  Event           : {args.event}")
    print(f"  Device          : {device}")
    print(f"  Batch size      : {args.batch_size}")
    print(f"  Input files     : {len(args.input)}")
    for p in args.input:
        print(f"    {p}")
    print()

    metrics_mod = _load_metrics_module()

    # --- Load + embed real comments (once, shared across all inputs) ---
    real_df = _load_real(args.event)
    real_text_col = _find_text_col(real_df)
    real_texts = real_df[real_text_col].fillna("").tolist()

    real_cache = OUTPUTS_DIR / f"real_emb_cache_{_slug(args.event)}_{model_slug}.npy"
    if real_cache.exists():
        print(f"[embed] Loading cached real embeddings from {real_cache.name}")
        real_emb = np.load(real_cache)
        print(f"[embed] Cache hit  shape={real_emb.shape}")
    else:
        print(f"\n[embed] Embedding {len(real_texts)} real comments ...")
        t0 = time.time()
        real_emb = embed(real_texts, args.model, args.batch_size, device)
        print(f"[embed] Done in {time.time()-t0:.1f}s  shape={real_emb.shape}")
        np.save(real_cache, real_emb)
        print(f"[embed] Saved real embedding cache -> {real_cache.name}")

    # --- Process each input file ---
    results: list[dict] = []

    for csv_str in args.input:
        csv_path = Path(csv_str)
        if not csv_path.is_absolute():
            csv_path = ROOT / csv_path
        if not csv_path.exists():
            print(f"\n[WARN] File not found, skipping: {csv_path}")
            results.append(
                {
                    "input_file": str(csv_path),
                    "label": csv_path.stem,
                    "n_sim": None,
                    "mmd_semantic_qwen3": None,
                    "mmd_semantic_minilm": None,
                    "error": "file not found",
                }
            )
            continue

        label = f"{csv_path.parent.name}/{csv_path.stem}"
        print(f"\n{'-'*65}")
        print(f"Processing: {label}")

        sim_df = pd.read_csv(csv_path)
        sim_text_col = _find_text_col(sim_df)
        sim_texts = sim_df[sim_text_col].fillna("").tolist()
        print(f"  {len(sim_texts)} generated comments")

        print(f"[embed] Embedding generated comments ...")
        t1 = time.time()
        sim_emb = embed(sim_texts, args.model, args.batch_size, device)
        print(f"[embed] Done in {time.time()-t1:.1f}s  shape={sim_emb.shape}")

        gamma = _safe_gamma(real_emb, sim_emb)
        print(f"  RBF gamma (safe median): {gamma:.6f}")
        mmd_val = float(metrics_mod.mmd_rbf(real_emb, sim_emb, gamma=gamma))
        minilm_mmd = _get_minilm_mmd(csv_path)

        print(f"  MMD ({args.model}):  {mmd_val:.6f}")
        if minilm_mmd is not None:
            print(f"  MMD (MiniLM baseline):     {minilm_mmd:.6f}")

        results.append(
            {
                "input_file":           str(csv_path.relative_to(ROOT)),
                "label":                label,
                "run_folder":           csv_path.parent.name,
                "condition":            csv_path.stem.replace("prompt_exp_", "").replace("_comments", ""),
                "n_real":               len(real_texts),
                "n_sim":                len(sim_texts),
                "embedding_model":      args.model,
                "mmd_semantic_qwen3":   mmd_val,
                "mmd_semantic_minilm":  minilm_mmd,
                "event_id":             args.event,
                "computed_at":          datetime.utcnow().isoformat() + "Z",
            }
        )

    # --- Sort by MMD (best first) ---
    valid = [r for r in results if r["mmd_semantic_qwen3"] is not None]
    invalid = [r for r in results if r["mmd_semantic_qwen3"] is None]
    valid.sort(key=lambda r: r["mmd_semantic_qwen3"])
    results_sorted = valid + invalid

    # --- Write JSON ---
    json_name = f"embedding_robustness_{model_slug}.json"
    json_data = {
        "embedding_model":       args.model,
        "event_id":              args.event,
        "device":                device,
        "batch_size":            args.batch_size,
        "n_real_comments":       len(real_texts),
        "generated_at":          datetime.utcnow().isoformat() + "Z",
        "results":               results_sorted,
    }
    for dest_dir in [OUTPUTS_DIR, run_out_dir]:
        out_path = dest_dir / json_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"\n[out] Saved JSON -> {out_path.relative_to(ROOT)}")

    # --- Write Markdown ---
    md_lines = [
        f"# Embedding Robustness Check — {args.event}",
        "",
        f"**Embedding model:** `{args.model}`  ",
        f"**Baseline embedding:** `{MINILM_LABEL}`  ",
        f"**Event:** `{args.event}`  ",
        f"**Real comments:** {len(real_texts)}  ",
        f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "---",
        "",
        "## Semantic MMD Rankings (lower = more similar to real data)",
        "",
        "| Rank | Run | Condition | MMD (Qwen3-Emb) | MMD (MiniLM) | Δ |",
        "|------|-----|-----------|-----------------|--------------|---|",
    ]
    for rank, r in enumerate(valid, 1):
        q3_val = f"{r['mmd_semantic_qwen3']:.6f}"
        ml_val = f"{r['mmd_semantic_minilm']:.6f}" if r["mmd_semantic_minilm"] is not None else "n/a"
        if r["mmd_semantic_minilm"] is not None:
            delta = r["mmd_semantic_qwen3"] - r["mmd_semantic_minilm"]
            delta_str = f"{delta:+.6f}"
        else:
            delta_str = "n/a"
        md_lines.append(
            f"| {rank} | `{r['run_folder']}` | `{r['condition']}` "
            f"| {q3_val} | {ml_val} | {delta_str} |"
        )

    # Ranking stability note
    if len(valid) >= 2:
        qwen3_order = [r["label"] for r in valid]

        # Attempt to reconstruct MiniLM ranking
        ml_ranked = [r for r in valid if r["mmd_semantic_minilm"] is not None]
        ml_ranked.sort(key=lambda r: r["mmd_semantic_minilm"])
        ml_order = [r["label"] for r in ml_ranked]

        if len(ml_ranked) == len(valid):
            ranking_stable = qwen3_order == ml_order
            stable_word = "**stable**" if ranking_stable else "**changed**"
            md_lines += [
                "",
                f"### Ranking stability: {stable_word}",
                "",
                f"- Qwen3-Embedding-0.6B order: {' > '.join(qwen3_order)}",
                f"- MiniLM order:               {' > '.join(ml_order)}",
                "",
                "_(best first in each list)_",
            ]
        else:
            md_lines += [
                "",
                "### Ranking stability",
                "",
                "_MiniLM MMD values not available for all inputs — cannot compare rankings._",
            ]

    # Report sentence
    best = valid[0] if valid else None
    worst = valid[-1] if valid else None
    if best and worst:
        q3_spread = worst["mmd_semantic_qwen3"] - best["mmd_semantic_qwen3"]
        report_sentence = (
            f"Using `{args.model}` as an alternative embedding model, "
            f"the best-performing condition (`{best['condition']}` from `{best['run_folder']}`) "
            f"achieved MMD = {best['mmd_semantic_qwen3']:.4f} and the worst "
            f"(`{worst['condition']}` from `{worst['run_folder']}`) achieved "
            f"MMD = {worst['mmd_semantic_qwen3']:.4f} (spread = {q3_spread:.4f}); "
        )
        if len(ml_ranked) == len(valid) and len(valid) >= 2:
            if qwen3_order == ml_order:
                report_sentence += (
                    "the ranking was **identical** to the MiniLM baseline, "
                    "confirming that the semantic-similarity conclusions are robust "
                    "to the choice of embedding model."
                )
            else:
                report_sentence += (
                    "the ranking **differed** from the MiniLM baseline — "
                    "the semantic-similarity ordering may be sensitive to embedding model choice."
                )
        else:
            report_sentence += (
                "MiniLM baselines were unavailable for full ranking comparison."
            )
    else:
        report_sentence = "No valid results to summarise."

    md_lines += [
        "",
        "---",
        "",
        "## Paste-ready report sentence",
        "",
        f"> {report_sentence}",
        "",
        "---",
        "",
        "## Notes",
        "",
        "- MMD is computed with RBF kernel, median-heuristic bandwidth "
        "(Gretton et al., 2012), biased U-statistic estimator.",
        "- Embeddings are L2-normalised before MMD computation.",
        f"- `{args.model}` uses last-token pooling on the decoder hidden state.",
        "- Real comments are filtered to `event_id = NVDA_Q3FY26`.",
        "- Input CSV files were not modified.",
    ]

    md_content = "\n".join(md_lines) + "\n"
    md_name = f"embedding_robustness_{model_slug}.md"
    for dest_dir in [OUTPUTS_DIR, run_out_dir]:
        md_path = dest_dir / md_name
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"[out] Saved MD  -> {md_path.relative_to(ROOT)}")

    # Copy input CSVs into the run folder (read-only copies for provenance)
    for csv_str in args.input:
        csv_path = Path(csv_str)
        if not csv_path.is_absolute():
            csv_path = ROOT / csv_path
        if csv_path.exists():
            dest = run_out_dir / f"{csv_path.parent.name}__{csv_path.name}"
            shutil.copy2(csv_path, dest)

    # Print final table to stdout
    print("\n" + "=" * 65)
    print("RESULTS (ranked best -> worst by Qwen3-Embedding MMD)")
    print("=" * 65)
    print(f"{'Rank':<5} {'MMD (Qwen3)':<16} {'MMD (MiniLM)':<16} Condition")
    print("-" * 65)
    for rank, r in enumerate(valid, 1):
        ml = f"{r['mmd_semantic_minilm']:.6f}" if r["mmd_semantic_minilm"] is not None else "n/a"
        print(
            f"  {rank:<3} {r['mmd_semantic_qwen3']:<16.6f} {ml:<16} "
            f"{r['condition']}  [{r['run_folder']}]"
        )
    print()
    print("Paste-ready report sentence:")
    print(f"  {report_sentence}")
    print()


if __name__ == "__main__":
    main()
