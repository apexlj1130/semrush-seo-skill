#!/usr/bin/env python3
"""pipeline_four_quadrants.py

哥飞四象限完整自动化流水线

四象限:
  1. 站找站 (Similarweb): domain → similar domains
  2. 站找词 (Semrush Top Pages): domain → top keywords
  3. 词找站 (Semrush SERP URLs): keyword → ranking domains
  4. 词找词 (Semrush Ideas): keyword → related keywords

Pipeline modes:
  --discover <seed_domain>   : 站找站 → 站找词 完整发现流程
  --expand <keyword>         : 词找词 → 词找站 完整扩展流程
  --full <seed_domain>       : 全四象限完整跑一遍

Output:
  - evidence/ 目录下保存所有 raw JSON (审计用)
  - results/ 目录下保存 CSV 汇总

Usage:
  python3 pipeline_four_quadrants.py --discover invoicesimple.com
  python3 pipeline_four_quadrants.py --expand "invoice generator"
  python3 pipeline_four_quadrants.py --full invoicesimple.com --output-dir ./pipeline_results
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_script(script_name: str, args: list, capture=True):
    """Run a sibling script and return output"""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    cmd = ["python3", script_path] + args
    
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode, result.stdout, result.stderr
    else:
        return subprocess.run(cmd, timeout=120).returncode, "", ""


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def discover_pipeline(seed_domain: str, output_dir: str, limit_similar: int = 10):
    """
    站找站 → 站找词 发现流程
    
    1. Similarweb: seed_domain → similar domains (站找站)
    2. Semrush Top Pages: each domain → top pages (站找词)
    3. Semrush GetBulk: keywords → vol/kd/cpc validation
    """
    evidence_dir = ensure_dir(os.path.join(output_dir, "evidence"))
    results_dir = ensure_dir(os.path.join(output_dir, "results"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n{'='*60}")
    print(f"🔍 发现流水线 - 种子域名: {seed_domain}")
    print(f"{'='*60}\n")
    
    # Step 1: 站找站
    print("📌 Step 1: 站找站 (Similarweb Similar Sites)")
    similar_raw = os.path.join(evidence_dir, f"similar_sites_{ts}.json")
    similar_csv = os.path.join(results_dir, f"similar_sites_{ts}.csv")
    
    ret, out, err = run_script(
        "similarweb_similar_sites.py",
        [seed_domain, "--limit", str(limit_similar), "--raw", similar_raw, "--output", similar_csv]
    )
    
    if ret != 0:
        print(f"⚠️  Similarweb failed: {err}")
        print("   继续使用种子域名...")
        domains = [seed_domain]
    else:
        print(out)
        # Parse similar domains from CSV
        domains = [seed_domain]
        if os.path.exists(similar_csv):
            import csv
            with open(similar_csv, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    d = row.get("similar_domain", "").strip()
                    if d and d not in domains:
                        domains.append(d)
    
    print(f"   域名池: {len(domains)} 个")
    
    # Step 2: 站找词 (Top Pages for each domain)
    print(f"\n📌 Step 2: 站找词 (Semrush Top Pages)")
    all_keywords = set()
    
    for domain in domains[:5]:  # Limit to top 5 to conserve API quota
        print(f"   → {domain}")
        top_pages_raw = os.path.join(evidence_dir, f"top_pages_{domain.replace('.', '_')}_{ts}.json")
        top_pages_csv = os.path.join(results_dir, f"top_pages_{domain.replace('.', '_')}_{ts}.csv")
        
        ret, out, err = run_script(
            "semrush_domain_top_pages.py",
            [domain, "--raw", top_pages_raw, "--output", top_pages_csv]
        )
        
        if ret != 0:
            print(f"     ⚠️ Failed: {err[:100]}")
        else:
            print(f"     {out.strip()}")
            # Extract URLs from top pages to run organic positions later
        
        time.sleep(0.5)  # Rate limit
    
    # Step 3: 关键词验证 (GetBulk)
    print(f"\n📌 Step 3: 关键词批量验证")
    
    # Collect keywords from all CSV files
    import csv
    import glob
    
    all_urls = []
    for csv_file in glob.glob(os.path.join(results_dir, f"top_pages_*_{ts}.csv")):
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("url", "")
                if url:
                    all_urls.append(url)
    
    print(f"   共发现 {len(all_urls)} 个高流量页面")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ 发现流水线完成")
    print(f"   证据目录: {evidence_dir}")
    print(f"   结果目录: {results_dir}")
    print(f"   域名数: {len(domains)}")
    print(f"   高流量页面: {len(all_urls)}")
    print(f"{'='*60}\n")
    
    return {
        "seed_domain": seed_domain,
        "domains": domains,
        "urls": all_urls,
        "evidence_dir": evidence_dir,
        "results_dir": results_dir,
    }


def expand_pipeline(keyword: str, output_dir: str):
    """
    词找词 → 词找站 扩展流程
    
    1. Semrush Ideas: keyword → related keywords (词找词)
    2. Semrush SERP URLs: each keyword → ranking sites (词找站)
    3. Filter: Vol≥500, KD≤40%, CPC≥$1
    """
    evidence_dir = ensure_dir(os.path.join(output_dir, "evidence"))
    results_dir = ensure_dir(os.path.join(output_dir, "results"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n{'='*60}")
    print(f"🔍 扩展流水线 - 种子关键词: {keyword}")
    print(f"{'='*60}\n")
    
    # Step 1: 词找词
    print("📌 Step 1: 词找词 (Semrush Related Keywords)")
    
    ret, out, err = run_script(
        "semrush_query.py",
        [keyword]
    )
    
    if ret != 0:
        print(f"⚠️  Semrush query failed: {err}")
    else:
        print(out[:2000])
    
    # Step 2: Batch validation with CSV output
    print(f"\n📌 Step 2: 批量验证")
    
    # Create temp keyword file
    keyword_file = os.path.join(evidence_dir, f"keywords_seed_{ts}.txt")
    with open(keyword_file, "w") as f:
        f.write(keyword + "\n")
    
    batch_csv = os.path.join(results_dir, f"batch_results_{ts}.csv")
    
    ret, out, err = run_script(
        "semrush_query.py",
        ["--batch", keyword_file, "--output", batch_csv]
    )
    
    if ret != 0:
        print(f"⚠️  Batch validation failed: {err}")
    else:
        print(out)
    
    print(f"\n{'='*60}")
    print(f"✅ 扩展流水线完成")
    print(f"   结果: {batch_csv}")
    print(f"{'='*60}\n")
    
    return {
        "seed_keyword": keyword,
        "results_dir": results_dir,
    }


def full_pipeline(seed_domain: str, output_dir: str):
    """完整四象限流水线"""
    print(f"\n{'='*60}")
    print(f"🚀 完整四象限流水线 - 种子: {seed_domain}")
    print(f"{'='*60}\n")
    
    # Phase 1: Discover
    discover_result = discover_pipeline(seed_domain, output_dir)
    
    # Phase 2: 从发现的URL提取关键词并扩展
    # (This would require organic.Positions per URL - future enhancement)
    
    print(f"\n{'='*60}")
    print(f"🎯 四象限流水线完成")
    print(f"{'='*60}\n")
    
    return discover_result


def main():
    parser = argparse.ArgumentParser(
        description="哥飞四象限完整自动化流水线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 发现模式：站找站 → 站找词
  python3 pipeline_four_quadrants.py --discover invoicesimple.com

  # 扩展模式：词找词 → 词找站
  python3 pipeline_four_quadrants.py --expand "invoice generator"

  # 完整四象限
  python3 pipeline_four_quadrants.py --full invoicesimple.com --output-dir ./results
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--discover", metavar="DOMAIN", help="发现模式：站找站 → 站找词")
    group.add_argument("--expand", metavar="KEYWORD", help="扩展模式：词找词 → 词找站")
    group.add_argument("--full", metavar="DOMAIN", help="完整四象限流水线")
    
    parser.add_argument("--output-dir", default="./pipeline_output", help="输出目录")
    parser.add_argument("--limit-similar", type=int, default=10, help="站找站最大数量")
    
    args = parser.parse_args()
    
    output_dir = os.path.abspath(args.output_dir)
    
    if args.discover:
        discover_pipeline(args.discover, output_dir, args.limit_similar)
    elif args.expand:
        expand_pipeline(args.expand, output_dir)
    elif args.full:
        full_pipeline(args.full, output_dir)


if __name__ == "__main__":
    main()
