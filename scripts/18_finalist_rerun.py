#!/usr/bin/env python3
"""
18_finalist_rerun.py - Finalist rerun at larger sample size.

Generates comments for the two finalist conditions across multiple
temperatures and seeds, then evaluates each run against real NVDA data.

Usage (GPU):
  python scripts/18_finalist_rerun.py --dry-run   # smoke test
  python scripts/18_finalist_rerun.py              # full run

Each combo gets its own subfolder under runs/:
  runs/finalist_{modelslug}_{prompt}_{persona}_t{temp}_s{seed}/
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data" / "processed"
RUNS = ROOT / "runs"
RUNS.mkdir(exist_ok=True)

# ── Import metrics + grounding + stance from existing scripts ────────────
def _imp(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

metrics_mod = _imp("compute_metrics", "04_compute_metrics.py")
grounding_mod = _imp("eval_grounding", "12_eval_grounding.py")
stance_mod = _imp("label_stance", "label_stance_rulebased.py")

# ── Event card ───────────────────────────────────────────────────────────
EVENT_ID = "NVDA_Q3FY26"
TICKER = "NVDA"
EVENT_TIME = datetime(2025, 11, 19, 21, 0, 0, tzinfo=timezone.utc)
EVENT_SUMMARY = (
    "NVIDIA reported Q3 FY2026 revenue of $57 billion, up 62% year-over-year, "
    "driven by strong data center demand and the Blackwell GPU production ramp. "
    "The company beat analyst expectations on both revenue and earnings per share. "
    "CEO Jensen Huang raised guidance for Q4, citing continued AI infrastructure demand. "
    "The stock had a mixed after-hours reaction despite the beat."
)

# ── Archetypes ───────────────────────────────────────────────────────────
# V0: 9 archetypes (identical to 11_run_qwen_oneshot.py / 13_prompt_condition_experiment.py)
V0_ARCHETYPES = {
    "valuation-focused": {
        "cohort": "long-horizon",
        "description": "Evaluates NVIDIA on valuation metrics like P/E, forward growth vs price. Holds long-term positions. Skeptical of paying premium multiples even for good results.",
        "style": "Measured analysis, references valuation. 1-3 sentences, Reddit casual tone.",
    },
    "fundamentals-focused": {
        "cohort": "long-horizon",
        "description": "Focuses on revenue growth trajectory, data center TAM, competitive position. Long-term thesis holder. Cares about whether the growth story is intact.",
        "style": "Substantive, references specific financial metrics. Reddit casual tone, 1-3 sentences.",
    },
    "buy-the-dip": {
        "cohort": "long-horizon",
        "description": "Looks for entry points on pullbacks. Generally bullish on NVIDIA long-term. If earnings are good but stock dips, sees it as opportunity.",
        "style": "Confident and opportunistic. Short punchy Reddit comment. 1-2 sentences.",
    },
    "momentum-following": {
        "cohort": "short-horizon",
        "description": "Trades based on price momentum and technical signals. Cares about after-hours reaction, volume, and whether to ride the wave or exit.",
        "style": "Uses trader slang, references price action. Short, informal. 1-2 sentences.",
    },
    "event-reactive": {
        "cohort": "short-horizon",
        "description": "Reacts quickly to earnings headlines. May hold options or short-dated positions. Focuses on beat/miss magnitude and immediate price response.",
        "style": "Fast, emotional, uses WSB slang. References options, IV crush, AH moves. 1-2 sentences.",
    },
    "profit-taking": {
        "cohort": "short-horizon",
        "description": "Has been holding NVIDIA and considering whether to lock in gains. Weighs whether the good earnings justify continued holding or if it's time to sell.",
        "style": "Cautious, mentions position sizing or exits. Reddit casual. 1-2 sentences.",
    },
    "uncertain": {
        "cohort": "info-seeking",
        "description": "Not sure what to make of the earnings. New to NVIDIA or investing generally. Asks questions and looks for others' opinions.",
        "style": "Questioning, sometimes confused, asks for help. Casual Reddit language. 1-2 sentences.",
    },
    "evidence-seeking": {
        "cohort": "info-seeking",
        "description": "Wants to dig into the details before forming an opinion. Asks about specific line items, margins, guidance details, or competitive threats.",
        "style": "Analytical but uncertain. Asks specific questions about the numbers. 1-3 sentences.",
    },
    "wait-and-see": {
        "cohort": "info-seeking",
        "description": "Watching from the sidelines. Interested but not ready to commit. Wants to see how the market digests the news before acting.",
        "style": "Cautious observer. May express interest without commitment. 1-2 sentences.",
    },
}

# V1: 3 broad archetypes
V1_ARCHETYPES = {
    "long_horizon": {
        "cohort": "long-horizon",
        "description": (
            "A retail investor who thinks in years, not days. "
            "Cares about business quality, long-term growth, competitive position, "
            "and whether the stock will be worth more in 3-5 years. "
            "Less reactive to short-term price swings."
        ),
        "style": "Measured. May reference fundamentals or valuation. Less reactive to short-term noise.",
    },
    "short_horizon": {
        "cohort": "short-horizon",
        "description": (
            "A retail investor focused on near-term price action, momentum, and tradeable setups. "
            "Reacts strongly to earnings beats/misses, guidance changes, and after-hours moves. "
            "More likely to express strong directional opinions."
        ),
        "style": "Reactive, fast. Focused on charts, momentum, and the immediate market reaction.",
    },
    "information_seeking": {
        "cohort": "info-seeking",
        "description": (
            "A retail investor who is unsure, wants more data, or is trying to understand "
            "what the earnings mean before taking a position. "
            "Often expresses uncertainty, asks questions, or waits for more clarity."
        ),
        "style": "Hesitant, questioning. May express confusion or ask for clarification. Avoids strong conclusions.",
    },
}

# ── Prompt builders ──────────────────────────────────────────────────────

SYSTEM_P0 = (
    "You are simulating a retail investor posting on Reddit after NVIDIA's earnings announcement. "
    "Write exactly ONE short Reddit-style comment (1-4 sentences max). "
    "Rules: Use casual Reddit language, not formal finance writing. "
    "Reference specific facts from the earnings when relevant to your persona. "
    "Do NOT write disclaimers, headers, or break character. "
    "Do NOT say 'As a [type] investor'. Output ONLY the comment text."
)

USER_P0 = """EARNINGS EVENT:
{event_summary}

