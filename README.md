# semrush-seo — OpenClaw Skill

> 🔍 Automated SEO keyword research & competitor backlink analysis via Semrush (sem.3ue.com proxy)

An [OpenClaw](https://openclaw.ai) skill that automates keyword research workflows using the Semrush API through sem.3ue.com proxy — no manual CSV exports required.

## Features

- **Keyword research** — query Vol / KD / CPC for any keyword (single or batch)
- **Related keyword expansion** — discover long-tail variations via `ideas.GetKeywords`
- **SERP analysis** — see who ranks for your target keywords
- **Competitor backlink analysis** — find the sites linking to competitors (= your future link-building targets)
- **Auto-filter** — marks keywords passing the 3-metric threshold: Vol≥500 + KD≤40% + CPC≥$1
- **CSV output** — batch queries export to CSV for easy review

## Quick Start

```bash
# 1. Setup auth (run once, then whenever cf_clearance expires ~24h)
bash scripts/setup.sh <cf_clearance_value>

# 2. Single keyword query
python3 scripts/semrush_query.py "invoice generator"

# 3. Batch query → CSV
python3 scripts/semrush_query.py --batch keywords.txt --output results.csv

# 4. Competitor backlink analysis
python3 scripts/semrush_query.py --backlinks invoice-generator.com
```

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
├── SKILL.md            # OpenClaw skill instructions
├── README.md           # This file
├── _meta.json          # Skill metadata
└── scripts/
    ├── semrush_query.py  # Main tool (Python 3, stdlib only)
    └── setup.sh          # Auth setup script
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
