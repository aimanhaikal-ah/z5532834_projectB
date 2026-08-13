"""Station 2 feature helpers reused from the BetaVest Part A foundation.

Part B uses these helpers for two purposes:

- create return diagnostics from the cleaned price panels
- assemble the equity-news text panel before Station 3 sentiment scoring

The sentiment score itself belongs in `src/sentiment.py`.
"""
from __future__ import annotations

import re

import pandas as pd


def daily_returns(prices: pd.DataFrame, price_col: str = "adjClose") -> pd.DataFrame:
    """Simple daily returns per ticker using adjusted close."""
    df = prices.copy().sort_values(["ticker", "date"]).reset_index(drop=True)
    df["daily_return"] = df.groupby("ticker", observed=True)[price_col].pct_change(
        fill_method=None
    )
    df["growth_of_1"] = (
        1 + df["daily_return"].fillna(0)
    ).groupby(df["ticker"], observed=True).cumprod()
    df["rolling_volatility_21d"] = (
        df.groupby("ticker", observed=True)["daily_return"]
        .rolling(21)
        .std()
        .reset_index(level=0, drop=True)
    )
    return df


def combined_returns_panel(
    equity_returns: pd.DataFrame,
    crypto_returns: pd.DataFrame,
) -> pd.DataFrame:
    """Left-merge crypto returns onto the equity trading calendar after differencing."""
    equity_dates = pd.Index(sorted(equity_returns["date"].unique()), name="date")
    equity_panel = equity_returns[
        ["date", "ticker", "sector", "daily_return", "growth_of_1", "rolling_volatility_21d"]
    ].assign(asset_class="Equity")

    crypto_panel = (
        crypto_returns.set_index("date")
        .groupby("ticker", observed=True)
        .apply(lambda group: group.reindex(equity_dates), include_groups=False)
        .reset_index()
    )
    crypto_panel["asset_class"] = "Crypto"
    crypto_panel["sector"] = "Crypto"
    crypto_panel = crypto_panel[
        [
            "date",
            "ticker",
            "sector",
            "daily_return",
            "growth_of_1",
            "rolling_volatility_21d",
            "asset_class",
        ]
    ]
    return (
        pd.concat([equity_panel, crypto_panel], ignore_index=True)
        .sort_values(["asset_class", "ticker", "date"])
        .reset_index(drop=True)
    )


def return_descriptive_stats(returns: pd.DataFrame) -> pd.DataFrame:
    """Return descriptive statistics by asset class."""
    clean = returns.dropna(subset=["daily_return"]).copy()
    stats = (
        clean.groupby("asset_class", observed=True)["daily_return"]
        .agg(
            observations="count",
            mean_daily_return="mean",
            daily_volatility="std",
            min_daily_return="min",
            max_daily_return="max",
            skewness="skew",
        )
        .reset_index()
    )
    stats["kurtosis"] = (
        clean.groupby("asset_class", observed=True)["daily_return"]
        .apply(pd.Series.kurt)
        .values
    )
    stats["annualized_return"] = stats["mean_daily_return"] * stats["asset_class"].map(
        {"Equity": 252, "Crypto": 365}
    )
    stats["annualized_volatility"] = stats["daily_volatility"] * (
        stats["asset_class"].map({"Equity": 252, "Crypto": 365}) ** 0.5
    )
    return stats[
        [
            "asset_class",
            "observations",
            "mean_daily_return",
            "daily_volatility",
            "annualized_return",
            "annualized_volatility",
            "min_daily_return",
            "max_daily_return",
            "skewness",
            "kurtosis",
        ]
    ]


FINANCE_TERMS = {
    "beat",
    "beats",
    "buy",
    "growth",
    "upgrade",
    "upside",
    "gain",
    "gains",
    "strong",
    "surge",
    "profit",
    "profits",
    "outperform",
    "miss",
    "misses",
    "sell",
    "downgrade",
    "risk",
    "risks",
    "loss",
    "losses",
    "weak",
    "decline",
    "falls",
    "fall",
    "lawsuit",
    "cut",
    "cuts",
    "warning",
    "debt",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "s",
    "stock",
    "stocks",
    "the",
    "this",
    "to",
    "vs",
    "with",
    "what",
    "why",
    "you",
    "your",
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z\-']+", str(text).lower())


def align_headlines_to_trading_days(
    headlines: pd.DataFrame,
    equity_dates: pd.Series,
) -> pd.DataFrame:
    """Map each headline date to the same or next equity trading day."""
    calendar = pd.DataFrame(
        {
            "trading_date": pd.to_datetime(
                sorted(pd.to_datetime(equity_dates).unique())
            ).astype("datetime64[ns]")
        }
    )
    source = headlines.sort_values("date").copy()
    source["date"] = pd.to_datetime(source["date"]).astype("datetime64[ns]")
    aligned = pd.merge_asof(
        source,
        calendar,
        left_on="date",
        right_on="trading_date",
        direction="forward",
    )
    return aligned.dropna(subset=["trading_date"]).reset_index(drop=True)


def assemble_headline_panel(
    headlines: pd.DataFrame,
    equity_dates: pd.Series | None = None,
) -> pd.DataFrame:
    """Assemble headlines into a daily panel per ticker and sector.

    This is text assembly only. Scoring the text and lagging the signal are
    handled later in the Station 3 sentiment model.
    """
    aligned = headlines.copy()
    if equity_dates is not None:
        aligned = align_headlines_to_trading_days(aligned, equity_dates)
        date_column = "trading_date"
    else:
        date_column = "date"

    panel = (
        aligned.groupby([date_column, "ticker", "sector"], observed=True)
        .agg(
            headline_count=("title", "size"),
            combined_headlines=("title", lambda values: " | ".join(values)),
        )
        .reset_index()
        .rename(columns={date_column: "date"})
        .sort_values(["date", "ticker"])
        .reset_index(drop=True)
    )
    panel["word_count"] = panel["combined_headlines"].map(
        lambda text: len(_tokenize(text))
    )
    panel["finance_term_count"] = panel["combined_headlines"].map(
        lambda text: sum(token in FINANCE_TERMS for token in _tokenize(text))
    )
    return panel


def top_terms(headlines: pd.DataFrame, *, n: int = 25) -> pd.DataFrame:
    """Most frequent non-stopword headline terms."""
    counts: dict[str, int] = {}
    for title in headlines["title"]:
        for token in _tokenize(title):
            if token not in STOPWORDS and len(token) > 2:
                counts[token] = counts.get(token, 0) + 1
    return (
        pd.DataFrame({"term": list(counts), "count": list(counts.values())})
        .sort_values(["count", "term"], ascending=[False, True])
        .head(n)
        .reset_index(drop=True)
    )


def monthly_news_counts(headline_panel: pd.DataFrame) -> pd.DataFrame:
    """Headline counts by aligned trading month and sector."""
    monthly = headline_panel.copy()
    monthly["month"] = monthly["date"].dt.to_period("M").dt.to_timestamp()
    return (
        monthly.groupby(["month", "sector"], observed=True)["headline_count"]
        .sum()
        .reset_index()
        .sort_values(["month", "sector"])
    )