YOUR INVESTOR PROFILE:
{description}

WRITING STYLE:
{style}

Write one Reddit comment from this investor's perspective about this NVIDIA earnings result. Only output the comment text."""

SYSTEM_P2 = (
    "You are simulating one Reddit user reacting to a company earnings event.\n\n"
    "Write one short comment that reflects how this kind of user would actually react online.\n\n"
    "The comment should reflect the user's behaviour, priorities, and time horizon "
    "more than perfect factual coverage.\n\n"
    "Possible behaviours include:\n"
    "- excitement\n- skepticism\n- confusion\n- caution\n"
    "- fear of missing out\n- concern about valuation\n"
    "- waiting for more information\n"
    "- comparing this event with expectations\n"
    "- focusing on short-term price action\n"
    "- focusing on long-term business strength\n\n"
    "Important:\n"
    "- The comment can be bullish, bearish, neutral, or mixed.\n"
    "- The comment can be uncertain.\n"
    "- The comment does not need to mention all details.\n"
    "- It should not read like a clean earnings summary.\n"
    "- It should feel like a real post/comment, not a textbook answer.\n"
    "- Keep it short and natural.\n"
    "- Mild informality is good.\n"
    "- Do not make every comment sound rational, complete, or polished.\n\n"
    "Output only the comment text."
)

USER_P2 = """EARNINGS EVENT:
{event_summary}

USER TYPE: {archetype_label}
BEHAVIOUR PROFILE:
{description}

Write one Reddit comment from this user's perspective. Only output the comment text."""


def build_messages(prompt_ver: str, archetype_id: str, arch_info: dict) -> list[dict]:
    if prompt_ver == "P0_V0":
        system = SYSTEM_P0
        user = USER_P0.format(
            event_summary=EVENT_SUMMARY,
            description=arch_info["description"],
            style=arch_info["style"],
        )
    elif prompt_ver == "P2_V1":
        system = SYSTEM_P2
        user = USER_P2.format(
            event_summary=EVENT_SUMMARY,
            archetype_label=archetype_id.replace("_", " ").title(),
            description=arch_info["description"],
        )
    else:
        raise ValueError(f"Unknown prompt_ver: {prompt_ver}")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ── Temporal assignment (same as 11_run_qwen_oneshot.py) ─────────────────
