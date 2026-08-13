# BetaVest: Part B Funds, Sentiment and App

FINS3645 Project B. Data Factory Floor Stations 3-4  
Name: Aiman Haikal Bin Ahmad Norzi  
zID: z5532834

## Introduction

BetaVest now moves from a verified data foundation to an investable product test. Part A built the back end for an experimental systematic investment platform for young retail investors: 50 US equities, 10 cryptocurrencies, and 146,836 deduplicated equity-news headlines over 2020-2023. Part B uses those inputs to build out-of-sample funds, score financial news sentiment, test whether sentiment improves an equity portfolio, and present the results through a Streamlit app.

The Part A evidence sets a clear design problem for Part B. Equity returns averaged 0.06% per day, or 14.97% annualised, with annualised volatility of 36.58%. Crypto returns averaged 0.23% per day, or 84.86% annualised, but annualised volatility reached 107.45%. The return panel also contains fat tails: the outlier screen flagged 21 observations, including OXY at -52.01% on 2020-03-09 and XLM at +74.92% on 2021-01-06. These numbers mean that BetaVest cannot sell performance by showing return lines alone. The Part B product must compare funds on risk-adjusted returns, drawdowns, and holdings.

The main contribution of Part B is therefore a transparent fund comparison workflow. The report asks three questions. First, which systematic fund construction rule gives the strongest out-of-sample trade-off between return and risk? Second, does a lagged sector sentiment signal add value to the base equity fund after avoiding look-ahead bias? Third, does the app give a young retail investor enough evidence to choose an allocation without relying on unsupported single-ticker views?

## 1. Funds and Backtest Design

BetaVest tests twelve funds across three groups of permitted assets: equity-only, crypto-only, and combined equity-plus-crypto. Each group is tested with equal weight, minimum variance, maximum Sharpe, and risk parity methods. The required combined funds are therefore covered by Combined Equal Weight, Combined Minimum Variance, Combined Maximum Sharpe, and Combined Risk Parity. I also include the same methods for the equity-only and crypto-only sleeves because Part A showed that equities and crypto form different risk blocks rather than one homogeneous asset class.

The assets each fund is allowed to hold follow the Part A cleaning rules. Equity returns are simple adjusted-close returns on the US equity trading calendar. Crypto returns are first calculated on their native daily calendar and then aligned to the equity trading calendar, so weekend crypto prices do not create artificial weekday returns. This choice is important for a combined fund because the equity leg cannot trade on weekends. It also keeps the backtest aligned with the user journey in the app, where fund returns are displayed on common decision dates.

The backtest is walk-forward and out of sample. We estimate weights using a 252-trading-day rolling window and rebalance at month end. The first live backtest date is 2021-01-04 for the equity and combined funds and 2020-12-31 for the crypto funds. At each rebalance, the optimiser can use only returns observed before the rebalance date. The realised fund return is then measured after the weights are formed. This timing rule is the central guard against look-ahead bias.

The base methods provide different economic views of the same data. The maximum Sharpe fund uses expected returns and covariances to target a high risk-adjusted return, so it can be sensitive to noisy mean estimates. The minimum-variance fund focuses more directly on realised risk, so it should be more stable when crypto volatility is high. The equal-weight benchmark gives a simple reference point that does not rely on estimated means or covariances. Risk parity adds a more stable extra method by solving a long-only optimisation problem that equalises each asset's contribution to portfolio risk while keeping weights non-negative and summing to 1. Comparing these methods matters because Part A showed both high crypto returns and high crypto volatility; a method that looks attractive in average return may still be unsuitable for BetaVest users if drawdowns are severe.

The risk-parity objective minimises the squared distance between each asset's percentage risk contribution and the equal-risk target of 1/N. The optimiser uses `scipy.optimize.minimize` with long-only bounds and a full-investment constraint. This makes the risk-parity fund a genuine equal-risk-contribution portfolio rather than a simple inverse-volatility approximation.

I assume a zero risk-free rate when calculating Sharpe ratios and include transaction costs of 10 basis points on daily turnover. Turnover is measured as the absolute change in portfolio weights, so a strategy that changes positions frequently pays a larger implementation penalty. This makes the fund comparison more realistic than a purely gross-return backtest.

**Table 1. Performance metrics across BetaVest funds, 2021-2023 live backtest.** Annualised return, annualised volatility, Sharpe ratio, maximum drawdown, total return, average daily turnover, and total transaction cost are calculated from walk-forward daily fund returns. Source: `results/tables/performance_metrics_report.csv`.

