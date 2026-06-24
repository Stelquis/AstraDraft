# ===================================================================
# Claude Code 配置初始化脚本（DeepSeek 官方渠道）
# 配置路径: /root/.claude/ 和 /home/admin/.claude/
# 一键运行: 
#    bash /workspace/scripts/init-claude.sh
# ===================================================================
set -e

# -----------------------------------------------------------------------------
# 用户配置区
# -----------------------------------------------------------------------------

# DeepSeek API Key（留空则交互式输入，填写则直接使用）
MY_API_KEY=""

# DeepSeek Anthropic API 地址
MY_BASE_URL="https://api.deepseek.com/anthropic"

# 主模型 / 轻量模型
MY_MODEL="deepseek-v4-pro[1m]"
MY_LIGHT_MODEL="deepseek-v4-flash"

# 执行力度: min / low / medium / high / max
MY_EFFORT_LEVEL="min"

# -----------------------------------------------------------------------------
# 配置读取（优先级: 环境变量 > 脚本配置区 > 交互式输入）
# -----------------------------------------------------------------------------

ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-$MY_BASE_URL}"
ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-$MY_MODEL}"
ANTHROPIC_DEFAULT_OPUS_MODEL="${ANTHROPIC_DEFAULT_OPUS_MODEL:-$MY_MODEL}"
ANTHROPIC_DEFAULT_SONNET_MODEL="${ANTHROPIC_DEFAULT_SONNET_MODEL:-$MY_MODEL}"
ANTHROPIC_DEFAULT_HAIKU_MODEL="${ANTHROPIC_DEFAULT_HAIKU_MODEL:-$MY_LIGHT_MODEL}"
CLAUDE_CODE_SUBAGENT_MODEL="${CLAUDE_CODE_SUBAGENT_MODEL:-$MY_LIGHT_MODEL}"
CLAUDE_CODE_EFFORT_LEVEL="${CLAUDE_CODE_EFFORT_LEVEL:-$MY_EFFORT_LEVEL}"

ROOT_CLAUDE_DIR="/root/.claude"
ADMIN_CLAUDE_DIR="/home/admin/.claude"

# -----------------------------------------------------------------------------
# API Key 获取
# -----------------------------------------------------------------------------

if [ -n "${ANTHROPIC_AUTH_TOKEN:-}" ] || [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-${ANTHROPIC_API_KEY}}"
elif [ -n "$MY_API_KEY" ]; then
    ANTHROPIC_AUTH_TOKEN="$MY_API_KEY"
else
    echo ""
    echo "🔑 请输入 DeepSeek API Key（获取: https://platform.deepseek.com/api_keys）"
    printf "API Key: "
    read -r USER_API_KEY
    [ -n "$USER_API_KEY" ] && ANTHROPIC_AUTH_TOKEN="$USER_API_KEY"
    echo ""
fi

# -----------------------------------------------------------------------------
# 生成配置文件
# -----------------------------------------------------------------------------

if [ -z "$ANTHROPIC_AUTH_TOKEN" ]; then
    echo "⚠️  未设置 API Key，跳过配置生成"
    echo "   用法: ANTHROPIC_API_KEY=\"sk-xxx\" bash /workspace/scripts/init-claude.sh"
    mkdir -p "$ROOT_CLAUDE_DIR" "$ADMIN_CLAUDE_DIR"
else
    mkdir -p "$ROOT_CLAUDE_DIR"

    cat > "$ROOT_CLAUDE_DIR/settings.json" << EOF
{
    "env": {
        "ANTHROPIC_BASE_URL": "${ANTHROPIC_BASE_URL}",
        "ANTHROPIC_AUTH_TOKEN": "${ANTHROPIC_AUTH_TOKEN}",
        "ANTHROPIC_MODEL": "${ANTHROPIC_MODEL}",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "${ANTHROPIC_DEFAULT_OPUS_MODEL}",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "${ANTHROPIC_DEFAULT_SONNET_MODEL}",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "${ANTHROPIC_DEFAULT_HAIKU_MODEL}",
        "CLAUDE_CODE_SUBAGENT_MODEL": "${CLAUDE_CODE_SUBAGENT_MODEL}",
        "CLAUDE_CODE_EFFORT_LEVEL": "${CLAUDE_CODE_EFFORT_LEVEL}"
    },
    "theme": "light-daltonized"
}
EOF

    cat > "$ROOT_CLAUDE_DIR/.claude.json" << EOF
{
    "hasCompletedOnboarding": true
}
EOF

    mkdir -p "$ADMIN_CLAUDE_DIR"
    cp "$ROOT_CLAUDE_DIR/settings.json" "$ADMIN_CLAUDE_DIR/"
    cp "$ROOT_CLAUDE_DIR/.claude.json" "$ADMIN_CLAUDE_DIR/"

    echo "✅ 配置完成"
    echo "   Base URL: ${ANTHROPIC_BASE_URL}"
    echo "   主模型:   ${ANTHROPIC_MODEL}"
fi