import random as _random

def assign_hour(cohort: str, rng: _random.Random) -> float:
    if cohort == "short-horizon":
        return round(max(-1, min(12, rng.gauss(2, 3))), 2)
    elif cohort == "long-horizon":
        return round(max(-6, min(48, rng.gauss(10, 10))), 2)
    else:
        return round(max(0, min(36, rng.gauss(6, 6))), 2)

def assign_depth(rng: _random.Random) -> int:
    return rng.choices([0, 1, 2], weights=[0.5, 0.35, 0.15])[0]


# ── Generation ───────────────────────────────────────────────────────────

def generate_one(tokenizer, model, messages, temperature, top_p, max_new_tokens, gen_seed):
    import torch
    text_input = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text_input, return_tensors="pt").to(model.device)
    torch.manual_seed(gen_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(gen_seed)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    raw = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    if "\n\n" in raw:
        raw = raw.split("\n\n")[0].strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1].strip()
    return raw

def generate_dry(archetype_id, idx):
    return f"[DRY-RUN] {archetype_id} #{idx}: Interesting quarter, watching closely."


# ── SBERT embedding ──────────────────────────────────────────────────────

_SBERT_MODEL = None

def embed_texts(texts: list[str]) -> np.ndarray:
    global _SBERT_MODEL
    if _SBERT_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _SBERT_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _SBERT_MODEL.encode(texts, batch_size=64, normalize_embeddings=True,
                               show_progress_bar=len(texts) > 50,
                               convert_to_numpy=True).astype(np.float32)


_REAL_EMB_CACHE = ROOT / "outputs" / "real_emb_cache_nvda_minilm.npy"

def load_real_embeddings(real_df: pd.DataFrame) -> np.ndarray:
    """Load or compute + cache real comment MiniLM embeddings."""
    if _REAL_EMB_CACHE.exists():
        emb = np.load(_REAL_EMB_CACHE)
        if emb.shape[0] == len(real_df):
            print(f"  Real embeddings loaded from cache ({emb.shape})")
            return emb
        print(f"  Cache shape mismatch ({emb.shape[0]} vs {len(real_df)}), re-embedding")
    print(f"  Embedding {len(real_df)} real comments (MiniLM) ...")
    emb = embed_texts(real_df["text"].fillna("").tolist())
    np.save(_REAL_EMB_CACHE, emb)
    print(f"  Saved cache -> {_REAL_EMB_CACHE.name} ({emb.shape})")
    return emb


# ── Load real data ───────────────────────────────────────────────────────

def load_real():
    csv = DATA / "real_comments_curated_labeled.csv"
    if not csv.exists():
        csv = DATA / "comments.csv"
    df = pd.read_csv(csv)
    if "event_id" in df.columns:
        df = df[df["event_id"] == EVENT_ID]
    return df


# ── Experiment definitions ───────────────────────────────────────────────

EXPERIMENTS = [
    {
        "label": "A",
        "prompt_ver": "P0_V0",
        "archetypes": V0_ARCHETYPES,
        "temps": [0.5, 0.9, 1.1],
        "seeds": [42, 123],
        "n_comments": 108,  # = 12 per archetype * 9
    },
    {
        "label": "B",
        "prompt_ver": "P2_V1",
        "archetypes": V1_ARCHETYPES,
        "temps": [0.5, 0.7, 0.9, 1.1],
        "seeds": [42, 123],
        "n_comments": 108,  # = 36 per archetype * 3
    },
]


# ── Main ─────────────────────────────────────────────────────────────────

def slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", s).strip("_").lower()


