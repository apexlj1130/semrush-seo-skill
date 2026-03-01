#!/usr/bin/env python3
"""similarweb_similar_sites.py

哥飞四象限之「站找站」：给定域名 → 返回相似站点列表

Endpoint: GET https://sim.3ue.com/api/WebsiteOverview/getsimilarsites
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.parse
import uuid

CONFIG_FILE = os.path.expanduser("~/.similarweb-config")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"


def load_config():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    cfg[k.strip()] = v.strip().strip("'\"")
    return cfg


def make_cookie(cfg):
    token = cfg.get("TOKEN", "")
    ec = cfg.get("EC", "")
    cf = cfg.get("CF_CLEARANCE", "")
    aws_waf = cfg.get("AWS_WAF_TOKEN", "")
    sgid = cfg.get("SGID", "4785eea1-e808-43f7-92a3-4c9ed00c9712")
    
    gmitm_config = '{"semrush":{"node":"10","lang":"zh"},"similarweb":{"node":"1","lang":"zh-cn"}}'
    
    parts = [
        "GMITM_lang=zh-Hans",
        f"GMITM_uname={cfg.get('UNAME', 'Charlestaglia')}",
        f"GMITM_config={gmitm_config}",
        f"GMITM_token={token}",
        "locale@similarweb.com=zh-cn",
        f"cf_clearance={cf}",
        f"sgID@similarweb.com={sgid}",
    ]
    
    if aws_waf:
        parts.append(f"aws-waf-token@pro.similarweb.com={aws_waf}")
    if ec:
        parts.append(f"GMITM_ec={ec}")
    
    return "; ".join(parts)


def sh(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def get_similar_sites(cfg, domain: str, limit: int = 20, country: int = 999):
    url = (
        f"https://sim.3ue.com/api/WebsiteOverview/getsimilarsites"
        f"?key={urllib.parse.quote(domain)}"
        f"&limit={limit}"
        f"&country={country}"
        f"&webSource=Total"
    )
    
    cookie = make_cookie(cfg)
    page_view_id = str(uuid.uuid4())
    sw_page = f"https://pro.similarweb.com/#/digitalsuite/websiteanalysis/overview/competitive-landscape/*/999/3m?key={domain}"
    
    cmd = (
        "curl -s " + sh(url) + " "
        "-H " + sh("accept: application/json") + " "
        "-H " + sh("content-type: application/json; charset=utf-8") + " "
        "-H " + sh("x-requested-with: XMLHttpRequest") + " "
        "-H " + sh(f"x-sw-page: {sw_page}") + " "
        "-H " + sh(f"x-sw-page-view-id: {page_view_id}") + " "
        "-H " + sh("referer: https://sim.3ue.com/") + " "
        "-H " + sh("user-agent: " + UA) + " "
        "-H " + sh('sec-ch-ua: "Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"') + " "
        "-H " + sh("sec-ch-ua-mobile: ?0") + " "
        "-H " + sh('sec-ch-ua-platform: "macOS"') + " "
        "-H " + sh("sec-fetch-dest: empty") + " "
        "-H " + sh("sec-fetch-mode: cors") + " "
        "-H " + sh("sec-fetch-site: same-origin") + " "
        "-b " + sh(cookie)
    )
    
    out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
    body = out.decode("utf-8", errors="ignore").strip()
    
    if not body:
        raise RuntimeError("Empty response")
    if "<!DOCTYPE html>" in body or "<html" in body.lower():
        raise RuntimeError("CF challenge detected - refresh cf_clearance")
    
    return json.loads(body)


def main():
    cfg = load_config()
    if not cfg:
        print("ERROR: ~/.similarweb-config not found.", file=sys.stderr)
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description="Similarweb Similar Sites (站找站)")
    parser.add_argument("domain", nargs="?", help="Domain to query")
    parser.add_argument("--batch", help="File with domains (one per line)")
    parser.add_argument("--limit", type=int, default=20, help="Max similar sites")
    parser.add_argument("--country", type=int, default=999, help="Country code (999=worldwide)")
    parser.add_argument("--raw", default="", help="Path to write raw JSON")
    parser.add_argument("--output", default="", help="Path to write CSV")
    
    args = parser.parse_args()
    
    domains = []
    if args.batch:
        with open(args.batch, "r", encoding="utf-8") as f:
            domains = [line.strip() for line in f if line.strip()]
    elif args.domain:
        domains = [args.domain]
    else:
        parser.error("Either domain or --batch required")
    
    all_results = []
    all_rows = []
    
    for domain in domains:
        try:
            result = get_similar_sites(cfg, domain, args.limit, args.country)
            all_results.append({"source_domain": domain, "result": result})
            
            sites = result if isinstance(result, list) else result.get("SimilarSites", [])
            for site in sites:
                row = {
                    "source_domain": domain,
                    "similar_domain": site.get("Domain", ""),
                    "rank": site.get("Rank", ""),
                }
                all_rows.append(row)
            
            print(f"✓ {domain}: {len(sites)} similar sites")
            time.sleep(0.3)
            
        except Exception as e:
            print(f"✗ {domain}: {e}", file=sys.stderr)
            all_results.append({"source_domain": domain, "error": str(e)})
    
    if args.raw:
        os.makedirs(os.path.dirname(args.raw) or ".", exist_ok=True)
        with open(args.raw, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"Raw JSON: {args.raw}")
    
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        fields = ["source_domain", "similar_domain", "rank"]
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"CSV: {args.output} ({len(all_rows)} rows)")
    
    print(f"\nTotal: {len(domains)} domains → {len(all_rows)} similar sites")


if __name__ == "__main__":
    main()
