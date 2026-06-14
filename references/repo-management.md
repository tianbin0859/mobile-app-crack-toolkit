# 仓库管理指南

## 技能重命名流程

当用户要求重命名技能时：

1. **更新本地目录**
   ```bash
   cd ~/.hermes/skills/software-development/
   mv old-name new-name
   ```

2. **更新SKILL.md**
   - `title:` 字段
   - `name:` 字段（YAML frontmatter）
   - 所有内部引用

3. **更新脚本路径**
   - `scripts/auto_push.sh` 中的 `SKILL_DIR` 和 `LOG_FILE`
   - `scripts/evolution_tracker.py` 中的 `DEFAULT_EVO_DIR`
   - 其他硬编码路径

4. **更新参考文档**
   - `references/repo-privacy-guide.md` 中的仓库列表
   - `references/gitee-github-api-automation.md` 中的敏感项目列表

5. **验证**
   ```bash
   grep -r "old-name" ~/.hermes/skills/software-development/new-name/
   ```
   应返回0结果

## 新建远程仓库流程

### 创建Gitee私有仓库
```bash
curl -s -X POST https://gitee.com/api/v5/user/repos \
  -H "Content-Type: application/json" \
  -H "Authorization: token <TOKEN>" \
  -d '{
    "name": "new-repo-name",
    "description": "项目描述",
    "private": true,
    "auto_init": false
  }'
```

### 推送代码到新仓库
```bash
cd <project-dir>
git remote add new-gitee https://gitee.com/<user>/<repo>.git
git push new-gitee main
```

### 双仓库管理策略
- **旧仓库**: 保留历史，归档处理
- **新仓库**: 活跃开发，后续更新推送至此
- 可选：在旧仓库README中添加指向新仓库的链接

## 合并冲突解决（macOS）

### 问题: sed命令在macOS上失效
macOS的sed与GNU sed不兼容，处理换行符时会出现 `invalid command code` 错误。

### 解决方案: 使用Python
```python
import re

# 读取文件
with open('SKILL.md', 'r') as f:
    lines = f.readlines()

# 删除包含冲突标记的行
filtered_lines = []
for line in lines:
    if '<<<<<<<' in line or '=======' in line or '>>>>>>>' in line:
        continue
    filtered_lines.append(line)

# 写回文件
with open('SKILL.md', 'w') as f:
    f.writelines(filtered_lines)
```

### 验证
```python
with open('SKILL.md', 'r') as f:
    content = f.read()
    assert content.count('<<<<<<<') == 0, "仍有冲突残留"
```

## 用户偏好记录

- **命名风格**: 偏好简洁中文名称（"破解工具箱"而非"APK Crack Engine Pro"）
- **仓库可见性**: 所有破解/逆向项目必须设为私有
- **执行模式**: 直接执行而非生成脚本（Python自动连接设备并注入Hook）
