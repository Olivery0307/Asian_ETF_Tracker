# Thematic ETF Tracker

A Streamlit dashboard for tracking and analysing thematic ETFs across Hong Kong and A-Share markets.

---

## Quick Start

```bash
# 1. Activate the virtual environment
source venv/bin/activate

# 2. Fetch / update market data
python data_collection.py

# 3. Launch the dashboard
python -m streamlit run app.py
```

---

## Project Structure

```
project/
├── app.py                        # Main entrypoint (~120 lines)
├── data_collection.py            # Fetches ETF price data (yfinance → AkShare fallback)
├── run_daily_update.py           # One-shot manual data update
├── scheduler.py                  # Automated daily scheduler (Tue–Sat, 18:00)
├── generate_ashare_config.py     # Regenerates a_share_etf_config.json from XLS source
│
├── utils/
│   ├── config.py                 # Constants, CONFIG_FILES, load_all_configs()
│   ├── data.py                   # All data-loading and computation helpers
│   └── charts.py                 # Reusable Plotly chart builders
│
├── pages/
│   ├── summary.py                # Summary Dashboard page
│   ├── industry.py               # Industry Analysis page
│   ├── comparison.py             # Multi-asset Comparison page
│   ├── pair_analysis.py          # Pair Analysis page (statistical deep-dive)
│   └── emerging.py               # Emerging ETFs page (post-2025 A-Share listings)
│
├── sentiment_analysis/
│   ├── app_sentiment.py          # Sentiment Analysis Streamlit page
│   ├── google_trends.py          # Google Trends data fetcher (pytrends)
│   ├── trend_analysis.py         # Stats + chart builders for trends data
│   └── topics_config.json        # Themes, keywords, timeframes, geo labels
│
├── etf_config.json               # Hong Kong ETF configuration (9 industries, 70+ ETFs)
├── a_share_etf_config.json       # A-Share ETF configuration (15+ industries, 100+ ETFs)
├── a_share_etf_emerging.json     # Emerging A-Share ETFs (listed ≥ 2025-01-01, scale ≥ 10B CNY)
│
├── data/                         # Hong Kong ETF price CSVs (OHLCV, daily)
├── data_ashare/                  # A-Share ETF price CSVs (OHLCV, daily)
├── docs/                         # Reference documents (factsheets, XLS source data)
└── archive/                      # One-off scripts and old notebooks
```

---

## Dashboard Pages

| Page | Description |
|---|---|
| **Summary Dashboard** | Top 10 / Bottom 10 ETFs, industry average returns, trading volume by industry |
| **Industry Analysis** | Price and volume chart for a selected thematic industry vs benchmark |
| **Comparison** | Multi-asset cumulative return and volume comparison across both markets |
| **Pair Analysis** | Deep two-asset statistical analysis (see below) |
| **Emerging ETFs** | A-Share ETFs listed after 2025-01-01 — trend, growth rate, scale vs return bubble chart |
| **Sentiment Analysis** | Google Trends search interest for investment themes in HK and CN |

### Pair Analysis — statistical methods

| Tab | What it shows |
|---|---|
| **Price & Volume** | Normalised cumulative return overlay, return spread (A − B), relative volume |
| **Single-Asset Stats** | Total/annualised return, volatility, Sharpe, max drawdown, skewness, excess kurtosis, ADF stationarity test, return distribution histogram with normal fit, ACF of daily returns |
| **Pair Statistics** | Rolling correlation (21d + 63d), full-period Pearson & Spearman, OLS scatter with β/α/R², Engle-Granger cointegration test (with Z-score spread if cointegrated), rolling beta (63d), rolling volatility (21d), lead-lag cross-correlation |

---

## Data Collection

```bash
# Full update (HK + A-Share, dynamic end date = last trading day)
python data_collection.py

# Emerging A-Share ETFs are in a_share_etf_emerging.json.
# Their data is fetched via AkShare (fund_etf_hist_em) since yfinance
# does not cover STAR-market ETFs.
```

Data is stored as daily OHLCV CSVs under `data/` (HK) and `data_ashare/` (A-Share).
The collection script is incremental — it only fetches missing date ranges.

### Automated scheduling

```bash
# Runs every Tue–Sat at 18:00 (collects previous day's data)
python scheduler.py
```

---

## Sentiment Analysis

Google Trends data is fetched separately and cached as CSVs in `sentiment_analysis/data/trends/`.

```bash
# Fast: one representative keyword per theme (~2 min)
python sentiment_analysis/google_trends.py --mode comparative --geo HK,CN --timeframe 1y

# Full: all keywords per theme (~10–15 min due to rate limits)
python sentiment_analysis/google_trends.py --mode all --geo HK,CN --timeframe 1y
```

Or use the **Fetch fresh data** button on the Sentiment Analysis page in the dashboard.

---

## Dependencies

```
streamlit, plotly, pandas, numpy
yfinance, akshare
scipy, statsmodels
pytrends
matplotlib, seaborn
schedule
```

Install: `pip install -r requirements.txt`

> **Note:** `pytrends` 4.9.2 has a compatibility issue with `urllib3` v2.
> The venv copy has been patched (`method_whitelist` → `allowed_methods`).
