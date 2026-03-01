#!/usr/bin/env python3
"""semrush_domain_top_pages.py

Automate Semrush UI: Organic Research → Top Pages

Inputs:
  - domain (searchItem)
  - db (database, default: us)

Outputs:
  - raw JSON (verbatim Semrush response)
  - CSV with top pages metrics

Data source:
  https://sem.3ue.com/dpa/rpc?__gmitm=... JSON-RPC
  method: organic.PagesV2 (and optional organic.PagesTotalV2)

This script is intentionally "auditable": it can persist the raw response and
never invents numbers.
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
import subprocess
from datetime import datetime

CONFIG_FILE = os.path.expanduser("~/.semrush-config")
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
    # DPA endpoints appear to require these cookies.
    # Keep GMITM_config in the simplest stable form.
    token = cfg.get("TOKEN", "")
    ec = cfg.get("EC", "")
    cf = cfg.get("CF_CLEARANCE", "")
    if not (token and ec and cf):
        raise RuntimeError("Missing TOKEN/EC/CF_CLEARANCE in ~/.semrush-config")
    gmitm_config = '{"semrush":{"node":"10","lang":"zh"},"similarweb":{"node":"1","lang":"zh-cn"}}'
    # IMPORTANT: keep it as a single -b argument. Avoid spaces after ';' to reduce parsing edge cases.
    return (
        "GMITM_lang=zh-Hans;"
        "GMITM_uname=Charlestaglia;"
        f"GMITM_config={gmitm_config};"
        f"GMITM_token={token};"
        f"cf_clearance={cf};"
        f"GMITM_ec={ec}"
    )


def rpc_call(cfg, method, params, referer):
    """Use curl (HTTP/2) to avoid CF managed challenge edge cases."""
    gmitm = cfg.get("GMITM", "")
    if not gmitm:
        raise RuntimeError("Missing GMITM in ~/.semrush-config")

    url = f"https://sem.3ue.com/dpa/rpc?__gmitm={urllib.parse.quote(gmitm)}"

    payload = json.dumps({
        "id": 1,
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    })

    cookie = make_cookie(cfg)

    # NOTE: For reasons unclear, passing -b cookie via argv list occasionally yields empty body.
    # Using a single shell-quoted command has been stable with sem.3ue.com.
    def sh(s: str) -> str:
        return "'" + s.replace("'", "'\\''") + "'"

    sec_ch_ua = 'sec-ch-ua: "Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"'
    sec_ch_platform = 'sec-ch-ua-platform: "macOS"'

    cmd = (
        "curl -s " + sh(url) + " -X POST "
        + "-H " + sh("accept: */*") + " "
        + "-H " + sh("accept-language: zh-CN,zh;q=0.9") + " "
        + "-H " + sh("content-type: application/json; charset=utf-8") + " "
        + "-H " + sh("origin: https://sem.3ue.com") + " "
        + "-H " + sh("referer: " + referer) + " "
        + "-H " + sh("user-agent: " + UA) + " "
        + "-H " + sh(sec_ch_ua) + " "
        + "-H " + sh("sec-ch-ua-mobile: ?0") + " "
        + "-H " + sh(sec_ch_platform) + " "
        + "-H " + sh("sec-fetch-dest: empty") + " "
        + "-H " + sh("sec-fetch-mode: cors") + " "
        + "-H " + sh("sec-fetch-site: same-origin") + " "
        + "-b " + sh(cookie) + " "
        + "--data-raw " + sh(payload)
    )

    out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=40)
    body = out.decode("utf-8", errors="ignore").strip()
    if not body:
        raise RuntimeError("Empty response body (likely CF / auth issue)")

    data = json.loads(body)
    if "error" in data:
        raise RuntimeError(f"RPC error: {data['error']}")
    return data.get("result")


def get_latest_snapshot_date(cfg, db: str):
    apikey = cfg.get("APIKEY")
    params = {"database": db, "apiKey": apikey}
    # referer doesn't seem strict for this call, but keep it consistent.
    referer = f"https://sem.3ue.com/analytics/toppages/?db={db}&q=example.com&searchType=domain"
    result = rpc_call(cfg, "organic.SnapshotDates", params, referer)
    # observed: result is a list of unix timestamps (seconds)
    if isinstance(result, list) and result:
        # choose the max (latest)
        return int(max(result))
    raise RuntimeError(f"Unexpected SnapshotDates result: {str(result)[:200]}")


def main():
    cfg = load_config()

    parser = argparse.ArgumentParser(description="Semrush Organic Research → Top Pages (domain) via RPC")
    parser.add_argument("domain", help="Domain to query (e.g. invoicesimple.com)")
    parser.add_argument("--db", default="us", help="Semrush database (default: us)")
    parser.add_argument("--date", type=int, default=0, help="Unix timestamp (seconds). 0=auto latest snapshot")
    parser.add_argument("--page-size", type=int, default=100, help="Rows per page (default: 100)")
    parser.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    parser.add_argument("--raw", default="", help="Path to write raw JSON")
    parser.add_argument("--output", default="", help="Path to write CSV")

    args = parser.parse_args()

    date_ts = args.date or get_latest_snapshot_date(cfg, args.db)

    apikey = cfg.get("APIKEY")
    request_id = f"pm-{int(time.time())}"

    params = {
        "request_id": request_id,
        "report": "organic.pages",
        "args": {
            "database": args.db,
            "searchItem": args.domain,
            "searchType": "domain",
            "date": date_ts,
            "dateType": "daily",
            "filter": {},
            "display": {
                "order": {"field": "traffic", "direction": "desc"},
                "page": args.page,
                "pageSize": args.page_size,
            },
        },
        "apiKey": apikey,
    }

    referer = f"https://sem.3ue.com/analytics/toppages/?db={args.db}&q={urllib.parse.quote(args.domain)}&searchType=domain&date={datetime.utcfromtimestamp(date_ts).strftime('%Y%m%d')}&__gmitm={urllib.parse.quote(cfg.get('GMITM',''))}"

    result = rpc_call(cfg, "organic.PagesV2", params, referer)

    if args.raw:
        os.makedirs(os.path.dirname(args.raw) or ".", exist_ok=True)
        with open(args.raw, "w", encoding="utf-8") as f:
            json.dump({"domain": args.domain, "db": args.db, "date": date_ts, "result": result}, f, ensure_ascii=False)

    rows = result if isinstance(result, list) else []

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "url",
                    "traffic",
                    "trafficPercent",
                    "positions",
                    "changeOfTrafficSigned",
                    "intentNavigationalTraffic",
                    "intentInformationalTraffic",
                    "intentCommercialTraffic",
                    "intentTransactionalTraffic",
                    "adwordsPositions",
                ],
            )
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k, "") for k in writer.fieldnames})

    # Print minimal stdout summary (no invented numbers; directly from response)
    print(f"domain={args.domain} db={args.db} date={date_ts} rows={len(rows)}")
    if rows:
        top = rows[0]
        print(f"top_url={top.get('url')} traffic={top.get('traffic')} trafficPercent={top.get('trafficPercent')}")


if __name__ == "__main__":
    main()
