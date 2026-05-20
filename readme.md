# Thematic ETF Tracker

A Streamlit dashboard for tracking and analysing thematic ETFs across 5 markets: Hong Kong, A-Share, Taiwan, South Korea, and US.

---

## Run Locally

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Fetch market data (first run takes ~20–40 min, incremental after that)
python data_collection.py

# 4. Launch the dashboard
streamlit run app.py
```

The app opens at `http://localhost:8501`. Select a market from the sidebar to get started.

> **Data note:** `data/`, `data_ashare/`, `data_tw/`, `data_sk/`, and `data_us/` are gitignored. You must run `data_collection.py` locally before the dashboard has anything to show.

---

## Project Structure

```
project/
├── app.py                        # Main entrypoint — routing and sidebar
├── data_collection.py            # Fetches OHLCV data (yfinance → AkShare fallback)
├── run_daily_update.py           # One-shot manual data update
├── scheduler.py                  # Automated daily scheduler (Tue–Sat, 18:00)
│
├── utils/
│   ├── config.py                 # Constants, CONFIG_FILES, load_all_configs()
│   ├── data.py                   # All data-loading and computation helpers
│   └── charts.py                 # Reusable Plotly chart builders
│
├── _pages/
│   ├── summary.py                # Summary Dashboard page
│   ├── industry.py               # Industry Analysis page
│   ├── comparison.py             # Multi-asset Comparison page
│   ├── pair_analysis.py          # Pair Analysis page (statistical deep-dive)
│   └── emerging.py               # Emerging ETFs page (post-2025 A-Share listings)
│
├── sentiment_analysis/           # Optional Google Trends module (see below)
│
├── etf_config.json               # Hong Kong: HSI benchmark, 10 industries, 1 ETF each
├── a_share_etf_config.json       # A-Share: CSI 300 benchmark, 12 industries, 1 ETF each
├── tw_etf_config.json            # Taiwan: TAIEX proxy benchmark, 7 industries, 1 ETF each
├── sk_etf_config.json            # South Korea: KOSPI 200 benchmark, 10 industries, 1 ETF each
├── us_etf_config.json            # US: SPY benchmark, 11 SPDR sector ETFs, 1 each
├── a_share_etf_emerging.json     # Emerging A-Share ETFs (listed ≥ 2025-01-01)
│
├── data/                         # HK price CSVs (gitignored)
├── data_ashare/                  # A-Share price CSVs (gitignored)
├── data_tw/                      # Taiwan price CSVs (gitignored)
├── data_sk/                      # South Korea price CSVs (gitignored)
├── data_us/                      # US price CSVs (gitignored)
│
├── docs/
│   └── deployment_plan.md        # Full GCP deployment guide (start here to deploy)
├── gcp-deploy.sh                 # One-shot GCP deployment script
├── Dockerfile                    # Container image (gcsfuse + Streamlit)
├── docker-entrypoint.sh          # Mounts GCS bucket at /data, starts Streamlit
└── archive/                      # One-off scripts and old notebooks
```

---

## Dashboard Pages

### Summary Dashboard
The main overview page. Sections in order:

| Section | What it shows |
|---------|--------------|
| **Industry Average Performance** | Absolute return per industry for the selected period, colour-coded table + horizontal bar chart |
| **Industry Momentum Heatmap** | Rolling returns (5d, 21d, 63d, YTD) per industry — toggle absolute vs relative to benchmark |
| **Top 10 / Bottom 10 ETFs** | Best and worst performing ETFs across all industries in the selected period |
| **Turnover by Industry** | Stacked area chart of daily turnover (volume × close price) over the selected period |
| **1M vs 3M Turnover** | Grouped bar chart comparing last month's turnover to the 3-month monthly average — shows whether a theme is becoming more or less actively traded |

### Industry Analysis
Price and volume chart for a selected industry vs benchmark. Filter by currency. Toggle between price, volume, or both.

### Comparison
Multi-asset cumulative return overlay across any combination of ETFs and benchmarks from any market.

