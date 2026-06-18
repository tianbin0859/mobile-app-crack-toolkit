# 报告整合与技能更新陷阱

> 来源：黑曼巴6.16逆向分析经验整合过程
> 适用：将用户提供的分析/研究报告整合到技能中时

## 陷阱1：多版本报告处理

**场景**：用户连续发送多个版本的同一报告（如"黑曼巴"vs"黑曼巻"），内容基本相同但文件名/标题不同。

**问题**：
- 可能重复处理相同内容
- 文件名差异导致无法识别为同一报告
- 占用额外存储空间

**解决方案**：
```python
def deduplicate_reports(reports):
    """去重报告列表"""
    seen_content = set()
    unique_reports = []
    
    for report in reports:
        # 使用内容哈希去重（忽略文件名和标题差异）
        content_hash = hashlib.md5(
            report.content.strip().encode()
        ).hexdigest()
        
        if content_hash not in seen_content:
            seen_content.add(content_hash)
            unique_reports.append(report)
    
    return unique_reports
```

**处理流程**：
1. 收到报告后，先检查是否已有相似内容（标题相似度>80%）
2. 如果内容相同，只保留最新版本
3. 如果内容有更新，合并差异部分
4. 更新技能引用时，只指向最新版本

## 陷阱2：Patch循环检测

**场景**：尝试用patch工具修改文件，但连续多次失败（3次以上），使用相同的old_string和new_string。

**问题**：
- 陷入无限循环，浪费时间和token
- 可能破坏文件结构
- 用户等待时间增加

**解决方案**：
```python
def safe_patch(file_path, old_string, new_string, max_retries=2):
    """安全patch，防止循环"""
    patch_history = []
    
    for attempt in range(max_retries):
        # 记录patch尝试
        patch_history.append({
            'old': old_string[:50],
            'new': new_string[:50],
            'time': time.time()
        })
        
        # 检查是否重复（最近3次相同）
        if len(patch_history) >= 3:
            last_3 = patch_history[-3:]
            if all(p['old'] == last_3[0]['old'] for p in last_3):
                raise PatchLoopError("检测到patch循环，停止尝试")
        
        # 执行patch前重新读取文件
        current_content = read_file(file_path)
        
        # 检查old_string是否仍然存在
        if old_string not in current_content:
            # 可能已经被修改过，检查new_string是否已存在
            if new_string in current_content:
                print("[+] 目标内容已存在，跳过patch")
                return True
            else:
                raise PatchError(f"old_string不存在，且new_string也未找到")
        
        # 执行patch
        result = patch(file_path, old_string, new_string)
        
        if result.success:
            return True
        
        # 失败时等待并重新读取
        time.sleep(1)
    
    raise PatchError(f"Patch失败，已尝试{max_retries}次")
```

**处理流程**：
1. 每次patch前重新读取文件
2. 检查old_string是否仍然存在
3. 如果old_string不存在，检查new_string是否已存在（可能已修改成功）
4. 记录patch历史，检测循环
5. 超过max_retries时停止，改用write_file重写整个文件

## 陷阱3：技能引用更新遗漏

**场景**：创建了新参考文档，但忘记在SKILL.md的引用表格中添加条目。

**问题**：
- 新文档无法被技能系统发现
- 其他agent不知道文档存在
- 知识沉淀不完整

**解决方案**：
```python
def update_skill_references(skill_path, new_refs):
    """更新技能引用表格"""
    # 读取SKILL.md
    content = read_file(skill_path)
    
    # 找到引用表格区域
    table_start = content.find("| 文档 | 内容 |")
    table_end = content.find("## 模块", table_start)
    
    # 在表格末尾添加新引用
    for ref in new_refs:
        new_line = f"| `{ref.path}` | **{ref.description}** |\n"
        content = content[:table_end] + new_line + content[table_end:]
    
    # 写回文件
    write_file(skill_path, content)
```

**检查清单**：
- [ ] 新文档已创建
- [ ] 文档内容完整
- [ ] SKILL.md引用表格已更新
- [ ] 文档路径正确（references/xxx.md）
- [ ] 描述准确反映文档内容

## 陷阱4：YAML Frontmatter破坏

**场景**：修改SKILL.md时，不小心破坏了YAML frontmatter（如description字段中的特殊字符）。

**问题**：
- 技能无法加载
- 解析错误
- 触发器丢失

**解决方案**：
1. 修改前备份frontmatter
2. 使用专门的YAML编辑工具
3. 修改后验证YAML格式
4. 避免在description中使用未转义的 `|` 或 `*`

**验证命令**：
```bash
python3 -c "import yaml; yaml.safe_load(open('SKILL.md'))"
```

## 陷阱5：版本号不一致

**场景**：更新了技能内容，但忘记更新版本号，或版本号与变更日志不匹配。

**问题**：
- 用户无法识别最新版本
- 版本历史混乱
- 自进化系统无法追踪变更

**解决方案**：
```python
def bump_version(skill_path, change_type='patch'):
    """自动升级版本号"""
    # 读取当前版本
    content = read_file(skill_path)
    version_match = re.search(r'v(\d+)\.(\d+)\.(\d+)', content)
    
    if version_match:
        major, minor, patch = map(int, version_match.groups())
        
        if change_type == 'major':
            major += 1
            minor = 0
            patch = 0
        elif change_type == 'minor':
            minor += 1
            patch = 0
        else:
            patch += 1
        
        new_version = f"v{major}.{minor}.{patch}"
        
        # 更新所有版本号引用
        content = content.replace(
            f"v{version_match.group(1)}.{version_match.group(2)}.{version_match.group(3)}",
            new_version
        )
        
        write_file(skill_path, content)
```

**版本号规则**：
- major：架构级变更（如新增模块类别）
- minor：功能新增（如新增参考文档）
- patch：修复/优化（如更新陷阱、修正错误）
