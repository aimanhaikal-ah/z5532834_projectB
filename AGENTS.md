# AGENTS.md - BetaVest Part B Assistant Instructions

This folder is the working folder for FINS3645 Project B for BetaVest. Keep all
work inside this folder unless the student explicitly asks to inspect the Part A
folder for continuity. Do not commit or copy raw source data files. Load raw
project data only through `src/data_access.py`; store only derived outputs under
`results/`.

## Project Scope

- Part B covers funds, sentiment, fusion, and the Streamlit app for BetaVest.
- Continue from the Part A product concept: BetaVest targets young retail
  investors who need clear evidence on equity, crypto, and combined funds.
- Reuse the Part A design choices: equity and crypto returns are computed in
  their own native panels before calendar alignment, crypto is capped at
  2023-12-31, and headlines are aligned to the same or next equity trading day.
- Sentiment applies to equities only. Lag any sentiment signal by at least one
  trading day before using it in a trading or weighting decision.
- Portfolio backtests must be walk-forward and out of sample. Weights must use
  only information available before the rebalance date.

## Required Part B Outputs

- `results/data/fund_returns.csv`
- `results/data/fund_weights.csv`
- `results/data/sector_sentiment_index.csv`
- `results/tables/performance_metrics.csv`
- Required figures should be saved under `results/figures/`.
- The deployed app should read precomputed outputs from `results/`; it should
  not recompute VADER scores or portfolio backtests at runtime.

## Reproducible Commands

Run from this project folder:

```bash
python scripts/run_part_b.py
streamlit run streamlit_app.py
python scripts/check_handin.py
git status
```

If using the repo environment from the fins-agent root, use:

```bash
./.venv/bin/python fins2026/z5532834_projectB/scripts/run_part_b.py
./.venv/bin/python fins2026/z5532834_projectB/scripts/check_handin.py
```

## Report Rules

- The editable final report should be `report/report.docx`; Markdown drafts in
  `report/` are planning aids.
- Every table and figure must be captioned, labelled, and interpreted in the
  text.
- Every quantitative result must trace to a generated table, figure, or script.
- Do not invent results. Use `[HUMAN EDIT REQUIRED: ...]` for missing metrics,
  app URLs, GitHub URLs, or citations.
- Before final submission, rerun the Part B script and hand-in checker, update
  the Word fields and captions, export `report/report.pdf`, and review all AI
  draft text manually.
