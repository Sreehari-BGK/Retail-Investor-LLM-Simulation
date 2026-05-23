#!/usr/bin/env python3
"""
13_prompt_condition_experiment.py

Prompt-condition ablation for NVDA_Q3FY26.

Runs three prompt × persona combinations with the same seed and the same
evaluation pipeline so the results are directly comparable.

Combinations
------------
  1. P0 + V0  — current baseline (preserves 11_run_qwen_oneshot.py exactly)
  2. P1 + V0  — balanced retail reaction
  3. P2 + V1  — behavior-first + three broad archetypes

Every run saves:
  - CSV of generated comments (schema matches sim_comments.csv)
  - JSONL with one metadata record per comment (prompt text, hyperparams, seed)
  - Metrics against real NVDA data (JSD stance, Wasserstein time, MMD semantic)

Usage
-----
  # Full run (requires GPU + model weights):
  python scripts/13_prompt_condition_experiment.py

  # Smoke test without model (placeholder text, full pipeline):
  python scripts/13_prompt_condition_experiment.py --dry-run

  # Override model or seed:
  python scripts/13_prompt_condition_experiment.py --model Qwen/Qwen2.5-7B-Instruct --seed 7

Outputs (all in outputs/)
-------------------------
  prompt_exp_P0_V0_comments.csv
  prompt_exp_P1_V0_comments.csv
  prompt_exp_P2_V1_comments.csv
  prompt_exp_all_comments.csv         — combined, ready for downstream analysis
  prompt_exp_metadata.jsonl           — per-comment metadata
  prompt_exp_metrics.json             — evaluation metrics per condition
  prompt_exp_summary.md               — human-readable comparison table
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
import uuid
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
OUTPUTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Import 04_compute_metrics (leading digit prevents normal import)
# ---------------------------------------------------------------------------
def _load_metrics_module():
    spec = importlib.util.spec_from_file_location(
        "compute_metrics",
        SCRIPTS_DIR / "04_compute_metrics.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# ---------------------------------------------------------------------------
# Event card  (NVDA Q3 FY2026)
# ---------------------------------------------------------------------------
EVENT_ID = "NVDA_Q3FY26"
EVENT_TIME_UTC = "2025-11-19T21:00:00Z"
EVENT_SUMMARY = (
    "NVIDIA reported Q3 FY2026 revenue of $57 billion, up 62% year-over-year, "
    "driven by strong data center demand and the Blackwell GPU production ramp. "
    "The company beat analyst expectations on both revenue and earnings per share. "
    "CEO Jensen Huang raised guidance for Q4, citing continued AI infrastructure demand. "
    "The stock had a mixed after-hours reaction despite the beat."
)

# ---------------------------------------------------------------------------
# Temporal distribution across event window
# Weights mirror the clustering seen in real Reddit activity.
# ---------------------------------------------------------------------------
_TEMPORAL_BUCKETS: list[tuple[float, float, float]] = [
    (-12.0,  -2.0, 0.10),   # pre-event anticipation
    (  0.0,   2.0, 0.40),   # immediate reaction
    (  2.0,  12.0, 0.30),   # digest / second take
    ( 12.0,  24.0, 0.15),   # follow-up
    ( 24.0,  48.0, 0.05),   # wind-down
]

def _sample_hours(n: int, seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    lows  = np.array([b[0] for b in _TEMPORAL_BUCKETS])
    highs = np.array([b[1] for b in _TEMPORAL_BUCKETS])
    wts   = np.array([b[2] for b in _TEMPORAL_BUCKETS])
    wts  /= wts.sum()
    idx   = rng.choice(len(_TEMPORAL_BUCKETS), size=n, p=wts)
    return [float(rng.uniform(lows[i], highs[i])) for i in idx]

# ---------------------------------------------------------------------------
# Rule-based stance labeler
# ---------------------------------------------------------------------------
_BULLISH_KW = {
    "buy", "long", "bullish", "growth", "upside", "beat", "strong",
    "bull", "great", "raised", "positive", "opportunity", "undervalued",
    "surge", "rally", "moon", "diamond", "hold", "accumulate",
    "impressive", "monster", "dominat", "ai demand", "blackwell",
    "explosive", "massive", "blew", "crush", "incredible", "love",
}
_BEARISH_KW = {
    "sell", "short", "bearish", "overvalued", "concern", "risk", "miss",
    "weak", "bear", "drop", "down", "expensive", "correction", "dump",
    "bubble", "priced in", "already priced", "cautious", "skeptic",
    "disappoint", "margin", "slowing", "peak", "worried", "warning",
    "not sure", "hesit", "wait", "pullback", "resistance",
}

def _label_stance(text: str) -> str:
    t = text.lower()
    b = sum(1 for kw in _BULLISH_KW if kw in t)
    r = sum(1 for kw in _BEARISH_KW if kw in t)
    if b == r:
        return "neutral"
    return "bullish" if b > r else "bearish"

# ---------------------------------------------------------------------------
# Persona sets
# ---------------------------------------------------------------------------

# V0: 9 archetypes (exactly as in 07_agent_simulation.py / 11_run_qwen_oneshot.py)
V0_PERSONAS: list[dict] = [
    {
        "archetype": "valuation-focused",
        "cohort": "long-horizon",
        "description": (
            "You are a long-term value investor who focuses on earnings quality, "
            "PE ratios, and whether the stock is fairly priced relative to future earnings."
        ),
        "style": (
            "Analytical but accessible. May mention multiples or growth rates. "
            "Skeptical of hype."
        ),
        "stance_weights": {"bullish": 0.40, "bearish": 0.25, "neutral": 0.35},
    },
    {
        "archetype": "fundamentals-focused",
        "cohort": "long-horizon",
        "description": (
            "You care deeply about business fundamentals: revenue growth, margins, "
            "competitive moat, and management quality."
        ),
        "style": (
            "Thoughtful. References business metrics. "
            "Not easily swayed by short-term price moves."
        ),
        "stance_weights": {"bullish": 0.50, "bearish": 0.20, "neutral": 0.30},
    },
    {
        "archetype": "buy-the-dip",
        "cohort": "long-horizon",
        "description": (
            "You see any pullback as a buying opportunity, "
            "especially in high-quality growth companies."
        ),
        "style": "Opportunistic. Optimistic on dips. Focused on long-term compounding.",
        "stance_weights": {"bullish": 0.65, "bearish": 0.10, "neutral": 0.25},
    },
    {
        "archetype": "momentum-following",
        "cohort": "short-horizon",
        "description": (
            "You follow price and volume momentum. "
            "Strong earnings beats that gap up are buy signals for you."
        ),
        "style": "Fast-paced. Focused on technicals and price action. Short-termist.",
        "stance_weights": {"bullish": 0.60, "bearish": 0.20, "neutral": 0.20},
    },
    {
        "archetype": "event-reactive",
        "cohort": "short-horizon",
        "description": (
            "You trade around specific events like earnings. "
            "You care about beats/misses and initial market reaction."
        ),
        "style": "Reactive. Focused on the immediate post-event price move. Decisive.",
        "stance_weights": {"bullish": 0.50, "bearish": 0.25, "neutral": 0.25},
    },
    {
        "archetype": "profit-taking",
        "cohort": "short-horizon",
        "description": (
            "You tend to lock in gains after strong runs, "
            "especially if the stock is already up a lot."
        ),
        "style": "Cautious optimist. Often sells into strength. Focused on risk/reward.",
        "stance_weights": {"bullish": 0.25, "bearish": 0.35, "neutral": 0.40},
    },
    {
        "archetype": "uncertain",
        "cohort": "info-seeking",
        "description": (
            "You are not sure how to interpret the earnings "
            "and want to hear more before acting."
        ),
        "style": "Hesitant. Asks questions. Waits for clarity. Does not rush to conclusions.",
        "stance_weights": {"bullish": 0.20, "bearish": 0.20, "neutral": 0.60},
    },
    {
        "archetype": "evidence-seeking",
        "cohort": "info-seeking",
        "description": (
            "You want to see the details: revenue breakdown, margin trends, "
            "guidance specifics, before committing."
        ),
        "style": "Methodical. References specific data points. Wants to verify before acting.",
        "stance_weights": {"bullish": 0.30, "bearish": 0.25, "neutral": 0.45},
    },
    {
        "archetype": "wait-and-see",
        "cohort": "info-seeking",
        "description": (
            "You prefer to watch how the stock reacts over the next few days "
            "rather than trading on day one."
        ),
        "style": "Patient. Observational. Does not feel urgency to act immediately.",
        "stance_weights": {"bullish": 0.25, "bearish": 0.20, "neutral": 0.55},
    },
]

# V1: 3 broad archetypes (behavior-first, simpler framing)
V1_PERSONAS: list[dict] = [
    {
        "archetype": "long_horizon",
        "cohort": "long-horizon",
        "description": (
            "A retail investor who thinks in years, not days. "
            "Cares about business quality, long-term growth, competitive position, "
            "and whether the stock will be worth more in 3-5 years. "
            "Less reactive to short-term price swings."
        ),
        "style": (
            "Measured. May reference fundamentals or valuation. "
            "Less reactive to short-term noise."
        ),
        "stance_weights": {"bullish": 0.45, "bearish": 0.20, "neutral": 0.35},
    },
    {
        "archetype": "short_horizon",
        "cohort": "short-horizon",
        "description": (
            "A retail investor focused on near-term price action, momentum, and tradeable setups. "
            "Reacts strongly to earnings beats/misses, guidance changes, and after-hours moves. "
            "More likely to express strong directional opinions."
        ),
        "style": (
            "Reactive, fast. Focused on charts, momentum, and the immediate market reaction."
        ),
        "stance_weights": {"bullish": 0.50, "bearish": 0.25, "neutral": 0.25},
    },
    {
        "archetype": "information_seeking",
        "cohort": "info-seeking",
        "description": (
            "A retail investor who is unsure, wants more data, or is trying to understand "
            "what the earnings mean before taking a position. "
            "Often expresses uncertainty, asks questions, or waits for more clarity."
        ),
        "style": (
            "Hesitant, questioning. May express confusion or ask for clarification. "
            "Avoids strong conclusions."
        ),
        "stance_weights": {"bullish": 0.20, "bearish": 0.20, "neutral": 0.60},
    },
]

# ---------------------------------------------------------------------------
# Prompt builders
# Each returns a list of chat messages: [{"role": ..., "content": ...}, ...]
# The exact text stored in run metadata comes from these functions.
# ---------------------------------------------------------------------------

def _build_P0(persona: dict, event_summary: str) -> list[dict]:
    """P0_baseline_current — preserve 11_run_qwen_oneshot.py exactly."""
    system = (
        "You are simulating a retail investor posting on Reddit after NVIDIA's earnings announcement. "
        "Write exactly ONE short Reddit-style comment (1-4 sentences max). "
        "Rules: Use casual Reddit language, not formal finance writing. "
        "Reference specific facts from the earnings when relevant to your persona. "
        "Do NOT write disclaimers, headers, or break character. "
        "Do NOT say 'As a [type] investor'. Output ONLY the comment text."
    )
    user = (
        f"EARNINGS EVENT:\n{event_summary}\n\n"
        f"YOUR INVESTOR PROFILE:\n{persona['description']}\n\n"
        f"WRITING STYLE:\n{persona['style']}\n\n"
        "Write one Reddit comment from this investor's perspective about this NVIDIA earnings result. "
        "Only output the comment text."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _build_P1(persona: dict, event_summary: str) -> list[dict]:
    """P1_balanced_retail_reaction — reduce over-bullishness and summary tone."""
    system = (
        "You are writing like a retail investor commenting on Reddit after a company earnings event.\n\n"
        "Write one short Reddit-style comment reacting to the event.\n\n"
        "Important:\n"
        "- React like a person, not like a financial report.\n"
        "- You may be bullish, bearish, neutral, or unsure.\n"
        "- Focus on expectations, surprise, risk, sentiment, valuation, guidance, "
        "or what this could mean next.\n"
        "- You do not need to mention every fact from the event.\n"
        "- Do not over-explain.\n"
        "- Do not sound like an analyst note.\n"
        "- Casual language is fine, but stay coherent.\n"
        "- It is okay to be uncertain or conflicted.\n"
        "- Avoid always sounding optimistic.\n\n"
        "Output only the comment text."
    )
    user = (
        f"EARNINGS EVENT:\n{event_summary}\n\n"
        f"YOUR INVESTOR PROFILE:\n{persona['description']}\n\n"
        f"WRITING STYLE:\n{persona['style']}\n\n"
        "Write one Reddit comment reacting to these earnings. "
        "Only output the comment text."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _build_P2(persona: dict, event_summary: str) -> list[dict]:
    """P2_behavior_first_diversity — target uniformity failure, vary behaviour."""
    system = (
        "You are simulating one Reddit user reacting to a company earnings event.\n\n"
        "Write one short comment that reflects how this kind of user would actually react online.\n\n"
        "The comment should reflect the user's behaviour, priorities, and time horizon "
        "more than perfect factual coverage.\n\n"
        "Possible behaviours include:\n"
        "- excitement\n"
        "- skepticism\n"
        "- confusion\n"
        "- caution\n"
        "- fear of missing out\n"
        "- concern about valuation\n"
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
    user = (
        f"EARNINGS EVENT:\n{event_summary}\n\n"
        f"USER TYPE: {persona['archetype'].replace('_', ' ').title()}\n"
        f"BEHAVIOUR PROFILE:\n{persona['description']}\n\n"
        "Write one Reddit comment from this user's perspective. "
        "Only output the comment text."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


_PROMPT_BUILDERS = {
    "P0_baseline_current":        _build_P0,
    "P1_balanced_retail_reaction": _build_P1,
    "P2_behavior_first_diversity": _build_P2,
}

# ---------------------------------------------------------------------------
# Experiment grid
# Total generated comments per condition = n_per_archetype × len(personas) = 27
# ---------------------------------------------------------------------------
EXPERIMENT_GRID: list[dict] = [
    {
        "prompt_version":  "P0_baseline_current",
        "persona_version": "V0_current",
        "personas":        V0_PERSONAS,
        "n_per_archetype": 3,   # 9 archetypes × 3 = 27
    },
    {
        "prompt_version":  "P1_balanced_retail_reaction",
        "persona_version": "V0_current",
        "personas":        V0_PERSONAS,
        "n_per_archetype": 3,   # 9 × 3 = 27
    },
    {
        "prompt_version":  "P2_behavior_first_diversity",
        "persona_version": "V1_three_archetypes",
        "personas":        V1_PERSONAS,
        "n_per_archetype": 9,   # 3 archetypes × 9 = 27
    },
]

# ---------------------------------------------------------------------------
# LLM generation
# ---------------------------------------------------------------------------

def _load_model(model_name: str):
    """Load Qwen tokenizer and model.  Returns (tokenizer, model, device)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"[model] Loading {model_name} ...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype="auto",
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    print(f"[model] Loaded on {device}.")
    return tokenizer, model, device


