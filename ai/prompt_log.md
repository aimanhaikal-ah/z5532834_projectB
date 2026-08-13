# Prompt log - BetaVest Part B

## Entry 1 - Reuse the clean Part A foundation

### What I wanted
Use my Part A BetaVest cleaning and feature logic in Part B, instead of starting
again from the placeholder starter code.

### Prompt(s)
"Please reuse the clean data-processing logic from my Part A BetaVest project
where it is useful for Part B, especially the return construction, calendar
alignment, and headline-cleaning steps."

### What the assistant produced
The assistant copied the useful Part A logic into the Part B folder so the
submission stays self-contained. This included clean equity and crypto price
loading, exact headline deduplication, daily return features, crypto-to-equity
calendar alignment, and headline alignment to the same or next trading day.

### What was wrong or risky
The risky option was importing directly from `z5532834_projectA`, because the
Part B folder must run by itself when submitted. Direct cross-folder imports
could fail for the marker or deployed app.

### What I changed and why
I kept the Part A logic inside `z5532834_projectB/src/` rather than depending on
the Part A folder. This keeps Part B reproducible while still reusing my own
verified cleaning decisions.

---

## Entry 2 - Build the first fund backtest outputs

### What I wanted
Generate the first Part B fund evidence: fund returns, fund weights, performance
metrics, and figures for the report.

### Prompt(s)
"Please complete the first Part B modelling step by building the fund backtests
and generating the required fund returns, weights, metrics, and figures. Any
writing or interpretation should be treated as draft material only."

### What the assistant produced
The assistant implemented a walk-forward backtest with a 252-trading-day
estimation window and month-end rebalancing. It produced equity-only,
crypto-only, and combined funds using equal weight, minimum variance, and maximum
Sharpe methods. Any accompanying writing or interpretation from this step was
used as draft material only and was not treated as final report wording.

### What was wrong or risky
The first script run could not access the hosted dataset inside the sandbox. The
backtest also uses simplifying assumptions: zero risk-free rate, zero transaction
costs, and no turnover penalty. These assumptions are acceptable for a first
baseline, but they need to be stated in the report.

### What I changed and why
I reran the script with approved data access and checked that the generated
weights summed to 1 for each fund-date. I kept the baseline assumptions for now
because they let me finish the required fund outputs before adding sentiment,
fusion, and app features.

---

## Entry 3 - Sentiment calculation and fusion test

### What I wanted
Calculate the sector sentiment index and test whether lagged sentiment improves
the base equity fund.

### Prompt(s)
"Please complete the sentiment modelling step, then test whether a lagged sector
sentiment signal improves the base equity fund through a sentiment-fusion
portfolio."

### What the assistant produced
The assistant built a finance-lexicon sentiment score from the cleaned headline
panel, aggregated it into an equal-weight sector sentiment index, lagged the
signal by one trading day, and applied a sentiment tilt to the Equity Equal
Weight fund. It produced the sector sentiment outputs and a base-versus-fusion
comparison table and figure.

### What was wrong or risky
VADER could not be used because the local build could not download the VADER
lexicon due to a certificate error. There was also a look-ahead risk if same-day
sentiment was used directly in the portfolio. A very strong sentiment tilt could
also create excessive active weights.

### What I changed and why
I used a transparent finance-lexicon baseline and required a one-trading-day lag
before sentiment could affect weights. I capped the sentiment multiplier between
0.70 and 1.30, checked that weights stayed long-only and summed to 1, and then
retested the signal after adding transaction costs and a tilt-strength grid.

---

## Entry 4 - Build the Streamlit app with stronger features

### What I wanted
Turn the Part B outputs into a stronger Streamlit app that helps users compare
funds, inspect risk, and understand the sentiment-fusion results.

### Prompt(s)
"Please build the Streamlit app for BetaVest and improve it with stronger app
features, including fund comparison, fact sheets, allocation tools, sentiment
analysis, and clear method explanations."

### What the assistant produced
The assistant built a Streamlit app that reads the precomputed Part B result
files instead of recomputing the full analysis at runtime. The app includes fund
comparison charts, fund fact sheets, current holdings, an allocation builder,
sector sentiment analytics, a sentiment-tilt sensitivity table, downloads, and a
method tab.

### What was wrong or risky
A basic app could have shown only return charts and ignored the main investor
risks. That would make crypto-heavy or high-turnover funds look more attractive
than they are. There was also a deployment risk if the app recomputed raw data,
downloaded models, or used a non-standard Streamlit entrypoint.

### What I changed and why
I added risk labels, suggested fund uses, turnover, transaction-cost fields, and
the sentiment tilt grid so the app explains both performance and implementation
risk. I kept the deployable Streamlit entrypoint at the project root as
`streamlit_app.py`, matching the Station 4 deployment instructions.

---

## Entry 5 - Improve the Streamlit dashboard interface

