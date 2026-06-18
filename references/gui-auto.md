# GUI自动化框架

## 概述

GUI自动化框架用于自动操作Windows GUI程序（填表、点击、处理弹窗）。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `gui_auto.py` | 窗口查找/自动填表/按钮点击/弹窗处理/操作录制 | `scripts/gui_auto.py` |

## 核心功能

1. **窗口查找**：通过标题模式（支持通配符）查找窗口
2. **自动填表**：自动输入文本到指定控件
3. **按钮点击**：自动点击按钮
4. **弹窗处理**：自动等待并处理弹窗
5. **操作录制**：录制操作序列并保存为JSON
6. **操作播放**：播放录制的操作序列

## 用法

```bash
# 自动填卡密并点击登录
python gui_auto.py --window "黑曼巴*" --input "卡密:Edit1=123456789" --click "登录:Button1" --delay 2

# 自动处理弹窗
python gui_auto.py --window "黑曼巴*" --wait-popup --click "确定:Button1"

# 录制操作序列
python gui_auto.py --record --output actions.json

# 播放操作序列
python gui_auto.py --play actions.json
```

## 依赖

- pip install pywinauto pyautogui
