"""Station 1 - ETL helpers for the Part B build.

Part B reuses the Part A data-design choices: clean price panels first, compute
returns inside each native asset calendar, then align crypto to the equity
trading calendar for combined fund tests.
"""
from __future__ import annotations

import pandas as pd

from src import data_access


PRICE_COLUMNS = ["open", "high", "low", "close", "adjClose", "volume"]


def _clean_price_panel(frame: pd.DataFrame, *, has_sector: bool) -> pd.DataFrame:
    """Standardise price-panel types and ordering."""
    df = frame.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    df["ticker"] = df["ticker"].astype(str)
    if has_sector:
        df["sector"] = df["sector"].astype(str)
    for column in PRICE_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)


def load_clean_equities():
    """Load and clean equity prices.

    Price observations should be unique by ticker-date. Extreme returns are kept
    for the backtest because they represent realised investor risk.
    """
    df = _clean_price_panel(data_access.load_equity_prices(), has_sector=True)
    return df.drop_duplicates(["ticker", "date"], keep="first")


def load_clean_crypto():
    """Load and clean crypto prices, capped at the Part A sample end."""
    df = _clean_price_panel(data_access.load_crypto_prices(), has_sector=False)
    df = df[df["date"].le(pd.Timestamp("2023-12-31"))].copy()
    return df.drop_duplicates(["ticker", "date"], keep="first")


def load_clean_headlines() -> pd.DataFrame:
    """Load, date-normalise, and deduplicate the equity-news headlines.

    This carries forward the Part A rule: remove exact duplicate
    ticker-date-title records, but keep distinct headlines on the same
    ticker-date because they are valid information flow.
    """
    df = data_access.load_news_headlines().copy()
    df["date"] = (
        pd.to_datetime(df["date"], utc=True)
        .dt.tz_convert(None)
        .dt.normalize()
        .astype("datetime64[ns]")
    )
    df["ticker"] = df["ticker"].astype(str)
    df["sector"] = df["sector"].astype(str)
    df["title"] = df["title"].fillna("").astype(str).str.strip()
    df["publisher"] = df["publisher"].fillna("Unknown").astype(str)
    df["url"] = df["url"].fillna("").astype(str)
    return (
        df.drop_duplicates(["ticker", "date", "title"], keep="first")
        .sort_values(["ticker", "date", "title"])
        .reset_index(drop=True)
    )
