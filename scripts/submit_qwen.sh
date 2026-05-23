#!/bin/bash
#SBATCH --job-name=qwen_gen
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=outputs/logs/gen_%j.out
#SBATCH --error=outputs/logs/gen_%j.err

# NOTE: Check partition names with: sinfo -s
# Alternatives: --partition=gpu_a100, --partition=gpuq, --partition=ai
# If Rangpur uses PBS not SLURM, see submit_qwen_pbs.sh

echo "Job started: $(date)"
echo "Node: $(hostname)"
nvidia-smi

source activate investor_sim 2>/dev/null || conda activate investor_sim

cd ~/llm-investor-sim
mkdir -p outputs/logs

echo "=== Seed 42 ==="
python scripts/11_run_qwen_oneshot.py --n-per-archetype 50 --seed 42

echo "=== Seed 123 ==="
python scripts/11_run_qwen_oneshot.py --n-per-archetype 50 --seed 123 \
    --output-csv data/processed/sim_comments_qwen_oneshot_s123.csv

echo "Job finished: $(date)"
