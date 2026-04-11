# ETF Universe Documentation

Last updated: 2026-04-10  
Total coverage: **4 markets, 309 ETFs across 14 thematic categories**

---

## Overview

| Market | Config File | Benchmark | ETFs | Themes | Data Dir | yfinance Suffix |
|--------|-------------|-----------|------|--------|----------|-----------------|
| Hong Kong | `etf_config.json` | HSI (Hang Seng Index) | 74 | 10 | `data/` | none (e.g. `02820.HK`) |
| A-Share (CN) | `a_share_etf_config.json` | 000300 (CSI 300) | 136 | 13 | `data_ashare/` | `.SS` / `.SZ` |
| Taiwan | `tw_etf_config.json` | 0050 (TAIEX proxy) | 27 | 7 | `data_tw/` | `.TW` |
| South Korea | `sk_etf_config.json` | 069500 (KOSPI 200) | 72 | 10 | `data_sk/` | `.KS` |

---

## Sources

| Market | Primary Source | Notes |
|--------|---------------|-------|
| **HK** | yfinance (`.HK` suffix) | Good coverage; some dual-currency ETFs (HKD/USD/RMB) |
| **CN** | AkShare (`fund_etf_hist_em`) | yfinance works for most; AkShare needed for STAR Market codes (`588xxx`) |
| **TW** | yfinance (`.TW` suffix) | Sourced from investing.com/etfs/taiwan-etfs |
| **SK** | yfinance (`.KS` suffix) | Sourced from investing.com/etfs/south-korea-etfs |

---

## Theme Coverage by Market

| Theme | HK | CN | TW | SK |
|-------|----|----|----|----|
| semiconductor | 5 | 12 | 5 | 7 |
| technology_innovations | 24 | 8 | 3 | 8 |
| cloud_computing_robotics_ai | 4 | 9 | 3 | 8 |
| internet_communications | 4 | 8 | 6 | 8 |
| esg_clean_energy | 17 | 11 | 5 | 8 |
| biotech_healthcare | 4 | 14 | — | 8 |
| consumer_e_commerce | 8 | 8 | 2 | 8 |
| military_defense | — | 4 | — | 8 |
| real_estate | 2 | 38 | 3 | 8 |
| transportation | 3 | — | — | 1 |
| virtual_assets | 3 | — | — | — |
| broad_market | — | 12 | — | — |
| financials | — | 5 | — | — |
| gold_commodities | — | 2 | — | — |
| materials | — | 5 | — | — |

---

## Market Details

### Hong Kong (HK)

