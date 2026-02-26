#!/bin/bash
# setup.sh - 保存 Semrush (sem.3ue.com) 认证配置
#
# 用法: bash setup.sh <cf_clearance_value>
#
# 获取 cf_clearance:
#   1. 浏览器打开 sem.3ue.com 并登录
#   2. F12 → Application → Cookies → https://sem.3ue.com
#   3. 找 cf_clearance 行，复制 Value

set -e

CONFIG_FILE="$HOME/.semrush-config"

CF_CLEARANCE="${1:-}"
if [ -z "$CF_CLEARANCE" ]; then
  echo "❌ 用法: $0 <cf_clearance_value>"
  echo ""
  echo "获取步骤:"
  echo "  1. 浏览器打开 sem.3ue.com 并登录"
  echo "  2. F12 → Application → Cookies → https://sem.3ue.com"
  echo "  3. 找 cf_clearance 行，复制 Value"
  exit 1
fi

# ⚠️ 注意：GMITM / APIKEY / TOKEN / EC 是账号相关配置
# 如需自定义，直接编辑 ~/.semrush-config
# 以下为默认配置（团队共享账号）

cat > "$CONFIG_FILE" << EOF
# Semrush 3ue.com 认证配置
# 生成时间: $(date)
# cf_clearance 有效期约 24 小时

CF_CLEARANCE='${CF_CLEARANCE}'
GMITM='ayWzA3*l4EVcTpZei43sW*qRvljSdU'
APIKEY='b2f5ff47436671b6e533d8dc3614845d'
USERID=444444444
TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1bmFtZSI6IkNoYXJsZXN0YWdsaWEiLCJwZXJtaXNzaW9ucyI6WyJzaW1pbGFyd2ViLnBybyIsInNlbXJ1c2guY2hlYXAiLCJ1c2VyIl0sImlhdCI6MTc3MjA4ODgwNywiZXhwIjoxNzcyMzQ4MDA3fQ.oNvzsSyna0yWMGYhDUA4n9H-qVib9IHdei0I-Ozsr-7vlb3Vj5C3LtfMXlRicsgoRlEMcx5J_gy_EjN8hwwSxCr-P_RI2PxJy4KeZ8lGr7ExervAynW-ZTUdgbfmUwwDC6_J7lyA85jxoN0bjvBFxOuAQio6vNcyi3i8CKhVo62pvRNnCQcdtHw7DdIyaJbNhI762uX5gOEwpakE9UNSoj8BpkL9fimOT0buT-g_I5H2M6MFo5xjz3D_ig4NwbCCTWMukr8cPgRckjXGgU91o0HEI9F5F760tdI8ZPff_uqtgOvIkdVTLspVkqoCiWxpnzADaUUhXgv0NYev3Yxrwg|MzMw'
EC='MhTTKV~NlrAsBOtEPojso!xtBYmb1IxTik0Nv7c3w3jB2h6DPYKx31tdek08q0V3wxSnax6FeI9wJghdaQ!EnycgJ!ufMWOtQ19mE!3RGUFZrEW5gxGwsyGJFvtRNEQEw98ETv3PPsxe*msVEs4EaXa*dVsLEJgwwyy*iC7vB76tB3bbeC!'
EOF

chmod 600 "$CONFIG_FILE"
echo "✅ 配置已保存到 $CONFIG_FILE"
echo "🔑 cf_clearance 有效期约 24 小时，过期后重新运行此脚本"
echo ""

# 测试连通性
echo "🔗 测试连通性..."
source "$CONFIG_FILE"
RESULT=$(curl -s "https://sem.3ue.com/kwogw/rpc?__gmitm=${GMITM}" -X POST \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "Origin: https://sem.3ue.com" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -b "cf_clearance=${CF_CLEARANCE}; GMITM_token=${TOKEN}; GMITM_ec=${EC}; GMITM_uname=Charlestaglia" \
  -d "{\"id\":1,\"jsonrpc\":\"2.0\",\"method\":\"user.GetSettings\",\"params\":{\"UserId\":${USERID},\"APIKey\":\"${APIKEY}\"}}" \
  --max-time 10 2>/dev/null)

if echo "$RESULT" | grep -q '"result"'; then
  echo "✅ 连通成功！可以开始查询了"
  echo ""
  echo "示例："
  echo "  python3 semrush_query.py \"invoice generator\""
  echo "  python3 semrush_query.py --batch keywords.txt --output results.csv"
  echo "  python3 semrush_query.py --backlinks invoice-generator.com"
else
  echo "❌ 连通失败，可能 cf_clearance 已过期"
  echo "   请重新从浏览器获取 cf_clearance 并再次运行"
fi
