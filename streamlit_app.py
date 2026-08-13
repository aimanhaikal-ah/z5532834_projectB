"""BetaVest Streamlit app.

The deployed app reads precomputed Part B artifacts from results/. It does not
download raw data, run VADER, or recompute portfolio backtests.
"""
from __future__ import annotations

import pathlib
from string import Template

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ROOT = pathlib.Path(__file__).resolve().parent
RESULTS_DATA = ROOT / "results" / "data"
RESULTS_TABLES = ROOT / "results" / "tables"
CACHE_TTL_SECONDS = 6 * 60 * 60
FUND_COLOR_SEQUENCE = [
    "#2F6ECB",
    "#B0172E",
    "#13A38B",
    "#7C3AED",
    "#F59E0B",
    "#2563EB",
    "#DC2626",
    "#059669",
    "#9333EA",
    "#EA580C",
    "#0891B2",
    "#4B5563",
    "#F43F5E",
]


st.set_page_config(
    page_title="BetaVest",
    page_icon=":material/monitoring:",
    layout="wide",
)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_outputs() -> dict[str, pd.DataFrame]:
    """Load precomputed app artifacts."""
    return {
        "fund_returns": pd.read_csv(RESULTS_DATA / "fund_returns.csv", parse_dates=["date"]),
        "fund_weights": pd.read_csv(RESULTS_DATA / "fund_weights.csv", parse_dates=["date"]),
        "asset_metadata": pd.read_csv(RESULTS_DATA / "combined_returns_panel.csv")[
            ["ticker", "sector", "asset_class"]
        ].drop_duplicates("ticker"),
        "metrics": pd.read_csv(RESULTS_TABLES / "performance_metrics_report.csv"),
        "sector_sentiment": pd.read_csv(
            RESULTS_DATA / "sector_sentiment_index.csv",
            parse_dates=["date"],
        ),
        "sentiment_summary": pd.read_csv(RESULTS_TABLES / "sector_sentiment_summary.csv"),
        "sentiment_returns": pd.read_csv(
            RESULTS_DATA / "sentiment_fund_returns.csv",
            parse_dates=["date"],
        ),
        "sentiment_weights": pd.read_csv(
            RESULTS_DATA / "sentiment_fund_weights.csv",
            parse_dates=["date"],
        ),
        "fusion": pd.read_csv(RESULTS_TABLES / "fusion_comparison_report.csv"),
        "tilt_grid": pd.read_csv(RESULTS_TABLES / "sentiment_tilt_grid_report.csv"),
        "robustness": pd.read_csv(RESULTS_TABLES / "robustness_by_period_report.csv"),
        "sentiment_regimes": pd.read_csv(
            RESULTS_TABLES / "sentiment_regime_analysis_report.csv",
        ),
        "sentiment_model_comparison": pd.read_csv(
            RESULTS_TABLES / "sentiment_model_comparison_report.csv",
        ),
        "sentiment_holdout": pd.read_csv(
            RESULTS_TABLES / "sentiment_holdout_validation_report.csv",
        ),
        "sentiment_audit": pd.read_csv(
            RESULTS_TABLES / "sentiment_model_disagreement_audit.csv",
            parse_dates=["date"],
        ),
    }


def pct(value: float) -> str:
    return f"{value:.2f}%"


def fear_greed_label(score: float) -> str:
    """Translate a 0-100 sentiment percentile into an investor-facing label."""
    if score < 25:
        return "Fear"
    if score < 45:
        return "Cautious"
    if score <= 55:
        return "Neutral"
    if score <= 75:
        return "Greed"
    return "Extreme greed"


def query_list(key: str, valid_options: list[str], fallback: list[str]) -> list[str]:
    """Read a pipe-delimited URL query parameter and keep valid selections."""
    raw = st.query_params.get(key)
    if raw is None:
        return fallback
    values = [value for value in str(raw).split("|") if value in valid_options]
    return values or fallback


def query_value(key: str, valid_options: list[str], fallback: str) -> str:
    """Read one URL query parameter value with a valid fallback."""
    raw = st.query_params.get(key)
    if raw is None:
        return fallback
    value = str(raw)
    return value if value in valid_options else fallback


def filter_by_horizon(frame: pd.DataFrame, horizon: str) -> pd.DataFrame:
    """Filter chart data to the selected display horizon."""
    if horizon == "Full sample" or frame.empty:
        return frame
    years = {"1Y": 1, "2Y": 2}[horizon]
    cutoff = frame["date"].max() - pd.DateOffset(years=years)
    return frame[frame["date"].ge(cutoff)].copy()


def metric_card(column, label: str, value: object, delta: object | None = None) -> None:
    """Render a KPI inside a bordered card container."""
    with column:
        with st.container(border=True, height="stretch", vertical_alignment="center"):
            st.markdown(f'<div class="kpi-label">{label}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="kpi-value">{value}</div>', unsafe_allow_html=True)
            if delta is not None:
                st.markdown(f'<div class="kpi-delta">↑ {delta}</div>', unsafe_allow_html=True)


def compact_table_height(row_count: int, *, min_height: int = 150, max_height: int = 430) -> int:
    """Streamlit dataframe height with no large empty grid area."""
    return min(max_height, max(min_height, 38 * row_count + 44))


def csv_download_button(label: str, frame: pd.DataFrame, file_name: str) -> None:
    """Render a compact CSV download button below the related exhibit."""
    st.download_button(
        label=f"Download {label}",
        data=frame.to_csv(index=False),
        file_name=file_name,
        mime="text/csv",
    )


def plotly_chart(fig: go.Figure, **kwargs) -> None:
    """Render Plotly figures using the app-selected template, not Streamlit's browser theme."""
    st.plotly_chart(fig, theme=None, **kwargs)


def risk_label(row: pd.Series) -> str:
    """Translate backtest risk into a simple app-facing label."""
    volatility = float(row["Ann. volatility (%)"])
    drawdown = abs(float(row["Max drawdown (%)"]))
    if volatility >= 50 or drawdown >= 60:
        return "Speculative"
    if volatility >= 22 or drawdown >= 25:
        return "Aggressive"
    if volatility <= 13 and drawdown <= 16:
        return "Defensive"
    return "Core"


def suggested_use(row: pd.Series) -> str:
    fund = str(row["Fund"])
    label = risk_label(row)
    if "Crypto" in fund:
        return "Satellite only"
    if "Sentiment Tilt" in fund:
        return "Experimental equity sleeve"
    if label == "Defensive":
        return "Lower-risk stabiliser"
    if "Combined" in fund:
        return "Growth sleeve"
    return "Core benchmark"


def fund_profile(fund: str, row: pd.Series) -> dict[str, str]:
    """Client-facing fact-sheet description for one fund."""
    risk = risk_label(row)
    use = suggested_use(row)
    if fund == "Equity Sentiment Tilt":
        objective = "Tilt an equity risk-parity fund toward sectors with stronger lagged news sentiment."
        main_risk = "Sentiment model error and active sector tilts."
    elif "Risk Parity" in fund:
        objective = "Balance risk contributions so no single asset dominates portfolio volatility."
        main_risk = "Model risk from changing volatility and correlation estimates."
    elif "Min Variance" in fund:
        objective = "Reduce realised volatility and drawdown risk using a defensive optimiser."
        main_risk = "Lower upside during strong growth markets."
    elif "Max Sharpe" in fund:
        objective = "Target higher return per unit of estimated risk using historical mean-variance inputs."
        main_risk = "Noisy return estimates and higher turnover."
    else:
        objective = "Provide a transparent diversified benchmark with simple equal weights."
        main_risk = "Limited risk control beyond broad diversification."

    return {
        "Objective": objective,
        "Investor profile": f"{risk} risk profile; intended as a {use.lower()}.",
        "Main risk": main_risk,
    }


def benchmark_for(fund: str) -> str:
    """Choose the most relevant app benchmark for a selected fund."""
    if fund == "Equity Sentiment Tilt":
        return "Equity Risk Parity"
    if fund.startswith("Combined"):
        return "Combined Equal Weight"
    if fund.startswith("Crypto"):
        return "Crypto Equal Weight"
    return "Equity Equal Weight"


