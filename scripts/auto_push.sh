#!/bin/bash
# APK Crack Engine 自动推送脚本
# 定时推送技能更新到Gitee/GitHub

set -e

SKILL_DIR="/Users/tianbin/.hermes/skills/software-development/apk-crack-engine"
LOG_FILE="/Users/tianbin/.hermes/logs/apk-crack-engine-push.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$DATE] $1" | tee -a "$LOG_FILE"
}

cd "$SKILL_DIR"

# 检查是否有变更
if git diff --quiet && git diff --cached --quiet; then
    log "无变更，跳过推送"
    exit 0
fi

# 添加所有变更
git add -A

# 生成提交信息
CHANGED_FILES=$(git diff --cached --name-only | wc -l | tr -d ' ')
COMMIT_MSG="auto: 定时推送 $CHANGED_FILES 个文件变更 ($(date '+%m-%d %H:%M'))"

# 提交
git commit -m "$COMMIT_MSG"
log "提交: $COMMIT_MSG"

# 推送到Gitee
if git remote | grep -q "gitee"; then
    git push gitee main 2>&1 | tee -a "$LOG_FILE"
    log "✅ Gitee推送成功"
else
    log "⚠️ Gitee远程不存在"
fi

# 推送到GitHub (如果有)
if git remote | grep -q "github"; then
    git push github main 2>&1 | tee -a "$LOG_FILE"
    log "✅ GitHub推送成功"
else
    log "ℹ️ GitHub远程不存在，跳过"
fi

log "定时推送完成"
