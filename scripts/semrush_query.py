#!/usr/bin/env python3
"""
Semrush SEO 自动化工具 (sem.3ue.com API)
用法:
  python3 semrush_query.py "invoice generator"
  python3 semrush_query.py "invoice generator" --db uk
  python3 semrush_query.py --batch keywords.txt --output results.csv
  python3 semrush_query.py --backlinks invoice-generator.com
  python3 semrush_query.py --backlinks joist.app --bl-page 1
"""

import json
import sys
import os
import argparse
import csv
import time
import urllib.parse
import urllib.request
import urllib.error

# ============ 配置 ============
CONFIG_FILE = os.path.expanduser("~/.semrush-config")

def load_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    config[key.strip()] = val.strip().strip("'\"")
    return config

cfg = load_config()

CF_CLEARANCE = cfg.get("CF_CLEARANCE", "")
GMITM        = cfg.get("GMITM", "")
APIKEY       = cfg.get("APIKEY", "")
USERID       = int(cfg.get("USERID", "444444444"))
TOKEN        = cfg.get("TOKEN", "")
EC           = cfg.get("EC", "")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"

def make_cookie():
    return f"cf_clearance={CF_CLEARANCE}; GMITM_token={TOKEN}; GMITM_ec={EC}; GMITM_uname=Charlestaglia; GMITM_lang=zh-Hans"

# ============ 关键词 API（JSON-RPC）============

def sem_rpc(method, params, phrase="", db="us"):
    url = f"https://sem.3ue.com/kwogw/rpc?__gmitm={GMITM}"
    encoded = urllib.parse.quote(phrase)
    referer = f"https://sem.3ue.com/analytics/keywordoverview/?q={encoded}&db={db}&__gmitm={GMITM}"
    
    payload = json.dumps({"id": 1, "jsonrpc": "2.0", "method": method, "params": params}).encode()
    
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    req.add_header("Origin", "https://sem.3ue.com")
    req.add_header("Referer", referer)
    req.add_header("User-Agent", UA)
    req.add_header("Cookie", make_cookie())
    
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            if "error" in data:
                return None, data["error"]["message"]
            return data.get("result"), None
    except Exception as e:
        return None, str(e)

def bulk_query(phrases, db="us"):
    """批量查询多个关键词的完整指标 (Vol/CPC/KD/Competition/Trend)"""
    params = {
        "user_id": USERID,
        "api_key": APIKEY,
        "phrases": phrases,
        "database": db,
        "currency": "USD",
        "date": ""
    }
    results, err = sem_rpc("keywords.GetBulk", params, phrase=phrases[0] if phrases else "", db=db)
    if err:
        print(f"  ⚠️  GetBulk error: {err}", file=sys.stderr)
    return results or []

def query_keyword(phrase, db="us"):
    """查询单个关键词：相关词扩展 + SERP 竞品"""
    base_params = {
        "user_id": USERID,
        "api_key": APIKEY,
        "phrase": phrase,
        "database": db,
        "currency": "USD",
        "date": "",
        "device": 0,
        "location": 0
    }
    
    # 相关词 + Vol + KD
    ideas_params = {**base_params, "mode": 0, "questions_only": False}
    ideas, err = sem_rpc("ideas.GetKeywords", ideas_params, phrase=phrase, db=db)
    if err:
        print(f"  ⚠️  ideas.GetKeywords error: {err}", file=sys.stderr)
    
    # 用 GetBulk 补全 CPC
    if ideas:
        all_phrases = [r["phrase"] for r in ideas]
        bulk_results = bulk_query(all_phrases, db)
        bulk_map = {r["phrase"]: r for r in bulk_results}
        for idea in ideas:
            if idea["phrase"] in bulk_map:
                idea.update({k: v for k, v in bulk_map[idea["phrase"]].items() if v is not None})
    
    # SERP 竞品
    serp, err2 = sem_rpc("serp.GetURLs", base_params, phrase=phrase, db=db)
    if err2:
        print(f"  ⚠️  serp.GetURLs error: {err2}", file=sys.stderr)
    
    return ideas or [], serp or []