def benchmark_comparison(
    fund: str,
    row: pd.Series,
    display_metrics: pd.DataFrame,
) -> pd.DataFrame:
    """Return a compact benchmark comparison for the fact sheet."""
    benchmark = benchmark_for(fund)
    benchmark_row = display_metrics[display_metrics["Fund"].eq(benchmark)]
    if benchmark_row.empty:
        return pd.DataFrame()
    benchmark_row = benchmark_row.iloc[0]
    metrics_to_compare = [
        ("Ann. return (%)", "Ann. return"),
        ("Sharpe", "Sharpe"),
        ("Max drawdown (%)", "Max drawdown"),
    ]
    rows = []
    for column, label in metrics_to_compare:
        fund_value = float(row[column])
        benchmark_value = float(benchmark_row[column])
        difference = fund_value - benchmark_value
        rows.append(
            {
                "Metric": label,
                "Selected fund": f"{fund_value:.2f}" if column != "Sharpe" else f"{fund_value:.3f}",
                "Benchmark": f"{benchmark_value:.2f}" if column != "Sharpe" else f"{benchmark_value:.3f}",
                "Difference": f"{difference:+.2f}" if column != "Sharpe" else f"{difference:+.3f}",
            }
        )
    return pd.DataFrame(rows)


def drawdown_summary(returns_frame: pd.DataFrame) -> dict[str, str]:
    """Summarise the worst drawdown episode for the selected fund."""
    frame = returns_frame.sort_values("date").copy()
    trough = frame.loc[frame["drawdown"].idxmin()]
    latest = frame.iloc[-1]
    recovered = "Recovered by latest date" if float(latest["drawdown"]) >= -0.001 else "Not fully recovered"
    return {
        "Worst drawdown": pct(float(trough["drawdown"]) * 100),
        "Trough date": str(pd.Timestamp(trough["date"]).date()),
        "Recovery status": recovered,
    }


def enrich_weights(weights: pd.DataFrame, asset_metadata: pd.DataFrame) -> pd.DataFrame:
    """Attach sector and asset-class metadata to latest holdings."""
    enriched = weights.copy()
    if "sector" not in enriched.columns:
        enriched = enriched.merge(asset_metadata, on="ticker", how="left")
    else:
        enriched = enriched.merge(
            asset_metadata[["ticker", "asset_class"]],
            on="ticker",
            how="left",
        )
    enriched["sector"] = enriched["sector"].fillna("Unknown")
    enriched["asset_class"] = enriched["asset_class"].fillna("Equity")
    return enriched


