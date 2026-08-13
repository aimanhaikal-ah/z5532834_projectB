"""Reproduce your Part B results. Run from this project folder:

    python scripts/run_part_b.py
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
import pandas as pd  # noqa: E402

from src import etl, evaluation, features, portfolios, sentiment, fusion  # noqa: E402


ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS_DATA = ROOT / "results" / "data"
RESULTS_TABLES = ROOT / "results" / "tables"
RESULTS_FIGURES = ROOT / "results" / "figures"


def _ensure_dirs() -> None:
    for folder in (RESULTS_DATA, RESULTS_TABLES, RESULTS_FIGURES):
        folder.mkdir(parents=True, exist_ok=True)


def _save_growth_figure(fund_returns):
    fig, ax = plt.subplots(figsize=(9, 5))
    for fund, group in fund_returns.groupby("fund", observed=True):
        ax.plot(group["date"], group["growth_of_1"], linewidth=1.4, label=fund)
    ax.set_title("Growth of $1 by BetaVest fund")
    ax.set_xlabel("Date")
    ax.set_ylabel("Growth of $1")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, ncols=2)
    fig.tight_layout()
    fig.savefig(RESULTS_FIGURES / "fund_growth_of_1.png", dpi=180)
    plt.close(fig)


def _save_drawdown_figure(fund_returns, selected_fund):
    frame = fund_returns[fund_returns["fund"].eq(selected_fund)]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.fill_between(frame["date"], frame["drawdown"] * 100, 0, alpha=0.35)
    ax.plot(frame["date"], frame["drawdown"] * 100, linewidth=1.5)
    ax.set_title(f"Drawdown: {selected_fund}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (%)")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(RESULTS_FIGURES / "selected_fund_drawdown.png", dpi=180)
    plt.close(fig)


def _save_weights_figure(fund_weights, selected_fund):
    frame = fund_weights[fund_weights["fund"].eq(selected_fund)].copy()
    latest_mean = (
        frame.groupby("ticker", observed=True)["weight"]
        .mean()
        .sort_values(ascending=False)
    )
    keep = latest_mean.head(10).index
    frame.loc[~frame["ticker"].isin(keep), "ticker"] = "Other"
    wide = (
        frame.groupby(["date", "ticker"], observed=True)["weight"]
        .sum()
        .unstack(fill_value=0)
        .sort_index()
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.stackplot(wide.index, [wide[column] for column in wide.columns], labels=wide.columns)
    ax.set_title(f"Portfolio weights over time: {selected_fund}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Weight")
    ax.legend(fontsize=7, ncols=2, loc="upper left")
    fig.tight_layout()
    fig.savefig(RESULTS_FIGURES / "selected_fund_weights_over_time.png", dpi=180)
    plt.close(fig)


def _save_sentiment_weights_figure(sentiment_weights):
    frame = sentiment_weights.copy()
    frame["date"] = mdates.date2num(frame["date"])
    sector_weights = (
        frame.groupby(["date", "sector"], observed=True)["weight"]
        .sum()
        .unstack(fill_value=0)
        .sort_index()
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.stackplot(
        sector_weights.index,
        [sector_weights[column].astype(float).to_numpy() for column in sector_weights.columns],
        labels=sector_weights.columns,
    )
    ax.xaxis_date()
    ax.set_title("Equity Sentiment Tilt sector weights over time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio weight")
    ax.legend(fontsize=7, ncols=2, loc="upper left")
    fig.tight_layout()
    fig.savefig(RESULTS_FIGURES / "selected_fund_weights_over_time.png", dpi=180)
    plt.close(fig)


def _save_sharpe_figure(metrics):
    ordered = metrics.sort_values("sharpe_ratio", ascending=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(ordered["fund"], ordered["sharpe_ratio"])
    ax.set_title("Sharpe ratio by BetaVest fund")
    ax.set_xlabel("Sharpe ratio")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(RESULTS_FIGURES / "fund_sharpe_ratios.png", dpi=180)
    plt.close(fig)


def _save_sentiment_figure(sector_sentiment):
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for sector, group in sector_sentiment.groupby("sector", observed=True):
        smoothed = group.set_index("date")["sentiment_score"].rolling(21, min_periods=5).mean()
        ax.plot(smoothed.index, smoothed, linewidth=1.3, label=sector)
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.6)
    ax.set_title("BetaVest sector sentiment index")
    ax.set_xlabel("Date")
    ax.set_ylabel("Finance-lexicon sentiment, 21-day moving average")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, ncols=2)
    fig.tight_layout()
    fig.savefig(RESULTS_FIGURES / "sector_sentiment_index.png", dpi=180)
    plt.close(fig)


def _save_fusion_figure(
    fund_returns,
    sentiment_returns,
    *,
    base_fund: str = "Equity Risk Parity",
):
    base = fund_returns[fund_returns["fund"].eq(base_fund)].copy()
    tilted = sentiment_returns.copy()
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(base["date"], base["growth_of_1"], linewidth=1.8, label=base_fund)
    ax.plot(
        tilted["date"],
        tilted["growth_of_1"],
        linewidth=1.8,
        label="Equity Sentiment Tilt",
    )
    ax.set_title("Fusion test: optimiser fund vs sentiment tilt")
    ax.set_xlabel("Date")
    ax.set_ylabel("Growth of $1")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS_FIGURES / "fusion_base_vs_sentiment.png", dpi=180)
    plt.close(fig)


def _save_report_tables(
    metrics,
    sector_sentiment,
    fusion_table,
    tilt_grid,
    robustness_table,
    sentiment_regime_table,
    sentiment_model_summary,
    sentiment_holdout_validation,
):
    report_metrics = metrics.copy()
    for column in [
        "total_return",
        "annualized_return",
        "annualized_volatility",
        "max_drawdown",
        "total_transaction_cost",
    ]:
        report_metrics[column] = report_metrics[column] * 100
    report_metrics = report_metrics[
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
    ].sort_values("sharpe_ratio", ascending=False)
    report_metrics.columns = [
        "Fund",
        "Ann. return (%)",
        "Ann. volatility (%)",
        "Sharpe",
        "Max drawdown (%)",
        "Total return (%)",
        "Avg daily turnover",
        "Total cost (%)",
    ]
    report_metrics.to_csv(RESULTS_TABLES / "performance_metrics_report.csv", index=False)

    sentiment_summary = (
        sector_sentiment.groupby("sector", observed=True)
        .agg(
            avg_sentiment=("sentiment_score", "mean"),
            total_headlines=("headline_count", "sum"),
            avg_tickers_with_headlines=("tickers_with_headlines", "mean"),
        )
        .reset_index()
        .sort_values("avg_sentiment", ascending=False)
    )
    sentiment_summary.columns = [
        "Sector",
        "Average sentiment",
        "Total headlines",
        "Avg tickers with headlines",
    ]
    sentiment_summary.to_csv(RESULTS_TABLES / "sector_sentiment_summary.csv", index=False)

    report_fusion = fusion_table.copy()
    for column in [
        "total_return",
        "annualized_return",
        "annualized_volatility",
        "max_drawdown",
        "total_transaction_cost",
    ]:
        report_fusion[column] = report_fusion[column] * 100
    report_fusion.columns = [
        "Fund",
        "Ann. return (%)",
        "Ann. volatility (%)",
        "Sharpe",
        "Max drawdown (%)",
        "Total return (%)",
        "Avg daily turnover",
        "Total cost (%)",
    ]
    report_fusion.to_csv(RESULTS_TABLES / "fusion_comparison_report.csv", index=False)

    report_grid = tilt_grid.copy()
    for column in [
        "total_return",
        "annualized_return",
        "annualized_volatility",
        "max_drawdown",
        "total_transaction_cost",
    ]:
        report_grid[column] = report_grid[column] * 100
    report_grid = report_grid[
        [
            "sentiment_strength",
            "annualized_return",
            "annualized_volatility",
            "sharpe_ratio",
            "max_drawdown",
            "total_return",
            "average_turnover",
            "total_transaction_cost",
        ]
    ].sort_values("sharpe_ratio", ascending=False)
    report_grid.columns = [
        "Tilt strength",
        "Ann. return (%)",
        "Ann. volatility (%)",
        "Sharpe",
        "Max drawdown (%)",
        "Total return (%)",
        "Avg daily turnover",
        "Total cost (%)",
    ]
    report_grid.to_csv(RESULTS_TABLES / "sentiment_tilt_grid_report.csv", index=False)

    robustness_table.to_csv(RESULTS_TABLES / "robustness_by_period_report.csv", index=False)
    sentiment_regime_table.to_csv(
        RESULTS_TABLES / "sentiment_regime_analysis_report.csv",
        index=False,
    )
    appendix_funds = [
        "Combined Risk Parity",
        "Combined Max Sharpe",
        "Equity Equal Weight",
        "Equity Risk Parity",
        "Equity Sentiment Tilt",
        "Crypto Min Variance",
    ]
    robustness_table[robustness_table["Fund"].isin(appendix_funds)].to_csv(
        RESULTS_TABLES / "robustness_by_period_appendix.csv",
        index=False,
    )
    regime_appendix_funds = [
        "Combined Risk Parity",
        "Equity Risk Parity",
        "Equity Sentiment Tilt",
    ]
    sentiment_regime_table[
        sentiment_regime_table["Fund"].isin(regime_appendix_funds)
    ].to_csv(
        RESULTS_TABLES / "sentiment_regime_analysis_appendix.csv",
        index=False,
    )

    sentiment_model_summary.to_csv(
        RESULTS_TABLES / "sentiment_model_comparison_report.csv",
        index=False,
    )

    holdout_report = sentiment_holdout_validation.copy()
    for column in [
        "holdout_base_return",
        "holdout_tilt_return",
        "holdout_base_drawdown",
        "holdout_tilt_drawdown",
        "holdout_tilt_cost",
    ]:
        holdout_report[column] = holdout_report[column] * 100
    holdout_report = holdout_report[
        [
            "sentiment_model",
            "selected_strength",
            "discovery_base_sharpe",
            "discovery_tilt_sharpe",
            "discovery_sharpe_lift",
            "holdout_base_return",
            "holdout_tilt_return",
            "holdout_base_sharpe",
            "holdout_tilt_sharpe",
            "holdout_sharpe_lift",
            "holdout_base_drawdown",
            "holdout_tilt_drawdown",
            "holdout_tilt_cost",
        ]
    ]
    holdout_report.columns = [
        "Sentiment model",
        "Selected tilt",
        "Discovery base Sharpe",
        "Discovery tilt Sharpe",
        "Discovery Sharpe lift",
        "Holdout base return (%)",
        "Holdout tilt return (%)",
        "Holdout base Sharpe",
        "Holdout tilt Sharpe",
        "Holdout Sharpe lift",
        "Holdout base drawdown (%)",
        "Holdout tilt drawdown (%)",
        "Holdout tilt cost (%)",
    ]
    holdout_report.to_csv(
        RESULTS_TABLES / "sentiment_holdout_validation_report.csv",
        index=False,
    )
    holdout_report[
        [
            "Sentiment model",
            "Selected tilt",
            "Discovery base Sharpe",
            "Discovery tilt Sharpe",
            "Holdout base return (%)",
            "Holdout tilt return (%)",
            "Holdout base Sharpe",
            "Holdout tilt Sharpe",
            "Holdout Sharpe lift",
            "Holdout tilt drawdown (%)",
        ]
    ].to_csv(
        RESULTS_TABLES / "sentiment_holdout_validation_appendix.csv",
        index=False,
    )


def main():
    _ensure_dirs()
    equities = etl.load_clean_equities()
    crypto = etl.load_clean_crypto()
    headlines = etl.load_clean_headlines()
    equity_returns = features.daily_returns(equities)
    crypto_returns = features.daily_returns(crypto)
    returns = features.combined_returns_panel(equity_returns, crypto_returns)
    fund_returns, fund_weights, metrics = portfolios.run_fund_suite(returns, window=252)
    headline_panel = features.assemble_headline_panel(headlines, equities["date"])
    headline_scores = sentiment.score_headlines(
        headline_panel,
        model="finance_lexicon",
    )
    vader_scores = sentiment.score_headlines(headline_panel, model="vader")
    sentiment_model_summary, sentiment_audit_sample = sentiment.compare_sentiment_models(
        headline_panel,
        audit_size=50,
    )
    sector_sentiment = sentiment.sector_sentiment_index(
        headline_scores,
        trading_dates=equities["date"],
        sector_universe=equities[["ticker", "sector"]],
    )
    vader_sector_sentiment = sentiment.sector_sentiment_index(
        vader_scores,
        trading_dates=equities["date"],
        sector_universe=equities[["ticker", "sector"]],
    )

    validation_rows = []
    model_results = {}
    base_equity_risk_parity = fund_returns[
        fund_returns["fund"].eq("Equity Risk Parity")
    ].copy()
    for model_name, model_sector_sentiment in [
        ("Finance lexicon", sector_sentiment),
        ("VADER", vader_sector_sentiment),
    ]:
        discovery_grid = fusion.sentiment_tilt_grid(
            returns,
            model_sector_sentiment,
            strengths=(0.05, 0.10, 0.15, 0.20, 0.25, 0.30),
            base_method="risk_parity",
            window=252,
            rebalance="ME",
            max_weight=0.25,
            transaction_cost_bps=10.0,
            start_date="2021-01-04",
            end_date="2022-12-30",
        )
        selected_strength = float(discovery_grid.iloc[0]["sentiment_strength"])
        model_returns, model_weights, model_metrics = fusion.apply_sentiment(
            returns,
            model_sector_sentiment,
            base_method="risk_parity",
            window=252,
            rebalance="ME",
            max_weight=0.25,
            strength=selected_strength,
            min_multiplier=0.70,
            max_multiplier=1.30,
            start_date="2021-01-04",
            transaction_cost_bps=10.0,
        )
        validation_rows.append(
            fusion.holdout_validation_row(
                base_equity_risk_parity,
                model_returns,
                model_name=model_name,
                selected_strength=selected_strength,
            )
        )
        model_results[model_name] = (
            discovery_grid,
            model_returns,
            model_weights,
            model_metrics,
        )

    sentiment_holdout_validation = pd.DataFrame(validation_rows)
    tilt_grid, sentiment_returns, sentiment_weights, sentiment_metrics = model_results[
        "Finance lexicon"
    ]
    best_tilt_strength = float(tilt_grid.iloc[0]["sentiment_strength"])
    fusion_table = fusion.fusion_comparison(
        metrics,
        sentiment_metrics,
        base_fund="Equity Risk Parity",
    )
    app_fund_returns = pd.concat([fund_returns, sentiment_returns], ignore_index=True)
    robustness_table = evaluation.robustness_by_period(app_fund_returns)
    sentiment_regime_table = evaluation.sentiment_regime_analysis(
        app_fund_returns,
        sector_sentiment,
    )

    returns.to_csv(RESULTS_DATA / "combined_returns_panel.csv", index=False)
    fund_returns.to_csv(RESULTS_DATA / "fund_returns.csv", index=False)
    fund_weights.to_csv(RESULTS_DATA / "fund_weights.csv", index=False)
    headline_panel.to_csv(RESULTS_DATA / "headline_panel.csv", index=False)
    headline_scores.to_csv(RESULTS_DATA / "headline_sentiment_scores.csv", index=False)
    vader_sector_sentiment.to_csv(
        RESULTS_DATA / "vader_sector_sentiment_index.csv",
        index=False,
    )
    sentiment_audit_sample.to_csv(
        RESULTS_TABLES / "sentiment_model_disagreement_audit.csv",
        index=False,
    )
    sector_sentiment.to_csv(RESULTS_DATA / "sector_sentiment_index.csv", index=False)
    sentiment_returns.to_csv(RESULTS_DATA / "sentiment_fund_returns.csv", index=False)
    sentiment_weights.to_csv(RESULTS_DATA / "sentiment_fund_weights.csv", index=False)
    metrics.to_csv(RESULTS_TABLES / "performance_metrics.csv", index=False)
    sentiment_metrics.to_csv(RESULTS_TABLES / "sentiment_fund_metrics.csv", index=False)
    fusion_table.to_csv(RESULTS_TABLES / "fusion_comparison.csv", index=False)
    tilt_grid.to_csv(RESULTS_TABLES / "sentiment_tilt_grid.csv", index=False)
    sentiment_holdout_validation.to_csv(
        RESULTS_TABLES / "sentiment_holdout_validation.csv",
        index=False,
    )
    _save_report_tables(
        metrics,
        sector_sentiment,
        fusion_table,
        tilt_grid,
        robustness_table,
        sentiment_regime_table,
        sentiment_model_summary,
        sentiment_holdout_validation,
    )

    best_fund = metrics.sort_values("sharpe_ratio", ascending=False).iloc[0]["fund"]
    _save_growth_figure(fund_returns)
    _save_drawdown_figure(fund_returns, best_fund)
    _save_sentiment_weights_figure(sentiment_weights)
    _save_sharpe_figure(metrics)
    _save_sentiment_figure(sector_sentiment)
    _save_fusion_figure(fund_returns, sentiment_returns, base_fund="Equity Risk Parity")

    print(f"equities: {equities.shape}, crypto: {crypto.shape}, headlines: {headlines.shape}")
    print(f"combined returns panel: {returns.shape} -> {RESULTS_DATA / 'combined_returns_panel.csv'}")
    print(f"fund returns: {fund_returns.shape} -> {RESULTS_DATA / 'fund_returns.csv'}")
    print(f"fund weights: {fund_weights.shape} -> {RESULTS_DATA / 'fund_weights.csv'}")
    print(f"sector sentiment: {sector_sentiment.shape} -> {RESULTS_DATA / 'sector_sentiment_index.csv'}")
    print(f"fusion comparison: {fusion_table.shape} -> {RESULTS_TABLES / 'fusion_comparison.csv'}")
    print(f"robustness table: {robustness_table.shape} -> {RESULTS_TABLES / 'robustness_by_period_report.csv'}")
    print(f"sentiment regime table: {sentiment_regime_table.shape} -> {RESULTS_TABLES / 'sentiment_regime_analysis_report.csv'}")
    print(f"discovery-selected sentiment tilt strength: {best_tilt_strength:.2f}")
    print(f"sentiment holdout validation: {sentiment_holdout_validation.shape} -> {RESULTS_TABLES / 'sentiment_holdout_validation_report.csv'}")
    print(f"metrics: {metrics.shape} -> {RESULTS_TABLES / 'performance_metrics.csv'}")
    print(f"best fund by Sharpe: {best_fund}")


if __name__ == "__main__":
    main()
