# 仓库隐私设置指南

## 规则

涉及破解/逆向/游戏自动化的项目，**必须设为私有仓库**。

## 适用项目类型

- APK破解工具/脚本
- 游戏自动化/打金脚本
- 内存读取/修改工具
- 逆向工程分析结果
- 收费软件破解方案
- 授权绕过工具

## Gitee仓库管理

### 创建私有仓库

**方式1: 网页创建 (推荐)**
1. 访问 https://gitee.com/projects/new
2. 填写仓库名称
3. 选择 **私有仓库** 🔒
4. 点击创建

**方式2: API创建 (需认证)**
```bash
curl -X POST "https://gitee.com/api/v5/user/repos" \
  -H "Content-Type: application/json" \
  -d '{"name":"repo-name","private":true}'
```

### 修改已有仓库为私有

1. 访问 `https://gitee.com/<用户名>/<仓库名>/settings`
2. 找到"是否开源"选项
3. 选择 **私有仓库**
4. 保存

### 批量修改

```bash
# 列出所有公开仓库
# 逐个访问设置页面修改为私有
```

## 当前项目清单

| 项目 | 平台 | 状态 | 操作 |
|------|------|------|------|
| apk-crack-engine | Gitee | 待改为私有 | [设置](https://gitee.com/tianbinice/apk-crack-engine/settings) |
| wendao-gold-bot | Gitee | 待改为私有 | [设置](https://gitee.com/tianbinice/wendao-gold-bot/settings) |
| github-research-pro | Gitee | 待改为私有 | [设置](https://gitee.com/tianbinice/github-research-pro/settings) |
| dnf-gold-bot | Gitee | 待创建(私有) | [创建](https://gitee.com/projects/new?name=dnf-gold-bot&private=true) |

## GitHub仓库管理

### 创建私有仓库

```bash
# 使用gh CLI
gh repo create repo-name --private
```

### 修改已有仓库为私有

```bash
gh repo edit <用户名>/<仓库名> --visibility private
```

## 注意事项

1. **API认证失效**: Gitee API可能因认证问题无法使用，此时必须手动网页操作
2. **创建后推送**: 仓库创建完成后才能执行 `git push`
3. **404错误**: 如果推送时报404，说明仓库不存在或未创建
4. **双重备份**: 建议同时推送到Gitee和GitHub，两者都设为私有

## 故障排查

| 错误 | 原因 | 解决 |
|------|------|------|
| 404 not found | 仓库不存在 | 先创建仓库 |
| 登录失效 | API认证过期 | 手动网页操作 |
| 无权限 | 未授权访问 | 检查仓库所有权 |
| 推送超时 | 网络问题 | 重试或检查代理 |
