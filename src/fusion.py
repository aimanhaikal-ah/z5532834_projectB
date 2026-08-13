"""Station 3 extension - fuse lagged sector sentiment into an equity fund."""
from __future__ import annotations

import pandas as pd

from src import portfolios


def _sentiment_tilt_multiplier(
    sector_sentiment: pd.DataFrame,
    *,
    strength: float,
    min_multiplier: float,
    max_multiplier: float,
) -> pd.DataFrame:
    """Create cross-sectional sector tilt multipliers from lagged sentiment."""
    required = {"date", "sector", "sentiment_lag1"}
    missing = required - set(sector_sentiment.columns)
    if missing:
        raise ValueError(f"sector_sentiment is missing required columns: {sorted(missing)}")

    signals = sector_sentiment[["date", "sector", "sentiment_lag1"]].copy()
    signals["date"] = pd.to_datetime(signals["date"]).dt.normalize()
    by_date = signals.groupby("date", observed=True)["sentiment_lag1"]
    demeaned = signals["sentiment_lag1"] - by_date.transform("mean")
    dispersion = by_date.transform("std").replace(0, pd.NA)
    signals["sentiment_z"] = (demeaned / dispersion).fillna(0.0)
    signals["tilt_multiplier"] = (1.0 + strength * signals["sentiment_z"]).clip(
        lower=min_multiplier,
        upper=max_multiplier,
    )
    return signals


