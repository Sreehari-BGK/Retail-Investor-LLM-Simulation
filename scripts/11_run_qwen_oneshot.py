#!/usr/bin/env python3
"""
11_run_qwen_oneshot.py — Generate investor comments using an open-weight LLM
=============================================================================
Replaces template-based comments from 07_agent_simulation.py with actual
LLM-generated text. Outputs match the existing sim_comments.csv schema so
the evaluation pipeline (04_compute_metrics, 09_real_vs_sim) works unchanged.

Usage (interactive GPU session on Rangpur):
    srun --gres=gpu:1 --mem=24G --time=02:00:00 --pty bash
    conda activate investor_sim
    python scripts/11_run_qwen_oneshot.py --n-per-archetype 50 --seed 42

Usage (batch):
    sbatch scripts/submit_qwen.sh

Outputs:
    data/processed/sim_comments_qwen_oneshot.csv
    data/processed/sim_comments_qwen_oneshot.jsonl  (backup with full metadata)
"""

import argparse
import json
import random
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ── Project paths ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"
CARDS_DIR = ROOT / "data" / "event_cards"
PROMPTS_DIR = ROOT / "prompts"

# ── Event constants ────────────────────────────────────────────────────────
EVENT_ID   = "NVDA_Q3FY26"
TICKER     = "NVDA"
EVENT_TIME = datetime(2025, 11, 19, 21, 0, 0, tzinfo=timezone.utc)

EVENT_SUMMARY = (
    "NVIDIA reported Q3 FY2026 revenue of $57 billion, up 62% year-over-year, "
    "driven by strong data center demand and the Blackwell GPU production ramp. "
    "The company beat analyst expectations on both revenue and earnings. "
    "CEO Jensen Huang raised guidance for Q4, citing continued AI infrastructure demand. "
    "The stock had mixed after-hours reaction despite the beat."
)

# ── Archetype definitions (matches 07_agent_simulation.py structure) ──────
ARCHETYPES = {
    "valuation-focused": {
        "cohort": "long-horizon",
        "description": "Evaluates NVIDIA on valuation metrics like P/E, forward growth vs price. Holds long-term positions. Skeptical of paying premium multiples even for good results.",
        "style": "Measured analysis, references valuation. 1-3 sentences, Reddit casual tone."
    },
    "fundamentals-focused": {
        "cohort": "long-horizon",
        "description": "Focuses on revenue growth trajectory, data center TAM, competitive position. Long-term thesis holder. Cares about whether the growth story is intact.",
        "style": "Substantive, references specific financial metrics. Reddit casual tone, 1-3 sentences."
    },
    "buy-the-dip": {
        "cohort": "long-horizon",
        "description": "Looks for entry points on pullbacks. Generally bullish on NVIDIA long-term. If earnings are good but stock dips, sees it as opportunity.",
        "style": "Confident and opportunistic. Short punchy Reddit comment. 1-2 sentences."
    },
    "momentum-following": {
        "cohort": "short-horizon",
        "description": "Trades based on price momentum and technical signals. Cares about after-hours reaction, volume, and whether to ride the wave or exit.",
        "style": "Uses trader slang, references price action. Short, informal. 1-2 sentences."
    },
    "event-reactive": {
        "cohort": "short-horizon",
        "description": "Reacts quickly to earnings headlines. May hold options or short-dated positions. Focuses on beat/miss magnitude and immediate price response.",
        "style": "Fast, emotional, uses WSB slang. References options, IV crush, AH moves. 1-2 sentences."
    },
    "profit-taking": {
        "cohort": "short-horizon",
        "description": "Has been holding NVIDIA and considering whether to lock in gains. Weighs whether the good earnings justify continued holding or if it's time to sell.",
        "style": "Cautious, mentions position sizing or exits. Reddit casual. 1-2 sentences."
    },
    "uncertain": {
        "cohort": "info-seeking",
        "description": "Not sure what to make of the earnings. New to NVIDIA or investing generally. Asks questions and looks for others' opinions.",
        "style": "Questioning, sometimes confused, asks for help. Casual Reddit language. 1-2 sentences."
    },
    "evidence-seeking": {
        "cohort": "info-seeking",
        "description": "Wants to dig into the details before forming an opinion. Asks about specific line items, margins, guidance details, or competitive threats.",
        "style": "Analytical but uncertain. Asks specific questions about the numbers. 1-3 sentences."
    },
    "wait-and-see": {
        "cohort": "info-seeking",
        "description": "Watching from the sidelines. Interested but not ready to commit. Wants to see how the market digests the news before acting.",
        "style": "Cautious observer. May express interest without commitment. 1-2 sentences."
    },
}

