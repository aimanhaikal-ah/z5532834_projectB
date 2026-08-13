"""Station 3 - fund construction and out-of-sample backtests."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.optimize import minimize


TRADING_DAYS = 252


def daily_returns(prices: pd.DataFrame, price_col: str = "adjClose") -> pd.DataFrame:
    """Simple adjusted-close returns computed independently per ticker."""
    df = prices.copy().sort_values(["ticker", "date"]).reset_index(drop=True)
    df["daily_return"] = df.groupby("ticker", observed=True)[price_col].pct_change(
        fill_method=None
    )
    return df


def combined_returns_panel(
    equity_prices: pd.DataFrame,
    crypto_prices: pd.DataFrame,
) -> pd.DataFrame:
    """Build the aligned return panel used by all Part B funds.

    Crypto returns are calculated on their native daily calendar first, then
    left-aligned to the equity trading calendar. This keeps weekend crypto moves
    from being accidentally treated as equity-trading-day returns.
    """
    equity_returns = daily_returns(equity_prices)
    crypto_returns = daily_returns(crypto_prices)
    equity_dates = pd.Index(sorted(equity_returns["date"].unique()), name="date")

    equity_panel = equity_returns[
        ["date", "ticker", "sector", "daily_return"]
    ].assign(asset_class="Equity")

    crypto_panel = (
        crypto_returns.set_index("date")
        .groupby("ticker", observed=True)
        .apply(lambda group: group.reindex(equity_dates), include_groups=False)
        .reset_index()
    )
    crypto_panel["sector"] = "Crypto"
    crypto_panel["asset_class"] = "Crypto"
    crypto_panel = crypto_panel[["date", "ticker", "sector", "daily_return", "asset_class"]]

    return (
        pd.concat([equity_panel, crypto_panel], ignore_index=True)
        .dropna(subset=["daily_return"])
        .sort_values(["date", "asset_class", "ticker"])
        .reset_index(drop=True)
    )


def returns_to_wide(returns: pd.DataFrame, universe: str) -> pd.DataFrame:
    """Pivot long returns to a complete date-by-ticker matrix for one universe."""
    if universe == "Equity":
        frame = returns[returns["asset_class"].eq("Equity")]
    elif universe == "Crypto":
        frame = returns[returns["asset_class"].eq("Crypto")]
    elif universe == "Combined":
        frame = returns
    else:
        raise ValueError(f"unknown universe: {universe}")

    wide = frame.pivot(index="date", columns="ticker", values="daily_return").sort_index()
    return wide.dropna(how="any")


def _equal_weight(n_assets: int) -> np.ndarray:
    return np.repeat(1.0 / n_assets, n_assets)


def _inverse_vol_start(window: pd.DataFrame) -> np.ndarray:
    """Create a stable starting point for risk-parity optimisation."""
    vol = window.std(ddof=1).replace(0, np.nan)
    inv_vol = (1.0 / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy()
    if inv_vol.sum() <= 0:
        return _equal_weight(window.shape[1])
    return inv_vol / inv_vol.sum()


def _risk_contributions(weights: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """Asset contributions to total portfolio volatility."""
    portfolio_vol = _portfolio_volatility(weights, cov)
    if portfolio_vol <= 0:
        return np.zeros_like(weights)
    marginal_risk = cov @ weights / portfolio_vol
    return weights * marginal_risk


def _risk_parity_weight(
    window: pd.DataFrame,
    cov: np.ndarray,
    *,
    max_weight: float,
) -> np.ndarray:
    """Long-only equal-risk-contribution portfolio via constrained optimisation."""
    n_assets = window.shape[1]
    upper = min(max_weight, 1.0)
    if upper * n_assets < 1.0:
        upper = 1.0 / n_assets

    start = np.clip(_inverse_vol_start(window), 0.0, upper)
    if start.sum() <= 0:
        start = _equal_weight(n_assets)
    else:
        start = start / start.sum()

    target_share = np.repeat(1.0 / n_assets, n_assets)

    def objective(weights: np.ndarray) -> float:
        contributions = _risk_contributions(weights, cov)
        total_risk = contributions.sum()
        if total_risk <= 0:
            return 1e6
        contribution_shares = contributions / total_risk
        return float(((contribution_shares - target_share) ** 2).sum())

    result = minimize(
        objective,
        start,
        method="SLSQP",
        bounds=[(0.0, upper) for _ in range(n_assets)],
        constraints=[{"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0}],
        options={"maxiter": 800, "ftol": 1e-12},
    )
    if not result.success or np.any(~np.isfinite(result.x)):
        return start

    weights = np.clip(result.x, 0.0, upper)
    total = weights.sum()
    if total <= 0:
        return start
    return weights / total


def _portfolio_volatility(weights: np.ndarray, cov: np.ndarray) -> float:
    return float(np.sqrt(max(weights @ cov @ weights, 0.0)))


def _optimise_weights(
    window: pd.DataFrame,
    *,
    method: str,
    max_weight: float = 0.25,
) -> np.ndarray:
    """Estimate long-only weights from past returns only."""
    n_assets = window.shape[1]
    if method == "equal_weight":
        return _equal_weight(n_assets)

    cov = window.cov().to_numpy()
    cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
    cov = cov + np.eye(n_assets) * 1e-8
    if method == "risk_parity":
        return _risk_parity_weight(window, cov, max_weight=max_weight)

    mu = window.mean().to_numpy()
    upper = min(max_weight, 1.0)
    if upper * n_assets < 1.0:
        upper = 1.0 / n_assets
    bounds = [(0.0, upper) for _ in range(n_assets)]
    constraints = [{"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0}]
    start = _equal_weight(n_assets)

    if method == "min_variance":
        objective = lambda weights: weights @ cov @ weights
    elif method == "max_sharpe":
        def objective(weights: np.ndarray) -> float:
            vol = _portfolio_volatility(weights, cov)
            if vol <= 0:
                return 1e6
            return -float(weights @ mu / vol)
    else:
        raise ValueError(f"unknown method: {method}")

    result = minimize(
        objective,
        start,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-10},
    )
    if not result.success or np.any(~np.isfinite(result.x)):
        return start

    weights = np.clip(result.x, 0.0, upper)
    total = weights.sum()
    if total <= 0:
        return start
    return weights / total


def oos_backtest(
    returns: pd.DataFrame,
    method: str = "min_variance",
    *,
    window: int = 252,
    rebalance: str = "ME",
    max_weight: float = 0.25,
    transaction_cost_bps: float = 0.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Walk-forward backtest with no look-ahead.

    Weights are estimated from the previous `window` trading observations and
    are applied after the rebalance date.
    """
    clean = returns.dropna(how="any").copy().sort_index()
    if clean.shape[0] <= window:
        raise ValueError("not enough observations for the requested estimation window")

    rebalance_dates = clean.iloc[window:].resample(rebalance).last().index
    rebalance_dates = [date for date in rebalance_dates if date in clean.index]
    if not rebalance_dates:
        raise ValueError("no rebalance dates available after the estimation window")

    weights_by_date: list[dict[str, object]] = []
    return_records: list[dict[str, object]] = []
    current_weights: np.ndarray | None = None
    previous_weights: np.ndarray | None = None
    next_rebalance = set(rebalance_dates)

    live_dates = clean.index[window:]
    for date in live_dates:
        loc = clean.index.get_loc(date)
        if date in next_rebalance or current_weights is None:
            history = clean.iloc[loc - window:loc]
            current_weights = _optimise_weights(
                history,
                method=method,
                max_weight=max_weight,
            )
            turnover = (
                1.0
                if previous_weights is None
                else float(np.abs(current_weights - previous_weights).sum())
            )
            previous_weights = current_weights.copy()
            for ticker, weight in zip(clean.columns, current_weights):
                weights_by_date.append(
                    {
                        "date": date,
                        "ticker": ticker,
                        "weight": float(weight),
                        "turnover": turnover,
                    }
                )
        else:
            turnover = 0.0

        gross_return = float(clean.loc[date].to_numpy() @ current_weights)
        cost = turnover * transaction_cost_bps / 10_000
        daily_return = gross_return - cost
        return_records.append(
            {
                "date": date,
                "daily_return": daily_return,
                "gross_return": gross_return,
                "transaction_cost": cost,
                "turnover": turnover,
            }
        )

    fund_returns = pd.DataFrame(return_records)
    fund_returns["growth_of_1"] = (1.0 + fund_returns["daily_return"]).cumprod()
    running_max = fund_returns["growth_of_1"].cummax()
    fund_returns["drawdown"] = fund_returns["growth_of_1"] / running_max - 1.0
    fund_weights = pd.DataFrame(weights_by_date)
    return fund_returns, fund_weights


