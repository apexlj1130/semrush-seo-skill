#!/bin/bash
# Similarweb sim.3ue.com 认证配置脚本
#
# 用法: bash similarweb-setup.sh <cf_clearance> <GMITM_token> <GMITM_ec>
#
# ⚠️ sim.3ue.com 的 GMITM_token 和 sem.3ue.com 的不同，不能共用！
#
# 获取步骤（三个值都从 sim.3ue.com 的 Cookie 里拿）：
#   1. 浏览器打开 sim.3ue.com 并登录
#   2. 搜索任意关键词（如 invoice generator）
#   3. F12 → Application → Cookies → sim.3ue.com
#   4. 复制以下三个值：
#      - cf_clearance  （约24h有效）
#      - GMITM_token   （约3天有效）
#      - GMITM_ec      （约3天有效）

set -e

CF_CLEARANCE="${1:-}"
SW_TOKEN="${2:-}"
SW_EC="${3:-}"

if [ -z "$CF_CLEARANCE" ]; then
    echo "用法: bash similarweb-setup.sh <cf_clearance> [GMITM_token] [GMITM_ec]"
    echo ""
    echo "获取步骤:"
    echo "  1. 浏览器打开 sim.3ue.com 登录"
    echo "  2. 搜索一个关键词（触发 API 调用）"
    echo "  3. F12 → Application → Cookies → sim.3ue.com"
    echo "  4. 复制 cf_clearance、GMITM_token、GMITM_ec 的值"
    echo ""
    echo "⚠️  GMITM_token 和 GMITM_ec 约3天有效（比 cf_clearance 长）"
    echo "   只有 cf_clearance 过期时，可以只更新第一个参数"
    exit 1
fi

# 如果没有提供新的 TOKEN/EC，从现有配置读取（只刷新 cf_clearance）
CONFIG_FILE="$HOME/.similarweb-config"
if [ -z "$SW_TOKEN" ] && [ -f "$CONFIG_FILE" ]; then
    SW_TOKEN=$(grep "^TOKEN=" "$CONFIG_FILE" | cut -d= -f2- | tr -d "'\"")
    SW_EC=$(grep "^EC=" "$CONFIG_FILE" | cut -d= -f2- | tr -d "'\"")
    echo "ℹ️  TOKEN/EC 未变，只更新 cf_clearance"
fi

cat > "$CONFIG_FILE" << EOF
# Similarweb sim.3ue.com 认证配置
# 生成时间: $(date)
# cf_clearance: 约24h，GMITM_token/ec: 约3天
# ⚠️ 与 ~/.semrush-config 是独立的不同账号
CF_CLEARANCE='${CF_CLEARANCE}'
TOKEN='${SW_TOKEN}'
EC='${SW_EC}'
UNAME='Charlestaglia'
EOF

chmod 600 "$CONFIG_FILE"
echo "✅ 配置已保存到 $CONFIG_FILE"
echo ""

# 测试连通性
echo "🔗 测试连通性..."
RESULT=$(python3 /root/.openclaw/workspace/agents/pm/scripts/similarweb_query.py "test" 2>&1)

if echo "$RESULT" | grep -q "monthlyVolume\|月搜索量\|条记录\|查询失败\|Vol="; then
    echo "✅ 连通成功！"
    echo ""
    echo "示例命令:"
    echo "  python3 similarweb_query.py \"invoice generator\""
    echo "  python3 similarweb_query.py --batch keywords.txt --output sw_results.csv"
    echo "  python3 similarweb_query.py --domain joist.app --top-pages"
else
    echo "⚠️  返回内容:"
    echo "$RESULT" | head -5
fi
