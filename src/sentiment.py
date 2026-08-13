"""Station 3 - sentiment model and equity-sector news index."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd


POSITIVE_TERMS = {
    "accelerate",
    "accelerates",
    "approval",
    "approved",
    "beat",
    "beats",
    "boost",
    "boosts",
    "buy",
    "buyback",
    "buybacks",
    "deal",
    "deals",
    "dividend",
    "dividends",
    "exceed",
    "exceeds",
    "growth",
    "upgrade",
    "upgraded",
    "upside",
    "gain",
    "gains",
    "higher",
    "raise",
    "raises",
    "raised",
    "strong",
    "stronger",
    "surge",
    "surges",
    "profit",
    "profits",
    "profitable",
    "outperform",
    "rally",
    "rallies",
    "record",
    "recovery",
    "recover",
}

NEGATIVE_TERMS = {
    "bankruptcy",
    "bankrupt",
    "charge",
    "charges",
    "crisis",
    "miss",
    "misses",
    "sell",
    "downgrade",
    "downgraded",
    "risk",
    "risks",
    "loss",
    "losses",
    "lower",
    "weak",
    "weaker",
    "decline",
    "declines",
    "falls",
    "fall",
    "lawsuit",
    "lawsuits",
    "cut",
    "cuts",
    "warning",
    "warns",
    "debt",
    "default",
    "fraud",
    "probe",
    "recall",
    "recession",
    "slump",
    "slumps",
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z\-']+", str(text).lower())


def _lexicon_scores(text: str) -> dict[str, float]:
    """Small finance-word sentiment baseline used if VADER data is unavailable."""
    tokens = _tokenize(text)
    positive = sum(token in POSITIVE_TERMS for token in tokens)
    negative = sum(token in NEGATIVE_TERMS for token in tokens)
    total = positive + negative
    compound = (positive - negative) / total if total else 0.0
    token_count = max(len(tokens), 1)
    return {
        "neg": negative / token_count,
        "neu": max(1.0 - total / token_count, 0.0),
        "pos": positive / token_count,
        "compound": compound,
    }


def _vader_analyzer():
    """Return an offline VADER analyzer, with NLTK as a build-time fallback."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        return SentimentIntensityAnalyzer()
    except ImportError:
        pass

    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer

    project_nltk_data = Path(__file__).resolve().parent.parent / ".nltk_data"
    project_nltk_data.mkdir(exist_ok=True)
    if str(project_nltk_data) not in nltk.data.path:
        nltk.data.path.insert(0, str(project_nltk_data))
    os.environ.setdefault("NLTK_DATA", str(project_nltk_data))

    try:
        return SentimentIntensityAnalyzer()
    except LookupError:
        ok = nltk.download("vader_lexicon", download_dir=str(project_nltk_data), quiet=True)
        if not ok:
            return None
        try:
            return SentimentIntensityAnalyzer()
        except LookupError:
            return None


def score_headlines(
    panel: pd.DataFrame,
    *,
    model: str = "finance_lexicon",
) -> pd.DataFrame:
    """Score the assembled ticker-day headline panel with one transparent model.

    The input should come from `features.assemble_headline_panel()`, so each row
    is one ticker-day-sector text bundle. VADER receives the original text because
    punctuation, casing, intensifiers, and negation are part of its scoring rules.
    """
    required = {"date", "ticker", "sector", "combined_headlines", "headline_count"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"headline panel is missing required columns: {sorted(missing)}")

    scores = panel.copy()
    if model == "finance_lexicon":
        model_scores = scores["combined_headlines"].fillna("").map(_lexicon_scores)
        scores["sentiment_model"] = "finance_lexicon_baseline"
    elif model == "vader":
        analyzer = _vader_analyzer()
        if analyzer is None:
            raise RuntimeError("VADER is unavailable in the build environment")
        model_scores = scores["combined_headlines"].fillna("").map(
            analyzer.polarity_scores
        )
        scores["sentiment_model"] = "vader"
    else:
        raise ValueError("model must be 'finance_lexicon' or 'vader'")

    model_frame = pd.DataFrame(model_scores.tolist(), index=scores.index)
    scores["sentiment_neg"] = model_frame["neg"]
    scores["sentiment_neu"] = model_frame["neu"]
    scores["sentiment_pos"] = model_frame["pos"]
    scores["sentiment_score"] = model_frame["compound"]
    return scores[
        [
            "date",
            "ticker",
            "sector",
            "headline_count",
            "word_count",
            "finance_term_count",
            "sentiment_model",
            "sentiment_neg",
            "sentiment_neu",
            "sentiment_pos",
            "sentiment_score",
        ]
    ]


