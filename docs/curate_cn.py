"""
Curate CN (A-Share) ETF config:
- Drop bonds_fixed_income entirely
- Drop 'other' (offshore trackers)
- Deduplicate broad_market: keep 1 per major index
- Deduplicate gold_commodities: keep best-known funds
- Deduplicate technology_innovations: 1 per index
- Deduplicate financials: keep 5
- Real estate REITs: keep all (individual assets, not duplicates)
Writes the cleaned config back to a_share_etf_config.json
"""

import json, shutil, os

PATH = '/Users/oliveryang/Desktop/rays/project/a_share_etf_config.json'
BACKUP = PATH + '.bak'

# ── Curated selections ────────────────────────────────────────────────────────

# broad_market: 1 per major index — pick largest/most liquid fund per index
BROAD_MARKET_KEEP = [
    # Index             Code      Name (display)
    ('510050',),   # SSE 50 (上证50) — 华夏
    ('510300',),   # CSI 300 (沪深300) — 华夏
    ('510500',),   # CSI 500 — 南方
    ('512100',),   # CSI 1000
    ('560010',),   # CSI 1000 alternative → keep 510500 only; actually keep 512100
    ('512500',),   # CSI 500 alternative → deduplicate, keep 510500
    ('560610',),   # A500 — 华泰柏瑞
    ('510880',),   # CSI Dividend (中证红利)
    ('588000',),   # STAR 50 (科创50) — moved to tech but keep broad ref
    ('510180',),   # SSE 180
    ('563300',),   # CSI 2000
    ('513600',),   # Hang Seng Index (A-share tracker)
    ('513500',),   # S&P 500 (offshore)
    ('510900',),   # Hang Seng China (H-share)
]

# Keep these specific codes for broad_market (1 per index, most liquid)
BROAD_KEEP = {
    '510050',   # SSE 50
    '510300',   # CSI 300
    '510500',   # CSI 500
    '512100',   # CSI 1000
    '560610',   # A500
    '510880',   # CSI Dividend
    '510180',   # SSE 180
    '563300',   # CSI 2000
    '513600',   # Hang Seng Index
    '510900',   # Hang Seng China Enterprises
    '513500',   # S&P 500
    '512720',   # Computer / tech broad (计算机)
}

# gold_commodities: keep 1 physical gold + 1 gold stock ETF + 1 materials broad
GOLD_KEEP = {
    '518880',   # 黄金ETF — largest physical gold (华夏)
    '517400',   # 黄金股票 — gold mining stocks
    '516150',   # 稀土基金 — rare earth (from materials, notable)
}

# gold_commodities original has both gold and some misclassified; keep:
GOLD_COMMODITIES_KEEP = {
    '518880',   # 黄金ETF — physical gold (largest, most liquid)
    '517400',   # 黄金股票 — gold mining equity
}

# materials: keep 1 per sub-sector
MATERIALS_KEEP = {
    '516150',   # 稀土基金 — rare earth
    '515220',   # 煤炭ETF — coal
    '512400',   # 有色ETF — non-ferrous metals (broad)
    '515210',   # 钢铁ETF — steel
    '516570',   # 石化ETF — petrochemicals
}

# technology_innovations: 1 per index
TECH_KEEP = {
    '588000',   # 科创50 — STAR Market 50 (largest, most liquid)
    '588190',   # 科创100
    '588230',   # 科创200
    '588300',   # 双创ETF — ChiNext + STAR dual innovation
    '513130',   # 恒生科技 — Hang Seng Tech (HK-listed tech)
    '515000',   # 科技ETF — CSI Tech broad
    '513260',   # 恒科技 — alternative HK tech tracker → keep 513130 only
    '515680',   # 创新央企 — SOE innovation
}

TECH_KEEP = {
    '588000',   # 科创50
    '588190',   # 科创100
    '588230',   # 科创200
    '588300',   # 双创ETF
    '513130',   # 恒生科技 (HK tech)
    '515000',   # 科技ETF (CSI broad tech)
    '515680',   # 创新央企
    '515900',   # 央创ETF
}

# financials: keep 5 most distinct
FINANCIALS_KEEP = {
    '512880',   # 证券ETF — securities brokers (华夏)
    '512800',   # 银行ETF — banks (华夏)
    '512000',   # 券商ETF — brokers alternative
    '516860',   # 金融科技 — fintech
    '510230',   # 金融ETF — broad financials
}

# internet_communications: already small (8), keep all
# esg_clean_energy: already small (11), keep all
# cloud_computing_robotics_ai: already small (9), keep all
# semiconductor: already small (12), keep all
# military_defense: already small (4), keep all
# consumer_e_commerce: already small (8), keep all
# biotech_healthcare: already small (14), keep all
# real_estate: keep all REITs (individual assets)


def curate(config: dict) -> dict:
    industries = config['industries']
    new_industries = {}

    for key, etfs in industries.items():
        # Drop entirely
        if key in ('bonds_fixed_income', 'other'):
            print(f'  DROP  {key} ({len(etfs)} ETFs)')
            continue

        if key == 'broad_market':
            kept = [e for e in etfs if e['code'] in BROAD_KEEP]
            print(f'  broad_market: {len(etfs)} → {len(kept)}')
            new_industries[key] = kept

        elif key == 'gold_commodities':
            kept = [e for e in etfs if e['code'] in GOLD_COMMODITIES_KEEP]
            print(f'  gold_commodities: {len(etfs)} → {len(kept)}')
            new_industries[key] = kept

        elif key == 'materials':
            kept = [e for e in etfs if e['code'] in MATERIALS_KEEP]
            print(f'  materials: {len(etfs)} → {len(kept)}')
            new_industries[key] = kept

        elif key == 'technology_innovations':
            kept = [e for e in etfs if e['code'] in TECH_KEEP]
            print(f'  technology_innovations: {len(etfs)} → {len(kept)}')
            new_industries[key] = kept

        elif key == 'financials':
            kept = [e for e in etfs if e['code'] in FINANCIALS_KEEP]
            print(f'  financials: {len(etfs)} → {len(kept)}')
            new_industries[key] = kept

        else:
            print(f'  KEEP  {key} ({len(etfs)} ETFs)')
            new_industries[key] = etfs

    config['industries'] = new_industries
    return config


if __name__ == '__main__':
    shutil.copy(PATH, BACKUP)
    print(f'Backup saved to {BACKUP}')

    config = json.load(open(PATH))
    total_before = sum(len(v) for v in config['industries'].values())

    print('\nCurating...')
    config = curate(config)

    total_after = sum(len(v) for v in config['industries'].values())
    print(f'\nTotal ETFs: {total_before} → {total_after}')

    with open(PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    print(f'Saved {PATH}')
