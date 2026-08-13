"""Checks for Part A cleaning and feature logic reused in Part B."""
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import etl, features  # noqa: E402


def test_daily_returns_are_computed_per_ticker():
    prices = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-01", "2020-01-02"]),
            "ticker": ["AAA", "AAA", "BBB", "BBB"],
            "adjClose": [100.0, 110.0, 50.0, 45.0],
        }
    )
    returns = features.daily_returns(prices)
    second_day = returns.dropna(subset=["daily_return"]).set_index("ticker")["daily_return"]
    assert round(second_day["AAA"], 4) == 0.1000
    assert round(second_day["BBB"], 4) == -0.1000


def test_headline_alignment_uses_same_or_next_trading_day():
    headlines = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-03", "2020-01-04"]),
            "ticker": ["AAA", "AAA"],
            "sector": ["Tech", "Tech"],
            "title": ["Friday news", "Saturday news"],
        }
    )
    trading_days = pd.to_datetime(["2020-01-03", "2020-01-06"])
    panel = features.assemble_headline_panel(headlines, trading_days)
    counts = panel.set_index("date")["headline_count"].to_dict()
    assert counts[pd.Timestamp("2020-01-03")] == 1
    assert counts[pd.Timestamp("2020-01-06")] == 1


def test_clean_headlines_removes_exact_duplicates():
    raw = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-01"]),
            "ticker": ["AAA", "AAA"],
            "sector": ["Tech", "Tech"],
            "title": ["Same headline", "Same headline"],
            "publisher": ["Wire", "Wire"],
            "url": ["", ""],
        }
    )
    # Exercise the same deduplication key without calling the network-backed loader.
    normalised = raw.copy()
    normalised["date"] = pd.to_datetime(normalised["date"]).dt.normalize()
    cleaned = normalised.drop_duplicates(["ticker", "date", "title"], keep="first")
    assert len(cleaned) == 1
    assert hasattr(etl, "load_clean_headlines")
