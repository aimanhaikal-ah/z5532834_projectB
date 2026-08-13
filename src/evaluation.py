"""Extra evaluation checks for the BetaVest Part B extension."""
from __future__ import annotations

import pandas as pd

from src import portfolios


ROBUSTNESS_PERIODS: tuple[tuple[str, str | None, str | None], ...] = (
    ("Full sample", None, None),
    ("2021 recovery", "2021-01-01", "2021-12-31"),
    ("2022 drawdown", "2022-01-01", "2022-12-31"),
    ("2023 recovery", "2023-01-01", "2023-12-31"),
)


def _report_metric_row(
    returns: pd.Series,
    *,
    period: str,
    fund: str,
) -> dict[str, object]:
    metrics = portfolios.performance_metrics(
        returns,
        periods_per_year=portfolios.TRADING_DAYS,
    )
    return {
        "Period": period,
        "Fund": fund,
        "Start date": pd.Timestamp(metrics["start_date"]).date().isoformat(),
        "End date": pd.Timestamp(metrics["end_date"]).date().isoformat(),
        "Observations": metrics["observations"],
        "Ann. return (%)": metrics["annualized_return"] * 100,
        "Ann. volatility (%)": metrics["annualized_volatility"] * 100,
        "Sharpe": metrics["sharpe_ratio"],
        "Max drawdown (%)": metrics["max_drawdown"] * 100,
        "Total return (%)": metrics["total_return"] * 100,
    }


def robustness_by_period(
    fund_returns: pd.DataFrame,
    *,
    periods: tuple[tuple[str, str | None, str | None], ...] = ROBUSTNESS_PERIODS,
    min_observations: int = 30,
) -> pd.DataFrame:
    """Evaluate each fund in full sample and named sub-periods."""
    frame = fund_returns.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    rows: list[dict[str, object]] = []

    for fund, group in frame.groupby("fund", observed=True):
        group = group.sort_values("date")
        for period, start, end in periods:
            period_group = group
            if start is not None:
                period_group = period_group[period_group["date"].ge(pd.Timestamp(start))]
            if end is not None:
                period_group = period_group[period_group["date"].le(pd.Timestamp(end))]
            if len(period_group) < min_observations:
                continue
            returns = period_group.set_index("date")["daily_return"]
            rows.append(_report_metric_row(returns, period=period, fund=fund))

    return pd.DataFrame(rows)


def sentiment_regime_analysis(
    fund_returns: pd.DataFrame,
    sector_sentiment: pd.DataFrame,
    *,
    min_observations: int = 30,
) -> pd.DataFrame:
    """Test fund behaviour across negative, neutral, and positive sentiment days.

    Regimes are terciles of the equal-weight average lagged sector sentiment.
    This keeps the test aligned with the one-day lag used by the sentiment tilt.
    """
    returns = fund_returns.copy()
    returns["date"] = pd.to_datetime(returns["date"])

    sentiment = sector_sentiment.copy()
    sentiment["date"] = pd.to_datetime(sentiment["date"])
    daily_signal = (
        sentiment.groupby("date", observed=True)["sentiment_lag1"]
        .mean()
        .rename("Lagged sentiment")
        .reset_index()
    )
    daily_signal["Regime"] = pd.qcut(
        daily_signal["Lagged sentiment"],
        q=3,
        labels=["Negative", "Neutral", "Positive"],
        duplicates="drop",
    )
    daily_signal = daily_signal.dropna(subset=["Regime"])

    merged = returns.merge(daily_signal, on="date", how="inner")
    rows: list[dict[str, object]] = []
    for (fund, regime), group in merged.groupby(["fund", "Regime"], observed=True):
        if len(group) < min_observations:
            continue
        metric = _report_metric_row(
            group.set_index("date")["daily_return"],
            period=str(regime),
            fund=str(fund),
        )
        metric["Regime"] = str(regime)
        metric["Average daily return (%)"] = group["daily_return"].mean() * 100
        metric["Positive return days (%)"] = (group["daily_return"] > 0).mean() * 100
        metric["Average lagged sentiment"] = group["Lagged sentiment"].mean()
        rows.append(metric)

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result[
        [
            "Regime",
            "Fund",
            "Observations",
            "Average lagged sentiment",
            "Average daily return (%)",
            "Positive return days (%)",
            "Ann. return (%)",
            "Ann. volatility (%)",
            "Sharpe",
            "Max drawdown (%)",
            "Total return (%)",
        ]
    ]