### Pair Analysis
Deep two-asset statistical analysis:

| Tab | What it shows |
|-----|--------------|
| **Price & Volume** | Normalised return overlay, return spread (A − B), relative volume |
| **Single-Asset Stats** | Total/annualised return, volatility, Sharpe, max drawdown, skewness, kurtosis, ADF stationarity, return distribution histogram, ACF |
| **Pair Statistics** | Rolling correlation (21d + 63d), Pearson & Spearman, OLS regression (β/α/R²), Engle-Granger cointegration, rolling beta (63d), rolling volatility (21d), lead-lag cross-correlation |

### Emerging ETFs
A-Share ETFs listed after 2025-01-01. Price trend from listing date, growth rate, AUM vs return bubble chart.

### Sentiment Analysis *(optional)*
Google Trends search interest for investment themes. Requires `pytrends`. See [Sentiment Analysis](#sentiment-analysis) below.

---

## Data Collection

Each market fetches from **yfinance** with **AkShare** as a fallback for HK and A-Share:

| Market | Benchmark | Fallback |
|--------|-----------|---------|
| Hong Kong | HSI | AkShare `stock_hk_daily` |
| A-Share | CSI 300 (000300) | AkShare `fund_etf_hist_sina` |
| Taiwan | 0050 (TAIEX proxy) | None |
| South Korea | 069500.KS (KOSPI 200) | None |
| US | SPY (S&P 500) | None |

Collection is **incremental** — only missing date ranges are fetched. Running it again after a gap will fill in only the days since the last update.

```bash
# Update all 5 markets
python data_collection.py

# Automated: runs every Tue–Sat at 18:00 local time
python scheduler.py
```

---

## Sentiment Analysis *(optional)*

Google Trends data is fetched separately via `pytrends` and cached as CSVs.

```bash
# Fast: one representative keyword per theme (~2 min)
python sentiment_analysis/google_trends.py --mode comparative --geo HK,CN --timeframe 1y

# Full: all keywords per theme (~10–15 min, rate-limited)
python sentiment_analysis/google_trends.py --mode all --geo HK,CN --timeframe 1y
```

Or use the **Fetch fresh data** button on the Sentiment Analysis page in the dashboard.

> **Note:** `pytrends` 4.9.2 has a compatibility issue with `urllib3` v2. If you hit errors, patch `method_whitelist` → `allowed_methods` in the pytrends source.

---

## Deploy to GCP

See [docs/deployment_plan.md](docs/deployment_plan.md) for the full step-by-step guide. The short version:

```bash
# First time
./gcp-deploy.sh

# After code changes
./gcp-deploy.sh update
```

---

## What's Missing / Potential Next Steps

### Signal & Analysis
- **52-week high/low proximity** — flag themes near breakout vs exhaustion levels; buildable from existing OHLCV data
- **Theme correlation matrix** — heatmap showing which industries move together across markets; helps avoid double-counting exposure (e.g. semiconductor and AI are highly correlated)
- **Relative strength vs broad market** — currently removed from summary; could be a toggleable overlay on the industry performance chart
- **Forward-looking signal score** — combine momentum + turnover trend + cross-market alignment into a single ranked score per theme per market

### Data
- **AUM per ETF** — currently using avg daily volume as a proxy; proper AUM (from fund manager websites) would make the "largest ETF" selection more accurate
- **Dividend-adjusted returns** — current prices are not total-return; high-dividend themes (financials, REITs, utilities) are understated
- **Macro overlays** — interest rates, FX (USD/CNY, USD/HKD), commodity prices as context for sector moves

### Infrastructure
- **Automated config refresh** — when a new high-AUM ETF launches in a theme, it should replace the current representative automatically rather than requiring a manual config edit
- **Data quality alerts** — flag when a CSV hasn't been updated in >3 trading days (data source outage)
- **Historical backtesting tab** — given a theme selection rule, show what the signal would have returned historically