def compare_sentiment_models(
    panel: pd.DataFrame,
    *,
    audit_size: int = 50,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare the finance lexicon with VADER and return an audit sample.

    The audit sample contains the ticker-days with the largest score differences.
    It is evidence for targeted human review, not a labelled accuracy test.
    """
    finance = score_headlines(panel, model="finance_lexicon")
    vader = score_headlines(panel, model="vader")
    comparison = panel[
        ["date", "ticker", "sector", "headline_count", "combined_headlines"]
    ].copy()
    comparison["Finance score"] = finance["sentiment_score"].to_numpy()
    comparison["VADER score"] = vader["sentiment_score"].to_numpy()
    comparison["Absolute difference"] = (
        comparison["Finance score"] - comparison["VADER score"]
    ).abs()

    def direction(values: pd.Series) -> pd.Series:
        return values.gt(0.05).astype(int) - values.lt(-0.05).astype(int)

    finance_direction = direction(comparison["Finance score"])
    vader_direction = direction(comparison["VADER score"])
    comparison["Direction agreement"] = finance_direction.eq(vader_direction)
    correlation = comparison[["Finance score", "VADER score"]].corr().iloc[0, 1]
    agreement = comparison["Direction agreement"].mean() * 100

    rows = []
    for label, column in [
        ("Finance lexicon", "Finance score"),
        ("VADER", "VADER score"),
    ]:
        values = comparison[column]
        labels = direction(values)
        rows.append(
            {
                "Model": label,
                "Mean sentiment": values.mean(),
                "Standard deviation": values.std(),
                "Neutral ticker-days (%)": labels.eq(0).mean() * 100,
                "Positive ticker-days (%)": labels.eq(1).mean() * 100,
                "Negative ticker-days (%)": labels.eq(-1).mean() * 100,
                "Cross-model correlation": correlation,
                "Direction agreement (%)": agreement,
            }
        )

    audit = comparison.nlargest(audit_size, "Absolute difference").copy()
    audit["Headline bundle"] = audit["combined_headlines"].str.slice(0, 240)
    audit = audit[
        [
            "date",
            "ticker",
            "sector",
            "headline_count",
            "Headline bundle",
            "Finance score",
            "VADER score",
            "Absolute difference",
            "Direction agreement",
        ]
    ]
    return pd.DataFrame(rows), audit.reset_index(drop=True)


def sector_sentiment_index(
    scores: pd.DataFrame,
    *,
    trading_dates: pd.Series | pd.DatetimeIndex | None = None,
    sector_universe: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build an equal-weight daily sentiment index by equity sector.

    Ticker-days with no headlines are treated as neutral (`0.0`) so every sector
    is averaged across its full ticker universe rather than only across firms
    that happened to receive news. The lagged score is first usable on the next
    trading day.
    """
    required = {"date", "ticker", "sector", "sentiment_score", "headline_count"}
    missing = required - set(scores.columns)
    if missing:
        raise ValueError(f"sentiment scores are missing required columns: {sorted(missing)}")

    scored = scores.copy()
    scored["date"] = pd.to_datetime(scored["date"]).dt.normalize()

    if trading_dates is None:
        dates = pd.Index(sorted(scored["date"].unique()), name="date")
    else:
        normalised_dates = pd.Series(pd.to_datetime(trading_dates)).dt.normalize()
        dates = pd.Index(sorted(normalised_dates.unique()), name="date")

    if sector_universe is None:
        universe = scored[["ticker", "sector"]].drop_duplicates()
    else:
        universe = sector_universe[["ticker", "sector"]].drop_duplicates().copy()
        universe["ticker"] = universe["ticker"].astype(str)
        universe["sector"] = universe["sector"].astype(str)

    full_index = pd.MultiIndex.from_product(
        [dates, universe["ticker"].sort_values().unique()],
        names=["date", "ticker"],
    )
    ticker_sector = universe.drop_duplicates("ticker").set_index("ticker")["sector"]

    ticker_day = (
        scored.groupby(["date", "ticker"], observed=True)
        .agg(
            sector=("sector", "first"),
            sentiment_score=("sentiment_score", "mean"),
            headline_count=("headline_count", "sum"),
        )
        .reindex(full_index)
        .reset_index()
    )
    ticker_day["sector"] = ticker_day["ticker"].map(ticker_sector)
    ticker_day["sentiment_score"] = ticker_day["sentiment_score"].fillna(0.0)
    ticker_day["headline_count"] = ticker_day["headline_count"].fillna(0).astype(int)
    ticker_day["has_headlines"] = ticker_day["headline_count"].gt(0)

    sector_index = (
        ticker_day.groupby(["date", "sector"], observed=True)
        .agg(
            sentiment_score=("sentiment_score", "mean"),
            ticker_count=("ticker", "nunique"),
            tickers_with_headlines=("has_headlines", "sum"),
            headline_count=("headline_count", "sum"),
        )
        .reset_index()
        .sort_values(["sector", "date"])
    )
    sector_index["sentiment_lag1"] = sector_index.groupby("sector", observed=True)[
        "sentiment_score"
    ].shift(1)
    sector_index["sentiment_lag1"] = sector_index["sentiment_lag1"].fillna(0.0)
    return sector_index.sort_values(["date", "sector"]).reset_index(drop=True)