def performance_metrics(daily_returns: pd.Series, periods_per_year: int = 252) -> dict:
    """Annualised return, volatility, Sharpe ratio, and maximum drawdown."""
    returns = pd.to_numeric(daily_returns, errors="coerce").dropna()
    growth = (1.0 + returns).cumprod()
    n_obs = len(returns)
    if n_obs == 0:
        raise ValueError("daily_returns is empty")

    total_return = float(growth.iloc[-1] - 1.0)
    annualized_return = float(growth.iloc[-1] ** (periods_per_year / n_obs) - 1.0)
    annualized_volatility = float(returns.std(ddof=1) * math.sqrt(periods_per_year))
    sharpe_ratio = (
        annualized_return / annualized_volatility
        if annualized_volatility > 0
        else np.nan
    )
    drawdown = growth / growth.cummax() - 1.0
    return {
        "observations": n_obs,
        "start_date": returns.index.min(),
        "end_date": returns.index.max(),
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe_ratio": float(sharpe_ratio),
        "max_drawdown": float(drawdown.min()),
    }


def run_fund_suite(
    returns: pd.DataFrame,
    *,
    window: int = 252,
    methods: tuple[str, ...] = ("equal_weight", "min_variance", "max_sharpe", "risk_parity"),
    transaction_cost_bps: float = 10.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the Part B fund suite and return app/report-ready outputs."""
    fund_return_frames: list[pd.DataFrame] = []
    fund_weight_frames: list[pd.DataFrame] = []
    metric_rows: list[dict[str, object]] = []

    for universe in ("Equity", "Crypto", "Combined"):
        wide = returns_to_wide(returns, universe)
        max_weight = 0.40 if universe == "Crypto" else 0.25

        for method in methods:
            fund_name = f"{universe} {method.replace('_', ' ').title()}"
            fund_returns, fund_weights = oos_backtest(
                wide,
                method=method,
                window=window,
                rebalance="ME",
                max_weight=max_weight,
                transaction_cost_bps=transaction_cost_bps,
            )
            fund_returns["fund"] = fund_name
            fund_returns["asset_family"] = universe
            fund_returns["method"] = method
            fund_weights["fund"] = fund_name
            fund_weights["asset_family"] = universe
            fund_weights["method"] = method

            metric = performance_metrics(
                fund_returns.set_index("date")["daily_return"],
                periods_per_year=TRADING_DAYS,
            )
            metric.update(
                {
                    "fund": fund_name,
                    "asset_family": universe,
                    "method": method,
                    "estimation_window_days": window,
                    "rebalance_frequency": "month_end",
                    "risk_free_rate": 0.0,
                    "transaction_cost_bps": transaction_cost_bps,
                    "average_turnover": float(fund_returns["turnover"].mean()),
                    "total_transaction_cost": float(fund_returns["transaction_cost"].sum()),
                }
            )
            metric_rows.append(metric)
            fund_return_frames.append(fund_returns)
            fund_weight_frames.append(fund_weights)

    fund_returns_all = pd.concat(fund_return_frames, ignore_index=True)
    fund_weights_all = pd.concat(fund_weight_frames, ignore_index=True)
    metrics = pd.DataFrame(metric_rows)

    return (
        fund_returns_all[
            [
                "date",
                "fund",
                "asset_family",
                "method",
                "daily_return",
                "gross_return",
                "transaction_cost",
                "turnover",
                "growth_of_1",
                "drawdown",
            ]
        ],
        fund_weights_all[
            ["date", "fund", "asset_family", "method", "ticker", "weight", "turnover"]
        ],
        metrics[
            [
                "fund",
                "asset_family",
                "method",
                "start_date",
                "end_date",
                "observations",
                "total_return",
                "annualized_return",
                "annualized_volatility",
                "sharpe_ratio",
                "max_drawdown",
                "estimation_window_days",
                "rebalance_frequency",
                "risk_free_rate",
                "transaction_cost_bps",
                "average_turnover",
                "total_transaction_cost",
            ]
        ].sort_values(["asset_family", "method"]).reset_index(drop=True),
    )