**Benchmark:** Hang Seng Index (HSI)  
**Exchange:** HKEX  
**Currencies covered:** HKD, USD, RMB (dual/triple-listed ETFs included)
**Sources:** [hkex.com.hk/](https://www.hkex.com.hk/-/media/HKEX-Market/Products/Securities/Exchange-Traded-Products/Launch/Hong-Kong-listed-thematic-ETFs-factsheet.pdf)

**Notes:**
- Many ETFs are dual-listed in HKD + USD (e.g. `02820` / `09820`). Both are tracked; currency filter available in Industry Analysis page.
- `virtual_assets` theme is unique to HK — includes Bitcoin and Ethereum spot ETFs approved in 2024 (`03042`, `03046`, `03008`).
- `technology_innovations` is the largest theme (24 ETFs) due to broad HK tech ETF ecosystem.
- Source: manually curated from HKEX ETF listings and Global X, ChinaAMC, CSOP issuer pages.

**ETFs requiring attention:**
- `03174` (CSOP China Healthcare Disruption) — underwent a stock split in 2025; split adjustment applied in `utils/config.py` via `STOCK_SPLITS`.

---

### A-Share / China (CN)

**Benchmark:** CSI 300 (000300, tracked via AkShare)  
**Exchanges:** SSE (Shanghai, `5xxxx`/`6xxxx`) and SZSE (Shenzhen, `1xxxx`/`3xxxx`)  
**Currency:** CNY only
**Sources**: Excel sheet exported from [etf.sse.com.cn](https://etf.sse.com.cn/fundlist/)

**Deduplication applied (2026-04-10):**  
Original config had 294 ETFs; reduced to **136** by:
- `broad_market`: 82 → 12 (kept 1 per major index: SSE50, CSI300, CSI500, CSI1000, A500, CSI Dividend, SSE180, CSI2000, HSI tracker, H-share tracker, S&P500 tracker)
- `technology_innovations`: 34 → 8 (kept 1 per index: 科创50/100/200, 双创, HK Tech, CSI Tech, SOE Innovation)
- `gold_commodities`: 14 → 2 (kept largest physical gold ETF `518880` + gold equity ETF `517400`)
- `financials`: 17 → 5 (kept most distinct: securities broker, bank, broad financial, fintech)
- `materials`: 11 → 5 (kept 1 per sub-sector: rare earth, coal, non-ferrous, steel, petrochemicals)
- Dropped `bonds_fixed_income` (15 ETFs) — out of scope
- Dropped `other` (17 ETFs) — offshore index trackers (Nikkei, NASDAQ) not relevant to CN thematic analysis

**Notes:**
- `real_estate` (38 ETFs) are individual C-REITs — infrastructure, logistics, residential, commercial. These are distinct assets, not fund duplicates. All retained.
- STAR Market codes (`588xxx`) require AkShare for data collection — yfinance returns empty for these.
- Scraping logic: yfinance first → AkShare fallback; skip on rate limit.

**ETFs requiring attention:**
- All `588xxx` codes (STAR Market) — yfinance cannot fetch these; AkShare `fund_etf_hist_em` required.
- `508xxx` codes (C-REITs) — traded on SSE/SZSE but structured differently; verify data availability.

---

### Taiwan (TW)

**Benchmark:** `0050.TW` — Yuanta P-shares Taiwan Top 50 (largest TAIEX-tracking ETF, ~60% TSMC weight)  
**Exchange:** TWSE / TPEx  
**Currency:** TWD

**Source:** [investing.com/etfs/taiwan-etfs](https://www.investing.com/etfs/taiwan-etfs)

**Exclusions applied:**
- Symbols ending in `L`/`R` (leveraged/inverse)
- Symbols ending in `U` (commodity futures ETNs)
- Symbols ending in `B` (bond ETFs)
- Symbols ending in `K` (currency-hedged duplicates with negligible volume)

**Notes:**
- TW has a large dividend ETF ecosystem (`00878`, `00919`, `0056`) — excluded from thematic config as they are factor strategies, not sector/theme.
- Semiconductor theme is TSMC-heavy by nature of the Taiwanese market — all semiconductor ETFs have significant TSMC exposure.
- `00881` (Cathay Taiwan 5G Plus) is the most traded pure 5G/telecom ETF in TW.

**ETFs requiring attention:**
- `020000.TW` (Fubon Big Apple Total Return Index) — tracks NYC-listed companies; unusual, verify yfinance coverage.
- `006201.TW` (Yuanta GreTai 50) — TPEx-listed; confirm `.TW` suffix works in yfinance.

**Major issuers:** Yuanta (元大), Cathay (國泰), Fubon (富邦), CTBC (中信), Capital (群益), Fuh Hwa (富邦華一), SinoPac (永豐)

---

### South Korea (SK)

**Benchmark:** `069500.KS` — Samsung KODEX 200 (KOSPI 200, most liquid SK ETF)  
**Exchange:** KRX  
**Currency:** KRW

**Source:** [investing.com/etfs/south-korea-etfs](https://www.investing.com/etfs/south-korea-etfs)

**Exclusions applied:**
- Symbols starting with `Q` (ETNs, not ETFs)
- Leveraged/inverse products filtered by name keywords
- Bond/fixed-income products filtered by name keywords
- Capped at **8 ETFs per theme** (PDF order ≈ volume order, so top-8 are highest liquidity)

**Notes:**
- `esg_clean_energy` is dominated by secondary battery / EV ETFs — reflects Korea's role as a global battery manufacturer (Samsung SDI, LG Energy, SK Innovation).
- `military_defense` includes both K-Defense (방산) and Shipbuilding themes — Korea is a major defense exporter; these had significant inflows in 2025.
- `cloud_computing_robotics_ai` includes China Humanoid Robot ETFs (`0048K0`, `0053L0`) — cross-market exposure.
- `internet_communications` is mostly NASDAQ 100 trackers — reflects Korean retail investor appetite for US tech.

**ETFs requiring attention:**
- Symbols with non-numeric characters (e.g. `0080G0`, `0008T0`, `0000Z0`) — newer KRX codes; verify yfinance coverage with `.KS` suffix before scraping.
- `140710.KS` (KODEX Transportation) — only 1 ETF in transportation theme; consider dropping theme or finding more.

**Major issuers:** Samsung (KODEX), Mirae Asset (TIGER), KB (KBSTAR/RISE), Shinhan (SOL), NH-Amundi (HANARO), Hanwha (ARIRANG), Timefolio, KIM (ACE)

---

## Thematic Category Definitions

| Theme Key | Description | Notes |
|-----------|-------------|-------|
| `semiconductor` | Chip design, fabrication, EDA, equipment, materials | Includes upstream (equipment/materials) and downstream (fabless, IDM) |
| `technology_innovations` | Broad tech, innovation indexes, IT sector | Catch-all for tech ETFs not fitting narrower themes |
| `cloud_computing_robotics_ai` | AI, cloud, robotics, automation, humanoid | Fastest-growing theme across all markets in 2025 |
| `internet_communications` | Internet platforms, 5G, telecom, NASDAQ | HK/CN focus on Chinese internet; TW/SK skew toward US NASDAQ |
| `esg_clean_energy` | Clean energy, EV, battery, ESG, carbon | SK dominated by battery ETFs; HK/CN by solar/wind |
| `biotech_healthcare` | Biotech, pharma, medical devices, healthcare | Includes cosmetics ETFs (SK: cosmetics classified here) |
| `consumer_e_commerce` | Consumer brands, retail, e-commerce, F&B | HK/CN focus on China consumer; SK tracks global/US consumer |
| `military_defense` | Defense, aerospace, shipbuilding, UAV | CN: military SOEs; SK: K-Defense + shipbuilding |
| `real_estate` | REITs, property, infrastructure | CN: 38 individual C-REITs; HK/TW/SK: diversified REIT ETFs |
| `transportation` | Logistics, shipping, aviation | Limited coverage — HK has most (3), SK has 1 |
| `virtual_assets` | Bitcoin/Ethereum spot ETFs | HK only — approved April 2024 |
| `broad_market` | Major market indexes | CN only — SSE50, CSI300/500/1000, A500, etc. |
| `financials` | Banks, brokers, insurance | CN only |
| `gold_commodities` | Physical gold, gold mining, metals | CN only |
| `materials` | Rare earth, steel, coal, chemicals | CN only |

---

## Data Collection

```bash
# Activate environment
source venv/bin/activate

# Collect / update all market data
python data_collection.py          # HK + CN (existing)
# TW and SK: to be added to data_collection.py
```

**Scraping logic:**
1. yfinance first (fast, no rate limit for HK/TW/SK)
2. AkShare fallback (CN STAR Market `588xxx` codes only)
3. Skip gracefully on AkShare rate limit — do not block

**Data directories:**

| Market | Directory | Format |
|--------|-----------|--------|
| HK | `data/` | `data/{industry}/{code}.csv` |
| CN | `data_ashare/` | `data_ashare/{industry}/{code}.csv` |
| TW | `data_tw/` | `data_tw/{industry}/{code}.csv` |
| SK | `data_sk/` | `data_sk/{industry}/{code}.csv` |

Each CSV contains: `Date, Open, High, Low, Close, Volume`
