# BetaVest - FinTech Project Part B

Part B extends the BetaVest Part A data foundation into investable funds,
sentiment analytics, a fusion test, and a Streamlit app.

BetaVest is a prototype investment platform for young retail investors. Part A
verified the equity price panel, crypto price panel, and equity-news text panel.
Part B turns those inputs into out-of-sample fund evidence and an investor-facing
app.

## Run Order

From this folder:

```bash
python scripts/run_part_b.py
streamlit run streamlit_app.py
python scripts/check_handin.py
git status
```

From the repo root with the shared virtual environment:

```bash
./.venv/bin/python fins2026/z5532834_projectB/scripts/run_part_b.py
./.venv/bin/python fins2026/z5532834_projectB/scripts/check_handin.py
```

## Required Outputs

- `results/data/fund_returns.csv`
- `results/data/fund_weights.csv`
- `results/data/sector_sentiment_index.csv`
- `results/tables/performance_metrics.csv`

The app should read these precomputed files rather than recomputing the full
backtest or sentiment model at runtime.
