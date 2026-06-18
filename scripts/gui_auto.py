#!/usr/bin/env python3
"""
gui_auto.py - GUI自动化框架（pywinauto封装）
基于黑曼巴6.16实战经验开发

功能:
    1. 自动查找窗口（标题/类名/进程名）
    2. 自动填表（卡密输入、按钮点击）
    3. 自动处理弹窗（错误提示、确认对话框）
    4. 支持多窗口切换
    5. 支持延迟和重试机制

用法:
    # 自动填卡密并点击登录
    python gui_auto.py --window "黑曼巴*" --input "卡密:Edit1=123456789" --click "登录:Button1" --delay 2
    
    # 自动处理弹窗
    python gui_auto.py --window "黑曼巴*" --wait-popup --click "确定:Button1"
    
    # 录制操作序列
    python gui_auto.py --record --output actions.json

依赖:
    - pip install pywinauto pyautogui
"""

import argparse
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

class GUIAutomator:
    """GUI自动化器"""
    
    def __init__(self):
        self.app = None
        self.window = None
        
    def find_window(self, title_pattern: str, class_name: Optional[str] = None) -> Optional[Any]:
        """查找窗口"""
        try:
            from pywinauto import Desktop
            
            desktop = Desktop(backend="win32")
            
            # 尝试匹配标题
            windows = desktop.windows(title_re=title_pattern)
            
            if windows:
                self.window = windows[0]
                print(f"[+] 找到窗口: {self.window.window_text()}")
                return self.window
            
            print(f"[-] 未找到窗口: {title_pattern}")
            return None
            
        except ImportError:
            print("[-] 需要pywinauto: pip install pywinauto")
            return None
    
    def find_control(self, control_id: str) -> Optional[Any]:
        """查找控件"""
        if not self.window:
            print("[-] 未找到窗口")
            return None
        
        try:
            # 支持多种查找方式
            # 1. 通过Automation ID
            control = self.window.child_window(auto_id=control_id)
            if control.exists():
                return control
            
            # 2. 通过Class Name
            control = self.window.child_window(class_name=control_id)
            if control.exists():
                return control
            
            # 3. 通过Title
            control = self.window.child_window(title=control_id)
            if control.exists():
                return control
            
            print(f"[-] 未找到控件: {control_id}")
            return None
            
        except Exception as e:
            print(f"[-] 查找控件失败: {e}")
            return None
    
    def input_text(self, control_id: str, text: str):
        """输入文本"""
        control = self.find_control(control_id)
        if control:
            control.set_text(text)
            print(f"[+] 输入: {control_id} = {text}")
    
    def click_button(self, control_id: str):
        """点击按钮"""
        control = self.find_control(control_id)
        if control:
            control.click()
            print(f"[+] 点击: {control_id}")
    
    def wait_for_popup(self, timeout: int = 10) -> Optional[Any]:
        """等待弹窗"""
        print(f"[*] 等待弹窗: {timeout}秒")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                from pywinauto import Desktop
                desktop = Desktop(backend="win32")
                
                # 查找所有对话框
                popups = desktop.windows(class_name="#32770")  # 对话框类名
                
                if popups:
                    popup = popups[0]
                    print(f"[+] 发现弹窗: {popup.window_text()}")
                    return popup
                
                time.sleep(0.5)
                
            except Exception as e:
                pass
        
        print(f"[-] 超时: 未找到弹窗")
        return None
    
    def handle_popup(self, popup_text: str, action: str):
        """处理弹窗"""
        popup = self.wait_for_popup()
        if popup:
            if action == "click":
                # 查找按钮并点击
                buttons = popup.descendants(control_type="Button")
                if buttons:
                    for button in buttons:
                        if popup_text in button.window_text():
                            button.click()
                            print(f"[+] 点击弹窗按钮: {button.window_text()}")
                            return
            
            elif action == "close":
                popup.close()
                print(f"[+] 关闭弹窗")