SYSTEM_PROMPT = (
    "You are simulating a retail investor posting on Reddit after NVIDIA's earnings announcement. "
    "Write exactly ONE short Reddit-style comment (1-4 sentences max). "
    "Rules: Use casual Reddit language, not formal finance writing. "
    "Reference specific facts from the earnings when relevant to your persona. "
    "Do NOT write disclaimers, headers, or break character. "
    "Do NOT say 'As a [type] investor'. Output ONLY the comment text."
)

USER_TEMPLATE = """EARNINGS EVENT:
{event_summary}

YOUR INVESTOR PROFILE:
{description}

WRITING STYLE:
{style}

Write one Reddit comment from this investor's perspective about this NVIDIA earnings result. Only output the comment text."""


def assign_hour_bin(archetype_id: str, rng: random.Random) -> float:
    """Assign plausible hours_from_event based on archetype behavior."""
    cohort = ARCHETYPES[archetype_id]["cohort"]
    if cohort == "short-horizon":
        h = rng.gauss(2, 3)
        return round(max(-1, min(12, h)), 2)
    elif cohort == "long-horizon":
        h = rng.gauss(10, 10)
        return round(max(-6, min(48, h)), 2)
    else:  # info-seeking
        h = rng.gauss(6, 6)
        return round(max(0, min(36, h)), 2)


def assign_depth(rng: random.Random) -> int:
    """Most one-shot comments are top-level or first reply."""
    return rng.choices([0, 1, 2], weights=[0.5, 0.35, 0.15])[0]


