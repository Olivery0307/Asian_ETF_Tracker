"""
Build tw_etf_config.json and sk_etf_config.json from curated lists.
Same schema as etf_config.json and a_share_etf_config.json.
"""

import json
from collections import defaultdict

BASE = '/Users/oliveryang/Desktop/rays/project'


def build_config(curated_path, settings, benchmark):
    etfs = json.load(open(curated_path))
    industries = defaultdict(list)
    for e in etfs:
        industries[e['theme']].append({
            'code':     e['code'],
            'name':     e['name'],
            'currency': e['currency'],
        })
    return {
        'settings':   settings,
        'benchmark':  benchmark,
        'industries': dict(industries),
    }


# ── Taiwan ────────────────────────────────────────────────────────────────────
tw_config = build_config(
    f'{BASE}/docs/tw_etfs_curated.json',
    settings={
        'start_date':    '2025-01-01',
        'end_date':      '2026-12-31',
        'data_root_dir': 'data_tw',
    },
    benchmark={
        'code':   '0050',
        'name':   'Yuanta Taiwan Top 50 (TAIEX proxy)',
        'market': 'tw_index',
    },
)

# ── South Korea ───────────────────────────────────────────────────────────────
sk_config = build_config(
    f'{BASE}/docs/sk_etfs_curated.json',
    settings={
        'start_date':    '2025-01-01',
        'end_date':      '2026-12-31',
        'data_root_dir': 'data_sk',
    },
    benchmark={
        'code':   '069500',
        'name':   'Samsung KODEX 200 (KOSPI 200)',
        'market': 'sk_index',
    },
)

# ── Save ──────────────────────────────────────────────────────────────────────
for name, cfg in [('tw_etf_config', tw_config), ('sk_etf_config', sk_config)]:
    path = f'{BASE}/{name}.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)
    total = sum(len(v) for v in cfg['industries'].values())
    print(f'Saved {path}  ({total} ETFs across {len(cfg["industries"])} themes)')
    for theme, etfs in sorted(cfg['industries'].items()):
        print(f'  {theme:35s} {len(etfs):2d} ETFs')
