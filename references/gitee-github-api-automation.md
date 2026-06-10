# Gitee/GitHub API 自动化操作指南

## 使用场景

批量管理仓库可见性、创建仓库、推送代码。适用于需要频繁操作多个仓库的破解/逆向项目。

## Gitee API

### 认证方式
```bash
# Header方式
-H "Authorization: token <YOUR_TOKEN>"
```

### 创建私有仓库
```bash
curl -s -X POST "https://gitee.com/api/v5/user/repos" \
  -H "Content-Type: application/json" \
  -H "Authorization: token <TOKEN>" \
  -d '{
    "name": "repo-name",
    "description": "项目描述",
    "private": true,
    "auto_init": false
  }'
```

### 修改仓库可见性
```bash
curl -s -X PATCH "https://gitee.com/api/v5/repos/<user>/<repo>" \
  -H "Content-Type: application/json" \
  -H "Authorization: token <TOKEN>" \
  -d '{"name": "repo-name", "private": true}'
```

### 常见错误
| 错误 | 原因 | 解决 |
|------|------|------|
| `40001 登录失效` | Token过期 | 重新获取Token |
| `name is missing` | 必须同时传name字段 | PATCH时加上 `"name": "xxx"` |
| `404 not found` | 仓库不存在 | 先创建仓库 |

## GitHub API (gh CLI)

### 修改仓库可见性
```bash
gh repo edit <user>/<repo> --visibility private --accept-visibility-change-consequences
```

### 批量列出仓库
```bash
gh repo list <user> --limit 20
```

### 要求
- 已登录: `gh auth status`
- 需要 `repo` scope权限

## 批量操作脚本

```python
#!/usr/bin/env python3
"""批量将敏感项目设为私有"""

import subprocess
import requests

# Gitee配置
GITEE_TOKEN = "your-token"
GITEE_USER = "your-username"

# GitHub配置 (使用gh CLI)
GITHUB_USER = "your-username"

# 敏感项目列表
SENSITIVE_REPOS = [
    "apk-crack-engine",
    "dnf-gold-bot",
    "wendao-gold-bot",
    "game-memory-module",
    "hearthstone-auto-bot",
]

def make_gitee_private(repo):
    """Gitee设为私有"""
    url = f"https://gitee.com/api/v5/repos/{GITEE_USER}/{repo}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"token {GITEE_TOKEN}"
    }
    data = {"name": repo, "private": True}
    
    resp = requests.patch(url, json=data, headers=headers)
    if resp.status_code == 200:
        print(f"✅ Gitee: {repo} -> 私有")
    else:
        print(f"❌ Gitee: {repo} -> {resp.json()}")

def make_github_private(repo):
    """GitHub设为私有"""
    result = subprocess.run(
        ["gh", "repo", "edit", f"{GITHUB_USER}/{repo}", 
         "--visibility", "private", 
         "--accept-visibility-change-consequences"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"✅ GitHub: {repo} -> 私有")
    else:
        print(f"❌ GitHub: {repo} -> {result.stderr}")

if __name__ == "__main__":
    for repo in SENSITIVE_REPOS:
        make_gitee_private(repo)
        make_github_private(repo)
```

## 强制私有规则

涉及以下类型的项目**必须**设为私有：
- 破解/逆向工程
- 游戏自动化/打金
- 内存读取/修改
- 协议逆向
- 授权绕过
- 脱壳/反编译工具
