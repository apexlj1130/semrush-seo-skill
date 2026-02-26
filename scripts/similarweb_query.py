#!/usr/bin/env python3
"""
Similarweb 关键词研究工具 — 通过 sim.3ue.com 代理
用途：Semrush 配额用完时的备用数据源，也可做交叉验证

数据来源：/api/KeywordGenerator/google/suggest
返回字段：monthlyVolume / cpc / difficulty / latestZeroClicks / primaryIntent / volumeTrend

配置文件：~/.similarweb-config  (cf_clearance + aws-waf-token 每次登录需刷新)

用法：
  python3 similarweb_query.py "invoice generator"
  python3 similarweb_query.py --batch keywords.txt --output results.csv
  python3 similarweb_query.py --domain joist.app           # 域名流量概览
  python3 similarweb_query.py --domain joist.app --top-pages  # Top Pages（站找词）
"""

import argparse, csv, gzip, json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime

# ─── 配置 ──────────────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.expanduser("~/.similarweb-config")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print("❌ 未找到 ~/.similarweb-config\n   请运行: bash similarweb-setup.sh <cf_clearance> <aws_waf_token>")
        sys.exit(1)
    cfg = {}
    with open(CONFIG_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                cfg[k.strip()] = v.strip().strip("'\"")
    return cfg

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
BASE = "https://sim.3ue.com"

def make_cookie(cfg):
    parts = [
        f"cf_clearance={cfg.get('CF_CLEARANCE','')}",
        f"GMITM_token={cfg.get('TOKEN','')}",
        f"GMITM_ec={cfg.get('EC','')}",
        f"GMITM_uname={cfg.get('UNAME','Charlestaglia')}",
        "GMITM_lang=zh-Hans",
        "locale=zh-cn",
    ]
    if cfg.get('AWS_WAF'):
        parts.append(f"aws-waf-token={cfg['AWS_WAF']}")
    if cfg.get('SGID'):
        parts.append(f"sgID={cfg['SGID']}")
    return "; ".join(parts)

def get_headers(cfg, referer="https://sim.3ue.com/"):
    return {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://sim.3ue.com",
        "Referer": referer,
        "Cookie": make_cookie(cfg),
    }

def current_month_range():
    """返回 (from_param, to_param) 格式 YYYY|MM|01 (URL 中 | 需编码为 %7C)"""
    now = datetime.now()
    from_p = f"{now.year}|01|01"
    to_p   = f"{now.year}|{now.month:02d}|01"
    return from_p, to_p

def do_request(url, cfg, method="POST", referer=None):
    headers = get_headers(cfg, referer or BASE + "/")
    body = b"" if method == "POST" else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            if not raw:
                return None, "空响应（cookie可能已过期）"
            # 自动解压 gzip
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            return json.loads(raw), None
    except Exception as e:
        return None, str(e)

# ─── 关键词研究（核心功能）──────────────────────────────────────────────────────

def query_keyword(keyword, cfg, country="999", rows=50):
    """
    查询单个关键词：返回 monthlyVolume / cpc / difficulty / latestZeroClicks 等
    endpoint: POST /api/KeywordGenerator/google/suggest
    """
    from_p, to_p = current_month_range()
    params = urllib.parse.urlencode({
        "keyword": keyword,
        "country": country,
        "from": from_p,
        "to": to_p,
        "isWindow": "false",
        "webSource": "Total",
        "rowsPerPage": rows,
        "asc": "false",
        "sort": "score",
        "type": "Related",
    })
    url = f"{BASE}/api/KeywordGenerator/google/suggest?{params}"
    referer = f"{BASE}/keyword-research/keyword-generator?keyword={urllib.parse.quote(keyword)}"
    data, err = do_request(url, cfg, method="POST", referer=referer)
    return data, err

def batch_query(keywords, cfg, output_file, min_vol=500, max_kd=40, min_cpc=1.0):
    """批量查询关键词，输出 CSV"""
    rows = []
    for i, kw in enumerate(keywords):
        kw = kw.strip()
        if not kw:
            continue
        data, err = query_keyword(kw, cfg)
        if (err or not data) and "502" in str(err):
            time.sleep(2)
            data, err = query_keyword(kw, cfg)  # 重试一次
        if err or not data:
            print(f"  ⚠️  {kw}: {err or '空响应'}")
            rows.append({"keyword": kw, "volume": 0, "kd": 0, "cpc": 0, "zero_click": "", "intent": "", "leading_site": "", "qualifies": "ERROR"})
            time.sleep(1)
            continue

        records = data.get("records", [])
        # 找精确匹配的记录（第一条通常是种子词本身）
        rec = next((r for r in records if r.get("keyword","").lower() == kw.lower()), records[0] if records else {})

        vol    = rec.get("monthlyVolume", 0) or 0
        kd     = rec.get("difficulty", 0) or 0
        cpc    = rec.get("cpc", 0) or 0
        zc     = rec.get("latestZeroClicks", 0) or 0
        intent = rec.get("primaryIntent", "")
        lsite  = rec.get("leadingSite", "")

        qualifies = "YES" if vol >= min_vol and kd <= max_kd and cpc >= min_cpc else "NO"
        status = "✅" if qualifies == "YES" else "❌"
        print(f"  {status} {kw}: Vol={int(vol):,} KD={kd} CPC=${cpc:.2f} ZC={zc:.0%} [{intent}]")

        rows.append({
            "keyword": kw, "volume": int(vol), "kd": kd,
            "cpc": f"{cpc:.2f}", "zero_click": f"{zc:.1%}",
            "intent": intent, "leading_site": lsite, "qualifies": qualifies
        })

        if i < len(keywords) - 1:
            time.sleep(0.5)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["keyword","volume","kd","cpc","zero_click","intent","leading_site","qualifies"])
        writer.writeheader()
        writer.writerows(rows)

    qualifying = [r for r in rows if r["qualifies"] == "YES"]
    print(f"\n✅ 已保存: {output_file}")
    print(f"📊 共 {len(rows)} 词，{len(qualifying)} 个符合条件 (Vol≥{min_vol} KD≤{max_kd}% CPC≥${min_cpc})")
    if qualifying:
        print("\n🎯 符合条件:")
        for r in qualifying:
            print(f"  {r['keyword']}: Vol={r['volume']:,} KD={r['kd']} CPC=${r['cpc']} ZC={r['zero_click']}")

