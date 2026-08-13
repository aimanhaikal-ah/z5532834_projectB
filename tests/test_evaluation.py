"""Tests for robustness and sentiment-regime evaluation tables."""
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import evaluation  # noqa: E402


def test_robustness_by_period_reports_named_subperiods():
    dates = pd.bdate_range("2021-01-01", periods=80)
    fund_returns = pd.DataFrame(
        {
            "date": list(dates) * 2,
            "fund": ["Fund A"] * len(dates) + ["Fund B"] * len(dates),
            "daily_return": [0.001] * len(dates) + [-0.001] * len(dates),
        }
    )

    result = evaluation.robustness_by_period(
        fund_returns,
        periods=(("Full sample", None, None), ("Early 2021", "2021-01-01", "2021-02-28")),
        min_observations=20,
    )

    assert set(result["Period"]) == {"Full sample", "Early 2021"}
    assert {"Fund", "Sharpe", "Max drawdown (%)"}.issubset(result.columns)


def test_sentiment_regime_analysis_uses_lagged_sentiment_terciles():
    dates = pd.bdate_range("2021-01-01", periods=90)
    fund_returns = pd.DataFrame(
        {
            "date": list(dates) * 2,
            "fund": ["Fund A"] * len(dates) + ["Fund B"] * len(dates),
            "daily_return": [0.001] * len(dates) + [0.0005] * len(dates),
        }
    )
    sentiment = pd.DataFrame(
        {
            "date": list(dates) * 2,
            "sector": ["Tech"] * len(dates) + ["Energy"] * len(dates),
            "sentiment_lag1": list(range(90)) + list(range(90)),
        }
    )

    result = evaluation.sentiment_regime_analysis(
        fund_returns,
        sentiment,
        min_observations=20,
    )

    assert set(result["Regime"]) == {"Negative", "Neutral", "Positive"}
    assert {"Average lagged sentiment", "Positive return days (%)"}.issubset(result.columns)
