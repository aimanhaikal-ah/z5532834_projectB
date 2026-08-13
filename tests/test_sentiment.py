"""Offline tests for the Part B sentiment index helpers."""
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import sentiment  # noqa: E402


def test_finance_lexicon_scores_positive_and_negative_terms():
    positive = sentiment._lexicon_scores("earnings beat expectations and shares gain")
    negative = sentiment._lexicon_scores("lawsuit warning as losses fall")
    assert positive["compound"] > 0
    assert negative["compound"] < 0


def test_sentiment_model_comparison_returns_summary_and_audit_sample():
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-02", "2020-01-03"]),
            "ticker": ["AAA", "BBB"],
            "sector": ["Tech", "Energy"],
            "headline_count": [1, 1],
            "word_count": [5, 5],
            "finance_term_count": [2, 2],
            "combined_headlines": [
                "Company beats estimates with strong growth",
                "Company warns of losses and lawsuit risk",
            ],
        }
    )

    summary, audit = sentiment.compare_sentiment_models(panel, audit_size=1)

    assert summary["Model"].tolist() == ["Finance lexicon", "VADER"]
    assert summary["Direction agreement (%)"].between(0, 100).all()
    assert len(audit) == 1
    assert {"Finance score", "VADER score", "Headline bundle"}.issubset(audit.columns)


def test_sector_sentiment_index_fills_no_headline_days_as_neutral():
    scores = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-02"]),
            "ticker": ["AAA"],
            "sector": ["Tech"],
            "sentiment_score": [1.0],
            "headline_count": [2],
        }
    )
    universe = pd.DataFrame(
        {"ticker": ["AAA", "BBB"], "sector": ["Tech", "Tech"]}
    )
    index = sentiment.sector_sentiment_index(
        scores,
        trading_dates=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        sector_universe=universe,
    )
    first_day = index[index["date"].eq(pd.Timestamp("2020-01-02"))].iloc[0]
    second_day = index[index["date"].eq(pd.Timestamp("2020-01-03"))].iloc[0]
    assert first_day["sentiment_score"] == 0.5
    assert first_day["tickers_with_headlines"] == 1
    assert second_day["sentiment_score"] == 0.0
    assert second_day["sentiment_lag1"] == 0.5
