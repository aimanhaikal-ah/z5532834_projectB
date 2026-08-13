"""Offline tests for the sentiment-fusion portfolio helper."""
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import fusion  # noqa: E402


def test_sentiment_tilt_weights_are_long_only_and_normalised():
    dates = pd.to_datetime(["2021-01-04", "2021-01-05", "2021-01-06"])
    returns = pd.DataFrame(
        {
            "date": [date for date in dates for _ in range(4)],
            "ticker": ["AAA", "BBB", "CCC", "DDD"] * 3,
            "sector": ["Tech", "Tech", "Energy", "Energy"] * 3,
            "daily_return": [
                0.01,
                0.02,
                -0.01,
                0.00,
                0.02,
                -0.01,
                0.01,
                -0.02,
                0.01,
                0.02,
                -0.01,
                0.00,
            ],
            "asset_class": ["Equity"] * 12,
        }
    )
    sentiment = pd.DataFrame(
        {
            "date": pd.to_datetime(["2021-01-06", "2021-01-06"]),
            "sector": ["Tech", "Energy"],
            "sentiment_lag1": [0.5, -0.5],
        }
    )
    fund_returns, weights, metrics = fusion.apply_sentiment(
        returns,
        sentiment,
        strength=0.3,
        base_method="equal_weight",
        window=2,
        rebalance="D",
        start_date="2021-01-06",
    )
    assert len(fund_returns) == 1
    assert metrics.iloc[0]["fund"] == "Equity Sentiment Tilt"
    assert metrics.iloc[0]["base_method"] == "equal_weight"
    assert weights["weight"].between(0, 1).all()
    assert round(weights["weight"].sum(), 8) == 1.0
    assert "base_weight" in weights.columns
    assert weights.groupby("sector")["weight"].sum()["Tech"] > weights.groupby("sector")["weight"].sum()["Energy"]


def test_fusion_comparison_keeps_transaction_cost_columns():
    base = pd.DataFrame(
        {
            "fund": ["Equity Equal Weight"],
            "annualized_return": [0.10],
            "annualized_volatility": [0.15],
            "sharpe_ratio": [0.67],
            "max_drawdown": [-0.20],
            "total_return": [0.30],
            "average_turnover": [0.01],
            "total_transaction_cost": [0.02],
        }
    )
    sentiment = base.copy()
    sentiment["fund"] = "Equity Sentiment Tilt"

    comparison = fusion.fusion_comparison(base, sentiment)

    assert "average_turnover" in comparison.columns
    assert "total_transaction_cost" in comparison.columns
    assert comparison["fund"].tolist() == ["Equity Equal Weight", "Equity Sentiment Tilt"]


def test_holdout_validation_reports_discovery_and_holdout_lifts():
    dates = pd.bdate_range("2021-01-04", "2023-12-29")
    base_returns = [0.0002 + (0.001 if index % 2 else -0.001) for index in range(len(dates))]
    base = pd.DataFrame(
        {
            "date": dates,
            "daily_return": base_returns,
            "turnover": 0.001,
            "transaction_cost": 0.000001,
        }
    )
    tilted = base.copy()
    tilted.loc[tilted["date"].dt.year.eq(2023), "daily_return"] += 0.0001

    row = fusion.holdout_validation_row(
        base,
        tilted,
        model_name="Finance lexicon",
        selected_strength=0.2,
    )

    assert row["sentiment_model"] == "Finance lexicon"
    assert row["selected_strength"] == 0.2
    assert row["holdout_sharpe_lift"] > 0
