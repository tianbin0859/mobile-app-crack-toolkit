# Git历史偏好

**日期**: 2026-06-17
**用户明确指令**: "不要合并"（当推送代码到Gitee时）

**说明**:
- 用户偏好干净的Git历史，不使用合并提交（merge commits）
- 当本地和远程历史分歧时，使用 `git reset --soft` + 重新提交 的方式创建线性历史
- 已验证于破解工具箱v6.20推送场景

**标准流程**:
```bash
# 1. Soft reset到远程分支（保留所有更改）
git reset --soft origin/main

# 2. 提交为单个干净提交
git add -A
git commit -m "vX.Y: 描述"

# 3. 正常推送（无需force）
git push origin main
```

**未来注意**:
- 推送破解工具箱更新时，保持线性历史
- 避免使用 `git merge` 或 `git pull` 合并远程分支
- 如果系统阻止force push，使用上述soft reset方案