def apply_sentiment(
    equity_returns: pd.DataFrame,
    sector_sentiment: pd.DataFrame,
    *,
    base_method: str = "risk_parity",
    window: int = 252,
    rebalance: str = "ME",
    max_weight: float = 0.25,
    strength: float = 0.15,
    min_multiplier: float = 0.70,
    max_multiplier: float = 1.30,
    start_date: str | pd.Timestamp = "2021-01-04",
    end_date: str | pd.Timestamp | None = None,
    transaction_cost_bps: float = 10.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Apply lagged sector sentiment to optimiser weights at each rebalance.

    The base portfolio is estimated from past returns only. On each rebalance
    date, each ticker's optimiser weight inherits its sector's lagged sentiment
    multiplier, then weights are renormalised to sum to 1 and held until the
    next rebalance.
    """
    required = {"date", "ticker", "sector", "daily_return", "asset_class"}
    missing = required - set(equity_returns.columns)
    if missing:
        raise ValueError(f"equity_returns is missing required columns: {sorted(missing)}")

    multipliers = _sentiment_tilt_multiplier(
        sector_sentiment,
        strength=strength,
        min_multiplier=min_multiplier,
        max_multiplier=max_multiplier,
    )

    equity = equity_returns[equity_returns["asset_class"].eq("Equity")].copy()
    equity["date"] = pd.to_datetime(equity["date"]).dt.normalize()
    ticker_sector = (
        equity[["ticker", "sector"]]
        .drop_duplicates("ticker")
        .set_index("ticker")["sector"]
        .to_dict()
    )
    clean = portfolios.returns_to_wide(equity, "Equity").sort_index()
    if clean.shape[0] <= window:
        raise ValueError("not enough observations for the requested estimation window")

    rebalance_dates = clean.iloc[window:].resample(rebalance).last().index
    rebalance_dates = {date for date in rebalance_dates if date in clean.index}
    earliest_live = max(clean.index[window], pd.Timestamp(start_date))
    live_dates = clean.index[clean.index >= earliest_live]
    if end_date is not None:
        live_dates = live_dates[live_dates <= pd.Timestamp(end_date)]
    if live_dates.empty:
        raise ValueError("no live dates available for the requested start date")

    signal_lookup = multipliers.set_index(["date", "sector"])
    current_weights = None
    previous_weights = None
    weight_records: list[dict[str, object]] = []
    return_records: list[dict[str, object]] = []

    for date in live_dates:
        loc = clean.index.get_loc(date)
        if date in rebalance_dates or current_weights is None:
            history = clean.iloc[loc - window:loc]
            base_weights = portfolios._optimise_weights(
                history,
                method=base_method,
                max_weight=max_weight,
            )
            tilt_values = []
            signal_values = []
            z_values = []
            for ticker in clean.columns:
                sector = ticker_sector[ticker]
                try:
                    signal = signal_lookup.loc[(date, sector)]
                    tilt_values.append(float(signal["tilt_multiplier"]))
                    signal_values.append(float(signal["sentiment_lag1"]))
                    z_values.append(float(signal["sentiment_z"]))
                except KeyError:
                    tilt_values.append(1.0)
                    signal_values.append(0.0)
                    z_values.append(0.0)

            raw_weights = base_weights * pd.Series(tilt_values).to_numpy()
            if raw_weights.sum() <= 0:
                current_weights = base_weights
            else:
                current_weights = raw_weights / raw_weights.sum()

            turnover = (
                1.0
                if previous_weights is None
                else float(abs(current_weights - previous_weights).sum())
            )
            previous_weights = current_weights.copy()
            for ticker, base_weight, weight, signal_value, z_value, tilt_value in zip(
                clean.columns,
                base_weights,
                current_weights,
                signal_values,
                z_values,
                tilt_values,
            ):
                weight_records.append(
                    {
                        "date": date,
                        "ticker": ticker,
                        "sector": ticker_sector[ticker],
                        "base_weight": float(base_weight),
                        "weight": float(weight),
                        "sentiment_lag1": signal_value,
                        "sentiment_z": z_value,
                        "tilt_multiplier": tilt_value,
                        "turnover": turnover,
                    }
                )
        else:
            turnover = 0.0

        gross_return = float(clean.loc[date].to_numpy() @ current_weights)
        transaction_cost = turnover * transaction_cost_bps / 10_000
        return_records.append(
            {
                "date": date,
                "gross_return": gross_return,
                "transaction_cost": transaction_cost,
                "turnover": turnover,
                "daily_return": gross_return - transaction_cost,
            }
        )

    fund_returns = pd.DataFrame(return_records)
    fund_returns["growth_of_1"] = (1.0 + fund_returns["daily_return"]).cumprod()
    fund_returns["drawdown"] = (
        fund_returns["growth_of_1"] / fund_returns["growth_of_1"].cummax() - 1.0
    )
    fund_returns["fund"] = "Equity Sentiment Tilt"
    fund_returns["asset_family"] = "Equity"
    fund_returns["method"] = f"{base_method}_sentiment_tilt"

    fund_weights = pd.DataFrame(weight_records)
    fund_weights["fund"] = "Equity Sentiment Tilt"
    fund_weights["asset_family"] = "Equity"
    fund_weights["method"] = f"{base_method}_sentiment_tilt"

    metrics = portfolios.performance_metrics(
        fund_returns.set_index("date")["daily_return"],
        periods_per_year=portfolios.TRADING_DAYS,
    )
    metrics.update(
        {
            "fund": "Equity Sentiment Tilt",
            "asset_family": "Equity",
            "method": f"{base_method}_sentiment_tilt",
            "base_method": base_method,
            "sentiment_strength": strength,
            "min_multiplier": min_multiplier,
            "max_multiplier": max_multiplier,
            "transaction_cost_bps": transaction_cost_bps,
            "average_turnover": float(fund_returns["turnover"].mean()),
            "total_transaction_cost": float(fund_returns["transaction_cost"].sum()),
        }
    )
    return fund_returns, fund_weights, pd.DataFrame([metrics])


def sentiment_tilt_grid(
    equity_returns: pd.DataFrame,
    sector_sentiment: pd.DataFrame,
    *,
    strengths: tuple[float, ...] = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30),
    base_method: str = "risk_parity",
    window: int = 252,
    rebalance: str = "ME",
    max_weight: float = 0.25,
    transaction_cost_bps: float = 10.0,
    start_date: str | pd.Timestamp = "2021-01-04",
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Evaluate several optimiser-weight sentiment tilts after transaction costs."""
    rows = []
    for strength in strengths:
        _, _, metrics = apply_sentiment(
            equity_returns,
            sector_sentiment,
            base_method=base_method,
            window=window,
            rebalance=rebalance,
            max_weight=max_weight,
            strength=strength,
            min_multiplier=0.70,
            max_multiplier=1.30,
            start_date=start_date,
            end_date=end_date,
            transaction_cost_bps=transaction_cost_bps,
        )
        rows.append(metrics.iloc[0].to_dict())
    return pd.DataFrame(rows).sort_values("sharpe_ratio", ascending=False)


def period_metrics(
    fund_returns: pd.DataFrame,
    *,
    start_date: str | pd.Timestamp,
    end_date: str | pd.Timestamp,
) -> dict[str, float]:
    """Calculate performance and implementation metrics for one fixed period."""
    frame = fund_returns.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame[frame["date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))]
    if frame.empty:
        raise ValueError("no fund returns are available for the requested period")
    metrics = portfolios.performance_metrics(
        frame.set_index("date")["daily_return"],
        periods_per_year=portfolios.TRADING_DAYS,
    )
    metrics["average_turnover"] = float(frame["turnover"].mean())
    metrics["total_transaction_cost"] = float(frame["transaction_cost"].sum())
    return metrics


def holdout_validation_row(
    base_returns: pd.DataFrame,
    tilted_returns: pd.DataFrame,
    *,
    model_name: str,
    selected_strength: float,
    discovery_start: str | pd.Timestamp = "2021-01-04",
    discovery_end: str | pd.Timestamp = "2022-12-30",
    holdout_start: str | pd.Timestamp = "2023-01-01",
    holdout_end: str | pd.Timestamp = "2023-12-31",
) -> dict[str, object]:
    """Summarise a frozen sentiment choice on discovery and holdout periods."""
    base_discovery = period_metrics(
        base_returns,
        start_date=discovery_start,
        end_date=discovery_end,
    )
    tilt_discovery = period_metrics(
        tilted_returns,
        start_date=discovery_start,
        end_date=discovery_end,
    )
    base_holdout = period_metrics(
        base_returns,
        start_date=holdout_start,
        end_date=holdout_end,
    )
    tilt_holdout = period_metrics(
        tilted_returns,
        start_date=holdout_start,
        end_date=holdout_end,
    )
    return {
        "sentiment_model": model_name,
        "selected_strength": selected_strength,
        "discovery_base_sharpe": base_discovery["sharpe_ratio"],
        "discovery_tilt_sharpe": tilt_discovery["sharpe_ratio"],
        "discovery_sharpe_lift": (
            tilt_discovery["sharpe_ratio"] - base_discovery["sharpe_ratio"]
        ),
        "holdout_base_return": base_holdout["annualized_return"],
        "holdout_tilt_return": tilt_holdout["annualized_return"],
        "holdout_base_sharpe": base_holdout["sharpe_ratio"],
        "holdout_tilt_sharpe": tilt_holdout["sharpe_ratio"],
        "holdout_sharpe_lift": (
            tilt_holdout["sharpe_ratio"] - base_holdout["sharpe_ratio"]
        ),
        "holdout_base_drawdown": base_holdout["max_drawdown"],
        "holdout_tilt_drawdown": tilt_holdout["max_drawdown"],
        "holdout_tilt_cost": tilt_holdout["total_transaction_cost"],
    }


def fusion_comparison(
    base_metrics: pd.DataFrame,
    sentiment_metrics: pd.DataFrame,
    *,
    base_fund: str = "Equity Equal Weight",
) -> pd.DataFrame:
    """Return a before-vs-after table for the report."""
    base = base_metrics[base_metrics["fund"].eq(base_fund)].copy()
    if base.empty:
        raise ValueError(f"base fund not found: {base_fund}")
    sentiment_row = sentiment_metrics.copy()
    comparison = pd.concat([base, sentiment_row], ignore_index=True, sort=False)
    return comparison[
        [
            "fund",
            "annualized_return",
            "annualized_volatility",
            "sharpe_ratio",
            "max_drawdown",
            "total_return",
            "average_turnover",
            "total_transaction_cost",
        ]
    ]
