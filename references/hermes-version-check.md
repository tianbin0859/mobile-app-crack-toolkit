# Hermes Agent 版本验证流程

## 场景

用户从外部来源（豆包AI、网页等）获取版本信息截图，说"有更新"。

## 验证步骤

1. **不要直接相信外部截图** — 外部信息可能滞后
2. **验证实际安装版本**：
   ```bash
   python3.11 -c "import hermes_cli; print(hermes_cli.__version__)"
   ```
3. **比较版本**：
   - 截图显示 v0.15.2（2026.5.29）
   - 实际安装 v0.16.0（2026.6.5）→ 已是最新
4. **更新命令**（如需要）：
   ```bash
   python3.11 -m pip install --upgrade hermes-agent --break-system-packages
   ```

## 常见情况

| 情况 | 处理 |
|------|------|
| 实际 ≥ 截图版本 | 已是最新，向用户说明 |
| 实际 < 截图版本 | 执行更新 |
| pip 命令不存在 | 使用 `python3.11 -m pip` |

## 路径信息

- Hermes 命令完整路径：`~/.local/share/uv/python/cpython-3.11.15-macos-x86_64-none/bin/hermes`
- 未加入 PATH，需使用完整路径或 alias