## 2. Out-of-Sample Results and Fund Fact Sheets

The out-of-sample results now favour Combined Risk Parity after transaction costs. Table 1 shows that Combined Risk Parity has the strongest risk-adjusted performance, with an annualised return of 13.65%, annualised volatility of 16.04%, a Sharpe ratio of 0.851, and a maximum drawdown of -19.79%. This is useful for BetaVest because the best fund is not the most aggressive crypto strategy; it is a balanced method that uses crypto exposure cautiously while keeping volatility close to the equity benchmark.

The combined funds increase return, but only some improve the investor trade-off. Combined Maximum Sharpe has the highest annualised return at 16.18% and the highest total live-period return at 56.52%. However, that return comes with annualised volatility of 22.39%, a Sharpe ratio of 0.722, a maximum drawdown of -26.01%, and total transaction costs of 1.80%. Combined Equal Weight also performs well, with a 14.94% annualised return and a 0.703 Sharpe ratio, but its maximum drawdown is deeper at -28.75%. These results mean combined funds should be presented as growth choices, with Combined Risk Parity as the stronger core candidate and Combined Maximum Sharpe as the more aggressive option.

The minimum-variance funds do reduce risk, but their lower return weakens the case for using them as the main BetaVest offer. Equity Minimum Variance has annualised volatility of 12.77% and a maximum drawdown of -15.55%, both better than Equity Equal Weight. The cost is return: its annualised return is only 4.25%, and its Sharpe ratio is 0.333. Combined Minimum Variance gives a similar pattern, with 12.80% annualised volatility, a -15.83% maximum drawdown, and a 0.338 Sharpe ratio. For a cautious user, these funds may still be useful, but they look more like defensive stabilisers than growth funds.

The crypto-only funds are not suitable as core BetaVest funds in this first test. Crypto Minimum Variance has the highest annualised return of the crypto sleeve at 22.61%, but its annualised volatility is 64.95% and its maximum drawdown is -75.13%. Crypto Equal Weight has a weak Sharpe ratio of 0.040 and a maximum drawdown of -84.85%. Crypto Maximum Sharpe performs worst, losing 49.53% over the live period and producing a Sharpe ratio of -0.290. The crypto results support keeping crypto as a satellite allocation or a controlled combined-fund component, not as the default product for young retail investors.

Figure 1 compares growth of $1 across the fund methods. The figure should be read beside Table 1 because a higher ending value does not necessarily mean a better fund. Combined Maximum Sharpe finishes with the highest cumulative return, but Combined Risk Parity has the stronger Sharpe ratio and a smaller drawdown. Figure 2 shows the drawdown path for Combined Risk Parity, where the worst loss from a prior peak is -19.79%. Figure 3 reports sector weights for the Equity Sentiment Tilt fund. This figure is useful because it shows how the lagged sentiment signal changes sector exposure through time while keeping the portfolio fully invested.

The fund fact sheets should therefore lead with Combined Risk Parity as the best risk-adjusted core candidate, Equity Equal Weight as the transparent equity benchmark, Combined Maximum Sharpe as the higher-return aggressive option, and Equity Minimum Variance as the lower-risk defensive option. This framing matches the target user better than ranking funds by return alone. A young retail investor can see that more crypto exposure may raise upside, but only risk-controlled crypto exposure improved the risk-adjusted result. For BetaVest, the main fund result is that a stable combined method beats both pure equity simplicity and crypto-only speculation on net Sharpe ratio.

**Figure 1. Growth of $1 across BetaVest funds, 2021-2023 live backtest.** Values are cumulative returns from the walk-forward fund returns in `results/data/fund_returns.csv`.

**Figure 2. Drawdown for the best-Sharpe BetaVest fund, 2021-2023 live backtest.** Drawdown is measured as the percentage fall from the previous cumulative-return peak.

**Figure 3. Sector weights over time for the Equity Sentiment Tilt fund, 2021-2023 live backtest.** Weights are daily equity-sector weights after applying the one-day-lagged sentiment multiplier and renormalising the portfolio to 100%.

**Figure 4. Sharpe ratio comparison across BetaVest funds, 2021-2023 live backtest.** Sharpe ratios assume a zero risk-free rate.

## 3. Sentiment Index

The sentiment model converts the Part A headline panel into an equity-sector news index. Part A deliberately stopped before scoring text, but it preserved headline wording, sector labels, and trading-day alignment. That design now matters because Part B needs a signal that uses only information available before a portfolio decision. The sentiment index is therefore built from ticker-day headline bundles that are aligned to the same or next equity trading day.

