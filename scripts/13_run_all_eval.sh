#!/bin/bash
# 13_run_all_eval.sh — Run complete evaluation pipeline
# No GPU needed. Run after 11_run_qwen_oneshot.py completes.
#
# Usage: bash scripts/13_run_all_eval.sh

set -e
cd "$(dirname "$0")/.."

echo "============================================"
echo "  Running full evaluation pipeline"
echo "============================================"

# Step 1: Label stances on the new Qwen outputs
echo ""
echo "--- Labeling stances for Qwen outputs ---"
if [ -f data/processed/sim_comments_qwen_oneshot.csv ]; then
    python3 scripts/label_stance_rulebased.py \
        --input data/processed/sim_comments_qwen_oneshot.csv \
        --output data/processed/sim_comments_qwen_oneshot_labeled.csv \
        2>/dev/null || echo "  (stance labeler needs adaptation — will use eval_similarity fallback)"
fi

# Step 2: Financial grounding — real data
echo ""
echo "--- Grounding: Real data ---"
python3 scripts/12_eval_grounding.py \
    --input data/processed/real_comments_curated.csv \
    --label real

# Step 3: Financial grounding — template sim
echo ""
echo "--- Grounding: Template simulation ---"
if [ -f data/processed/sim_comments.csv ]; then
    python3 scripts/12_eval_grounding.py \
        --input data/processed/sim_comments.csv \
        --label template
fi

# Step 4: Financial grounding — Qwen one-shot
echo ""
echo "--- Grounding: Qwen one-shot ---"
if [ -f data/processed/sim_comments_qwen_oneshot.csv ]; then
    python3 scripts/12_eval_grounding.py \
        --input data/processed/sim_comments_qwen_oneshot.csv \
        --label qwen_oneshot
fi

# Step 5: Run existing real-vs-sim comparison (09_real_vs_sim.py)
# This needs the embeddings. If not computed yet, compute them.
echo ""
echo "--- Similarity metrics (using existing pipeline) ---"
echo "  Run manually:"
echo "    python scripts/09_real_vs_sim.py"
echo "  (may need to point it to the new Qwen CSV)"

# Step 6: Print results
echo ""
echo "============================================"
echo "  RESULTS SUMMARY"
echo "============================================"

if [ -f outputs/grounding_comparison.csv ]; then
    echo ""
    echo "--- Financial Grounding ---"
    column -t -s',' outputs/grounding_comparison.csv 2>/dev/null || cat outputs/grounding_comparison.csv
fi

if [ -f outputs/real_vs_sim_metrics.json ]; then
    echo ""
    echo "--- Existing real-vs-sim metrics ---"
    cat outputs/real_vs_sim_metrics.json
fi

echo ""
echo "Done. Check outputs/ for all results."
