#!/bin/bash
# Setup conda environment on Rangpur for this project
# Run once: bash scripts/setup_rangpur.sh

set -e
ENV_NAME="investor_sim"

echo "Setting up ${ENV_NAME}..."

# Try to find conda
if ! command -v conda &>/dev/null; then
    echo "Looking for conda/modules..."
    module load anaconda3 2>/dev/null || \
    module load conda 2>/dev/null || \
    module load python/3.11 2>/dev/null || true
    
    if ! command -v conda &>/dev/null; then
        echo "ERROR: conda not found. Try:"
        echo "  module avail 2>&1 | grep -i conda"
        echo "  module avail 2>&1 | grep -i python"
        echo "  module avail 2>&1 | grep -i anaconda"
        exit 1
    fi
fi

conda create -n ${ENV_NAME} python=3.11 -y
conda activate ${ENV_NAME}

# Core dependencies
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate sentencepiece protobuf

# From existing requirements.txt
pip install pandas numpy scipy scikit-learn matplotlib sentence-transformers

echo ""
echo "Done! Usage:"
echo "  conda activate ${ENV_NAME}"
echo "  python -c \"import torch; print(torch.cuda.is_available())\""