The Part B model uses a finance-lexicon baseline. Positive terms include words such as beat, buy, growth, upgrade, gain, strong, profit, outperform, rally, and record. Negative terms include miss, sell, downgrade, risk, loss, weak, decline, lawsuit, cut, warning, debt, and probe. For each ticker-day, the score is calculated as positive word counts minus negative word counts, scaled by the total number of sentiment-bearing terms. This transparent signal is compared with standard VADER before it is used in the holdout test.

Scores are aggregated in two steps. First, each ticker-day receives one sentiment score from its combined headlines. Second, sector sentiment is calculated as an equal-weight average across the five tickers in each sector. Ticker-days with no headlines are treated as neutral with a score of zero. This choice avoids overstating a sector's sentiment when only one or two firms receive news. The signal is then lagged by one trading day, so a score observed on day t can first be used for a day t+1 portfolio decision.

Figure 5 shows the sector sentiment index from 2020-01-02 to 2023-12-29. Consumer has the highest average sentiment score at 0.521, followed by Technology at 0.485 and Healthcare at 0.396. Materials has the lowest average score at 0.164. The sector ranking is partly driven by headline language and partly by coverage: Technology has 26,632 headlines, Consumer has 25,877, and Materials has only 5,393. The index should therefore be interpreted as a news-tone measure, not a direct return forecast.

The figure also shows that sentiment is time-varying rather than a fixed sector label. Technology records the strongest smoothed positive period, with its 21-day average sentiment reaching about 0.786 around 2022-02-09. Energy records the weakest smoothed period, with its 21-day average sentiment falling to about -0.310 around 2020-04-15. This timing matters for investment use because the signal is more useful as a changing allocation input than as a statement that one sector is always good or bad.

For investing, the useful version of sentiment is the lagged sector signal, not the same-day score. A same-day score would risk using information that was not available when the trade was made. The lagged index can be used in three practical ways. First, it can act as a portfolio tilt: increase the equity sleeve's exposure to sectors with stronger lagged sentiment and reduce exposure to weaker sectors. Second, it can act as a risk warning: if a sector's sentiment turns sharply negative, the app can flag that the sector has weaker news tone even if recent returns still look strong. Third, it can improve the investor journey by explaining why the app may prefer one sector exposure over another.

The vocabulary evidence from Part A motivates this model but does not replace it. The most frequent terms included "buy" with 15,806 counts, "earnings" with 11,870, and "market" with 6,879. These words suggest finance-relevant information flow, but counts alone do not classify a headline as positive or negative. The Part B sentiment index adds direction, while the lag rule makes the signal usable in a backtest without peeking into the same-day outcome. The main limitation is that a small lexicon can miss context, sarcasm, negation, and finance-specific meanings. The index is therefore suitable as a transparent baseline for the fusion test, not as a final production sentiment model.

**Table 2. Sector sentiment summary, 2020-2023.** Average sentiment is the equal-weight sector average of ticker-day finance-lexicon scores; total headlines reports the number of aligned headlines used in each sector. Source: `results/tables/sector_sentiment_summary.csv`.

**Figure 5. Sector sentiment index time series for equity sectors, 2020-2023.** The figure plots the 21-day moving average of the daily sector finance-lexicon sentiment score. Source: `results/data/sector_sentiment_index.csv` and `results/figures/sector_sentiment_index.png`.

## 4. Fusion Extension

The fusion extension tests whether sentiment improves the base equity optimiser. I apply a sector sentiment tilt to the Equity Risk Parity portfolio at each rebalance date. The optimiser first estimates long-only risk-parity weights from the previous 252 trading days. Each ticker then inherits its sector's lagged sentiment multiplier on the rebalance date. Sectors with stronger lagged sentiment receive higher weights, and sectors with weaker lagged sentiment receive lower weights. The multiplier is capped between 0.70 and 1.30, and weights are renormalised to sum to 100%. The tilted weights are then held until the next rebalance. This keeps the strategy long-only, avoids same-day look-ahead, and avoids the excessive turnover that came from tilting weights every day.

The full-sample comparison shows a modest improvement after transaction costs. Table 3 reports annualised return of 10.08% for Equity Sentiment Tilt, compared with 9.80% for Equity Risk Parity. Sharpe rises from 0.672 to 0.690, maximum drawdown improves from -18.68% to -18.27%, and total transaction cost rises from 0.23% to 0.46%.