### What I wanted
Use practical Streamlit dashboard improvements to make the BetaVest app more
polished, shareable, and easier to use for fund comparison.

### Prompt(s)
"Please apply useful Streamlit dashboard improvements to my BetaVest app,
including wide layout, Material-style icons, asymmetric columns, card-like
containers, caching with a 6-hour TTL, hidden spinners, URL-synced controls, and
a clean horizon selector."

### What the assistant produced
The assistant improved the existing Streamlit app shell with Material icon tab
labels, bordered KPI and content containers, asymmetric chart/table layouts,
cached CSV loading with a 6-hour TTL, hidden loading spinners, a chart-horizon
selector using `st.pills`, and URL query parameters for selected funds, fact
sheet fund, selected sectors, and horizon.

### What was wrong or risky
Some dashboard advice was designed for live API apps and did not fit this
project. Custom ticker entry could confuse users because BetaVest only displays
precomputed fund outputs. Live rate-limit handling was also unnecessary because
the deployed app should not call Yahoo Finance or rebuild the analysis at
runtime.

### What I changed and why
I used the dashboard ideas that directly improve the coursework app: better
layout, stronger visual hierarchy, shareable controls, and safer cached loading.
I kept the app tied to precomputed result files so it remains fast and
reproducible for deployment.

---

## Entry 6 - Refine dashboard readability and chart interaction

### What I wanted
Improve the BetaVest dashboard so key wording is fully visible and the fund
comparison chart is more interactive for users.

### Prompt(s)
"Please fix the dashboard layout where some wording is cut off, then make the
comparison chart interactive by allowing fund overlays, date-range selection,
and switching between Growth of $1, Drawdown, and Rolling Sharpe views."

### What the assistant produced
The assistant changed the KPI cards so long fund names wrap instead of being
truncated, moved the fund metrics table under the comparison chart at full
width, and added chart controls for date range and comparison view. The chart
now supports Growth of $1, Drawdown, and 63-day Rolling Sharpe using the
existing fund return series.

### What was wrong or risky
The previous dashboard layout squeezed the metrics table beside the chart and
caused long text such as fund names or table headings to be cut off. A fixed
comparison chart also made it harder to inspect specific periods such as the
2022 drawdown.

### What I changed and why
I prioritised readability and user control. The chart now uses full width, the
table has more horizontal space, and users can choose which funds and which
performance lens to inspect without changing the underlying precomputed data.

---

## Entry 7 - Add robustness and sentiment regimes

### What I wanted
Strengthen the Part B innovation evidence by adding tests that go beyond the
baseline fund comparison and show whether the main findings hold across market
conditions and sentiment states.

### Prompt(s)
"Please add a robustness test and a sentiment regime analysis to the BetaVest
project, using the existing Part B outputs and keeping the calculations
reproducible."

### What the assistant produced
The assistant added a reusable evaluation module that calculates fund
performance across the full sample, 2021 recovery, 2022 drawdown, and 2023
recovery. It also added a sentiment regime analysis based on terciles of the
one-day-lagged sector sentiment signal. The results are saved as
`results/tables/robustness_by_period_report.csv` and
`results/tables/sentiment_regime_analysis_report.csv`, displayed in the
Streamlit app, and interpreted in the report draft.

### What was wrong or risky
A single full-sample Sharpe ratio could overstate a strategy if it performs
well only in one market period. A sentiment signal could also be overstated if
positive news days are assumed to be automatically better return days.

### What I changed and why
I added period and regime checks so the project evaluates stability and signal
usefulness more honestly. The robustness test supports Combined Risk Parity as
a stronger core fund, while the sentiment regime analysis shows that sentiment
tilt adds incremental value in some regimes but should remain a controlled
portfolio tilt rather than a standalone forecast.

---

## Entry 8 - Polish the investor dashboard journey and theme controls

### What I wanted
Improve the BetaVest Streamlit app so it feels more like a finished investor
dashboard rather than a set of disconnected coursework charts.

### Prompt(s)
"Please improve the app overview and dashboard interface by adding a clear
overview page, global controls, consistent fund colours, concise tab subtitles,
and a light/dark theme option that works across the full dashboard."

### What the assistant produced
The assistant added an Overview tab that explains what BetaVest does, highlights
the main findings, summarises the scale of the product, shows a featured fund,
displays a small sentiment pulse, explains risk tiers, and gives a short guide
to the other tabs. The assistant also moved the date range into the sidebar as a
global control, added a light/dark app theme toggle, and made fund colours
consistent across fund-based charts.

### What was wrong or risky
Some early interface choices were useful but not polished enough. The Overview
page repeated the "how to use" journey, the first theme toggle changed only
charts rather than the whole app, and several dark-theme controls had weak
contrast. Selected multiselect chips, number inputs, download buttons, and
bordered cards were especially hard to read in one theme or the other.

