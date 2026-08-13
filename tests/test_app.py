"""Smoke test for the BetaVest Streamlit app."""
import pathlib

from streamlit.testing.v1 import AppTest


def _sentiment_summary_table(app: AppTest):
    for dataframe in app.dataframe:
        value = getattr(dataframe, "value", None)
        if value is not None and {"Sector", "Average sentiment"}.issubset(value.columns):
            return value
    raise AssertionError("sentiment summary table was not rendered")


def _fund_metrics_table(app: AppTest):
    for dataframe in app.dataframe:
        value = getattr(dataframe, "value", None)
        if value is not None and {"Fund", "Risk label", "Suggested use"}.issubset(value.columns):
            return value
    raise AssertionError("fund metrics table was not rendered")


def test_streamlit_app_loads_without_exceptions():
    app_path = pathlib.Path(__file__).resolve().parent.parent / "streamlit_app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=20)
    assert not app.exception
    assert any("BetaVest" in markdown.value for markdown in app.markdown)
    assert [tab.label for tab in app.tabs] == [
        ":material/home: Overview",
        ":material/compare_arrows: Compare",
        ":material/fact_check: Fact Sheet",
        ":material/pie_chart: Allocation",
        ":material/trending_up: Sentiment",
        ":material/functions: Method",
    ]
    assert app.radio[0].label == "Comparison view"
    assert app.radio[0].options == ["Growth of $1", "Drawdown", "Rolling Sharpe"]
    assert any(slider.label == "Global date range" for slider in app.slider)
    markdown_text = "\n".join(markdown.value for markdown in app.markdown)
    assert "Why it matters" in markdown_text
    assert "Regimes are based on terciles" in markdown_text
    fund_table = _fund_metrics_table(app)
    assert set(fund_table["Fund"]) == {
        "Equity Equal Weight",
        "Combined Risk Parity",
        "Equity Sentiment Tilt",
    }
    app.multiselect[0].set_value(["Combined Max Sharpe", "Equity Max Sharpe"]).run(timeout=20)
    fund_table = _fund_metrics_table(app)
    assert set(fund_table["Fund"]) == {"Combined Max Sharpe", "Equity Max Sharpe"}
    allocation_inputs = [
        number_input
        for number_input in app.number_input
        if number_input.label.endswith(" allocation")
    ]
    allocation_inputs[0].set_value(60.0).run(timeout=20)
    allocation_inputs = [
        number_input
        for number_input in app.number_input
        if number_input.label.endswith(" allocation")
    ]
    allocation_values = [number_input.value for number_input in allocation_inputs]
    assert round(sum(allocation_values), 2) == 100.0
    assert allocation_values[:3] == [60.0, 20.0, 20.0]
    assert any(
        number_input.label == "Annual management fee (%)"
        for number_input in app.number_input
    )
    markdown_text = "\n".join(markdown.value for markdown in app.markdown)
    assert "Gross and net allocation growth" in markdown_text
    assert any(
        subheader.value == "Out-of-Sample Sentiment Holdout"
        for subheader in app.subheader
    )
    sentiment_table = _sentiment_summary_table(app)
    assert sentiment_table["Sector"].tolist() == ["Consumer", "Tech", "Healthcare", "Energy"]
    app.multiselect[2].set_value(["Consumer", "Tech", "Healthcare"]).run(timeout=20)
    sentiment_table = _sentiment_summary_table(app)
    assert sentiment_table["Sector"].tolist() == ["Consumer", "Tech", "Healthcare"]
