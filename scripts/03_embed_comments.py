"""
03_embed_comments.py
Embed all comments in data/processed/comments.csv using Sentence-BERT.
Model: all-MiniLM-L6-v2 (fast, 384-dim, good semantic quality)

Outputs:
    data/processed/comment_embeddings.npy  — float32 array (N, 384)
    data/processed/comments_with_index.csv — same rows as input, ordered

Run:
    python 03_embed_comments.py
"""

import os
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
INPUT_CSV = "data/processed/comments.csv"
EMB_OUT = "data/processed/comment_embeddings.npy"
INDEX_OUT = "data/processed/comments_with_index.csv"


def main():
    if not os.path.exists(INPUT_CSV):
        print(f"ERROR: {INPUT_CSV} not found.")
        print("Run 00_make_synthetic_data.py or 02_prepare_event_windows.py first.")
        return

    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} rows from {INPUT_CSV}")

    model = SentenceTransformer(MODEL_NAME)
    print(f"Encoding with {MODEL_NAME} ...")

    texts = df["text"].fillna("").tolist()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,   # unit-sphere norm → cosine = dot product
        show_progress_bar=True,
        batch_size=64,
    )

    os.makedirs("data/processed", exist_ok=True)
    np.save(EMB_OUT, embeddings)
    df.to_csv(INDEX_OUT, index=False)

    print(f"Saved embeddings: {embeddings.shape} -> {EMB_OUT}")
    print(f"Saved index CSV  -> {INDEX_OUT}")


if __name__ == "__main__":
    main()