def print_keyword_result(keyword, data, err):
    if err or not data:
        print(f"❌ 查询失败: {err or '空响应'}\n   → 可能 cf_clearance 或 aws-waf-token 已过期\n   → 运行: bash similarweb-setup.sh <cf_clearance> <aws_waf_token>")
        return

    records = data.get("records", [])
    print(f"\n{'='*65}")
    print(f"🔍 Similarweb 关键词: {keyword}")
    print(f"{'='*65}")
    print(f"{'关键词':<40} {'月搜索量':>9} {'CPC':>7} {'KD':>5} {'零点击':>7}  意图      评级")
    print("-"*90)

    qualifying = []
    for r in records[:30]:
        kw     = r.get("keyword","")
        vol    = r.get("monthlyVolume", 0) or 0
        cpc    = r.get("cpc", 0) or 0
        kd     = r.get("difficulty", 0) or 0
        zc     = r.get("latestZeroClicks", 0) or 0
        intent = (r.get("primaryIntent","") or "")[:10]

        if vol >= 500 and kd <= 40 and cpc >= 1:
            tag = "✅ 可做"
            qualifying.append(r)
        elif vol >= 500 and kd <= 40:
            tag = "⚠️  低CPC"
        elif vol < 500:
            tag = "❌ 量小"
        elif kd > 40:
            tag = "❌ KD高"
        else:
            tag = "—"

        cpc_str = f"${cpc:.2f}" if cpc else " N/A"
        print(f"{kw:<40} {int(vol):>9,} {cpc_str:>7} {kd:>5} {zc:>7.1%}  {intent:<10}  {tag}")

    if qualifying:
        print(f"\n🎯 符合条件 (Vol≥500, KD≤40%, CPC≥$1):")
        for r in qualifying:
            print(f"  → {r['keyword']} | Vol={int(r['monthlyVolume']):,} | CPC=${r['cpc']:.2f} | KD={r['difficulty']} | ZeroClick={r.get('latestZeroClicks',0):.1%}")