def exposure_table(weights: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    """Aggregate weights into an app-facing exposure table."""
    frame = (
        weights.groupby(column, observed=True)["weight"]
        .sum()
        .sort_values(ascending=False)
        .mul(100)
        .reset_index()
    )
    frame.columns = [label, "Weight (%)"]
    return frame


def allocation_key(fund: str, suffix: str) -> str:
    """Stable Streamlit state key for allocation controls."""
    cleaned = "".join(character if character.isalnum() else "_" for character in fund)
    return f"allocation_{cleaned}_{suffix}"


def allocation_keys_for(funds: list[str]) -> dict[str, tuple[str, str]]:
    """Return slider/input keys for selected allocation funds."""
    return {
        fund: (allocation_key(fund, "slider"), allocation_key(fund, "input"))
        for fund in funds
    }


def initialise_allocation_state(funds: list[str]) -> None:
    """Initialise or repair selected allocation weights so they sum to 100%."""
    if not funds:
        return
    keys = allocation_keys_for(funds)
    existing_total = 0.0
    missing_funds = []
    for fund, (_, input_key) in keys.items():
        if input_key in st.session_state:
            existing_total += float(st.session_state[input_key])
        else:
            missing_funds.append(fund)

    remaining = max(100.0 - existing_total, 0.0)
    default_missing = remaining / len(missing_funds) if missing_funds else 0.0
    for fund in missing_funds:
        _, input_key = keys[fund]
        st.session_state[input_key] = default_missing

    values = {fund: float(st.session_state[keys[fund][1]]) for fund in funds}
    total = sum(values.values())
    if total <= 0:
        values = {fund: 100.0 / len(funds) for fund in funds}
    else:
        values = {fund: value / total * 100.0 for fund, value in values.items()}

    rounded = {fund: round(value, 2) for fund, value in values.items()}
    difference = round(100.0 - sum(rounded.values()), 2)
    first_fund = funds[0]
    rounded[first_fund] = round(rounded[first_fund] + difference, 2)

    for fund, value in rounded.items():
        slider_key, input_key = keys[fund]
        st.session_state[slider_key] = value
        st.session_state[input_key] = value


def rebalance_allocation(changed_fund: str, funds: list[str], source_key: str) -> None:
    """Keep allocation controls exactly invested at 100% after one change."""
    keys = allocation_keys_for(funds)
    changed_value = max(0.0, min(float(st.session_state[source_key]), 100.0))
    other_funds = [fund for fund in funds if fund != changed_fund]

    if not other_funds:
        new_values = {changed_fund: 100.0}
    else:
        remaining = 100.0 - changed_value
        current_others = {
            fund: float(st.session_state.get(keys[fund][1], 0.0))
            for fund in other_funds
        }
        other_total = sum(current_others.values())
        if other_total <= 0:
            new_values = {fund: remaining / len(other_funds) for fund in other_funds}
        else:
            new_values = {
                fund: current_others[fund] / other_total * remaining
                for fund in other_funds
            }
        new_values[changed_fund] = changed_value

    rounded = {fund: round(value, 2) for fund, value in new_values.items()}
    difference = round(100.0 - sum(rounded.values()), 2)
    if rounded:
        adjustment_fund = changed_fund if changed_fund in rounded else next(iter(rounded))
        rounded[adjustment_fund] = round(rounded[adjustment_fund] + difference, 2)

    for fund, value in rounded.items():
        slider_key, input_key = keys[fund]
        st.session_state[slider_key] = value
        st.session_state[input_key] = value


def takeaway_card(title: str, body: str) -> None:
    """Render a concise interpretation card for a tab."""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.write(body)


def compare_guidance() -> str:
    """Explain how investors should interpret the comparison view."""
    return (
        "Return alone can be misleading. Use Sharpe and drawdown together: "
        "core funds should balance return with risk, while crypto-only funds "
        "are better treated as higher-risk satellite exposure."
    )


def allocation_risk_message(
    normalised: dict[str, float],
    display_metrics: pd.DataFrame,
) -> tuple[str, str]:
    """Return an investor-protection warning for the selected allocation."""
    selected_metrics = display_metrics.set_index("Fund")
    speculative_weight = sum(
        weight
        for fund, weight in normalised.items()
        if selected_metrics.loc[fund, "Risk label"] == "Speculative"
    )
    aggressive_weight = sum(
        weight
        for fund, weight in normalised.items()
        if selected_metrics.loc[fund, "Risk label"] == "Aggressive"
    )
    if speculative_weight >= 25:
        return (
            "High speculative exposure",
            f"{speculative_weight:.1f}% of the allocation is in speculative funds. "
            "Consider reducing crypto-only exposure if the investor cannot tolerate large drawdowns.",
        )
    if speculative_weight + aggressive_weight >= 50:
        return (
            "Growth-heavy allocation",
            f"{speculative_weight + aggressive_weight:.1f}% is in aggressive or speculative funds. "
            "This may suit higher-risk users but should not be presented as a defensive allocation.",
        )
    return (
        "Balanced risk mix",
        "The selected allocation is mostly in core or defensive funds. Review drawdowns before using it as a model allocation.",
    )


def allocation_download_frame(allocation_frame: pd.DataFrame) -> pd.DataFrame:
    """Prepare selected allocation for CSV download."""
    download = allocation_frame.copy()
    download["Allocation (%)"] = download["Allocation (%)"].round(2)
    download["Ann. return contribution (%)"] = download["Ann. return contribution (%)"].round(2)
    download["Volatility contribution proxy (%)"] = download[
        "Volatility contribution proxy (%)"
    ].round(2)
    return download


def comparison_chart(
    fund_returns: pd.DataFrame,
    selected: list[str],
    view: str,
    fund_colors: dict[str, str],
) -> go.Figure:
    """Interactive fund comparison chart for growth, drawdown, or rolling Sharpe."""
    frame = fund_returns[fund_returns["fund"].isin(selected)].sort_values(["fund", "date"]).copy()
    if view == "Growth of $1":
        y_col = "growth_of_1"
        y_label = "Growth of $1"
        chart_frame = frame
    elif view == "Drawdown":
        y_col = "drawdown"
        y_label = "Drawdown"
        chart_frame = frame
    elif view == "Rolling Sharpe":
        y_col = "rolling_sharpe"
        y_label = "63-day rolling Sharpe"
        rolling = frame.groupby("fund", observed=True)["daily_return"].transform
        rolling_mean = rolling(lambda values: values.rolling(63, min_periods=30).mean())
        rolling_vol = rolling(lambda values: values.rolling(63, min_periods=30).std())
        frame[y_col] = rolling_mean / rolling_vol * (252 ** 0.5)
        chart_frame = frame.dropna(subset=[y_col])
    else:
        raise ValueError(f"unknown comparison view: {view}")

    fig = px.line(
        chart_frame,
        x="date",
        y=y_col,
        color="fund",
        color_discrete_map=fund_colors,
        labels={"date": "Date", y_col: y_label, "fund": "Fund"},
    )
    fig.update_layout(hovermode="x unified", legend_title_text="")
    if view == "Drawdown":
        fig.update_yaxes(tickformat=".0%")
    if view == "Rolling Sharpe":
        fig.add_hline(y=0, line_width=1, line_color="black", opacity=0.45)
    return fig


def comparison_download_frame(fund_returns: pd.DataFrame, selected: list[str], view: str) -> pd.DataFrame:
    """Prepare the displayed comparison series for CSV export."""
    frame = fund_returns[fund_returns["fund"].isin(selected)].sort_values(["fund", "date"]).copy()
    if view == "Rolling Sharpe":
        rolling = frame.groupby("fund", observed=True)["daily_return"].transform
        rolling_mean = rolling(lambda values: values.rolling(63, min_periods=30).mean())
        rolling_vol = rolling(lambda values: values.rolling(63, min_periods=30).std())
        frame["rolling_sharpe"] = rolling_mean / rolling_vol * (252 ** 0.5)
    return frame


def robustness_chart(robustness: pd.DataFrame, selected: list[str]) -> go.Figure:
    """Heatmap of Sharpe ratios across market sub-periods."""
    period_order = ["Full sample", "2021 recovery", "2022 drawdown", "2023 recovery"]
    frame = robustness[robustness["Fund"].isin(selected)].copy()
    frame["Period"] = pd.Categorical(frame["Period"], categories=period_order, ordered=True)
    pivot = frame.pivot(index="Period", columns="Fund", values="Sharpe").sort_index()
    fig = px.imshow(
        pivot,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdYlGn",
        labels={"x": "Fund", "y": "Period", "color": "Sharpe"},
    )
    fig.update_layout(height=360, margin={"l": 20, "r": 20, "t": 20, "b": 20})
    return fig


def drawdown_chart(fund_returns: pd.DataFrame, fund: str) -> go.Figure:
    frame = fund_returns[fund_returns["fund"].eq(fund)].sort_values("date")
    fig = px.area(
        frame,
        x="date",
        y="drawdown",
        labels={"date": "Date", "drawdown": "Drawdown"},
    )
    fig.update_traces(line_color="#B42318", fillcolor="rgba(180,35,24,0.25)")
    fig.update_layout(hovermode="x unified", showlegend=False)
    fig.update_yaxes(tickformat=".0%")
    return fig


def sector_weight_chart(sentiment_weights: pd.DataFrame) -> go.Figure:
    frame = (
        sentiment_weights.groupby(["date", "sector"], observed=True)["weight"]
        .sum()
        .reset_index()
        .sort_values("date")
    )
    fig = px.area(
        frame,
        x="date",
        y="weight",
        color="sector",
        labels={"date": "Date", "weight": "Portfolio weight", "sector": "Sector"},
    )
    fig.update_layout(hovermode="x unified", legend_title_text="")
    fig.update_yaxes(tickformat=".0%")
    return fig


def sentiment_chart(sector_sentiment: pd.DataFrame, sectors: list[str]) -> go.Figure:
    frame = sector_sentiment[sector_sentiment["sector"].isin(sectors)].copy()
    frame = frame.sort_values(["sector", "date"])
    frame["Sentiment, 21-day average"] = frame.groupby("sector", observed=True)[
        "sentiment_score"
    ].transform(lambda values: values.rolling(21, min_periods=5).mean())
    fig = px.line(
        frame.dropna(subset=["Sentiment, 21-day average"]),
        x="date",
        y="Sentiment, 21-day average",
        color="sector",
        labels={"date": "Date", "sector": "Sector"},
    )
    fig.add_hline(y=0, line_width=1, line_color="black", opacity=0.45)
    fig.update_layout(hovermode="x unified", legend_title_text="")
    return fig


def sentiment_regime_chart(
    regime_table: pd.DataFrame,
    selected: list[str],
    fund_colors: dict[str, str],
) -> go.Figure:
    """Bar chart of average daily returns by lagged sentiment regime."""
    regime_order = ["Negative", "Neutral", "Positive"]
    frame = regime_table[regime_table["Fund"].isin(selected)].copy()
    frame["Regime"] = pd.Categorical(frame["Regime"], categories=regime_order, ordered=True)
    frame = frame.sort_values(["Regime", "Fund"])
    fig = px.bar(
        frame,
        x="Regime",
        y="Average daily return (%)",
        color="Fund",
        color_discrete_map=fund_colors,
        barmode="group",
        labels={"Average daily return (%)": "Average daily return (%)"},
    )
    fig.add_hline(y=0, line_width=1, line_color="black", opacity=0.45)
    fig.update_layout(hovermode="x unified", legend_title_text="", height=360)
    return fig


def fear_greed_gauge(score: float, label: str) -> go.Figure:
    """Gauge chart for the internal BetaVest fear-greed score."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"size": 30}},
            title={"text": label, "font": {"size": 18}},
            gauge={
                "axis": {"range": [0, 100], "tickmode": "array", "tickvals": [0, 25, 50, 75, 100]},
                "bar": {"color": "#B0172E"},
                "steps": [
                    {"range": [0, 25], "color": "#FEE2E2"},
                    {"range": [25, 45], "color": "#FED7AA"},
                    {"range": [45, 55], "color": "#F8FAFC"},
                    {"range": [55, 75], "color": "#DCFCE7"},
                    {"range": [75, 100], "color": "#BBF7D0"},
                ],
                "threshold": {
                    "line": {"color": "#111827", "width": 3},
                    "thickness": 0.75,
                    "value": score,
                },
            },
        )
    )
    fig.update_layout(height=230, margin={"l": 16, "r": 16, "t": 36, "b": 8})
    return fig


def allocation_chart(weights: dict[str, float], fund_colors: dict[str, str]) -> go.Figure:
    frame = pd.DataFrame(
        {"Fund": list(weights.keys()), "Allocation": [value / 100 for value in weights.values()]}
    )
    fig = px.pie(
        frame,
        names="Fund",
        values="Allocation",
        hole=0.45,
        color="Fund",
        color_discrete_map=fund_colors,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        textfont_size=14,
        marker_line_width=1.5,
        marker_line_color="white",
    )
    fig.update_layout(
        height=520,
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.14,
            "xanchor": "center",
            "x": 0.5,
        },
        uniformtext_minsize=12,
        uniformtext_mode="hide",
    )
    return fig


def allocation_growth_path(
    returns: pd.DataFrame,
    weights: dict[str, float],
    annual_fee_pct: float,
) -> pd.DataFrame:
    """Calculate gross and fee-adjusted growth from precomputed fund returns."""
    selected = list(weights)
    wide = (
        returns[returns["fund"].isin(selected)]
        .pivot(index="date", columns="fund", values="daily_return")
        .sort_index()
        .dropna(subset=selected)
    )
    if wide.empty:
        return pd.DataFrame(columns=["date", "Gross", "Net of fee"])
    weight_series = pd.Series({fund: weight / 100 for fund, weight in weights.items()})
    gross_return = wide[selected].mul(weight_series, axis=1).sum(axis=1)
    daily_fee_factor = (1.0 - annual_fee_pct / 100.0) ** (1.0 / 252.0)
    net_return = (1.0 + gross_return) * daily_fee_factor - 1.0
    return pd.DataFrame(
        {
            "date": wide.index,
            "Gross": (1.0 + gross_return).cumprod(),
            "Net of fee": (1.0 + net_return).cumprod(),
        }
    ).reset_index(drop=True)


def allocation_growth_chart(growth: pd.DataFrame) -> go.Figure:
    """Plot gross and fee-adjusted growth for the selected allocation."""
    long = growth.melt(id_vars="date", var_name="Series", value_name="Growth of $1")
    fig = px.line(
        long,
        x="date",
        y="Growth of $1",
        color="Series",
        color_discrete_map={"Gross": "#2F6ECB", "Net of fee": "#B0172E"},
    )
    fig.update_layout(
        height=390,
        hovermode="x unified",
        legend_title_text="",
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
    )
    return fig


try:
    data = load_outputs()
except Exception as exc:
    load_outputs.clear()
    st.error("BetaVest result files could not be loaded.")
    st.caption("Run `scripts/run_part_b.py` from the project folder, then refresh the app.")
    st.caption(str(exc))
    st.stop()
fund_returns = data["fund_returns"]
fund_weights = data["fund_weights"]
asset_metadata = data["asset_metadata"]
metrics = data["metrics"]
sector_sentiment = data["sector_sentiment"]
sentiment_summary = data["sentiment_summary"]
sentiment_returns = data["sentiment_returns"]
sentiment_weights = data["sentiment_weights"]
fusion = data["fusion"]
tilt_grid = data["tilt_grid"]
robustness = data["robustness"]
sentiment_regimes = data["sentiment_regimes"]
sentiment_model_comparison = data["sentiment_model_comparison"]
sentiment_holdout = data["sentiment_holdout"]
sentiment_audit = data["sentiment_audit"]
sentiment_returns_for_compare = sentiment_returns[
    ["date", "fund", "asset_family", "method", "daily_return", "growth_of_1", "drawdown"]
]
display_returns = pd.concat([fund_returns, sentiment_returns_for_compare], ignore_index=True)
sentiment_metric_row = fusion[fusion["Fund"].eq("Equity Sentiment Tilt")]
display_metrics = pd.concat([metrics, sentiment_metric_row], ignore_index=True)
display_metrics["Risk label"] = display_metrics.apply(risk_label, axis=1)
display_metrics["Suggested use"] = display_metrics.apply(suggested_use, axis=1)

latest_fund_date = display_returns["date"].max().date()
latest_sentiment_date = sector_sentiment["date"].max().date()
fund_names = display_metrics["Fund"].drop_duplicates().tolist()
horizon_options = ["Full sample", "1Y", "2Y"]
default_funds = ["Equity Equal Weight", "Combined Risk Parity", "Equity Sentiment Tilt"]
available_funds = fund_names
fund_color_map = {
    fund: FUND_COLOR_SEQUENCE[index % len(FUND_COLOR_SEQUENCE)]
    for index, fund in enumerate(available_funds)
}
default_selected_funds = query_list(
    "funds",
    available_funds,
    [fund for fund in default_funds if fund in available_funds],
)
fact_sheet_default = query_value("fact_sheet", available_funds, available_funds[0])
sector_options = sorted(sector_sentiment["sector"].unique())
default_selected_sectors = query_list(
    "sectors",
    sector_options,
    ["Consumer", "Tech", "Healthcare", "Energy"],
)
full_start_date = display_returns["date"].min().date()
full_end_date = display_returns["date"].max().date()
if "dark_app_theme" not in st.session_state:
    st.session_state["dark_app_theme"] = st.query_params.get("theme", "light") == "dark"
app_theme_dark = bool(st.session_state["dark_app_theme"])
theme_colors = {
    "page": "#0F172A" if app_theme_dark else "#FFFFFF",
    "sidebar": "#111827" if app_theme_dark else "#F8F4F0",
    "card": "#111827" if app_theme_dark else "#FFFFFF",
    "card_border": "#64748B" if app_theme_dark else "#D9D9D9",
    "text": "#E5E7EB" if app_theme_dark else "#262730",
    "muted": "#CBD5E1" if app_theme_dark else "#6B7280",
    "header_border": "#334155" if app_theme_dark else "#E5E7EB",
    "badge_bg": "#2A1720" if app_theme_dark else "#F8F4F0",
    "badge_border": "#7A1F2D" if app_theme_dark else "#E6DDD5",
    "badge_text": "#F8CBD3" if app_theme_dark else "#7A1F2D",
    "delta_bg": "#123524" if app_theme_dark else "#DFF7E8",
    "delta_text": "#86EFAC" if app_theme_dark else "#0E7C3A",
    "control_bg": "#172033" if app_theme_dark else "#FFFFFF",
    "control_hover": "#1E293B" if app_theme_dark else "#F8F4F0",
    "control_border": "#475569" if app_theme_dark else "#D9D9D9",
    "control_muted": "#94A3B8" if app_theme_dark else "#6B7280",
    "accent": "#B0172E",
    "accent_soft": "#2A1720" if app_theme_dark else "#FFF1F3",
    "chip_text": "#FFFFFF",
    "chip_icon": "#F8CBD3",
    "table_header": "#1E293B" if app_theme_dark else "#F8FAFC",
    "card_shadow": "0 0 0 1px rgba(100, 116, 139, 0.35)" if app_theme_dark else "none",
}

st.markdown(
    Template(
        """
    <style>
    .stApp {
        background: $page;
        color: $text;
    }
    [data-testid="stSidebar"] {
        background: $sidebar;
    }
    [data-testid="stSidebar"] * {
        color: $text;
    }
    h1, h2, h3, h4, h5, h6, p, li, label,
    [data-testid="stMarkdownContainer"] {
        color: $text;
    }
    [data-testid="stCaptionContainer"],
    [data-testid="stMarkdownContainer"] small {
        color: $muted;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: $card;
        border: 1px solid $card_border;
        box-shadow: $card_shadow;
    }
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        border-color: $card_border;
    }
    .block-container {
        padding-top: 2.2rem;
    }
    .app-header {
        border-bottom: 1px solid $header_border;
        margin-bottom: 1.2rem;
        padding: 0.6rem 0 1.1rem 0;
    }
    .brand-row {
        align-items: center;
        display: flex;
        gap: 1rem;
        justify-content: space-between;
    }
    .brand-left {
        align-items: center;
        display: flex;
        gap: 0.85rem;
        min-width: 0;
    }
    .brand-mark {
        align-items: center;
        background: #B0172E;
        border-radius: 12px;
        color: white;
        display: flex;
        flex: 0 0 auto;
        font-size: 1.7rem;
        font-weight: 800;
        height: 3.25rem;
        justify-content: center;
        letter-spacing: 0;
        width: 3.25rem;
    }
    .brand-name {
        color: $text;
        font-size: clamp(2.0rem, 4vw, 3.0rem);
        font-weight: 800;
        letter-spacing: 0;
        line-height: 1;
        margin: 0;
    }
    .brand-tagline {
        color: $muted;
        font-size: clamp(0.92rem, 1.4vw, 1.08rem);
        line-height: 1.45;
        margin-top: 0.45rem;
    }
    .brand-badge {
        background: $badge_bg;
        border: 1px solid $badge_border;
        border-radius: 999px;
        color: $badge_text;
        flex: 0 0 auto;
        font-size: 0.82rem;
        font-weight: 650;
        padding: 0.45rem 0.75rem;
        white-space: nowrap;
    }
    @media (max-width: 760px) {
        .brand-row {
            align-items: flex-start;
            flex-direction: column;
        }
        .brand-mark {
            height: 2.75rem;
            width: 2.75rem;
        }
    }
    .kpi-label {
        color: $text;
        font-size: 0.88rem;
        line-height: 1.2;
        margin-bottom: 0.45rem;
    }
    .kpi-value {
        color: $text;
        font-size: clamp(1.25rem, 2.2vw, 1.95rem);
        font-weight: 650;
        line-height: 1.15;
        white-space: normal;
        overflow-wrap: anywhere;
    }
    .kpi-delta {
        display: inline-block;
        color: $delta_text;
        background: $delta_bg;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        line-height: 1.2;
        margin-top: 0.6rem;
        padding: 0.22rem 0.48rem;
        white-space: normal;
        overflow-wrap: anywhere;
    }
    div[data-testid="stButtonGroup"] button,
    .stButton > button,
    .stDownloadButton > button,
    button[data-testid="baseButton-secondary"] {
        background: $control_bg;
        border: 1px solid $control_border;
        color: $text;
        box-shadow: none;
    }
    div[data-testid="stButtonGroup"] button:hover,
    .stButton > button:hover,
    .stDownloadButton > button:hover,
    button[data-testid="baseButton-secondary"]:hover {
        background: $control_hover;
        border-color: $accent;
        color: $text;
    }
    div[data-testid="stButtonGroup"] button p,
    .stButton > button p,
    .stDownloadButton > button p,
    button[data-testid="baseButton-secondary"] p {
        color: $text;
    }
    div[data-testid="stButtonGroup"] button[aria-pressed="true"] {
        background: $accent_soft;
        border-color: $accent;
        color: $text;
    }
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"],
    input,
    textarea {
        background: $control_bg !important;
        border-color: $control_border !important;
        color: $text !important;
    }
    [data-testid="stNumberInput"] div[data-baseweb="input"],
    [data-testid="stNumberInput"] div[data-baseweb="input"] > div,
    [data-testid="stNumberInput"] div[data-baseweb="base-input"],
    [data-testid="stNumberInput"] input {
        background: $control_bg !important;
        color: $text !important;
        -webkit-text-fill-color: $text !important;
        opacity: 1 !important;
    }
    [data-testid="stNumberInput"] button,
    [data-testid="stNumberInput"] button[kind],
    [data-testid="stNumberInput"] button[data-baseweb="button"] {
        background: $control_hover !important;
        border-left: 1px solid $control_border !important;
        color: $text !important;
    }
    [data-testid="stNumberInput"] button svg,
    [data-testid="stNumberInput"] button p,
    [data-testid="stNumberInput"] button span {
        color: $text !important;
        fill: $text !important;
    }
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] svg,
    input::placeholder,
    textarea::placeholder {
        color: $control_muted;
        fill: $control_muted;
    }
    div[data-baseweb="tag"] {
        background: $accent !important;
        border: 1px solid $accent !important;
        color: $chip_text !important;
    }
    div[data-baseweb="tag"] span,
    div[data-baseweb="tag"] p {
        color: $chip_text !important;
        -webkit-text-fill-color: $chip_text !important;
    }
    div[data-baseweb="tag"] svg,
    div[data-baseweb="tag"] button,
    div[data-baseweb="tag"] button svg {
        color: $chip_icon !important;
        fill: $chip_icon !important;
    }
    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        background: $card;
        border-color: $card_border;
    }
    [data-testid="stDataFrame"] div[role="columnheader"] {
        background: $table_header;
        color: $text;
    }
    </style>
    """
    ).substitute(theme_colors),
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="app-header">
        <div class="brand-row">
            <div class="brand-left">
                <div class="brand-mark">B</div>
                <div>
                    <div class="brand-name">BetaVest</div>
                    <div class="brand-tagline">
                        Systematic equity, crypto, and sentiment-aware fund evidence for young retail investors.
                    </div>
                </div>
            </div>
            <div class="brand-badge">Out-of-sample fund lab</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Controls")
    selected_horizon = st.pills(
        "Chart horizon",
        horizon_options,
        default=query_value("horizon", horizon_options, "Full sample"),
    )
    selected_horizon = selected_horizon or "Full sample"
    st.query_params["horizon"] = selected_horizon
    horizon_frame = filter_by_horizon(display_returns, selected_horizon)
    horizon_start = horizon_frame["date"].min().date()
    horizon_end = horizon_frame["date"].max().date()
    selected_date_range = st.slider(
        "Global date range",
        min_value=full_start_date,
        max_value=full_end_date,
        value=(horizon_start, horizon_end),
        format="YYYY-MM-DD",
        key=f"global_date_range_{selected_horizon}",
    )
    dark_app_theme = st.toggle(
        "Dark app theme",
        key="dark_app_theme",
    )
    st.query_params["theme"] = "dark" if dark_app_theme else "light"
    st.divider()
    st.caption("Data status")
    st.write(f"Fund data: {latest_fund_date}")
    st.write(f"Sentiment data: {latest_sentiment_date}")
    st.caption("Data source")
    st.write("Official FINS3645 project data bundle.")
    st.caption("50 US equities, 10 cryptocurrencies, and equity news headlines, 2020-2023.")
    st.caption("Dashboard values are loaded from precomputed Part B result files.")

global_start, global_end = pd.to_datetime(selected_date_range)
chart_returns = display_returns[display_returns["date"].between(global_start, global_end)].copy()
chart_sentiment = sector_sentiment[
    sector_sentiment["date"].between(global_start, global_end)
].copy()
px.defaults.template = "plotly_dark" if dark_app_theme else "plotly_white"

tab_overview, tab_compare, tab_fact_sheet, tab_allocation, tab_sentiment, tab_method = st.tabs(
    [
        ":material/home: Overview",
        ":material/compare_arrows: Compare",
        ":material/fact_check: Fact Sheet",
        ":material/pie_chart: Allocation",
        ":material/trending_up: Sentiment",
        ":material/functions: Method",
    ]
)

with tab_overview:
    st.subheader("Overview")
    equity_count = int(asset_metadata["asset_class"].str.lower().eq("equity").sum())
    crypto_count = int(asset_metadata["asset_class"].str.lower().eq("crypto").sum())
    sector_count = int(
        asset_metadata.loc[
            asset_metadata["asset_class"].str.lower().eq("equity"), "sector"
        ].nunique()
    )
    sample_start = display_returns["date"].min().date()
    sample_end = display_returns["date"].max().date()
    sample_years = (sample_end - sample_start).days / 365.25
    overview_best = display_metrics.sort_values("Sharpe", ascending=False).iloc[0]

    with st.container(border=True):
        st.markdown("**BetaVest objective**")
        st.write(
            "BetaVest is a fund-selection dashboard for young retail investors. "
            "It compares systematic equity, crypto, and mixed-asset funds using "
            "out-of-sample backtests, then adds news sentiment evidence to show "
            "whether market mood improves portfolio decisions. The dashboard helps "
            "investors compare funds, inspect risks and holdings, and build a "
            "simple allocation from the evidence."
        )

    with st.container(border=True):
        st.markdown("**Main findings**")
        finance_holdout = sentiment_holdout[
            sentiment_holdout["Sentiment model"].eq("Finance lexicon")
        ].iloc[0]
        st.markdown(
            "- Combined Risk Parity gives the best risk-adjusted result.\n"
            "- Crypto Min Variance has the highest return, but is speculative.\n"
            f"- The finance tilt improves 2023 holdout Sharpe by "
            f"{finance_holdout['Holdout Sharpe lift']:+.3f}."
        )

    st.markdown("#### Funds, backtests & sentiment")
    scale_cols = st.columns(4)
    metric_card(scale_cols[0], "Funds offered", len(available_funds), "Equity, crypto, combined")
    metric_card(scale_cols[1], "Assets covered", equity_count + crypto_count, f"{equity_count} equities, {crypto_count} crypto")
    metric_card(scale_cols[2], "Equity sectors", sector_count, "Sector sentiment index")
    metric_card(scale_cols[3], "Backtest window", f"{sample_years:.1f} years", f"{sample_start} to {sample_end}")

    feature_cols = st.columns([1, 1], gap="large")
    with feature_cols[0]:
        with st.container(border=True, height="stretch"):
            st.markdown("**Featured fund**")
            st.markdown(f"### {overview_best['Fund']}")
            st.write(
                f"Sharpe {overview_best['Sharpe']:.3f}, annual return "
                f"{pct(overview_best['Ann. return (%)'])}, max drawdown "
                f"{pct(overview_best['Max drawdown (%)'])}."
            )
            st.caption("See Fact Sheet tab -> select this fund for holdings and exposure detail.")
            st.divider()
            st.markdown("**Methodology trust signal**")
            st.caption(
                "All funds are backtested out-of-sample with no look-ahead bias. "
                "See the Method tab for the optimisation, sentiment tilt, and caveats."
            )
    with feature_cols[1]:
        with st.container(border=True, height="stretch"):
            st.markdown("**Sentiment analytics**")
            st.write(
                "Open the Sentiment tab to read the Fear-Greed Gauge, sector "
                "sentiment index, model comparison, sentiment tilt test, and regime analysis."
            )
            st.caption(
                "The gauge is kept with the detailed sentiment evidence so it is read as "
                "a mood check, not as a standalone trading rule."
            )

    st.markdown("#### Risk-tier guide")
    risk_cols = st.columns(4)
    risk_items = [
        ("Defensive", "Lower volatility and drawdown; useful as a stabiliser."),
        ("Core", "Balanced risk-adjusted exposure for the main portfolio sleeve."),
        ("Aggressive", "Higher return target with larger drawdown risk."),
        ("Speculative", "Crypto-heavy or very volatile; better as satellite exposure."),
    ]
    for column, (title, body) in zip(risk_cols, risk_items, strict=True):
        with column:
            with st.container(border=True, height="stretch"):
                st.markdown(f"**{title}**")
                st.caption(body)

    with st.container(border=True):
        st.markdown("**How to use**")
        how_cols = st.columns(5)
        how_items = [
            ("Compare", "Inspect fund performance."),
            ("Fact Sheet", "Review one fund in detail."),
            ("Allocation", "Build a custom portfolio."),
            ("Sentiment", "Understand sector mood."),
            ("Method", "Check assumptions."),
        ]
        for column, (title, body) in zip(how_cols, how_items, strict=True):
            with column:
                st.markdown(f"**{title}**")
                st.caption(body)

    st.caption(
        "Data source: Official FINS3645 project data bundle. "
        "50 US equities, 10 cryptocurrencies, and equity news headlines, 2020-2023."
    )

with tab_compare:
    st.subheader("Fund Comparison")
    st.caption("Compare funds by return, drawdown, Sharpe, and robustness across the selected date range.")
    takeaway_card("How to read this", compare_guidance())
    selected_funds = st.multiselect(
        "Funds to overlay",
        available_funds,
        default=default_selected_funds,
    )
    st.query_params["funds"] = "|".join(selected_funds)
    cols = st.columns(4)
    best_sharpe = display_metrics.sort_values("Sharpe", ascending=False).iloc[0]
    best_return = display_metrics.sort_values("Ann. return (%)", ascending=False).iloc[0]
    fusion_row = fusion[fusion["Fund"].eq("Equity Sentiment Tilt")].iloc[0]
    base_row = fusion[fusion["Fund"].eq("Equity Risk Parity")].iloc[0]
    metric_card(cols[0], "Best Sharpe fund", best_sharpe["Fund"], f"{best_sharpe['Sharpe']:.3f}")
    metric_card(cols[1], "Highest return fund", best_return["Fund"], pct(best_return["Ann. return (%)"]))
    metric_card(
        cols[2],
        "Fusion Sharpe lift",
        f"{fusion_row['Sharpe'] - base_row['Sharpe']:.3f}",
        "Sentiment Tilt vs Equity Risk Parity",
    )
    metric_card(cols[3], "Latest fund date", str(latest_fund_date), selected_horizon)

    with st.container(border=True):
        compare_view = st.radio(
            "Comparison view",
            ["Growth of $1", "Drawdown", "Rolling Sharpe"],
            horizontal=True,
        )
        st.caption(
            f"Showing {global_start.date()} to {global_end.date()}. "
            "Change the global date range in the sidebar."
        )
        compare_returns = chart_returns.copy()
        if selected_funds:
            comparison_download = comparison_download_frame(compare_returns, selected_funds, compare_view)
            plotly_chart(
                comparison_chart(comparison_download, selected_funds, compare_view, fund_color_map),
                width="stretch",
            )
            csv_download_button(
                "comparison chart data",
                comparison_download,
                "betavest_comparison_chart_data.csv",
            )
    selected_display_metrics = display_metrics[
        display_metrics["Fund"].isin(selected_funds)
    ].copy()
    if selected_display_metrics.empty:
        selected_display_metrics = display_metrics.copy()
    selected_metrics_table = selected_display_metrics[
        [
            "Fund",
            "Risk label",
            "Suggested use",
            "Ann. return (%)",
            "Ann. volatility (%)",
            "Sharpe",
            "Max drawdown (%)",
            "Total return (%)",
            "Avg daily turnover",
            "Total cost (%)",
        ]
    ].round(3)
    with st.container(border=True):
        st.dataframe(
            selected_metrics_table,
            width="stretch",
            hide_index=True,
            height=compact_table_height(len(selected_display_metrics)),
        )
        csv_download_button(
            "comparison table",
            selected_metrics_table,
            "betavest_comparison_table.csv",
        )
    st.subheader("Robustness Check")
    takeaway_card(
        "Why it matters",
        "A fund is more credible if it remains reasonable in the 2022 drawdown, "
        "not only in the full sample. Use this as a stability check before choosing a core fund.",
    )
    robustness_selected = selected_funds or default_funds
    robustness_table = robustness[robustness["Fund"].isin(robustness_selected)][
        [
            "Period",
            "Fund",
            "Ann. return (%)",
            "Sharpe",
            "Max drawdown (%)",
            "Total return (%)",
        ]
    ].round(3)
    with st.container(border=True):
        plotly_chart(robustness_chart(robustness, robustness_selected), width="stretch")
        csv_download_button(
            "robustness chart data",
            robustness_table,
            "betavest_robustness_chart_data.csv",
        )
    with st.container(border=True):
        st.dataframe(
            robustness_table,
            width="stretch",
            hide_index=True,
            height=360,
        )
        csv_download_button(
            "robustness table",
            robustness_table,
            "betavest_robustness_table.csv",
        )

with tab_fact_sheet:
    st.subheader("Fund Fact Sheet")
    st.caption(
        "Choose a fund from the dropdown to review its performance, risk profile, holdings, and current exposures."
    )
    fact_sheet_fund = st.selectbox(
        "Fact sheet fund",
        available_funds,
        index=available_funds.index(fact_sheet_default),
    )
    st.query_params["fact_sheet"] = fact_sheet_fund
    st.markdown(f"### {fact_sheet_fund}")
    if fact_sheet_fund == "Equity Sentiment Tilt":
        row = fusion[fusion["Fund"].eq(fact_sheet_fund)].iloc[0]
        returns_frame = sentiment_returns
        weights_frame = sentiment_weights
    else:
        row = metrics[metrics["Fund"].eq(fact_sheet_fund)].iloc[0]
        returns_frame = display_returns[display_returns["fund"].eq(fact_sheet_fund)]
        weights_frame = fund_weights[fund_weights["fund"].eq(fact_sheet_fund)]

    cols = st.columns(5)
    metric_card(cols[0], "Ann. return", pct(float(row["Ann. return (%)"])))
    metric_card(cols[1], "Ann. volatility", pct(float(row["Ann. volatility (%)"])))
    metric_card(cols[2], "Sharpe", f"{float(row['Sharpe']):.3f}")
    metric_card(cols[3], "Max drawdown", pct(float(row["Max drawdown (%)"])))
    metric_card(cols[4], "Total return", pct(float(row["Total return (%)"])))
    st.caption(
        f"{risk_label(row)} profile: {suggested_use(row)}. "
        f"Average daily turnover {float(row['Avg daily turnover']):.3f}; "
        f"total transaction cost {float(row['Total cost (%)']):.2f}%."
    )
    takeaway_card(
        "Key takeaway",
        f"{fact_sheet_fund} is best read as a {suggested_use(row).lower()} with "
        f"{risk_label(row).lower()} risk. Its main trade-off is return potential "
        "versus drawdown and implementation cost.",
    )

    profile = fund_profile(fact_sheet_fund, row)
    profile_cols = st.columns([2, 1, 1], vertical_alignment="top")
    for column, (label, value) in zip(profile_cols, profile.items()):
        with column:
            with st.container(border=True, height="stretch"):
                st.markdown(f"**{label}**")
                st.write(value)

    drawdown_info = drawdown_summary(returns_frame)
    benchmark_frame = benchmark_comparison(fact_sheet_fund, row, display_metrics)
    detail_cols = st.columns([1, 2], vertical_alignment="top")
    with detail_cols[0]:
        with st.container(border=True, height="stretch"):
            st.markdown("**Worst Drawdown Period**")
            st.metric("Worst drawdown", drawdown_info["Worst drawdown"])
            st.caption(f"Trough date: {drawdown_info['Trough date']}")
            st.caption(drawdown_info["Recovery status"])
    with detail_cols[1]:
        with st.container(border=True, height="stretch"):
            st.markdown(f"**Benchmark Comparison: {benchmark_for(fact_sheet_fund)}**")
            if benchmark_frame.empty:
                st.caption("No benchmark row is available for this fund.")
            else:
                st.dataframe(benchmark_frame, width="stretch", hide_index=True)

    left, right = st.columns([3, 1], vertical_alignment="top")
    with left:
        with st.container(border=True):
            if fact_sheet_fund == "Equity Sentiment Tilt":
                combined = sentiment_returns[
                    sentiment_returns["date"].between(global_start, global_end)
                ].copy()
                fig = px.line(
                    combined,
                    x="date",
                    y="growth_of_1",
                    labels={"date": "Date", "growth_of_1": "Growth of $1"},
                )
                fig.update_traces(line_color=fund_color_map.get(fact_sheet_fund, "#B0172E"))
                fig.update_layout(showlegend=False, hovermode="x unified")
                plotly_chart(fig, width="stretch")
                filtered_sentiment_weights = sentiment_weights[
                    sentiment_weights["date"].between(global_start, global_end)
                ].copy()
                plotly_chart(sector_weight_chart(filtered_sentiment_weights), width="stretch")
            else:
                plotly_chart(drawdown_chart(chart_returns, fact_sheet_fund), width="stretch")
            csv_download_button(
                "fact sheet chart data",
                returns_frame[returns_frame["date"].between(global_start, global_end)].copy(),
                f"betavest_{fact_sheet_fund.lower().replace(' ', '_')}_chart_data.csv",
            )
    with right:
        with st.container(border=True, height="stretch"):
            latest_date = weights_frame["date"].max()
            latest_weights_raw = (
                weights_frame[weights_frame["date"].eq(latest_date)]
                .sort_values("weight", ascending=False)
                .copy()
            )
            latest_enriched = enrich_weights(latest_weights_raw, asset_metadata)
            latest_weights = latest_enriched.head(12).copy()
            latest_weights["weight"] = latest_weights["weight"].map(lambda value: f"{value:.2%}")
            st.caption(f"Current holdings at {latest_date.date()}")
            st.dataframe(latest_weights[["ticker", "weight"]], width="stretch", hide_index=True)
            csv_download_button(
                "current holdings",
                latest_enriched,
                f"betavest_{fact_sheet_fund.lower().replace(' ', '_')}_current_holdings.csv",
            )

    exposure_cols = st.columns([1, 2], vertical_alignment="top")
    with exposure_cols[0]:
        with st.container(border=True):
            st.markdown("**Asset-Class Exposure**")
            st.dataframe(
                exposure_table(latest_enriched, "asset_class", "Asset class").round(2),
                width="stretch",
                hide_index=True,
            )
            csv_download_button(
                "asset-class exposure",
                exposure_table(latest_enriched, "asset_class", "Asset class").round(2),
                f"betavest_{fact_sheet_fund.lower().replace(' ', '_')}_asset_class_exposure.csv",
            )
        with st.container(border=True):
            st.markdown("**Holding Concentration**")
            concentration = pd.DataFrame(
                [
                    {"Measure": "Number of holdings", "Value": f"{latest_enriched['ticker'].nunique()}"},
                    {"Measure": "Top 5 holdings", "Value": pct(latest_enriched.head(5)["weight"].sum() * 100)},
                    {"Measure": "Top 10 holdings", "Value": pct(latest_enriched.head(10)["weight"].sum() * 100)},
                ]
            )
            st.dataframe(concentration, width="stretch", hide_index=True)
            csv_download_button(
                "holding concentration",
                concentration,
                f"betavest_{fact_sheet_fund.lower().replace(' ', '_')}_holding_concentration.csv",
            )
    with exposure_cols[1]:
        with st.container(border=True, height="stretch"):
            st.markdown("**Top Sector Exposure**")
            sector_exposure = exposure_table(latest_enriched, "sector", "Sector").head(8).round(2)
            st.dataframe(sector_exposure, width="stretch", hide_index=True)
            csv_download_button(
                "sector exposure",
                sector_exposure,
                f"betavest_{fact_sheet_fund.lower().replace(' ', '_')}_sector_exposure.csv",
            )

with tab_allocation:
    st.subheader("Allocation Builder")
    st.caption("Adjust weights with sliders or type exact percentages.")
    allocation_funds = st.multiselect(
        "Allocation funds",
        available_funds,
        default=["Equity Equal Weight", "Combined Max Sharpe", "Equity Sentiment Tilt"],
    )
    if allocation_funds:
        initialise_allocation_state(allocation_funds)
        raw_weights = {}
        with st.container(border=True):
            st.caption("Target allocation inputs")
            for fund in allocation_funds:
                slider_key = allocation_key(fund, "slider")
                input_key = allocation_key(fund, "input")

                label_col, slider_col, input_col = st.columns(
                    [1.4, 3, 1],
                    vertical_alignment="center",
                )
                label_col.write(fund)
                slider_col.slider(
                    f"{fund} slider",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    key=slider_key,
                    label_visibility="collapsed",
                    on_change=rebalance_allocation,
                    args=(fund, allocation_funds, slider_key),
                )
                input_col.number_input(
                    f"{fund} allocation",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    format="%.2f",
                    key=input_key,
                    label_visibility="collapsed",
                    on_change=rebalance_allocation,
                    args=(fund, allocation_funds, input_key),
                )
                raw_weights[fund] = float(st.session_state[input_key])
            target_total = sum(raw_weights.values())
            st.caption(f"Total allocation: {target_total:.2f}%.")
    else:
        raw_weights = {}

    total = sum(raw_weights.values())
    if total > 0:
        normalised = raw_weights
        allocation_rows = []
        for fund, weight in normalised.items():
            source = fusion if fund == "Equity Sentiment Tilt" else display_metrics
            row = source[source["Fund"].eq(fund)].iloc[0]
            allocation_rows.append(
                {
                    "Fund": fund,
                    "Allocation (%)": weight,
                    "Ann. return contribution (%)": weight / 100 * row["Ann. return (%)"],
                    "Volatility contribution proxy (%)": weight / 100 * row["Ann. volatility (%)"],
                }
            )
        allocation_frame = pd.DataFrame(allocation_rows)
        warning_title, warning_body = allocation_risk_message(normalised, display_metrics)
        takeaway_card(warning_title, warning_body)
        annual_fee = st.number_input(
            "Annual management fee (%)",
            min_value=0.0,
            max_value=3.0,
            value=0.75,
            step=0.05,
            format="%.2f",
        )
        st.caption("Annual management fee is the yearly cost charged to manage the selected allocation.")
        allocation_growth = allocation_growth_path(
            chart_returns,
            normalised,
            annual_fee,
        )
        if not allocation_growth.empty:
            gross_end = float(allocation_growth["Gross"].iloc[-1])
            net_end = float(allocation_growth["Net of fee"].iloc[-1])
            fee_drag = gross_end - net_end
            growth_cols = st.columns(3)
            metric_card(growth_cols[0], "Gross ending value", f"${gross_end:.3f}")
            metric_card(growth_cols[1], "Net ending value", f"${net_end:.3f}")
            metric_card(growth_cols[2], "Fee drag per $1", f"${fee_drag:.3f}", f"{annual_fee:.2f}% p.a.")
            with st.container(border=True):
                st.markdown("**Gross and net allocation growth**")
                plotly_chart(allocation_growth_chart(allocation_growth), width="stretch")
                st.caption(
                    "The management fee is deducted daily from the selected historical allocation. "
                    "Values start at $1 over the global date range."
                )
                csv_download_button(
                    "allocation growth data",
                    allocation_growth.round({"Gross": 6, "Net of fee": 6}),
                    "betavest_allocation_growth_data.csv",
                )
        with st.container(border=True):
            plotly_chart(allocation_chart(normalised, fund_color_map), width="stretch")
            csv_download_button(
                "allocation chart data",
                allocation_download_frame(allocation_frame),
                "betavest_allocation_chart_data.csv",
            )
        with st.container(border=True):
            allocation_table = allocation_frame.round(2)
            st.dataframe(allocation_table, width="stretch", hide_index=True)
            csv_download_button(
                "selected allocation table",
                allocation_download_frame(allocation_frame),
                "betavest_selected_allocation.csv",
            )

with tab_sentiment:
    st.subheader("Sector Sentiment")
    st.caption("Track sector news sentiment and inspect where the signal is strongest or weakest.")
    selected_sectors = st.multiselect(
        "Sentiment sectors",
        sector_options,
        default=default_selected_sectors,
    )
    st.query_params["sectors"] = "|".join(selected_sectors)
    selected_sentiment_summary = sentiment_summary[
        sentiment_summary["Sector"].isin(selected_sectors)
    ].copy()
    if selected_sentiment_summary.empty:
        selected_sentiment_summary = sentiment_summary.copy()
    sentiment_pulse = (
        sector_sentiment.groupby("date", as_index=False)["sentiment_score"]
        .mean()
        .sort_values("date")
    )
    sentiment_pulse["21-day average"] = sentiment_pulse["sentiment_score"].rolling(
        21, min_periods=5
    ).mean()
    pulse_history = sentiment_pulse.dropna(subset=["21-day average"]).copy()
    latest_pulse = pulse_history.iloc[-1]
    fear_greed_score = (
        pulse_history["21-day average"].rank(pct=True).iloc[-1] * 100
        if not pulse_history.empty
        else 50.0
    )
    fear_greed_status = fear_greed_label(float(fear_greed_score))
    latest = sector_sentiment[sector_sentiment["date"].eq(sector_sentiment["date"].max())]
    strongest = selected_sentiment_summary.iloc[0]
    weakest = selected_sentiment_summary.iloc[-1]
    gauge_cols = st.columns([2, 3], gap="large", vertical_alignment="top")
    with gauge_cols[0]:
        with st.container(border=True, height="stretch"):
            st.markdown("**Fear-Greed Gauge**")
            st.caption(
                f"{fear_greed_status} reading from the latest 21-day sector sentiment average "
                f"at {latest_sentiment_date}."
            )
            plotly_chart(
                fear_greed_gauge(float(fear_greed_score), fear_greed_status),
                width="stretch",
            )
            csv_download_button(
                "fear-greed pulse data",
                pulse_history,
                "betavest_fear_greed_pulse_data.csv",
            )
            st.caption(
                f"Raw sentiment pulse: {latest_pulse['21-day average']:.3f}. "
                "Score is a percentile against BetaVest history."
            )
    with gauge_cols[1]:
        with st.container(border=True, height="stretch"):
            st.markdown("**Market Sentiment Pulse**")
            st.caption(
                "Shows the latest 90-day path of the 21-day average sector sentiment "
                "used to form the fear-greed reading."
            )
            pulse_fig = px.line(
                pulse_history.tail(90),
                x="date",
                y="21-day average",
                labels={"date": "Date", "21-day average": "Sentiment"},
            )
            pulse_fig.add_hline(y=0, line_width=1, line_color="black", opacity=0.35)
            pulse_fig.update_traces(line_color="#B0172E", line_width=2)
            pulse_fig.update_layout(
                height=230,
                margin=dict(l=8, r=8, t=8, b=8),
                hovermode="x unified",
                showlegend=False,
            )
            plotly_chart(pulse_fig, width="stretch")
    cols = st.columns(4)
    metric_card(cols[0], "Highest average sentiment", strongest["Sector"], f"{strongest['Average sentiment']:.3f}")
    metric_card(cols[1], "Lowest average sentiment", weakest["Sector"], f"{weakest['Average sentiment']:.3f}")
    metric_card(cols[2], "Latest sentiment date", str(latest_sentiment_date), selected_horizon)
    metric_card(cols[3], "Selected sectors", f"{len(selected_sentiment_summary)}")
    left, right = st.columns([3, 2], vertical_alignment="top")
    with left:
        with st.container(border=True):
            if selected_sectors:
                sentiment_chart_data = chart_sentiment[
                    chart_sentiment["sector"].isin(selected_sectors)
                ].copy()
                plotly_chart(sentiment_chart(sentiment_chart_data, selected_sectors), width="stretch")
                csv_download_button(
                    "sector sentiment chart data",
                    sentiment_chart_data,
                    "betavest_sector_sentiment_chart_data.csv",
                )
    with right:
        with st.container(border=True, height="stretch"):
            selected_sentiment_table = selected_sentiment_summary.round(3)
            st.dataframe(selected_sentiment_table, width="stretch", hide_index=True)
            csv_download_button(
                "sector sentiment table",
                selected_sentiment_table,
                "betavest_sector_sentiment_table.csv",
            )
    st.subheader("Sentiment Model Check")
    st.caption(
        "Compare the finance lexicon with standard VADER before using either signal in a fund."
    )
    with st.container(border=True):
        sentiment_model_table = sentiment_model_comparison.round(3)
        st.dataframe(
            sentiment_model_table,
            width="stretch",
            hide_index=True,
            height=compact_table_height(len(sentiment_model_comparison)),
        )
        csv_download_button(
            "sentiment model comparison",
            sentiment_model_table,
            "betavest_sentiment_model_comparison.csv",
        )
    with st.expander("Review the largest model disagreements"):
        st.caption(
            "These ticker-days are selected for review because the two models disagree most. "
            "They are not manually labelled accuracy scores."
        )
        audit_table = sentiment_audit[
            [
                "date",
                "ticker",
                "sector",
                "Headline bundle",
                "Finance score",
                "VADER score",
                "Absolute difference",
            ]
        ].head(10)
        st.dataframe(
            audit_table,
            width="stretch",
            hide_index=True,
            height=420,
        )
        csv_download_button(
            "sentiment disagreement audit",
            audit_table,
            "betavest_sentiment_disagreement_audit.csv",
        )
    st.subheader("Sentiment Tilt Sensitivity")
    best_tilt = tilt_grid.sort_values("Sharpe", ascending=False).iloc[0]
    st.caption(
        "The 2021-2022 discovery period selects the tilt strength before the 2023 holdout is tested. "
        f"The selected finance-lexicon tilt is {best_tilt['Tilt strength']:.2f}, with discovery "
        f"Sharpe {best_tilt['Sharpe']:.3f}."
    )
    with st.container(border=True):
        tilt_grid_table = tilt_grid.round(3)
        st.dataframe(tilt_grid_table, width="stretch", hide_index=True)
        csv_download_button(
            "sentiment tilt sensitivity",
            tilt_grid_table,
            "betavest_sentiment_tilt_sensitivity.csv",
        )
    st.subheader("Out-of-Sample Sentiment Holdout")
    finance_holdout = sentiment_holdout[
        sentiment_holdout["Sentiment model"].eq("Finance lexicon")
    ].iloc[0]
    takeaway_card(
        "2023 holdout result",
        f"The finance tilt selected on 2021-2022 raises 2023 Sharpe from "
        f"{finance_holdout['Holdout base Sharpe']:.3f} to "
        f"{finance_holdout['Holdout tilt Sharpe']:.3f}. The lift is "
        f"{finance_holdout['Holdout Sharpe lift']:+.3f} after transaction costs.",
    )
    with st.container(border=True):
        holdout_table = sentiment_holdout[
            [
                "Sentiment model",
                "Selected tilt",
                "Discovery Sharpe lift",
                "Holdout base return (%)",
                "Holdout tilt return (%)",
                "Holdout base Sharpe",
                "Holdout tilt Sharpe",
                "Holdout Sharpe lift",
                "Holdout tilt drawdown (%)",
                "Holdout tilt cost (%)",
            ]
        ].round(3)
        st.dataframe(
            holdout_table,
            width="stretch",
            hide_index=True,
            height=compact_table_height(len(sentiment_holdout)),
        )
        csv_download_button(
            "sentiment holdout validation",
            holdout_table,
            "betavest_sentiment_holdout_validation.csv",
        )
    st.subheader("Sentiment Regime Analysis")
    takeaway_card(
        "How to read this",
        "Regimes are based on terciles of one-day-lagged sector sentiment. "
        "The test checks whether sentiment adds information, without assuming positive news always means higher returns.",
    )
    regime_funds = [
        fund
        for fund in ["Equity Risk Parity", "Equity Sentiment Tilt", "Combined Risk Parity"]
        if fund in sentiment_regimes["Fund"].unique()
    ]
    with st.container(border=True):
        plotly_chart(
            sentiment_regime_chart(sentiment_regimes, regime_funds, fund_color_map),
            width="stretch",
        )
        regime_table = sentiment_regimes[sentiment_regimes["Fund"].isin(regime_funds)][
            [
                "Regime",
                "Fund",
                "Observations",
                "Average lagged sentiment",
                "Average daily return (%)",
                "Positive return days (%)",
                "Sharpe",
                "Max drawdown (%)",
            ]
        ].round(3)
        csv_download_button(
            "sentiment regime chart data",
            regime_table,
            "betavest_sentiment_regime_chart_data.csv",
        )
    with st.container(border=True):
        st.dataframe(
            regime_table,
            width="stretch",
            hide_index=True,
            height=360,
        )
        csv_download_button(
            "sentiment regime table",
            regime_table,
            "betavest_sentiment_regime_table.csv",
        )

with tab_method:
    st.subheader("Method and Caveats")
    st.caption("Check the backtest rules, optimisation formulas, sentiment tilt, and key limitations.")
    takeaway_card(
        "Key takeaway",
        "The app separates build-time analysis from app-time display: funds, sentiment, "
        "and fusion are precomputed, while the dashboard lets users inspect the results "
        "without recomputing the models.",
    )
    method_cols = st.columns(2, vertical_alignment="top")
    with method_cols[0]:
        with st.container(border=True, height="stretch"):
            st.markdown("**Backtest and Sharpe Ratio**")
            st.write(
                "Weights are estimated from the previous 252 trading days and rebalanced at month end. "
                "Reported returns are net of 10 bps transaction costs on turnover."
            )
            st.latex(r"Sharpe = \frac{R_{ann} - R_f}{\sigma_{ann}}")
            st.caption("The app uses a zero risk-free rate for comparison.")
            csv_download_button(
                "fund returns",
                fund_returns,
                "betavest_fund_returns.csv",
            )
        with st.container(border=True, height="stretch"):
            st.markdown("**Risk Parity Objective**")
            st.write(
                "Risk Parity is a long-only optimiser. It chooses weights so each asset contributes "
                "approximately the same share of portfolio volatility."
            )
            st.latex(
                r"\min_w \sum_i \left(\frac{RC_i(w)}{\sum_j RC_j(w)} - \frac{1}{N}\right)^2"
            )
            st.latex(r"\text{s.t. } \sum_i w_i = 1,\quad w_i \ge 0")
            csv_download_button(
                "fund weights",
                fund_weights,
                "betavest_fund_weights.csv",
            )
    with method_cols[1]:
        with st.container(border=True, height="stretch"):
            st.markdown("**Sentiment Tilt**")
            st.write(
                "The sentiment signal is lagged by one trading day, converted into sector multipliers, "
                "and applied to optimiser weights at rebalance dates."
            )
            st.latex(r"\tilde{w}_{i,t} = \frac{w_{i,t}\,m_{s(i),t-1}}{\sum_j w_{j,t}\,m_{s(j),t-1}}")
            st.caption("Sector multipliers are capped between 0.70 and 1.30.")
        with st.container(border=True, height="stretch"):
            st.markdown("**Main Caveats**")
            st.write(
                "Backtests are historical simulations, not forecasts. Maximum Sharpe weights can be "
                "sensitive to noisy return estimates, crypto-only funds have severe drawdowns, and the "
                "sentiment model is a transparent finance-lexicon baseline rather than a production NLP model."
            )
            st.caption(
                "Tilt strength is selected on 2021-2022 and evaluated on an untouched 2023 holdout."
            )
