#!/usr/bin/env python3
"""
memory_dump_automation.py - 内存Dump自动化工具 v1.0
基于"全亮内存剥离"方案，自动化执行内存Dump、IAT修复、验证裁剪

用法:
    python memory_dump_automation.py <target_process> [--output dump.bin]
    python memory_dump_automation.py --check-env
    python memory_dump_automation.py --gui
"""

import argparse
import os
import sys
import subprocess
import json
from pathlib import Path

class MemoryDumpAutomator:
    """内存Dump自动化工具"""
    
    def __init__(self, target_process, output_path=None):
        self.target = target_process
        self.output = output_path or f"{target_process}_dump.bin"
        self.ce_path = self._find_cheat_engine()
        self.dbvm_ready = False
        
    def _find_cheat_engine(self):
        """查找Cheat Engine安装路径"""
        possible_paths = [
            r"C:\Program Files\Cheat Engine 7.5\cheatengine-x86_64.exe",
            r"C:\Program Files\Cheat Engine 7.4\cheatengine-x86_64.exe",
            r"C:\Program Files (x86)\Cheat Engine 7.5\cheatengine-x86_64.exe",
            r"C:\Tools\Cheat Engine\cheatengine-x86_64.exe",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def check_environment(self):
        """检测环境是否满足内存Dump条件"""
        print("[*] 检测内存Dump环境...")
        
        checks = {
            "cheat_engine": False,
            "dbvm_ready": False,
            "target_running": False,
            "admin_privileges": False,
        }
        
        # 1. 检测Cheat Engine
        if self.ce_path:
            print(f"    ✅ Cheat Engine found: {self.ce_path}")
            checks["cheat_engine"] = True
        else:
            print("    ❌ Cheat Engine not found")
            print("    💡 请安装Cheat Engine 7.5+ (https://cheatengine.org)")
        
        # 2. 检测管理员权限
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if is_admin:
                print("    ✅ Administrator privileges")
                checks["admin_privileges"] = True
            else:
                print("    ❌ Not running as administrator")
                print("    💡 请以管理员权限运行此脚本")
        except:
            print("    ⚠️  Cannot check admin privileges")
        
        # 3. 检测目标进程
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                if self.target.lower() in proc.info['name'].lower():
                    print(f"    ✅ Target process found: {proc.info['name']} (PID: {proc.info['pid']})")
                    checks["target_running"] = True
                    self.target_pid = proc.info['pid']
                    break
            if not checks["target_running"]:
                print(f"    ❌ Target process '{self.target}' not found")
                print("    💡 请先启动目标程序")
        except ImportError:
            print("    ⚠️  psutil not installed, cannot check processes")
            print("    💡 pip install psutil")
        
        # 4. 检测DBVM状态
        print("    ⚠️  DBVM status check requires manual verification")
        print("    💡 在Cheat Engine中点击'Help' -> 'About DBVM'")
        
        return checks
    
    def generate_ce_script(self):
        """生成Cheat Engine自动化脚本"""
        script = f"""
-- 内存Dump自动化脚本
-- 目标: {self.target}
-- 生成时间: {__import__('datetime').datetime.now().isoformat()}

function dump_process_memory()
    local process = getProcesslist()
    local target_pid = nil
    
    -- 查找目标进程
    for i=1, #process do
        if process[i].name:lower():find("{self.target.lower()}") then
            target_pid = process[i].processid
            print("Found target: " .. process[i].name .. " (PID: " .. target_pid .. ")")
            break
        end
    end
    
    if not target_pid then
        print("ERROR: Target process not found")
        return false
    end
    
    -- 打开进程
    openProcess(target_pid)
    
    -- 获取内存区域
    local regions = getMemoryRegionList()
    local dump_file = io.open("{self.output}", "wb")
    
    if not dump_file then
        print("ERROR: Cannot create dump file")
        return false
    end
    
    -- 遍历并Dump所有可读内存
    local total_size = 0
    for i=1, #regions do
        local region = regions[i]
        if region.isReadable and not region.isGuard then
            local data = readBytes(region.base, region.size, true)
            if data then
                dump_file:write(data)
                total_size = total_size + region.size
                print("Dumped: " .. string.format("0x%08X", region.base) .. " (" .. region.size .. " bytes)")
            end
        end
    end
    
    dump_file:close()
    print("Dump complete! Total: " .. total_size .. " bytes")
    print("Output: {self.output}")
    
    return true
end

-- 执行Dump
dump_process_memory()
"""
        return script
    
    def create_dump(self):
        """执行内存Dump"""
        print(f"[*] 准备内存Dump: {self.target}")
        
        # 1. 环境检测
        env = self.check_environment()
        if not all(env.values()):
            print("\n❌ 环境检测失败，请修复上述问题后重试")
            return False
        
        # 2. 生成CE脚本
        print("\n[*] 生成Cheat Engine脚本...")
        script = self.generate_ce_script()
        script_path = f"{self.target}_dump.lua"
        with open(script_path, 'w') as f:
            f.write(script)
        print(f"    ✅ 脚本已生成: {script_path}")
        
        # 3. 提示手动执行
        print("\n[*] 请按以下步骤执行:")
        print("    1. 以管理员权限启动Cheat Engine")
        print(f"    2. 打开目标进程: {self.target}")
        print(f"    3. 加载脚本: {script_path}")
        print("    4. 执行Dump")
        print(f"    5. 输出文件: {self.output}")
        
        return True
    
    def post_process(self):
        """后处理：IAT修复、验证裁剪"""
        print("\n[*] 后处理选项:")
        print("    1. IAT修复 (使用Scylla)")
        print("    2. 验证裁剪 (使用IDA Pro)")
        print("    3. 完整修复流程")
        
        # 这里可以集成Scylla和IDA的自动化调用
        print("\n⚠️  后处理需要手动执行，请参考以下工具:")
        print("    - Scylla: https://github.com/NtQuery/Scylla")
        print("    - IDA Pro: https://hex-rays.com/ida-pro")
        
        return True

def main():
    parser = argparse.ArgumentParser(description="Memory Dump Automation Tool v1.0")
    parser.add_argument("target", nargs="?", help="目标进程名或PID")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--check-env", action="store_true", help="仅检测环境")
    parser.add_argument("--gui", action="store_true", help="启动GUI模式")
    
    args = parser.parse_args()
    
    if args.check_env:
        # 仅检测环境
        automator = MemoryDumpAutomator("test")
        automator.check_environment()
        return
    
    if not args.target:
        print("Error: 请指定目标进程名")
        parser.print_help()
        return
    
    # 创建自动化工具实例
    automator = MemoryDumpAutomator(args.target, args.output)
    
    # 执行Dump
    if automator.create_dump():
        automator.post_process()
    
if __name__ == "__main__":
    main()