# ─── 域名分析（站找词辅助功能）──────────────────────────────────────────────────

def get_domain_data(domain, cfg, endpoint, referer=None):
    url = f"{BASE}{endpoint}"
    ref = referer or f"{BASE}/website/{domain}/overview"
    data, err = do_request(url, cfg, method="GET", referer=ref)
    return data, err

def domain_overview(domain, cfg):
    """域名流量概览"""
    now = datetime.now()
    start = f"{now.year-1}-{now.month:02d}"
    end   = f"{now.year}-{now.month:02d}"
    path = f"/api/website/{domain}/total-traffic-and-engagement/visits?country=world&granularity=monthly&main_domain_only=false&startDate={start}&endDate={end}&includeSubDomains=true"
    return get_domain_data(domain, cfg, path)

def domain_top_pages(domain, cfg):
    """Top Pages（站找词核心）"""
    now = datetime.now()
    end   = f"{now.year}-{now.month:02d}"
    start = f"{now.year}-{(now.month-3)%12 + 1:02d}"
    path = f"/api/website/{domain}/web-content/top-pages?startDate={start}&endDate={end}&country=world&main_domain_only=false&includeSubDomains=false&page=1&pageSize=30"
    return get_domain_data(domain, cfg, path)

def domain_competitors(domain, cfg):
    """竞品域名（站找站）"""
    now = datetime.now()
    end   = f"{now.year}-{now.month:02d}"
    start = f"{now.year}-{(now.month-3)%12 + 1:02d}"
    path = f"/api/website/{domain}/competitors/organic?country=world&startDate={start}&endDate={end}&main_domain_only=false"
    return get_domain_data(domain, cfg, path)

# ─── 入口 ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Similarweb 关键词研究 + 域名分析（Semrush 备用层）")
    parser.add_argument("keyword",   nargs="?",          help="单个关键词查询")
    parser.add_argument("--batch",   metavar="FILE",     help="批量查询文件（每行一个关键词）")
    parser.add_argument("--output",  default="sw_results.csv", help="CSV 输出路径")
    parser.add_argument("--country", default="999",      help="国家代码（默认999=全球，840=美国）")
    parser.add_argument("--domain",  metavar="DOMAIN",   help="域名流量分析")
    parser.add_argument("--top-pages", action="store_true", help="获取域名 Top Pages（需配合--domain）")
    parser.add_argument("--competitors", action="store_true", help="获取竞品域名（需配合--domain）")
    parser.add_argument("--raw",     action="store_true", help="输出原始 JSON（调试用）")
    args = parser.parse_args()

    cfg = load_config()

    if not cfg.get("CF_CLEARANCE"):
        print("❌ 未配置 cf_clearance\n   运行: bash similarweb-setup.sh <cf_clearance> <aws_waf_token>")
        sys.exit(1)

    # 域名分析模式
    if args.domain:
        domain = args.domain.replace("https://","").replace("http://","").strip("/")
        if args.top_pages:
            print(f"📄 Top Pages: {domain}")
            data, err = domain_top_pages(domain, cfg)
        elif args.competitors:
            print(f"🏆 竞品分析: {domain}")
            data, err = domain_competitors(domain, cfg)
        else:
            print(f"📊 域名概览: {domain}")
            data, err = domain_overview(domain, cfg)

        if err or not data:
            print(f"❌ 失败: {err or '空响应'}")
        elif args.raw:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        return

    # 关键词模式
    if args.batch:
        with open(args.batch) as f:
            keywords = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        print(f"📦 批量查询 {len(keywords)} 个关键词（Similarweb）...")
        batch_query(keywords, cfg, args.output)
    elif args.keyword:
        data, err = query_keyword(args.keyword, cfg, country=args.country)
        if args.raw:
            print(json.dumps(data, indent=2, ensure_ascii=False) if data else f"错误: {err}")
        else:
            print_keyword_result(args.keyword, data, err)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