def _generate_one(
    tokenizer,
    model,
    messages: list[dict],
    temperature: float,
    top_p: float,
    top_k: int,
    max_new_tokens: int,
    gen_seed: int,
) -> str:
    """Run one chat-format inference call; return stripped text."""
    import torch

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer([text], return_tensors="pt").to(model.device)

    with torch.no_grad():
        torch.manual_seed(gen_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(gen_seed)
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    new_tokens = out[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def _generate_dry_run(messages: list[dict], archetype: str, idx: int) -> str:
    """Return placeholder text when --dry-run is set (no model required)."""
    placeholders = [
        f"[DRY-RUN] {archetype} comment {idx}: Interesting earnings, watching closely.",
        f"[DRY-RUN] {archetype} comment {idx}: Not sure what to make of this tbh.",
        f"[DRY-RUN] {archetype} comment {idx}: Might add more if it dips.",
    ]
    return placeholders[idx % len(placeholders)]

# ---------------------------------------------------------------------------
# Embedding (SBERT)
# ---------------------------------------------------------------------------

def _embed_texts(texts: list[str]) -> np.ndarray:
    """Embed texts with all-MiniLM-L6-v2; returns L2-normalised float32 array."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = model.encode(
        texts,
        batch_size=64,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 20,
        convert_to_numpy=True,
    )
    return emb.astype(np.float32)

# ---------------------------------------------------------------------------
# Evaluation against real NVDA data
# ---------------------------------------------------------------------------

def _load_real_data() -> tuple[pd.DataFrame | None, np.ndarray | None]:
    """
    Try to load curated real NVDA comments and their embeddings.
    Returns (df, embeddings) or (None, None) if files are missing.
    """
    candidates_csv = [
        DATA_DIR / "real_comments_curated_labeled.csv",
        DATA_DIR / "comments.csv",
    ]
    candidates_emb = [
        DATA_DIR / "real_comment_embeddings_curated.npy",
        DATA_DIR / "comment_embeddings.npy",
    ]

    df_path = next((p for p in candidates_csv if p.exists()), None)
    emb_path = next((p for p in candidates_emb if p.exists()), None)

    if df_path is None:
        print("[eval] No real comment CSV found — skipping metric evaluation.")
        return None, None

    df = pd.read_csv(df_path)
    # Filter to NVDA event if event_id column present
    if "event_id" in df.columns:
        df = df[df["event_id"] == EVENT_ID].copy()
    if df.empty:
        print(f"[eval] No rows for event_id={EVENT_ID} — skipping evaluation.")
        return None, None

    emb = None
    if emb_path is not None:
        try:
            full_emb = np.load(emb_path)
            # If we filtered rows, try to align by position or index
            if len(full_emb) == len(df):
                emb = full_emb
            elif "comments_with_index.csv" in str(emb_path) or len(full_emb) >= len(df):
                emb = full_emb[: len(df)]
        except Exception as e:
            print(f"[eval] Could not load embeddings ({e}); will embed on-the-fly.")

    return df, emb


def _evaluate(
    sim_df: pd.DataFrame,
    sim_emb: np.ndarray,
    real_df: pd.DataFrame,
    real_emb: np.ndarray | None,
    metrics_mod,
) -> dict:
    """Run all three metrics; return dict with float values."""
    results: dict[str, float | str] = {}

    # --- JSD stance ---
    try:
        real_stance = real_df["stance"].tolist() if "stance" in real_df.columns else []
        sim_stance  = sim_df["stance"].tolist()
        if real_stance and sim_stance:
            results["jsd_stance"] = float(metrics_mod.jsd_stance(real_stance, sim_stance))
        else:
            results["jsd_stance"] = "n/a (missing stance column)"
    except Exception as e:
        results["jsd_stance"] = f"error: {e}"

    # --- Wasserstein time ---
    try:
        real_h = real_df["hours_from_event"].dropna().tolist() if "hours_from_event" in real_df.columns else []
        sim_h  = sim_df["hours_from_event"].dropna().tolist()
        if real_h and sim_h:
            results["wasserstein_time"] = float(metrics_mod.wasserstein_time(real_h, sim_h))
        else:
            results["wasserstein_time"] = "n/a (missing hours_from_event)"
    except Exception as e:
        results["wasserstein_time"] = f"error: {e}"

    # --- MMD semantic ---
    try:
        # Embed real comments if we don't have pre-computed embeddings
        if real_emb is None:
            print("[eval] Embedding real comments on-the-fly ...")
            real_emb = _embed_texts(real_df["text"].tolist())
        results["mmd_semantic"] = float(metrics_mod.mmd_rbf(real_emb, sim_emb))
    except Exception as e:
        results["mmd_semantic"] = f"error: {e}"

    return results

# ---------------------------------------------------------------------------
# One experiment run
# ---------------------------------------------------------------------------

def run_experiment(
    condition: dict,
    model_name: str,
    temperature: float,
    top_p: float,
    top_k: int,
    max_new_tokens: int,
    base_seed: int,
    dry_run: bool,
    tokenizer,
    model,
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Generate all comments for one condition.
    Returns (comments_df, metadata_records).
    """
    prompt_version  = condition["prompt_version"]
    persona_version = condition["persona_version"]
    personas        = condition["personas"]
    n_per_archetype = condition["n_per_archetype"]
    build_fn        = _PROMPT_BUILDERS[prompt_version]

    total_n = len(personas) * n_per_archetype
    hours   = _sample_hours(total_n, seed=base_seed)

    rows: list[dict] = []
    meta_records: list[dict] = []
    global_idx = 0

    for persona in personas:
        archetype = persona["archetype"]
        sw = persona["stance_weights"]
        rng = np.random.default_rng(base_seed + hash(archetype) % (2**31))

        for local_idx in range(n_per_archetype):
            gen_seed = base_seed + global_idx
            messages = build_fn(persona, EVENT_SUMMARY)

            # --- Generate text ---
            if dry_run:
                text = _generate_dry_run(messages, archetype, local_idx)
            else:
                text = _generate_one(
                    tokenizer, model, messages,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    max_new_tokens=max_new_tokens,
                    gen_seed=gen_seed,
                )

            # --- Stance: rule-based post-hoc label ---
            stance = _label_stance(text)

            comment_id = f"sim_{prompt_version}_{persona_version}_{archetype}_{local_idx}"
            h = hours[global_idx]

            row = {
                "event_id":         EVENT_ID,
                "ticker":           "NVDA",
                "event_time":       EVENT_TIME_UTC,
                "subreddit":        "wallstreetbets",   # default, consistent with pilot
                "thread_id":        f"thread_{prompt_version}_{archetype}",
                "comment_id":       comment_id,
                "parent_id":        f"thread_{prompt_version}_{archetype}",
                "hours_from_event": round(h, 4),
                "text":             text,
                "score":            0,
                "depth":            0,
                "source_type":      "sim_agent",
                "stance":           stance,
                # Extra tracking columns
                "prompt_version":   prompt_version,
                "persona_version":  persona_version,
                "archetype":        archetype,
                "cohort":           persona["cohort"],
            }
            rows.append(row)

            meta = {
                # Identity
                "comment_id":       comment_id,
                "prompt_version":   prompt_version,
                "persona_version":  persona_version,
                "archetype":        archetype,
                "cohort":           persona["cohort"],
                "local_idx":        local_idx,
                "global_idx":       global_idx,
                # Model hyperparameters
                "model_name":       model_name,
                "temperature":      temperature,
                "top_p":            top_p,
                "top_k":            top_k,
                "max_new_tokens":   max_new_tokens,
                "base_seed":        base_seed,
                "gen_seed":         gen_seed,
                # Exact prompts (preserved verbatim for report)
                "system_prompt":    messages[0]["content"],
                "user_prompt":      messages[1]["content"],
                # Output
                "text":             text,
                "stance":           stance,
                "hours_from_event": round(h, 4),
                "dry_run":          dry_run,
                "generated_at":     datetime.utcnow().isoformat() + "Z",
            }
            meta_records.append(meta)
            global_idx += 1

    df = pd.DataFrame(rows)
    return df, meta_records


# ---------------------------------------------------------------------------
# Summary markdown
# ---------------------------------------------------------------------------

def _build_summary_md(
    all_metrics: dict[str, dict],
    all_dfs: dict[str, pd.DataFrame],
    model_name: str,
    base_seed: int,
    temperature: float,
    top_p: float,
    top_k: int,
    max_new_tokens: int,
    dry_run: bool,
) -> str:
    lines = [
        "# Prompt Condition Experiment — NVDA Q3 FY2026",
        "",
        f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Model:** `{model_name}`  ",
        f"**Temperature:** {temperature} | **Top-p:** {top_p} | "
        f"**Top-k:** {top_k} | **Max new tokens:** {max_new_tokens}  ",
        f"**Base seed:** {base_seed}  ",
        f"**Dry run:** {dry_run}",
        "",
        "---",
        "",
        "## Combinations Run",
        "",
        "| # | Prompt | Persona | N comments |",
        "|---|--------|---------|------------|",
    ]
    for i, cond in enumerate(EXPERIMENT_GRID, 1):
        n = len(cond["personas"]) * cond["n_per_archetype"]
        lines.append(
            f"| {i} | `{cond['prompt_version']}` "
            f"| `{cond['persona_version']}` | {n} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Evaluation Metrics vs Real NVDA Data",
        "",
        "| Condition | JSD Stance ↓ | Wasserstein Time ↓ | MMD Semantic ↓ |",
        "|-----------|-------------|-------------------|----------------|",
    ]
    for key, m in all_metrics.items():
        jsd  = f"{m['jsd_stance']:.4f}"       if isinstance(m.get("jsd_stance"), float)       else str(m.get("jsd_stance", "n/a"))
        was  = f"{m['wasserstein_time']:.4f}"  if isinstance(m.get("wasserstein_time"), float)  else str(m.get("wasserstein_time", "n/a"))
        mmd  = f"{m['mmd_semantic']:.4f}"      if isinstance(m.get("mmd_semantic"), float)      else str(m.get("mmd_semantic", "n/a"))
        lines.append(f"| `{key}` | {jsd} | {was} | {mmd} |")

    lines += [
        "",
        "↓ = lower is more similar to real data",
        "",
        "---",
        "",
        "## Stance Distribution per Condition",
        "",
        "| Condition | % Bullish | % Bearish | % Neutral | N |",
        "|-----------|-----------|-----------|-----------|---|",
    ]
    for key, df in all_dfs.items():
        vc = df["stance"].value_counts(normalize=True)
        b  = f"{vc.get('bullish', 0)*100:.1f}%"
        br = f"{vc.get('bearish', 0)*100:.1f}%"
        n_  = f"{vc.get('neutral', 0)*100:.1f}%"
        lines.append(f"| `{key}` | {b} | {br} | {n_} | {len(df)} |")

    lines += [
        "",
        "---",
        "",
        "## Output Files",
        "",
        "| File | Contents |",
        "|------|----------|",
        "| `prompt_exp_P0_V0_comments.csv` | P0+V0 generated comments |",
        "| `prompt_exp_P1_V0_comments.csv` | P1+V0 generated comments |",
        "| `prompt_exp_P2_V1_comments.csv` | P2+V1 generated comments |",
        "| `prompt_exp_all_comments.csv` | All conditions combined |",
        "| `prompt_exp_metadata.jsonl` | Per-comment: exact prompts + hyperparams |",
        "| `prompt_exp_metrics.json` | Evaluation metrics per condition |",
        "| `prompt_exp_summary.md` | This file |",
        "",
        "## Notes",
        "",
        "- All three conditions use **the same base seed** (`base_seed`), "
        "with `gen_seed = base_seed + global_comment_index`.",
        "- `hours_from_event` is sampled from the same temporal distribution "
        "(bucket weights: 10% pre-event, 40% immediate, 30% digest, 15% follow-up, 5% wind-down).",
        "- Stance is assigned post-hoc using the rule-based keyword labeler "
        "(`_label_stance` in this script); not pre-assigned by the model.",
        "- Evaluation is skipped gracefully if real NVDA data files are absent.",
    ]

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prompt condition ablation — NVDA")
    p.add_argument("--model",          default="Qwen/Qwen2.5-3B-Instruct")
    p.add_argument("--seed",           type=int,   default=42)
    p.add_argument("--temperature",    type=float, default=0.9)
    p.add_argument("--top-p",          type=float, default=0.95,  dest="top_p")
    p.add_argument("--top-k",          type=int,   default=50,    dest="top_k")
    p.add_argument("--max-new-tokens", type=int,   default=150,   dest="max_new_tokens")
    p.add_argument(
        "--dry-run", action="store_true",
        help="Skip model loading; use placeholder text. Tests the full pipeline without GPU.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("Prompt Condition Experiment — NVDA_Q3FY26")
    print("=" * 60)
    print(f"  Model:          {args.model}")
    print(f"  Seed:           {args.seed}")
    print(f"  Temperature:    {args.temperature}")
    print(f"  Top-p:          {args.top_p}")
    print(f"  Top-k:          {args.top_k}")
    print(f"  Max new tokens: {args.max_new_tokens}")
    print(f"  Dry run:        {args.dry_run}")
    print()

    # Load metric module
    metrics_mod = _load_metrics_module()

    # Load model (skip on dry-run)
    tokenizer = model = None
    if not args.dry_run:
        tokenizer, model, _ = _load_model(args.model)

    # Load real data once (shared across all conditions)
    real_df, real_emb = _load_real_data()

    all_dfs: dict[str, pd.DataFrame] = {}
    all_meta: list[dict] = []
    all_metrics: dict[str, dict] = {}

    for cond in EXPERIMENT_GRID:
        label = f"{cond['prompt_version']}__{cond['persona_version']}"
        print(f"\n{'─'*60}")
        print(f"Running: {label}")
        print(f"  Personas: {len(cond['personas'])} archetypes × {cond['n_per_archetype']} = "
              f"{len(cond['personas']) * cond['n_per_archetype']} comments")
        print(f"{'─'*60}")

        t0 = time.time()
        df, meta_records = run_experiment(
            condition=cond,
            model_name=args.model,
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=args.top_k,
            max_new_tokens=args.max_new_tokens,
            base_seed=args.seed,
            dry_run=args.dry_run,
            tokenizer=tokenizer,
            model=model,
        )
        elapsed = time.time() - t0
        print(f"  Generated {len(df)} comments in {elapsed:.1f}s")

        # Embed generated comments
        print("  Embedding generated comments ...")
        try:
            sim_emb = _embed_texts(df["text"].tolist())
        except Exception as e:
            print(f"  [warn] Embedding failed ({e}); using random vectors for MMD.")
            sim_emb = np.random.default_rng(args.seed).standard_normal(
                (len(df), 384)
            ).astype(np.float32)

        # Evaluate
        if real_df is not None:
            print("  Evaluating metrics ...")
            metrics = _evaluate(df, sim_emb, real_df, real_emb, metrics_mod)
        else:
            metrics = {
                "jsd_stance":       "n/a (no real data)",
                "wasserstein_time": "n/a (no real data)",
                "mmd_semantic":     "n/a (no real data)",
            }

        print(f"  JSD stance:       {metrics['jsd_stance']}")
        print(f"  Wasserstein time: {metrics['wasserstein_time']}")
        print(f"  MMD semantic:     {metrics['mmd_semantic']}")

        # Save per-condition CSV
        short_label = (
            "P0_V0" if "P0" in label else
            "P1_V0" if "P1" in label else
            "P2_V1"
        )
        csv_path = OUTPUTS_DIR / f"prompt_exp_{short_label}_comments.csv"
        df.to_csv(csv_path, index=False)
        print(f"  Saved → {csv_path.name}")

        all_dfs[short_label] = df
        all_meta.extend(meta_records)
        all_metrics[short_label] = metrics

    # Combined CSV
    combined_df = pd.concat(list(all_dfs.values()), ignore_index=True)
    combined_path = OUTPUTS_DIR / "prompt_exp_all_comments.csv"
    combined_df.to_csv(combined_path, index=False)

    # Metadata JSONL
    meta_path = OUTPUTS_DIR / "prompt_exp_metadata.jsonl"
    with open(meta_path, "w", encoding="utf-8") as f:
        for rec in all_meta:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Metrics JSON
    metrics_path = OUTPUTS_DIR / "prompt_exp_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False)

    # Summary markdown
    summary_md = _build_summary_md(
        all_metrics=all_metrics,
        all_dfs=all_dfs,
        model_name=args.model,
        base_seed=args.seed,
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        max_new_tokens=args.max_new_tokens,
        dry_run=args.dry_run,
    )
    summary_path = OUTPUTS_DIR / "prompt_exp_summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_md)

    print("\n" + "=" * 60)
    print("Done.")
    print(f"  Combined CSV:    {combined_path.name}")
    print(f"  Metadata JSONL:  {meta_path.name}")
    print(f"  Metrics JSON:    {metrics_path.name}")
    print(f"  Summary MD:      {summary_path.name}")
    print("=" * 60)


if __name__ == "__main__":
    main()
