#!/usr/bin/env python3
"""semrush_domain_organic_keywords.py

Automate Semrush UI: Organic Research → Organic Keywords (approx)

We currently use method `organic.PositionsOverview` observed from the Organic Research overview page.
It returns top organic positions/keywords for the domain with fields like:
  phrase, position, volume, cpc, keywordDifficulty, traffic, trafficPercent, intents, url

This is auditable: save raw JSON and parsed CSV.

NOTE: If we later capture the exact Organic Keywords list page RPC, we can swap the method to match
that table exactly. For now this provides a concrete, real, reproducible keyword list.
"""

import argparse
import csv
import json
import os
import re
import subprocess
import urllib.parse

CONFIG_FILE = os.path.expanduser("~/.semrush-config")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"


def load_cfg():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        text = open(CONFIG_FILE, "r", encoding="utf-8").read()
        for k in ["CF_CLEARANCE", "GMITM", "APIKEY", "TOKEN", "EC"]:
            m = re.search(rf"{k}='([^']+)'", text)
            if m:
                cfg[k] = m.group(1)
    return cfg


def make_cookie(cfg):
    gmitm_config = '{"semrush":{"node":"10","lang":"zh"},"similarweb":{"node":"1","lang":"zh-cn"}}'
    # keep compact; CF can be picky about cookie formatting
    return (
        "GMITM_lang=zh-Hans;"
        "GMITM_uname=Charlestaglia;"
        f"GMITM_config={gmitm_config};"
        f"GMITM_token={cfg['TOKEN']};"
        f"cf_clearance={cfg['CF_CLEARANCE']};"
        f"GMITM_ec={cfg['EC']}"
    )


def sh(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def rpc(cfg, payload: dict, referer: str):
    url = f"https://sem.3ue.com/dpa/rpc?__gmitm={urllib.parse.quote(cfg['GMITM'])}"
    cookie = make_cookie(cfg)
    body = json.dumps(payload, ensure_ascii=False)

    sec_ch_ua = 'sec-ch-ua: "Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"'
    sec_ch_platform = 'sec-ch-ua-platform: "macOS"'

    cmd = (
        "curl -s "
        + sh(url)
        + " -X POST "
        + "-H "
        + sh("accept: */*")
        + " "
        + "-H "
        + sh("accept-language: zh-CN,zh;q=0.9")
        + " "
        + "-H "
        + sh("content-type: application/json; charset=utf-8")
        + " "
        + "-H "
        + sh("origin: https://sem.3ue.com")
        + " "
        + "-H "
        + sh("referer: " + referer)
        + " "
        + "-H "
        + sh("user-agent: " + UA)
        + " "
        + "-H "
        + sh(sec_ch_ua)
        + " "
        + "-H "
        + sh("sec-ch-ua-mobile: ?0")
        + " "
        + "-H "
        + sh(sec_ch_platform)
        + " "
        + "-H "
        + sh("sec-fetch-dest: empty")
        + " "
        + "-H "
        + sh("sec-fetch-mode: cors")
        + " "
        + "-H "
        + sh("sec-fetch-site: same-origin")
        + " "
        + "-b "
        + sh(cookie)
        + " "
        + "--data-raw "
        + sh(body)
    )

    out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=40)
    txt = out.decode("utf-8", errors="ignore")
    if not txt.strip():
        raise RuntimeError("Empty response")
    return json.loads(txt)


def main():
    cfg = load_cfg()
    for k in ["CF_CLEARANCE", "GMITM", "APIKEY", "TOKEN", "EC"]:
        if k not in cfg or not cfg[k]:
            raise SystemExit(f"Missing {k} in ~/.semrush-config")

    ap = argparse.ArgumentParser()
    ap.add_argument("domain")
    ap.add_argument("--db", default="us")
    ap.add_argument("--date", type=int, required=True, help="Unix timestamp seconds (snapshot date)")
    ap.add_argument("--raw", default="")
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    payload = {
        "id": 11,
        "jsonrpc": "2.0",
        "method": "organic.PositionsOverview",
        "params": {
            "request_id": "demo",
            "report": "organic.overview",
            "args": {
                "database": args.db,
                "date": args.date,
                "dateType": "daily",
                "searchItem": args.domain,
                "searchType": "domain",
                "display": {"order": {"field": "trafficPercent", "direction": "desc"}},
                "positionsType": "all",
            },
            "apiKey": cfg["APIKEY"],
        },
    }

    referer = f"https://sem.3ue.com/analytics/organic/overview/?db={args.db}&q={urllib.parse.quote(args.domain)}&searchType=domain&date=20260227&__gmitm={urllib.parse.quote(cfg['GMITM'])}"

    data = rpc(cfg, payload, referer)

    if args.raw:
        os.makedirs(os.path.dirname(args.raw) or ".", exist_ok=True)
        with open(args.raw, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    rows = data.get("result", [])
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        fields = ["phrase", "position", "volume", "cpc", "keywordDifficulty", "traffic", "trafficPercent", "intents", "url"]
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in fields})

    print(f"domain={args.domain} rows={len(rows)}")


if __name__ == "__main__":
    main()
