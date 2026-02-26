# semrush-seo — OpenClaw Skill

> 🔍 Automated SEO keyword research & competitor backlink analysis via Semrush (sem.3ue.com proxy)

An [OpenClaw](https://openclaw.ai) skill that automates keyword research workflows using the Semrush API through sem.3ue.com proxy — no manual CSV exports required.

## Features

**Semrush layer** (primary, ~1500 keywords/day limit):
- Batch keyword research (50 keywords/call) — Vol / KD / CPC / Competition
- Related keyword expansion via `ideas.GetKeywords`
- SERP competitor analysis
- Competitor backlink discovery

**Similarweb layer** (fallback when Semrush quota is exhausted):
- Single-keyword queries — Vol / KD / CPC + **zero-click rate** (Semrush doesn't have this)
- Search intent classification (Navigational / Informational / Transactional)
- Domain Top Pages analysis for competitor keyword mining

**Both tools:**
- Auto-filter: marks keywords as `qualifies=YES` when Vol≥500 + KD≤40% + CPC≥$1
- CSV batch output with identical column format

## Quick Start

### Semrush (primary, ~1500 keywords/day)

```bash
# Setup auth (run once, then whenever cf_clearance expires ~24h)
bash scripts/setup.sh <cf_clearance_value>

# Single keyword query
python3 scripts/semrush_query.py "invoice generator"

# Batch query → CSV
python3 scripts/semrush_query.py --batch keywords.txt --output results.csv

# Competitor backlink analysis
python3 scripts/semrush_query.py --backlinks invoice-generator.com
```

### Similarweb (fallback when Semrush quota runs out)

```bash
# First-time setup (cf_clearance + GMITM_token + GMITM_ec from sim.3ue.com cookies)
bash scripts/similarweb-setup.sh <cf_clearance> <GMITM_token> <GMITM_ec>

# Refresh only cf_clearance (every ~24h; token is valid ~3 days)
bash scripts/similarweb-setup.sh <cf_clearance>

# Single keyword — returns Vol/CPC/KD + zero-click rate + search intent
python3 scripts/similarweb_query.py "invoice generator"

# Batch → CSV (same format as Semrush output)
python3 scripts/similarweb_query.py --batch keywords.txt --output sw_results.csv
```

> ⚠️ sim.3ue.com uses a **different GMITM_token** from sem.3ue.com — they cannot be shared.

## Getting cf_clearance

1. Open **sem.3ue.com** in a browser and log in
2. Press F12 → Application → Cookies → `sem.3ue.com`
3. Copy the `cf_clearance` cookie value
4. Run `bash scripts/setup.sh <value>`

`cf_clearance` expires in ~24 hours. Just re-run setup to refresh it.

## SEO Methodology: 哥飞「站找词」

The built-in methodology for finding profitable keywords:

```
竞品站 → Top Pages → 提取主词
    ↓
semrush_query.py --batch
    ↓
自动过滤: Vol≥500 / KD≤40% / CPC≥$1
    ↓
SERP验证: 付费工具站 > 免费通用工具
    ↓
选主词 → 词集群 → 建站
```

### Why CPC matters most

CPC is the most direct signal of commercial value. A keyword with low KD but low CPC means advertisers don't bid on it — meaning users won't pay either. Focus on keywords where **advertisers spend money**.

## Keyword Filter Criteria

| Metric | Threshold | Why |
|--------|-----------|-----|
| Volume | ≥ 500/mo | Real traffic potential |
| KD | ≤ 40% | Can actually rank |
| CPC | ≥ $1 | Commercial intent (most important!) |

## File Structure

```
semrush-seo/
├── SKILL.md                  # OpenClaw skill instructions
├── README.md                 # This file
├── _meta.json                # Skill metadata
└── scripts/
    ├── semrush_query.py      # Semrush: keyword research + backlinks
    ├── setup.sh              # Semrush: auth setup (cf_clearance)
    ├── similarweb_query.py   # Similarweb: keyword research fallback
    └── similarweb-setup.sh   # Similarweb: auth setup (cf_clearance + GMITM)
```

## Requirements

- Python 3.6+ (stdlib only, no pip install needed)
- Access to sem.3ue.com (proxy account required)

## API Details

**Keyword endpoint:** `POST /kwogw/rpc` (JSON-RPC)
- `keywords.GetBulk` — batch Vol/KD/CPC/Competition
- `ideas.GetKeywords` — related keyword expansion
- `serp.GetURLs` — SERP competitor list

**Backlinks endpoint:** `GET /analytics/backlinks/webapi2/`
- Returns paginated backlink list with page_ascore, domain_ascore, anchor, source_url
- 100 records/page, client-side dofollow filtering

## License

MIT