Figure 6 compares growth of $1 for Equity Risk Parity and the sentiment-tilted version. The two lines are close for much of the sample, which means sentiment is not a replacement for diversification or risk control. The value of the signal is incremental: it improves the optimiser's sector exposure at rebalance dates while leaving the risk-parity framework in control of the base portfolio.

Table 4 uses 2021-2022 as a discovery period for tilt strengths from 0.05 to 0.30. A tilt of 0.15 is selected and then frozen before 2023 is examined. Table 7 shows that the finance tilt raises 2023 Sharpe from 0.944 to 1.003, a holdout lift of 0.059 after costs. VADER also improves holdout Sharpe, but by a smaller 0.037. This design is more credible than selecting and reporting the best setting on the same dates.

I add two innovation checks to test whether these results survive more than the headline metric. Table 5 reports a robustness test across the full sample, the 2021 recovery, the 2022 drawdown, and the 2023 recovery. Combined Risk Parity remains the strongest core candidate because it performs well in 2021 and 2023 while limiting the 2022 loss better than the higher-risk alternatives. Its Sharpe ratio is 2.501 in 2021, -0.354 in 2022, and 1.224 in 2023. Crypto Minimum Variance has much stronger upside in 2021 and 2023, but the 2022 return of -57.58% and maximum drawdown of -62.91% confirm that crypto-only funds should be treated as satellite exposure rather than a default allocation.

Table 6 reports the sentiment regime analysis. Regimes are terciles of the equal-weight average one-day-lagged sector sentiment, so the test uses information that would have been available before trading. Equity Sentiment Tilt improves the Equity Risk Parity Sharpe ratio in the negative regime from 0.516 to 0.527 and in the positive regime from 0.200 to 0.261, while neutral-regime Sharpe falls from 1.445 to 1.406. This means the signal adds information in some regimes but is not a standalone return forecast.

The extension also exposes a product-design boundary. Sentiment only applies to equities because the headline dataset covers the permitted equities. Applying the same signal to crypto would create a false sense of model coverage. The combined fund can still include crypto, but the sentiment tilt should affect the equity sleeve or equity-only fund unless a separate crypto-news dataset is added. The next robustness check should test whether the improvement survives alternative tilt strengths, transaction costs, and a finance-specific sentiment lexicon with manually reviewed terms.

**Table 3. Fusion comparison: base equity optimiser versus sentiment-augmented equity optimiser, 2021-2023 live backtest.** The sentiment fund tilts Equity Risk Parity weights at each rebalance using one-day-lagged sector sentiment and caps sector multipliers between 0.70 and 1.30. Both rows include 10 bps transaction costs on turnover. Source: `results/tables/fusion_comparison_report.csv`.

**Table 4. Sentiment tilt sensitivity after transaction costs, 2021-2022 discovery period.** Tilt strength controls how strongly sector sentiment changes equity weights; the selected strength is frozen before the 2023 holdout. Source: `results/tables/sentiment_tilt_grid_report.csv`.

**Table 5. Robustness by market period, 2021-2023 live backtest.** The table recalculates annualised return, Sharpe ratio, maximum drawdown, and total return for each fund across the full sample, 2021 recovery, 2022 drawdown, and 2023 recovery. Source: `results/tables/robustness_by_period_report.csv`.

**Table 6. Sentiment regime analysis, 2021-2023 live backtest.** Regimes are terciles of the equal-weight average one-day-lagged sector sentiment. The table reports return and risk metrics for each fund in negative, neutral, and positive sentiment regimes. Source: `results/tables/sentiment_regime_analysis_report.csv`.

**Table 7. Sentiment discovery and 2023 holdout validation.** Finance-lexicon and VADER tilt strengths are selected on 2021-2022 and evaluated without retuning on 2023 returns. Source: `results/tables/sentiment_holdout_validation_report.csv`.

**Table 8. Finance-lexicon and VADER score comparison.** The table compares score distributions, neutral coverage, cross-model correlation, and directional agreement across ticker-days. Source: `results/tables/sentiment_model_comparison_report.csv`.

**Figure 6. Fusion comparison: growth of $1 for Equity Risk Parity versus Equity Sentiment Tilt, 2021-2023 live backtest.** Values are cumulative returns from `results/data/fund_returns.csv` and `results/data/sentiment_fund_returns.csv`.

## 5. App and Investor Journey

