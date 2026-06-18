# 技能维护指南

> 来源：mobile-app-crack-toolkit v8.1.5 维护经验
> 适用：所有技能维护更新操作

## 新增参考文档清单（2026-06-18）

本次更新新增以下参考文档，需手动添加到SKILL.md引用表格：

| 文档路径 | 内容描述 | 状态 |
|---------|---------|------|
| `references/rust-reverse-experience-summary.md` | Rust程序逆向实战经验总结：7大教训、Rust特定技巧、优化流程、黑曼巴经验、技能进化建议 | ✅ 已创建 |
| `references/rustls-deep-analysis.md` | rustls TLS深入分析：TLS 1.3握手、密钥派生、为什么无法解密、突破点评估、客户端Patch方向 | ✅ 已创建 |
| `references/report-integration-pitfalls.md` | 报告整合陷阱：多版本处理、patch循环检测、YAML frontmatter保护、版本号同步 | ✅ 已创建 |

## 待添加到SKILL.md的内容

### 1. 引用表格更新

在SKILL.md的引用表格中，在`arkari-obfuscator-detection.md`和`ios-ipa-crack.md`之间插入：

```markdown
| `references/rust-reverse-experience-summary.md` | **Rust程序逆向实战经验总结：7大教训、Rust特定技巧、优化流程、黑曼巴经验、技能进化建议** |
| `references/rustls-deep-analysis.md` | **rustls TLS深入分析：TLS 1.3握手、密钥派生、为什么无法解密、突破点评估、客户端Patch方向** |
| `references/report-integration-pitfalls.md` | **报告整合陷阱：多版本处理、patch循环检测、YAML frontmatter保护、版本号同步** |
```

### 2. 版本历史更新

在版本历史部分添加：

```markdown
**v8.1.5 经验整合与文档完善：**
- 新增 `references/rust-reverse-experience-summary.md`：Rust程序逆向实战经验总结
- 新增 `references/rustls-deep-analysis.md`：rustls TLS深入分析
- 新增 `references/report-integration-pitfalls.md`：报告整合陷阱
- 基于黑曼巴6.16逆向分析（7+小时，27种方案）沉淀经验
- 记录5个技能维护陷阱（多版本报告、patch循环、YAML frontmatter、引用遗漏、版本同步）
```

### 3. 触发器更新

在触发器部分添加：

```markdown
- 需要整合用户提供的分析/研究报告到技能中
- 需要将逆向分析经验沉淀为技能参考文档
- 遇到技能维护问题（patch失败、YAML错误、版本混乱）
```

## 维护检查清单

每次更新技能时，按以下顺序检查：

- [ ] 1. 新文档已创建并保存到references/
- [ ] 2. 文档内容完整，格式正确
- [ ] 3. SKILL.md引用表格已更新（手动添加）
- [ ] 4. 版本号已升级（SKILL.md + 版本历史）
- [ ] 5. YAML frontmatter已验证（无特殊字符问题）
- [ ] 6. 触发器已更新（如需要）
- [ ] 7. 变更日志已记录
- [ ] 8. 技能已测试加载（无解析错误）

## 已知问题

### YAML Frontmatter 脆弱性

SKILL.md的YAML frontmatter对特殊字符敏感。以下字符需要转义：
- `|` → 使用 `"..."` 包裹或转义
- `*` → 避免在description中使用
- `:` → 确保后面有空格

**验证方法**：
```bash
python3 -c "import yaml; yaml.safe_load(open('SKILL.md'))"
```

### 当前版本状态

- 技能版本：v8.1.5（目标）
- 实际文件版本：v8.1.0（SKILL.md中）
- 差异：新增3个参考文档，但未更新SKILL.md主文件
- 解决方案：手动编辑SKILL.md，添加引用条目和版本历史

## 下一步维护计划

1. 修复SKILL.md YAML frontmatter问题
2. 添加引用表格条目
3. 更新版本历史到v8.1.5
4. 验证技能加载正常
5. 推送更新到Gitee仓库