def main():
    parser = argparse.ArgumentParser(
        description="Generate one-shot investor comments with Qwen"
    )
    parser.add_argument("--n-per-archetype", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--max-new-tokens", type=int, default=150)
    parser.add_argument("--output-csv", default=None,
                        help="Override output path (default: data/processed/sim_comments_qwen_oneshot.csv)")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts without running model (for debugging)")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    np.random.seed(args.seed)

    output_csv = args.output_csv or str(DATA_DIR / "sim_comments_qwen_oneshot.csv")
    output_jsonl = output_csv.replace(".csv", ".jsonl")

    print(f"{'='*60}")
    print(f"  LLM One-Shot Generation")
    print(f"{'='*60}")
    print(f"  Model:            {args.model}")
    print(f"  N per archetype:  {args.n_per_archetype}")
    print(f"  Total comments:   {args.n_per_archetype * len(ARCHETYPES)}")
    print(f"  Seed:             {args.seed}")
    print(f"  Temperature:      {args.temperature}")
    print(f"  Output:           {output_csv}")

    if args.dry_run:
        print("\n  DRY RUN — printing first prompt only\n")
        arch_id = list(ARCHETYPES.keys())[0]
        arch = ARCHETYPES[arch_id]
        user_msg = USER_TEMPLATE.format(
            event_summary=EVENT_SUMMARY,
            description=arch["description"],
            style=arch["style"]
        )
        print(f"SYSTEM: {SYSTEM_PROMPT}\n")
        print(f"USER: {user_msg}\n")
        return

    # ── Load model ─────────────────────────────────────────────────────────
    print("\nLoading model...")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map=device if device == "cuda" else None,
        trust_remote_code=True,
    )
    if device == "cpu":
        model = model.to("cpu")
    model.eval()
    print(f"  Model loaded on {device}")

    # ── Generate ───────────────────────────────────────────────────────────
    records = []
    total = args.n_per_archetype * len(ARCHETYPES)
    count = 0

    for arch_id, arch_info in ARCHETYPES.items():
        print(f"\n  Generating {args.n_per_archetype} for: {arch_id}")

        for i in range(args.n_per_archetype):
            count += 1
            gen_seed = args.seed * 10000 + count
            torch.manual_seed(gen_seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(gen_seed)

            user_msg = USER_TEMPLATE.format(
                event_summary=EVENT_SUMMARY,
                description=arch_info["description"],
                style=arch_info["style"]
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ]

            text_input = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = tokenizer(text_input, return_tensors="pt").to(model.device)

            with torch.no_grad():
                output_ids = model.generate(
                    **inputs,
                    max_new_tokens=args.max_new_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                )

            generated = tokenizer.decode(
                output_ids[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True,
            ).strip()

            # Clean: take only first paragraph if model over-generates
            if "\n\n" in generated:
                generated = generated.split("\n\n")[0].strip()
            # Remove any quotes the model wraps around
            if generated.startswith('"') and generated.endswith('"'):
                generated = generated[1:-1].strip()

            hours = assign_hour_bin(arch_id, rng)
            sim_ts = EVENT_TIME + timedelta(hours=hours)
            depth = assign_depth(rng)

            record = {
                # Match sim_comments.csv schema exactly
                "event_id": EVENT_ID,
                "ticker": TICKER,
                "event_time": EVENT_TIME.isoformat(),
                "round_id": 0,  # one-shot = single round
                "agent_id": f"{arch_id}_{i:03d}",
                "archetype": arch_id,
                "broad_cohort": arch_info["cohort"],
                "comment_id": f"qwen_{arch_id}_{args.seed}_{i:03d}",
                "parent_id": "",
                "hours_from_event": hours,
                "text": generated,
                "stance": "",  # will be labeled by label_stance_rulebased.py
                "source_type": "sim_qwen_oneshot",
                "simulated_timestamp": sim_ts.isoformat(),
                "depth": depth,
                # Extra metadata
                "model_name": args.model,
                "seed": args.seed,
                "gen_seed": gen_seed,
                "temperature": args.temperature,
                "prompt_version": "v1",
            }
            records.append(record)

            if count % 20 == 0:
                print(f"    [{count}/{total}] {generated[:80]}...")

    # ── Save ───────────────────────────────────────────────────────────────
    df = pd.DataFrame(records)

    # CSV (matching existing schema — drop extra metadata cols)
    csv_cols = [
        "event_id", "ticker", "event_time", "round_id", "agent_id",
        "archetype", "broad_cohort", "comment_id", "parent_id",
        "hours_from_event", "text", "stance", "source_type",
        "simulated_timestamp", "depth"
    ]
    df[csv_cols].to_csv(output_csv, index=False)
    print(f"\n  CSV saved: {output_csv} ({len(df)} rows)")

    # JSONL (full metadata for reproducibility)
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  JSONL saved: {output_jsonl}")

    # ── Quick stats ────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Generation Summary")
    print(f"{'='*60}")
    for aid in ARCHETYPES:
        subset = [r for r in records if r["archetype"] == aid]
        avg_words = np.mean([len(r["text"].split()) for r in subset])
        avg_chars = np.mean([len(r["text"]) for r in subset])
        print(f"  {aid:<24} {len(subset):>3} comments, "
              f"avg {avg_words:.0f} words, {avg_chars:.0f} chars")

    print(f"\n  Next steps:")
    print(f"    1. Read outputs:  head -5 {output_csv}")
    print(f"    2. Label stance:  python scripts/label_stance_rulebased.py")
    print(f"    3. Embed:         python scripts/03_embed_comments.py  (adapt for new file)")
    print(f"    4. Compare:       python scripts/09_real_vs_sim.py     (point to new file)")


if __name__ == "__main__":
    main()
