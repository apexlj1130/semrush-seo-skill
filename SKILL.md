---
name: semrush-seo
description: Automated SEO keyword research via Semrush + Similarweb (sem.3ue.com / sim.3ue.com proxies). Dual-layer design - Semrush for batch queries (~1500 keywords/day limit), Similarweb as fallback with zero-click rate data. Use when doing keyword research, competitor analysis, or building keyword lists for new sites.
homepage: https://github.com/apexlj1130/semrush-seo-skill
metadata: {"clawdbot":{"emoji":"🔍","requires":{"bins":["python3"]}}}
---

# semrush-seo

Automated keyword research and competitor analysis via Semrush (sem.3ue.com proxy).

## Setup（首次 / cf_clearance 过期后）

cf_clearance 每约 24 小时过期，需要从浏览器手动更新一次：

1. 浏览器打开 **sem.3ue.com** 并登录
2. F12 → Application → Cookies → 找 `cf_clearance` → 复制 Value
3. 运行：

```bash
bash {baseDir}/scripts/setup.sh <cf_clearance值>
```

配置保存到 `~/.semrush-config`（含 cf_clearance、GMITM_token、APIKey 等）。

---

## 1. 单词查询（相关词扩展 + SERP 竞品）

```bash
python3 {baseDir}/scripts/semrush_query.py "invoice generator"
python3 {baseDir}/scripts/semrush_query.py "invoice generator" --db uk
```

输出：
- 相关词列表（Vol / CPC / KD），自动标注 ✅可做 / ⚠️低CPC / ❌KD高
- SERP TOP10 竞品域名

---

## 2. 批量关键词查询（输出 CSV）

```bash
# 准备词库文件（每行一个词）
echo -e "invoice generator\nwork order template\npurchase order form" > keywords.txt

# 批量查询 → 自动筛选 + 输出 CSV
python3 {baseDir}/scripts/semrush_query.py --batch keywords.txt --output results.csv
```

CSV 字段：`keyword, volume, kd, cpc, competition, rds_median, qualifies`

`qualifies=YES` = Vol≥500 + KD≤40% + CPC≥$1（三合一过滤标准）

---

## 3. 竞品外链分析

```bash
python3 {baseDir}/scripts/semrush_query.py --backlinks invoice-generator.com
python3 {baseDir}/scripts/semrush_query.py --backlinks joist.app --bl-page 1
```

输出：按 page_ascore 排序的外链列表（source_url / anchor / AS分 / dofollow过滤）

用途：找到推荐竞品的目录站 → 建站后第一批外链提交目标

---

## Similarweb 备用层（Semrush 配额耗尽时）

> Semrush 限额约 **1500 词/天**。配额耗尽后切换 Similarweb。

### 首次设置 / TOKEN 过期时（约每3天）

```bash
# 从 sim.3ue.com 的 F12 → Application → Cookies 复制三个值：
bash {baseDir}/scripts/similarweb-setup.sh <cf_clearance> <GMITM_token> <GMITM_ec>

# 只刷新 cf_clearance（token 未过期时，每天一次）
bash {baseDir}/scripts/similarweb-setup.sh <cf_clearance>
```

⚠️ sim.3ue.com 的 `GMITM_token` 与 sem.3ue.com **不同，不可共用**

### 查询命令（与 Semrush 用法相同）

```bash
# 单词查询（Vol/CPC/KD/零点击率/搜索意图）
python3 {baseDir}/scripts/similarweb_query.py "invoice generator"

# 批量查询 → CSV
python3 {baseDir}/scripts/similarweb_query.py --batch keywords.txt --output sw_results.csv

# 域名 Top Pages（站找词）
python3 {baseDir}/scripts/similarweb_query.py --domain joist.app --top-pages
```

### 独有数据：零点击率

Similarweb 特有 `latestZeroClicks` 字段（如 32.5%），表示搜索后不点击任何结果的比例。
零点击率高 → 用户在搜索结果页直接得到答案 → 实际流量打折扣。

---

## 4. 哥飞「站找词」标准 SOP

**核心思路**：从已成功变现的竞品站反推关键词，天然有商业验证。

### 完整流程（每个新站）

1. **选竞品**：Similarweb 找同赛道月访问 10万+ 的站（3-5 个）
2. **扫词**：竞品 Semrush → Organic Research → Top Pages → 提取主词 → `--batch` 批量查询
3. **筛词**：`qualifies=YES`（Vol≥500 / KD≤40% / CPC≥$1）
4. **SERP 验证**：候选词逐一查 SERP，确认竞品是付费工具站（非免费通用工具）
5. **选主词**：1-3 个主词（优先 KD≤35%），构建词集群
6. **外链挖掘**：跑主词第 1 位竞品外链，找提交目标清单
7. **立项**：写可行性分析，入 Notion 月度建站看板

### 关键词过滤标准

| 指标 | 标准 | 说明 |
|------|------|------|
| Vol | ≥ 500 | 月搜索量，有真实流量基础 |
| KD | ≤ 40% | 关键词难度，打得进去 |
| CPC | ≥ $1 | 广告出价，**最关键的商业价值信号** |

> ⚠️ **重要教训**：CPC 是商业价值最直接信号。KD 低 ≠ 能赚钱。
> 低 CPC 词（如免费计算器类）变现天花板极低，不值得投入。

### SERP 信号判断

| 信号 | 判断 | 动作 |
|------|------|------|
| 主要是付费工具站（Rocket Lawyer、LegalZoom 等）| ✅ 好 | 继续推进 |
| 充斥免费通用工具 / 政府站 / 维基百科 | ❌ 坏 | 直接排除 |

---

## 5. 推荐竞品域名（承包商/文档工具赛道）

```
joist.app            invoicesimple.com      lawdepot.com
pandadoc.com         aidocmaker.com         invoice-generator.com
```

---

## API 端点（技术备忘）

- **关键词**：`POST https://sem.3ue.com/kwogw/rpc?__gmitm=<token>`
  - 方法：`keywords.GetBulk` / `ideas.GetKeywords` / `serp.GetURLs` / `clusters.Get`
- **外链**：`GET https://sem.3ue.com/analytics/backlinks/webapi2/?action=report&key=<APIKey>&target=<domain>...`
- **认证**：`cf_clearance`（24h）+ `GMITM_token`（7天）+ `APIKey`（长期）
