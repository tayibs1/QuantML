# `data/` — Local data & model artifacts

Everything here is **generated** and git-ignored (only `.gitkeep` files are
tracked). Nothing in here is hand-edited.

```
data/
├── raw/          downloaded OHLCV + fundamentals (parquet/duckdb)   ← ml/ingestion
├── processed/    engineered feature matrices                        ← ml/features
├── models/       trained + registered model artifacts (.pkl/.onnx)  ← ml/training
└── vectorstore/  embeddings index for the RAG assistant             ← backend research
```

Regenerate it all from scratch with the `ml/` pipeline — see `ml/README.md`.

For production, swap the file stores for managed services (Postgres/Timescale for
prices, S3/GCS for model artifacts, a hosted vector DB for RAG).