def print_results(phrase, ideas, serp):
    print(f"\n{'='*70}")
    print(f"🔍 关键词分析: {phrase}")
    print(f"{'='*70}")
    
    print(f"\n📊 相关词指标 (Vol + CPC + KD):")
    print(f"{'关键词':<42} {'月搜索量':>8} {'CPC':>7} {'KD':>5}  评级")
    print(f"{'-'*80}")
    
    qualifying = []
    for r in ideas:
        kw  = r.get("phrase", "")
        vol = r.get("volume", 0) or 0
        kd  = r.get("difficulty", 0) or 0
        cpc = r.get("cpc") or 0
        cpc_str = f"${cpc:.2f}" if cpc else "  N/A"
        
        if vol >= 500 and kd <= 40 and cpc >= 1:
            tag = "✅ 可做"
            qualifying.append(r)
        elif vol >= 500 and kd <= 40:
            tag = "⚠️  低CPC"
        elif vol >= 500 and kd <= 60:
            tag = "⚠️  竞争"
        elif vol < 500:
            tag = "❌ 量小"
        else:
            tag = "❌ KD高"
        
        print(f"{kw:<42} {vol:>8,} {cpc_str:>7} {kd:>5}%  {tag}")
    
    if qualifying:
        print(f"\n🎯 符合条件 (Vol≥500, KD≤40%, CPC≥$1):")
        for r in qualifying:
            cpc = r.get('cpc') or 0
            print(f"  → {r['phrase']} | Vol={r['volume']:,} | CPC=${cpc:.2f} | KD={r.get('difficulty',0)}%")
    
    print(f"\n🏆 SERP 竞品 TOP 10:")
    seen = set()
    count = 0
    for r in serp:
        domain = r.get("domain", "")
        if domain not in seen and count < 10:
            seen.add(domain)
            print(f"  #{r.get('position','?')} {domain}")
            count += 1

def batch_to_csv(keywords, db, output_file):
    """批量查询，输出 CSV"""
    keywords = [kw.strip() for kw in keywords if kw.strip()]
    BATCH_SIZE = 50
    all_results = {}
    
    for i in range(0, len(keywords), BATCH_SIZE):
        batch = keywords[i:i+BATCH_SIZE]
        print(f"批次 {i//BATCH_SIZE + 1}: 查询 {len(batch)} 个词...", flush=True)
        results = bulk_query(batch, db)
        for r in results:
            all_results[r["phrase"]] = r
        if i + BATCH_SIZE < len(keywords):
            time.sleep(0.3)
    
    rows = []
    for kw in keywords:
        r = all_results.get(kw, {})
        vol  = r.get("volume", 0) or 0
        kd   = r.get("difficulty", 0) or 0
        cpc  = r.get("cpc", 0) or 0
        comp = r.get("competition_level", 0) or 0
        rds  = r.get("rds_median", 0) or 0
        
        qualifies = "YES" if vol >= 500 and kd <= 40 and cpc >= 1 else "NO"
        row = {
            "keyword": kw, "volume": vol, "kd": kd,
            "cpc": f"{cpc:.2f}" if cpc else "",
            "competition": f"{comp:.2f}" if comp else "",
            "rds_median": rds, "qualifies": qualifies
        }
        rows.append(row)
        status = "✅" if qualifies == "YES" else "❌"
        print(f"  {status} {kw}: Vol={vol:,} CPC=${cpc:.2f} KD={kd}%")
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["keyword","volume","kd","cpc","competition","rds_median","qualifies"])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n✅ 结果已保存到: {output_file}")
    qualifying = [r for r in rows if r["qualifies"] == "YES"]
    print(f"📊 共 {len(rows)} 个词，{len(qualifying)} 个符合条件 (Vol≥500, KD≤40%, CPC≥$1)")
    if qualifying:
        print("\n🎯 符合条件的词:")
        for r in qualifying:
            print(f"  {r['keyword']}: Vol={r['volume']:,} CPC=${r['cpc']} KD={r['kd']}%")

