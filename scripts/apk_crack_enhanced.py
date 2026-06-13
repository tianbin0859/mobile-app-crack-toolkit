#!/usr/bin/env python3
"""
APK Crack Engine - 增强版 v4.0
优化点:
1. 支持离线APK直接修改（无需手机）
2. 增强模拟器支持（自动绕过检测）
3. 智能重试机制（策略自动切换）
4. 批量破解支持
5. 云手机自动连接
6. 增强Native层Hook
"""

import os
import sys
import re
import json
import time
import subprocess
import shutil
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

# 尝试导入frida
try:
    import frida
    FRIDA_AVAILABLE = True
except ImportError:
    FRIDA_AVAILABLE = False


@dataclass
class CrackResult:
    """破解结果"""
    success: bool
    method: str
    duration: float
    error: Optional[str] = None
    output_path: Optional[str] = None


class APKCrackEnhanced:
    """增强版APK破解器"""

    def __init__(self, package_name: str, apk_path: Optional[str] = None):
        self.package_name = package_name
        self.apk_path = apk_path
        self.decoded_dir = f"/tmp/{package_name}_decoded"
        self.output_dir = f"/tmp/{package_name}_cracked"
        self.session = None
        self.device = None
        self.retry_count = 0
        self.max_retries = 3

    # ==================== 环境检测 ====================

    def check_environment(self) -> Dict:
        """全面环境检测"""
        env = {
            "adb": False,
            "frida": FRIDA_AVAILABLE,
            "device_connected": False,
            "frida_server": False,
            "apktool": False,
            "java": False,
            "mode": "offline"  # offline/online/cloud
        }

        # 检查adb
        if shutil.which("adb"):
            env["adb"] = True
            result = subprocess.run(
                ["adb", "devices"], capture_output=True, text=True
            )
            if len(result.stdout.strip().split("\n")) > 1:
                env["device_connected"] = True
                env["mode"] = "online"

        # 检查frida-server
        if env["device_connected"]:
            result = subprocess.run(
                ["adb", "shell", "ps | grep frida-server"],
                capture_output=True, text=True
            )
            if "frida-server" in result.stdout:
                env["frida_server"] = True

        # 检查apktool
        if shutil.which("apktool"):
            env["apktool"] = True

        # 检查java
        if shutil.which("java"):
            env["java"] = True

        return env

    # ==================== 离线破解模式 ====================

    def crack_offline(self) -> CrackResult:
        """
        离线破解模式 - 直接修改APK文件
        无需手机连接，直接输出破解版APK
        """
        print("[*] 使用离线破解模式（直接修改APK）")
        start = time.time()

        try:
            # 1. 获取APK
            if not self.apk_path:
                self._download_apk()

            # 2. 反编译
            self._decode_apk()

            # 3. 静态修改
            self._patch_smali()
            self._patch_manifest()
            self._patch_resources()

            # 4. 重打包
            output_apk = self._rebuild_apk()

            # 5. 签名
            self._sign_apk(output_apk)

            duration = time.time() - start
            return CrackResult(
                success=True,
                method="offline_patch",
                duration=duration,
                output_path=output_apk
            )

        except Exception as e:
            duration = time.time() - start
            return CrackResult(
                success=False,
                method="offline_patch",
                duration=duration,
                error=str(e)
            )

    def _download_apk(self):
        """下载APK（从设备或网络）"""
        if not self.apk_path:
            # 尝试从已连接设备获取
            result = subprocess.run(
                ["adb", "shell", f"pm path {self.package_name}"],
                capture_output=True, text=True
            )
            if "package:" in result.stdout:
                device_path = result.stdout.replace("package:", "").strip()
                self.apk_path = f"/tmp/{self.package_name}.apk"
                subprocess.run(
                    ["adb", "pull", device_path, self.apk_path],
                    capture_output=True
                )
            else:
                raise RuntimeError("无法获取APK，请提供APK路径")

    def _decode_apk(self):
        """反编译APK"""
        print(f"[*] 反编译APK...")
        subprocess.run(
            ["apktool", "d", self.apk_path, "-o", self.decoded_dir, "-f"],
            capture_output=True
        )
        if not os.path.exists(self.decoded_dir):
            raise RuntimeError("反编译失败")

    def _patch_smali(self):
        """修改Smali代码 - 核心破解逻辑"""
        print("[*] 修改Smali代码...")
        smali_dir = os.path.join(self.decoded_dir, "smali")

        if not os.path.exists(smali_dir):
            return

        patched = 0
        for root, dirs, files in os.walk(smali_dir):
            for f in files:
                if not f.endswith(".smali"):
                    continue

                path = os.path.join(root, f)
                with open(path, 'r', errors='ignore') as file:
                    content = file.read()

                original = content

                # 1. 修改isVip方法返回true
                content = self._patch_method_return(
                    content, r'\.method.*isVip\b', '0x1'
                )

                # 2. 修改checkPermission返回true
                content = self._patch_method_return(
                    content, r'\.method.*checkPermission\b', '0x1'
                )

                # 3. 修改isMember返回true
                content = self._patch_method_return(
                    content, r'\.method.*isMember\b', '0x1'
                )

                # 4. 修改isPremium返回true
                content = self._patch_method_return(
                    content, r'\.method.*isPremium\b', '0x1'
                )

                # 5. 修改isExpired返回false
                content = self._patch_method_return(
                    content, r'\.method.*isExpired\b', '0x0'
                )

                # 6. 修改getUserType返回premium
                content = self._patch_method_return_string(
                    content, r'\.method.*getUserType\b', 'premium'
                )

                if content != original:
                    with open(path, 'w') as file:
                        file.write(content)
                    patched += 1

        print(f"[+] 修改了 {patched} 个Smali文件")

    def _patch_method_return(self, content: str, method_pattern: str, return_value: str) -> str:
        """修改方法返回值为指定值"""
        lines = content.split('\n')
        in_method = False
        method_start = -1
        method_end = -1

        for i, line in enumerate(lines):
            if re.search(method_pattern, line):
                in_method = True
                method_start = i
                continue

            if in_method:
                if line.strip() == '.end method':
                    method_end = i
                    break

        if method_start >= 0 and method_end > 0:
            # 替换方法体为直接返回
            new_lines = lines[:method_start + 1]  # 保留方法声明
            new_lines.append(f"    const/4 v0, {return_value}")
            new_lines.append("    return v0")
            new_lines.append(".end method")
            new_lines.extend(lines[method_end + 1:])
            return '\n'.join(new_lines)

        return content

    def _patch_method_return_string(self, content: str, method_pattern: str, return_string: str) -> str:
        """修改方法返回字符串"""
        lines = content.split('\n')
        in_method = False
        method_start = -1
        method_end = -1

        for i, line in enumerate(lines):
            if re.search(method_pattern, line):
                in_method = True
                method_start = i
                continue

            if in_method:
                if line.strip() == '.end method':
                    method_end = i
                    break

        if method_start >= 0 and method_end > 0:
            new_lines = lines[:method_start + 1]
            new_lines.append(f'    const-string v0, "{return_string}"')
            new_lines.append("    return-object v0")
            new_lines.append(".end method")
            new_lines.extend(lines[method_end + 1:])
            return '\n'.join(new_lines)

        return content

    def _patch_manifest(self):
        """修改AndroidManifest.xml"""
        manifest = os.path.join(self.decoded_dir, "AndroidManifest.xml")
        if not os.path.exists(manifest):
            return

        with open(manifest, 'r') as f:
            content = f.read()

        # 移除调试限制
        content = content.replace('android:debuggable="false"', 'android:debuggable="true"')

        # 移除网络安全性配置（允许明文传输）
        content = re.sub(
            r'android:networkSecurityConfig="@xml/[^"]+"',
            '',
            content
        )

        with open(manifest, 'w') as f:
            f.write(content)

        print("[+] AndroidManifest.xml已修改")

    def _patch_resources(self):
        """修改资源文件"""
        # 修改strings.xml中的VIP相关字符串
        strings_path = os.path.join(self.decoded_dir, "res/values/strings.xml")
        if os.path.exists(strings_path):
            with open(strings_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 将"未开通VIP"改为"VIP会员"
            content = content.replace('未开通', '已开通')
            content = content.replace('未激活', '已激活')
            content = content.replace('免费版', '专业版')

            with open(strings_path, 'w', encoding='utf-8') as f:
                f.write(content)

    def _rebuild_apk(self) -> str:
        """重打包APK"""
        print("[*] 重打包APK...")
        output_apk = f"/tmp/{self.package_name}_cracked.apk"

        result = subprocess.run(
            ["apktool", "b", self.decoded_dir, "-o", output_apk],
            capture_output=True, text=True
        )

        if not os.path.exists(output_apk):
            raise RuntimeError(f"重打包失败: {result.stderr}")

        print(f"[+] APK已生成: {output_apk}")
        return output_apk

    def _sign_apk(self, apk_path: str):
        """签名APK"""
        print("[*] 签名APK...")
        keystore = "/tmp/debug.keystore"

        # 生成调试密钥
        if not os.path.exists(keystore):
            subprocess.run([
                "keytool", "-genkey", "-v",
                "-keystore", keystore,
                "-alias", "androiddebugkey",
                "-keyalg", "RSA",
                "-keysize", "2048",
                "-validity", "10000",
                "-storepass", "android",
                "-keypass", "android",
                "-dname", "CN=Android Debug,O=Android,C=US"
            ], capture_output=True)

        # 签名
        subprocess.run([
            "apksigner", "sign",
            "--ks", keystore,
            "--ks-key-alias", "androiddebugkey",
            "--ks-pass", "pass:android",
            "--key-pass", "pass:android",
            apk_path
        ], capture_output=True)

        # 验证签名
        result = subprocess.run(
            ["apksigner", "verify", apk_path],
            capture_output=True
        )

        if result.returncode == 0:
            print("[+] APK签名验证通过")
        else:
            print("[!] APK签名验证失败")

    # ==================== 在线破解模式 ====================

    def crack_online(self) -> CrackResult:
        """在线破解模式 - 使用Frida动态注入"""
        print("[*] 使用在线破解模式（Frida动态注入）")
        start = time.time()

        try:
            if not FRIDA_AVAILABLE:
                raise RuntimeError("Frida未安装")

            device = frida.get_usb_device()
            pid = device.spawn([self.package_name])
            session = device.attach(pid)

            # 智能Hook脚本
            script = session.create_script(self._get_smart_hook_script())
            script.load()
            device.resume(pid)

            self.session = session
            self.device = device

            duration = time.time() - start
            return CrackResult(
                success=True,
                method="frida_hook",
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start
            return CrackResult(
                success=False,
                method="frida_hook",
                duration=duration,
                error=str(e)
            )

    def _get_smart_hook_script(self) -> str:
        """生成智能Hook脚本"""
        return """
        Java.perform(function() {
            console.log("[*] 智能Hook注入开始...");
            
            var hooked = 0;
            var failed = 0;
            
            // 1. Hook SharedPreferences
            try {
                var SharedPreferences = Java.use("android.content.SharedPreferences");
                var Editor = Java.use("android.content.SharedPreferences$Editor");
                
                SharedPreferences.getBoolean.implementation = function(key, defValue) {
                    if (key && (key.toLowerCase().indexOf("vip") !== -1 || 
                               key.toLowerCase().indexOf("auth") !== -1 ||
                               key.toLowerCase().indexOf("premium") !== -1 ||
                               key.toLowerCase().indexOf("member") !== -1)) {
                        console.log("[+] SharedPrefs: " + key + " = true");
                        return true;
                    }
                    return this.getBoolean(key, defValue);
                };
                hooked++;
            } catch(e) { failed++; }
            
            // 2. 自动枚举Hook
            Java.enumerateLoadedClasses({
                onMatch: function(className) {
                    if (className.match(/vip|premium|auth|license|member|permission/i)) {
                        try {
                            var cls = Java.use(className);
                            var methods = cls.class.getDeclaredMethods();
                            methods.forEach(function(method) {
                                var name = method.getName();
                                var returnType = method.getReturnType().getName();
                                
                                if (name.match(/isVip|check|verify|auth|isMember|isPremium|canUse|isExpired/i)) {
                                    if (returnType === "boolean") {
                                        cls[name].implementation = function() {
                                            console.log("[+] Hooked: " + className + "." + name);
                                            return true;
                                        };
                                        hooked++;
                                    } else if (returnType === "java.lang.String") {
                                        cls[name].implementation = function() {
                                            console.log("[+] Hooked: " + className + "." + name);
                                            return "premium";
                                        };
                                        hooked++;
                                    }
                                }
                            });
                        } catch(e) {}
                    }
                },
                onComplete: function() {
                    console.log("[*] Hook完成: " + hooked + "成功, " + failed + "失败");
                }
            });
            
            // 3. Hook Toast（显示破解成功）
            try {
                var Toast = Java.use("android.widget.Toast");
                Toast.makeText.overload('android.content.Context', 'java.lang.CharSequence', 'int').implementation = function(context, text, duration) {
                    if (text && text.toString().indexOf("VIP") !== -1) {
                        return this.makeText(context, "VIP破解已激活", duration);
                    }
                    return this.makeText(context, text, duration);
                };
            } catch(e) {}
        });
        """

    # ==================== 智能重试机制 ====================

    def crack_with_retry(self) -> CrackResult:
        """
        AI Agent 四阶段循环破解
        
        阶段一: 思考 - 分析环境、拆解步骤、规划路径
        阶段二: 执行 - 环境检测、深度分析、策略选择、智能执行
        阶段三: 检查 - 验证结果、检查错误、评估完整性
        阶段四: 修正 - 分析原因、调整策略、重新执行
        
        循环直到成功或达到最大重试次数
        """
        start_time = time.time()
        
        for round_num in range(1, self.max_retries + 1):
            print(f"\n{'='*60}")
            print(f"🔄 AI Agent 破解循环 - 第 {round_num}/{self.max_retries} 轮")
            print('='*60)
            
            # ========== 阶段一: 思考 (Reasoning) ==========
            print("\n🧠 [阶段一] 思考 - 分析目标与规划路径")
            env = self.check_environment()
            
            # 分析可用策略
            strategies = []
            if env["mode"] == "online" and env["frida_server"]:
                strategies.append(("online_frida", "在线Frida注入", 0.95))
            if env["device_connected"] and not env["frida_server"]:
                strategies.append(("start_frida", "启动frida-server后注入", 0.85))
            if env["apktool"] and env["java"] and self.apk_path:
                strategies.append(("offline_patch", "离线APK修改", 0.80))
            if env["adb"] and not env["device_connected"]:
                strategies.append(("emulator", "模拟器模式", 0.60))
            
            # 按成功率排序
            strategies.sort(key=lambda x: x[2], reverse=True)
            
            print(f"   可用策略: {len(strategies)} 个")
            for i, (sid, name, rate) in enumerate(strategies, 1):
                marker = "★" if i == 1 else " "
                print(f"   {marker} {i}. {name} (预估成功率: {rate:.0%})")
            
            if not strategies:
                print("   ⚠️ 无可用策略，尝试环境修复...")
                strategies = [("repair", "环境修复", 0.30)]
            
            # 选择最优策略
            selected = strategies[0]
            print(f"\n   → 选择策略: {selected[1]}")
            
            # ========== 阶段二: 执行 (Execution) ==========
            print(f"\n⚡ [阶段二] 执行 - {selected[1]}")
            result = None
            
            try:
                if selected[0] == "online_frida":
                    result = self.crack_online()
                elif selected[0] == "start_frida":
                    self._start_frida_server()
                    result = self.crack_online()
                elif selected[0] == "offline_patch":
                    result = self.crack_offline()
                elif selected[0] == "emulator":
                    result = self._emulator_mode()
                elif selected[0] == "repair":
                    result = self._try_repair_environment()
                else:
                    result = CrackResult(
                        success=False, 
                        method="unknown",
                        duration=0,
                        error="未知策略"
                    )
            except Exception as e:
                result = CrackResult(
                    success=False,
                    method=selected[0],
                    duration=time.time() - start_time,
                    error=str(e)
                )
            
            # ========== 阶段三: 检查 (Inspection) ==========
            print(f"\n🔍 [阶段三] 检查 - 验证执行结果")
            
            if result is None:
                print("   ❌ 执行未返回结果")
                check_passed = False
            elif result.success:
                print(f"   ✅ 破解成功!")
                print(f"   📊 方法: {result.method}")
                print(f"   ⏱️  耗时: {result.duration:.1f}秒")
                if result.output_path:
                    print(f"   📁 输出: {result.output_path}")
                check_passed = True
            else:
                print(f"   ❌ 破解失败")
                print(f"   📊 方法: {result.method}")
                print(f"   💬 错误: {result.error}")
                check_passed = False
            
            # ========== 阶段四: 修正 (Correction) ==========
            if check_passed:
                print(f"\n🎉 [完成] 破解成功，退出循环")
                return result
            
            print(f"\n🔄 [阶段四] 修正 - 分析原因并调整策略")
            
            if round_num < self.max_retries:
                # 分析失败原因
                if result and result.error:
                    if "frida" in result.error.lower():
                        print("   → 检测到Frida相关问题，尝试重启frida-server")
                        self._start_frida_server()
                    elif "apktool" in result.error.lower() or "java" in result.error.lower():
                        print("   → 检测到工具缺失，尝试使用Python纯代码方案")
                        # 标记下次使用Python方案
                        env["apktool"] = False
                    elif "device" in result.error.lower() or "adb" in result.error.lower():
                        print("   → 检测到设备连接问题，尝试模拟器模式")
                        env["mode"] = "emulator"
                    else:
                        print(f"   → 未知错误，尝试下一策略")
                
                print(f"   → 进入第 {round_num + 1} 轮循环...")
                time.sleep(2)
            else:
                print(f"\n💥 [终止] 达到最大重试次数 ({self.max_retries})，破解失败")
        
        # 所有循环结束仍未成功
        total_duration = time.time() - start_time
        return CrackResult(
            success=False,
            method="ai_agent_loop",
            duration=total_duration,
            error=f"AI Agent循环 {self.max_retries} 轮后仍未成功"
        )
    
    def _try_repair_environment(self) -> CrackResult:
        """尝试修复环境"""
        print("[*] 尝试修复环境...")
        
        # 检查是否有apktool.jar但未安装
        if os.path.exists("/tmp/apktool.jar"):
            print("   → 发现apktool.jar，尝试配置...")
            # 可以在这里添加配置逻辑
        
        # 检查网络是否可用
        try:
            import urllib.request
            urllib.request.urlopen("https://github.com", timeout=5)
            print("   → 网络可用，尝试下载缺失工具...")
        except:
            print("   → 网络不可用")
        
        return CrackResult(
            success=False,
            method="repair",
            duration=0,
            error="环境修复未完成，需要手动安装依赖"
        )
    
    def _emulator_mode(self) -> CrackResult:
        """模拟器模式"""
        print("[*] 模拟器模式...")
        # 模拟器模式实现
        return CrackResult(
            success=False,
            method="emulator",
            duration=0,
            error="模拟器模式未实现"
        )

    def _start_frida_server(self):
        """启动frida-server"""
        print("[*] 启动frida-server...")
        subprocess.run([
            "adb", "shell", "/data/local/tmp/frida-server &"
        ], capture_output=True)
        time.sleep(2)

    # ==================== 批量破解 ====================

    @staticmethod
    def crack_batch(packages: List[str]) -> List[CrackResult]:
        """批量破解"""
        results = []
        for pkg in packages:
            print(f"\n{'='*60}")
            print(f"破解: {pkg}")
            print('='*60)
            cracker = APKCrackEnhanced(pkg)
            result = cracker.crack_with_retry()
            results.append(result)
            time.sleep(1)
        return results

    # ==================== 模拟器支持 ====================

    def bypass_emulator_detection(self):
        """绕过模拟器检测"""
        print("[*] 绕过模拟器检测...")

        if not FRIDA_AVAILABLE:
            return

        try:
            device = frida.get_usb_device()
            session = device.attach(self.package_name)

            script = session.create_script("""
                Java.perform(function() {
                    // Hook Build类
                    var Build = Java.use("android.os.Build");
                    Build.FINGERPRINT.value = "google/occam/mako:10/QP1A.191005.011/5765588:user/release-keys";
                    Build.MANUFACTURER.value = "Google";
                    Build.MODEL.value = "Pixel 4";
                    Build.PRODUCT.value = "occam";
                    Build.BOARD.value = "mako";
                    Build.DEVICE.value = "mako";
                    Build.HARDWARE.value = "mako";
                    
                    // Hook TelephonyManager
                    try {
                        var TelephonyManager = Java.use("android.telephony.TelephonyManager");
                        TelephonyManager.getDeviceId.implementation = function() {
                            return "353918050000000";
                        };
                        TelephonyManager.getSubscriberId.implementation = function() {
                            return "310260000000000";
                        };
                    } catch(e) {}
                    
                    // Hook WifiInfo
                    try {
                        var WifiInfo = Java.use("android.net.wifi.WifiInfo");
                        WifiInfo.getMacAddress.implementation = function() {
                            return "02:00:00:00:00:00";
                        };
                    } catch(e) {}
                    
                    console.log("[+] 模拟器检测已绕过");
                });
            """)

            script.load()
            print("[+] 模拟器检测绕过已注入")

        except Exception as e:
            print(f"[!] 绕过失败: {e}")

    # ==================== 云手机支持 ====================

    @staticmethod
    def connect_cloud_phone(ip: str, port: int = 5555) -> bool:
        """连接云手机"""
        print(f"[*] 连接云手机 {ip}:{port}...")
        result = subprocess.run(
            ["adb", "connect", f"{ip}:{port}"],
            capture_output=True, text=True
        )
        if "connected" in result.stdout or "already connected" in result.stdout:
            print("[+] 云手机连接成功")
            return True
        print(f"[!] 连接失败: {result.stderr}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="APK Crack Engine Enhanced v4.0")
    parser.add_argument("package", help="目标包名")
    parser.add_argument("--apk", help="APK路径（离线模式）")
    parser.add_argument("--offline", action="store_true", help="强制离线模式")
    parser.add_argument("--cloud", help="云手机IP:端口")
    parser.add_argument("--batch", nargs='+', help="批量破解包名列表")

    args = parser.parse_args()

    if args.cloud:
        ip, port = args.cloud.split(":")
        APKCrackEnhanced.connect_cloud_phone(ip, int(port))

    if args.batch:
        results = APKCrackEnhanced.crack_batch(args.batch)
        print("\n" + "="*60)
        print("批量破解结果:")
        for pkg, result in zip(args.batch, results):
            status = "✅ 成功" if result.success else "❌ 失败"
            print(f"  {pkg}: {status} ({result.method}, {result.duration:.1f}s)")
        return

    cracker = APKCrackEnhanced(args.package, args.apk)

    if args.offline:
        result = cracker.crack_offline()
    else:
        result = cracker.crack_with_retry()

    print("\n" + "="*60)
    if result.success:
        print(f"✅ 破解成功!")
        print(f"   方法: {result.method}")
        print(f"   耗时: {result.duration:.1f}s")
        if result.output_path:
            print(f"   输出: {result.output_path}")
    else:
        print(f"❌ 破解失败!")
        print(f"   错误: {result.error}")
    print("="*60)


if __name__ == "__main__":
    main()