def run_one(exp, model_name, temp, seed, args, tokenizer, model, real_df, real_emb):
    """Generate + evaluate one (model, prompt, temp, seed) combo. Returns metrics dict."""
    archetypes = exp["archetypes"]
    prompt_ver = exp["prompt_ver"]
    n_total = exp["n_comments"]
    n_arch = len(archetypes)
    n_per = n_total // n_arch

    model_slug = slug(model_name)
    run_name = f"finalist_{model_slug}_{prompt_ver}_t{temp}_s{seed}"
    run_dir = RUNS / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    rng = _random.Random(seed)
    np.random.seed(seed)

    records = []
    count = 0
    for arch_id, arch_info in archetypes.items():
        for i in range(n_per):
            count += 1
            gen_seed = seed * 10000 + count
            messages = build_messages(prompt_ver, arch_id, arch_info)

            if args.dry_run:
                text = generate_dry(arch_id, i)
            else:
                text = generate_one(tokenizer, model, messages,
                                    temperature=temp, top_p=args.top_p,
                                    max_new_tokens=args.max_new_tokens,
                                    gen_seed=gen_seed)

            hours = assign_hour(arch_info["cohort"], rng)
            depth = assign_depth(rng)
            stance = stance_mod.label_text(text)

            records.append({
                "event_id": EVENT_ID,
                "ticker": TICKER,
                "event_time": EVENT_TIME.isoformat(),
                "subreddit": "wallstreetbets",
                "thread_id": f"thread_{prompt_ver}_{arch_id}",
                "comment_id": f"fin_{model_slug}_{prompt_ver}_{arch_id}_{seed}_{i:03d}",
                "parent_id": f"thread_{prompt_ver}_{arch_id}",
                "hours_from_event": hours,
                "text": text,
                "score": 0,
                "depth": depth,
                "source_type": "sim_agent",
                "stance": stance,
                "prompt_version": prompt_ver,
                "persona_version": "V0_current" if "P0" in prompt_ver else "V1_three_archetypes",
                "archetype": arch_id,
                "cohort": arch_info["cohort"],
            })
            if count % 20 == 0:
                print(f"    [{count}/{n_total}] {text[:70]}...")

    df = pd.DataFrame(records)
    csv_path = run_dir / f"prompt_exp_{prompt_ver}_comments.csv"
    df.to_csv(csv_path, index=False)

    # Save metadata JSONL
    meta_path = run_dir / "prompt_exp_metadata.jsonl"
    with open(meta_path, "w", encoding="utf-8") as f:
        for i, rec in enumerate(records):
            meta = {
                **rec,
                "model_name": model_name,
                "temperature": temp,
                "top_p": args.top_p,
                "max_new_tokens": args.max_new_tokens,
                "base_seed": seed,
                "gen_seed": seed * 10000 + i + 1,
                "dry_run": args.dry_run,
            }
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")

    print(f"  Saved {len(df)} comments -> {run_name}/")

    # ── Evaluate ─────────────────────────────────────────────────────────
    result = {
        "run_name": run_name,
        "model": model_name,
        "prompt_version": prompt_ver,
        "temperature": temp,
        "seed": seed,
        "n_comments": len(df),
    }

    if args.skip_eval:
        return result

    # Stance JSD
    if "stance" in real_df.columns:
        result["jsd_stance"] = float(metrics_mod.jsd_stance(
            real_df["stance"].tolist(), df["stance"].tolist()))

    # Wasserstein time
    if "hours_from_event" in real_df.columns:
        result["wasserstein_time"] = float(metrics_mod.wasserstein_time(
            real_df["hours_from_event"].dropna().tolist(),
            df["hours_from_event"].dropna().tolist()))

    # MMD semantic
    try:
        sim_emb = embed_texts(df["text"].tolist())
        result["mmd_semantic"] = float(metrics_mod.mmd_rbf(real_emb, sim_emb))
    except Exception as e:
        result["mmd_semantic"] = f"error: {e}"

    # Grounding
    try:
        g = grounding_mod.evaluate_corpus(df, text_col="text")
        result["grounded_pct"] = g["grounding"]["grounded_pct"]
        result["weakly_grounded_pct"] = g["grounding"]["weakly_grounded_pct"]
        result["ungrounded_pct"] = g["grounding"]["ungrounded_pct"]
        result["directional_accuracy_pct"] = g["directional"]["accuracy_pct"]
    except Exception as e:
        result["grounding_error"] = str(e)

    # Save per-run metrics
    with open(run_dir / "metrics.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


# ── Named batch definitions ──────────────────────────────────────────────
# Each batch is a list of (experiment_index, model_key, temps, seeds).
# model_key is "a" or "b" -> resolved to --model-a / --model-b at runtime.

BATCHES = {
    "semantic_first": [
        # Qwen3.5-2B + P2_V1  tau=0.5,0.9,1.1  seeds=42,123  (6 runs)
        (1, "b", [0.5, 0.9, 1.1], [42, 123]),
    ],
    "stance_first": [
        # Qwen2.5-3B + P0_V0  tau=0.5,0.9,1.1  seeds=42,123  (6 runs)
        (0, "a", [0.5, 0.9, 1.1], [42, 123]),
    ],
    "optional_tau07": [
        # Qwen3.5-2B + P2_V1  tau=0.7  seeds=42,123  (2 runs)
        (1, "b", [0.7], [42, 123]),
    ],
    "all": [
        (0, "a", [0.5, 0.9, 1.1], [42, 123]),
        (1, "b", [0.5, 0.7, 0.9, 1.1], [42, 123]),
    ],
}


def parse_args():
    p = argparse.ArgumentParser(
        description="Finalist rerun generation + evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Named batches:
  semantic_first   Qwen3.5-2B + P2_V1, tau=0.5/0.9/1.1, seeds=42/123  (6 runs)
  stance_first     Qwen2.5-3B + P0_V0, tau=0.5/0.9/1.1, seeds=42/123  (6 runs)
  optional_tau07   Qwen3.5-2B + P2_V1, tau=0.7, seeds=42/123           (2 runs)
  all              Full 14-run grid                                     (14 runs)

Examples:
  python scripts/18_finalist_rerun.py --batch semantic_first
  python scripts/18_finalist_rerun.py --batch stance_first --dry-run
  python scripts/18_finalist_rerun.py --batch semantic_first --batch stance_first
  python scripts/18_finalist_rerun.py --batch all
""")
    p.add_argument("--batch", action="append", dest="batches", metavar="NAME",
                   help="Named batch to run (repeatable). Choices: "
                        + ", ".join(BATCHES.keys()))
    p.add_argument("--model-a", default="Qwen/Qwen2.5-3B-Instruct",
                   help="Model for condition A / P0_V0")
    p.add_argument("--model-b", default="Qwen/Qwen3.5-2B",
                   help="Model for condition B / P2_V1")
    p.add_argument("--top-p", type=float, default=0.95)
    p.add_argument("--max-new-tokens", type=int, default=150)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-eval", action="store_true",
                   help="Skip metric computation (generation only)")
    return p.parse_args()


def _resolve_jobs(args) -> list[tuple[dict, str, list[float], list[int]]]:
    """
    Expand batch names into a deduplicated list of
    (experiment_dict, model_name, temps, seeds) tuples.
    """
    batch_names = args.batches or ["all"]
    for name in batch_names:
        if name not in BATCHES:
            sys.exit(f"Unknown batch '{name}'. Choices: {', '.join(BATCHES.keys())}")

    # Collect all (exp_idx, model_key, temp, seed) tuples, dedup
    seen = set()
    jobs: list[tuple[dict, str, float, int]] = []
    for name in batch_names:
        for exp_idx, model_key, temps, seeds in BATCHES[name]:
            exp = EXPERIMENTS[exp_idx]
            model_name = args.model_a if model_key == "a" else args.model_b
            for t in temps:
                for s in seeds:
                    key = (exp_idx, model_name, t, s)
                    if key not in seen:
                        seen.add(key)
                        jobs.append((exp, model_name, t, s))
    return jobs


def main():
    args = parse_args()
    jobs = _resolve_jobs(args)

    # Group jobs by model so we load each model only once
    from collections import OrderedDict
    model_jobs: OrderedDict[str, list] = OrderedDict()
    for exp, model_name, temp, seed in jobs:
        model_jobs.setdefault(model_name, []).append((exp, temp, seed))

    total_runs = len(jobs)
    batch_label = ", ".join(args.batches or ["all"])

    print("=" * 65)
    print("  Finalist Rerun Generation + Evaluation")
    print("=" * 65)
    print(f"  Batches:    {batch_label}")
    print(f"  Total runs: {total_runs}")
    for mn, jlist in model_jobs.items():
        temps_seen = sorted(set(t for _, t, _ in jlist))
        seeds_seen = sorted(set(s for _, _, s in jlist))
        print(f"  {mn}: {len(jlist)} runs  temps={temps_seen}  seeds={seeds_seen}")
    print(f"  Dry run:    {args.dry_run}")
    print()

    # Load real data + embed once
    real_df = load_real()
    print(f"  Real comments: {len(real_df)}")
    real_emb = None
    if not args.skip_eval:
        real_emb = load_real_embeddings(real_df)

    all_results = []
    run_count = 0

    for model_name, jlist in model_jobs.items():
        tokenizer = model_obj = None
        if not args.dry_run:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"\n  Loading {model_name} ...")
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            model_obj = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map=device if device == "cuda" else None,
                trust_remote_code=True,
            )
            if device == "cpu":
                model_obj = model_obj.to("cpu")
            model_obj.eval()
            print(f"  Loaded on {device}")

        for exp, temp, seed in jlist:
            run_count += 1
            print(f"\n  [{run_count}/{total_runs}] {model_name} | "
                  f"{exp['prompt_ver']} | t={temp} s={seed}")
            t0 = time.time()
            r = run_one(exp, model_name, temp, seed, args,
                        tokenizer, model_obj, real_df, real_emb)
            r["elapsed_s"] = round(time.time() - t0, 1)
            all_results.append(r)
            _print_metrics(r)

        # Free model before loading next
        if not args.dry_run:
            del model_obj, tokenizer
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    # ── Save / append master results ─────────────────────────────────────
    # Append to existing results file so incremental batches accumulate.
    master_path = RUNS / "finalist_rerun_results.json"
    existing = []
    if master_path.exists():
        try:
            existing = json.loads(master_path.read_text())
        except Exception:
            pass
    # Merge: update existing by run_name, append new
    by_name = {r["run_name"]: r for r in existing}
    for r in all_results:
        by_name[r["run_name"]] = r
    merged = list(by_name.values())

    with open(master_path, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    out_path = ROOT / "outputs" / "finalist_rerun_results.json"
    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"\n  Results ({len(merged)} total) -> {master_path.relative_to(ROOT)}")

    # ── Print summary table ──────────────────────────────────────────────
    _print_summary_table(all_results, label=f"This session ({batch_label})")
    if len(merged) > len(all_results):
        _print_summary_table(merged, label="All accumulated runs")


def _print_metrics(r):
    for k in ["jsd_stance", "wasserstein_time", "mmd_semantic",
              "grounded_pct", "ungrounded_pct", "directional_accuracy_pct"]:
        v = r.get(k)
        if v is not None and isinstance(v, (int, float)):
            print(f"    {k}: {v:.4f}")


def _print_summary_table(results, label="Results"):
    print(f"\n{'='*100}")
    print(f"  {label}")
    print(f"{'='*100}")
    print(f"{'Run':<55} {'JSD':>7} {'Wass':>7} {'MMD':>8} {'Gnd%':>6} {'Ung%':>6}")
    print("-" * 100)
    for r in sorted(results, key=lambda x: x.get("mmd_semantic", 999)
                    if isinstance(x.get("mmd_semantic"), float) else 999):
        jsd = f"{r['jsd_stance']:.4f}" if isinstance(r.get("jsd_stance"), float) else "n/a"
        was = f"{r['wasserstein_time']:.2f}" if isinstance(r.get("wasserstein_time"), float) else "n/a"
        mmd = f"{r['mmd_semantic']:.5f}" if isinstance(r.get("mmd_semantic"), float) else "n/a"
        gnd = f"{r['grounded_pct']:.1f}" if isinstance(r.get("grounded_pct"), (int, float)) else "n/a"
        ung = f"{r['ungrounded_pct']:.1f}" if isinstance(r.get("ungrounded_pct"), (int, float)) else "n/a"
        print(f"  {r['run_name']:<53} {jsd:>7} {was:>7} {mmd:>8} {gnd:>6} {ung:>6}")
    print("=" * 100)


if __name__ == "__main__":
    main()