# ============ 外链 API（GET /analytics/backlinks/webapi2/）============

def get_backlinks(domain, page=0, min_ascore=20, dofollow_only=True):
    """获取竞品域名的外链列表"""
    url = (
        f"https://sem.3ue.com/analytics/backlinks/webapi2/"
        f"?action=report&key={APIKEY}&type=backlinks"
        f"&target={urllib.parse.quote(domain)}&target_type=root_domain"
        f"&display_page={page}&sort_field=page_ascore&sort_type=desc"
        f"&__gmitm={GMITM}"
    )
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    req.add_header("Referer", f"https://sem.3ue.com/analytics/backlinks/?__gmitm={GMITM}")
    req.add_header("Cookie", make_cookie())
    
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            bl = data.get("backlinks", {})
            total   = bl.get("total", 0)
            results = bl.get("data", [])
            
            # 客户端过滤
            if dofollow_only:
                results = [r for r in results if not r.get("nofollow") and not r.get("ugc")]
            if min_ascore:
                results = [r for r in results if r.get("page_ascore", 0) >= min_ascore]
            
            return total, results
    except Exception as e:
        print(f"❌ 外链查询失败: {e}", file=sys.stderr)
        return 0, []

def print_backlinks(domain, total, results, page=0):
    print(f"\n{'='*70}")
    print(f"🔗 外链分析: {domain}  (总计 {total:,} 条，当前页 {page}，显示 {len(results)} 条)")
    print(f"{'='*70}")
    print(f"\n{'页AS':>5} {'域AS':>5}  {'位置':<9} {'锚文本':<25} 来源 URL")
    print(f"{'-'*80}")
    for r in results:
        pas    = r.get("page_ascore", 0)
        das    = r.get("domain_ascore", 0)
        pos    = str(r.get("position", ""))[:8]
        anchor = (r.get("anchor") or "")[:22]
        src    = (r.get("source_url") or "")[:55]
        print(f"{pas:>5} {das:>5}  {pos:<9} {anchor:<25} {src}")
    print(f"\n💡 提示：以上均为 dofollow 链接 (page_ascore≥20)")
    print(f"   这些来源站是建站后外链提交的优先目标")

# ============ 入口 ============

def main():
    if not CF_CLEARANCE:
        print("❌ 未配置 cf_clearance")
        print("   运行: bash setup.sh <cf_clearance值>")
        print("   获取: 浏览器打开 sem.3ue.com → F12 → Application → Cookies")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description="Semrush SEO 关键词 + 外链查询工具")
    parser.add_argument("keyword", nargs="?", help="单个关键词查询")
    parser.add_argument("--db", default="us", help="数据库地区 (默认: us)")
    parser.add_argument("--batch", metavar="FILE", help="批量查询文件（每行一个关键词）")
    parser.add_argument("--output", default="semrush_results.csv", help="CSV 输出文件")
    parser.add_argument("--backlinks", metavar="DOMAIN", help="竞品外链分析")
    parser.add_argument("--bl-page", type=int, default=0, metavar="N", help="外链分页 (0-based，每页100条)")
    
    args = parser.parse_args()
    
    if args.backlinks:
        print(f"🔍 查询外链: {args.backlinks} (页 {args.bl_page})...")
        total, results = get_backlinks(args.backlinks, page=args.bl_page)
        print_backlinks(args.backlinks, total, results, args.bl_page)
    elif args.batch:
        with open(args.batch) as f:
            keywords = [line.strip() for line in f if line.strip()]
        print(f"📦 批量查询 {len(keywords)} 个关键词...")
        batch_to_csv(keywords, args.db, args.output)
    elif args.keyword:
        ideas, serp = query_keyword(args.keyword, args.db)
        print_results(args.keyword, ideas, serp)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