The Streamlit app turns the modelling outputs into a fund-selection journey for young retail investors. It opens with fund comparison rather than a marketing page because the user needs evidence immediately: performance metrics, growth of $1, drawdowns, current holdings, sector sentiment, and the fusion result. The deployed app reads precomputed files from `results/`, which keeps it fast and avoids downloading raw data, scoring headlines, or recomputing portfolio backtests at runtime.

The app has six tabs. The Compare tab ranks the funds and plots growth of $1 for selected strategies. The Fact Sheet tab supports detailed fund inspection. The Allocation tab builds a model allocation and compares its gross growth with growth after a selected annual management fee. The Sentiment tab shows the Fear-Greed Gauge, sector index, finance-lexicon versus VADER comparison, discovery grid, 2023 holdout, and regime analysis. The Method tab explains the assumptions and the Overview tab introduces the product and main evidence.

The core journey has four steps. First, the user compares all funds by return, volatility, Sharpe ratio, maximum drawdown, turnover, and transaction cost. Second, the user opens a fund fact sheet to inspect the historical path and current holdings. Third, the user sets an allocation across funds and sees the implied mix. Fourth, the user reviews the sentiment analytics to understand whether recent sector news is supportive or cautious, while also seeing that stronger sentiment tilts can become too expensive to trade. This journey matches the Part A market gap: brokerage apps already make trading easy, but BetaVest gives young investors a structured layer for comparing diversified fund evidence.

The app should avoid overstating precision. Backtests are historical simulations, not guarantees, so the interface should show risk beside returns and make drawdowns visible. The allocation tool should also avoid implying personalised financial advice. A clear final version should include [HUMAN EDIT REQUIRED: app URL] and [HUMAN EDIT REQUIRED: public GitHub repository URL] in the hand-in materials.

## 6. Critical Reflection and Recommendations

The first limitation is estimation error. Mean-variance and maximum-Sharpe methods can be unstable because expected returns are noisy, especially in a 2020-2023 sample containing pandemic stress, crypto repricing, and high-growth technology stocks. Recommendation 1 has now been partly implemented by adding risk parity, weight caps, turnover, and transaction-cost reporting. The next improvement is to add shrinkage covariance and concentration checks so the optimiser is less dependent on noisy sample estimates.

The second limitation is sentiment measurement. A generic sentiment model may misread financial headlines because words such as "liability", "beat", "cut", or "downgrade" depend on context. Recommendation 2 has now been partly implemented by using a finance-specific lexicon baseline and a tilt-strength grid. The next improvement is to manually audit sampled scored headlines by sector, check false positives and false negatives, and test whether a lower-frequency weekly or monthly sentiment tilt reduces turnover.

The third limitation is deployment realism. The local pipeline can run heavier analysis, but the deployed app must load quickly and remain reproducible. Recommendation 3 has now been implemented by separating build-time analysis from app-time display: `scripts/run_part_b.py` generates derived CSVs and figures, while the Streamlit app reads those artifacts without downloading raw data or recomputing the full model. The next improvement is to add public deployment metadata once the final hand-in repository and Streamlit URL exist.

BetaVest's main Part B test is whether the product can turn noisy return and headline data into a clear investor decision process. The Part A foundation shows that the inputs are clean enough for a fair test. The final Part B result should be judged by out-of-sample performance, drawdown control, honest sentiment evidence, and whether the app helps a user understand the trade-off between equity, crypto, and combined fund exposure.

## Required Exhibits Checklist

- [ ] Performance-metrics table across funds and methods: annualised return, annualised volatility, Sharpe ratio, maximum drawdown.
- [ ] Growth-of-$1 figure comparing methods.
- [ ] Drawdown figure for at least one fund.
- [ ] Portfolio-weights-over-time figure across methods for at least one fund.
- [ ] Sharpe ratio or return-versus-risk barplot across funds and methods.
- [ ] Sentiment-index time series for equity sectors.
- [ ] Fusion before-versus-after comparison as both a table and a figure.
- [ ] Robustness table across market sub-periods.
- [ ] Sentiment regime analysis table.

## Human Edit Notes

- Replace every `[HUMAN EDIT REQUIRED: ...]` marker after `scripts/run_part_b.py` generates final outputs.
- Cross-check every metric against `results/tables/performance_metrics.csv`.
- Insert Word captions and cross-references in `report/report.docx`; do not manually type figure numbers in the final Word file.
- Add verified citations only after checking source metadata. Do not invent references for VADER, portfolio optimisation, or Streamlit.