### What I changed and why
I changed the Overview page into a clearer entry point for users: objective,
main findings, product scale, featured fund, sentiment pulse, risk tiers, and a
short navigation guide. I also changed the theme toggle into a full dashboard
theme option and improved CSS for controls, selected chips, cards, borders,
number inputs, download buttons, and tables. These edits make the app easier to
use and more professional for a non-technical investor or marker.

## Entry 9 - Improve dashboard accessibility and visual contrast

### What I wanted
Make the BetaVest app easier to read in both light and dark themes, especially
for controls and boxed dashboard sections.

### Prompt(s)
"Please fix the dashboard theme styling so selected controls, number inputs,
download buttons, and bordered sections remain clear and readable in both light
and dark mode."

### What the assistant produced
The assistant refined the app CSS for the light/dark theme system. It improved
the selected multiselect chips, allocation number inputs, plus/minus controls,
download buttons, bordered containers, dataframe areas, and general control
surfaces.

### What was wrong or risky
Some controls kept Streamlit's default light styling after switching to dark
theme. This made selected fund chips, allocation input values, and download
buttons hard to read. Some bordered cards also blended too closely into the
dark background, reducing the dashboard's visual structure.

### What I changed and why
I made the selected chips use red fill with white text, gave dark-theme boxes a
clearer slate border, and forced number inputs and control buttons to use theme
appropriate fills, borders, and text colours. This improves usability and makes
the app look more polished for users who prefer either light or dark mode.

### Verification
The Streamlit app smoke test passed after the contrast changes.

---

## Entry 10 - Test sentiment on an untouched holdout

### What I wanted
Reduce the risk of selecting a sentiment tilt that only performs well on the
same period used for tuning.

### Prompt(s)
"Please use 2021-2022 as the discovery period for selecting the sentiment tilt,
freeze the selected setting, and evaluate it separately on the 2023 holdout
after transaction costs. Compare the finance lexicon with standard VADER and
report the evidence clearly."

### What the assistant produced
The assistant added separate discovery and holdout calculations, a VADER
benchmark, a model-comparison table, and a reproducible sample of the largest
score disagreements. The finance tilt selected at 0.15 increased 2023 holdout
Sharpe from 0.944 to 1.003.

### What was wrong or risky
The earlier grid selected the best tilt using the full 2021-2023 sample and
reported performance on those same dates. This could overstate the result.

### What I changed and why
I kept 2023 outside the tuning decision and reported both models. This provides
more credible evidence while acknowledging that model agreement is not the same
as sentiment accuracy.

---

## Entry 11 - Add management-fee evidence to Allocation

### What I wanted
Make the Allocation tab show the practical effect of product fees for a selected
fund mix.

### Prompt(s)
"Please add an editable annual management-fee control to the BetaVest Allocation
tab and compare gross growth with growth after fees using the precomputed fund
return series. Keep the explanation concise and investor-facing."

### What the assistant produced
The assistant added a fee control, gross and net ending values, fee drag per
dollar, and an interactive gross-versus-net growth chart over the selected date
range.

### What was wrong or risky
A portfolio allocation without fee-adjusted performance could make the product
look more attractive than the amount retained by the investor.

### What I changed and why
I included daily fee deductions in the allocation view so implementation cost is
visible without rerunning the fund backtests in the deployed app.

---

## Entry 12 - Build Station 4 deployment app from precomputed outputs

### What I wanted
Turn the completed Part B analysis into a Station 4 Streamlit dashboard that is
ready for hand-in and deployment, while keeping the runtime app lightweight and
reproducible.

### Prompt(s)
"Part B analysis is complete: the funds, sentiment index, sentiment fusion, CSV
results, and figures have already been generated. Please follow the fins-agent
Part B protocol for Station 4. First read `AGENTS.md` and
`docs/STUDENT_DEPLOY.md` in the project folder. Build a root-level
`streamlit_app.py` that loads only precomputed result files at runtime, with no
backtest or NLTK processing inside the deployed app. Use `src/data_access.py`
for raw-data access during the analysis pipeline, but do not commit raw data.
Run `scripts/check_handin.py` and fix all failures. Initialise git, commit the
code and result outputs, and prepare the project for a new public repository.
The Streamlit browser deployment will be completed manually because it requires
my account login."

### What the assistant produced
The assistant converted the completed analysis outputs into a Streamlit
dashboard with tabs for Overview, Compare, Fact Sheet, Allocation, Sentiment,
and Method. The app loads precomputed CSVs and figures from `results/`, uses
the project data-access layer for analysis code, and avoids rerunning expensive
backtests or sentiment scoring at runtime.

### What was wrong or risky
Running portfolio backtests or text-sentiment processing inside Streamlit would
make the deployed app slower, less reliable, and harder to reproduce. Committing
raw data would also create a hand-in and licensing risk.

### What I changed and why
I kept the deployable app focused on presentation and interaction, while the
analysis pipeline remains in scripts and source modules. This makes the final
dashboard easier for a marker to run, inspect, and deploy.