class ActionRecorder:
    """操作录制器"""
    
    def __init__(self):
        self.actions = []
        self.recording = False
        
    def start_recording(self):
        """开始录制"""
        self.recording = True
        self.actions = []
        print("[*] 开始录制操作...")
        
    def stop_recording(self):
        """停止录制"""
        self.recording = False
        print(f"[+] 录制完成: {len(self.actions)} 个操作")
        
    def record_action(self, action_type: str, **kwargs):
        """记录操作"""
        if self.recording:
            action = {
                'type': action_type,
                'timestamp': time.time(),
                **kwargs,
            }
            self.actions.append(action)
    
    def save_actions(self, output_path: str):
        """保存操作序列"""
        with open(output_path, 'w') as f:
            json.dump(self.actions, f, indent=2)
        print(f"[+] 保存操作序列: {output_path}")
    
    def load_actions(self, input_path: str) -> List[Dict]:
        """加载操作序列"""
        with open(input_path, 'r') as f:
            self.actions = json.load(f)
        print(f"[+] 加载操作序列: {len(self.actions)} 个操作")
        return self.actions


class ActionPlayer:
    """操作播放器"""
    
    def __init__(self, automator: GUIAutomator):
        self.automator = automator
        
    def play_actions(self, actions: List[Dict]):
        """播放操作序列"""
        print(f"[*] 播放操作序列: {len(actions)} 个操作")
        
        for i, action in enumerate(actions):
            action_type = action.get('type')
            
            print(f"\n[{i+1}/{len(actions)}] {action_type}")
            
            if action_type == 'find_window':
                self.automator.find_window(action.get('title_pattern'))
            
            elif action_type == 'input':
                self.automator.input_text(action.get('control_id'), action.get('text'))
            
            elif action_type == 'click':
                self.automator.click_button(action.get('control_id'))
            
            elif action_type == 'wait_popup':
                self.automator.wait_for_popup(action.get('timeout', 10))
            
            elif action_type == 'delay':
                delay = action.get('seconds', 1)
                print(f"[*] 延迟 {delay} 秒")
                time.sleep(delay)
            
            # 操作间隔
            time.sleep(0.5)
        
        print(f"\n[+] 操作序列播放完成")


def main():
    parser = argparse.ArgumentParser(
        description="GUI自动化框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 自动填卡密并点击登录
    python gui_auto.py --window "黑曼巴*" --input "卡密:Edit1=123456789" --click "登录:Button1" --delay 2
    
    # 自动处理弹窗
    python gui_auto.py --window "黑曼巴*" --wait-popup --click "确定:Button1"
    
    # 录制操作序列
    python gui_auto.py --record --output actions.json
        """
    )
    
    parser.add_argument("--window", help="窗口标题模式（支持通配符*）")
    parser.add_argument("--input", action="append", help="输入操作（格式: 控件ID=文本）")
    parser.add_argument("--click", action="append", help="点击操作（格式: 控件ID）")
    parser.add_argument("--wait-popup", action="store_true", help="等待弹窗")
    parser.add_argument("--delay", type=float, default=0, help="操作延迟（秒）")
    parser.add_argument("--record", action="store_true", help="录制模式")
    parser.add_argument("--play", help="播放操作序列文件")
    parser.add_argument("--output", "-o", default="./gui_actions.json", help="输出文件")
    
    args = parser.parse_args()
    
    automator = GUIAutomator()
    
    # 录制模式
    if args.record:
        recorder = ActionRecorder()
        recorder.start_recording()
        
        print("[*] 录制中... 按Ctrl+C停止")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
        recorder.stop_recording()
        recorder.save_actions(args.output)
        return 0
    
    # 播放模式
    if args.play:
        recorder = ActionRecorder()
        actions = recorder.load_actions(args.play)
        
        player = ActionPlayer(automator)
        player.play_actions(actions)
        return 0
    
    # 实时操作模式
    if args.window:
        # 查找窗口
        automator.find_window(args.window)
        
        # 输入操作
        if args.input:
            for input_str in args.input:
                parts = input_str.split('=', 1)
                if len(parts) == 2:
                    control_id, text = parts
                    automator.input_text(control_id, text)
        
        # 点击操作
        if args.click:
            for click_str in args.click:
                automator.click_button(click_str)
        
        # 等待弹窗
        if args.wait_popup:
            popup = automator.wait_for_popup()
            if popup:
                print(f"[+] 发现弹窗: {popup.window_text()}")
        
        # 延迟
        if args.delay > 0:
            print(f"[*] 延迟 {args.delay} 秒")
            time.sleep(args.delay)
    
    print("\n[+] 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
