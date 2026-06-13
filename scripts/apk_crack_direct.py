#!/usr/bin/env python3
"""
APK Crack Engine - 直接执行版主控脚本
输入APK包名 → 自动连接手机 → 直接执行破解
"""

import os
import sys
import subprocess
import json
import re
import time
from typing import Optional, Dict, List

# 尝试导入frida
try:
    import frida
except ImportError:
    print("[!] Frida未安装，运行: pip install frida-tools")
    frida = None


class APKCracker:
    """APK直接破解器"""

    def __init__(self, package_name: str, apk_path: Optional[str] = None):
        self.package_name = package_name
        self.apk_path = apk_path or f"/tmp/{package_name}.apk"
        self.device = None
        self.session = None
        self._check_env()

    def _check_env(self):
        """检查环境"""
        # 检查adb
        if subprocess.run(["which", "adb"], capture_output=True).returncode != 0:
            raise RuntimeError("adb未安装")
        
        # 检查手机连接
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        if "device" not in result.stdout.split("\n")[1]:
            raise RuntimeError("手机未连接，请连接后开启USB调试")
        
        # 检查frida-server
        result = subprocess.run(
            ["adb", "shell", "ps | grep frida-server"],
            capture_output=True, text=True
        )
        if "frida-server" not in result.stdout:
            print("[*] 启动frida-server...")
            subprocess.run([
                "adb", "shell", "/data/local/tmp/frida-server &"
            ], capture_output=True)
            time.sleep(2)
        
        print("[+] 环境检查通过")

    def analyze(self) -> Dict:
        """分析APK"""
        print(f"[*] 分析APK: {self.package_name}")
        
        # 获取APK信息
        result = subprocess.run(
            ["adb", "shell", f"dumpsys package {self.package_name}"],
            capture_output=True, text=True
        )
        
        info = {
            "package": self.package_name,
            "path": None,
            "version": None,
            "shell_type": None
        }
        
        # 提取路径
        path_match = re.search(r"path:\s*(\S+)", result.stdout)
        if path_match:
            info["path"] = path_match.group(1)
        
        # 提取版本
        ver_match = re.search(r"versionName=(\S+)", result.stdout)
        if ver_match:
            info["version"] = ver_match.group(1)
        
        # 查壳
        info["shell_type"] = self.detect_shell()
        
        print(f"[+] 分析结果:")
        print(f"    包名: {info['package']}")
        print(f"    版本: {info['version']}")
        print(f"    路径: {info['path']}")
        print(f"    壳类型: {info['shell_type']}")
        
        return info

    def detect_shell(self) -> str:
        """检测壳类型"""
        # 获取APK路径
        result = subprocess.run(
            ["adb", "shell", f"pm path {self.package_name}"],
            capture_output=True, text=True
        )
        apk_path = result.stdout.replace("package:", "").strip()
        
        # 提取并分析SO
        subprocess.run([
            "adb", "pull", apk_path, "/tmp/target.apk"
        ], capture_output=True)
        
        # 解压查看SO
        subprocess.run([
            "unzip", "-o", "/tmp/target.apk", "lib/*.so", "-d", "/tmp/apk_lib/"
        ], capture_output=True)
        
        # 检查SO特征
        so_files = []
        lib_dir = "/tmp/apk_lib/lib"
        if os.path.exists(lib_dir):
            for root, dirs, files in os.walk(lib_dir):
                for f in files:
                    if f.endswith(".so"):
                        so_files.append(f)
        
        # 识别壳
        shell_patterns = {
            "360": ["libjiagu", "libjiagu_art"],
            "梆梆": ["libsecexe", "libsecmain"],
            "爱加密": ["libexec", "libexecmain"],
            "腾讯": ["libshell", "libtup"],
            "百度": ["libbaiduprotect"],
            "网易": ["libnesec"],
            "阿里": ["libmobisec"],
        }
        
        for shell_name, patterns in shell_patterns.items():
            for so in so_files:
                for pattern in patterns:
                    if pattern in so:
                        return shell_name
        
        return "none"

    def auto_unpack(self) -> List[str]:
        """自动脱壳"""
        print("[*] 开始自动脱壳...")
        
        shell_type = self.detect_shell()
        print(f"[*] 检测到壳: {shell_type}")
        
        if shell_type == "none":
            print("[*] 未检测到壳，直接提取DEX")
            return self._extract_dex()
        
        # 使用FRIDA-DEXDump
        print("[*] 使用FRIDA-DEXDump脱壳...")
        return self._frida_dump()

    def _extract_dex(self) -> List[str]:
        """直接提取DEX"""
        subprocess.run([
            "adb", "pull", 
            f"/data/app/{self.package_name}-*/base.apk",
            "/tmp/base.apk"
        ], capture_output=True)
        
        subprocess.run([
            "unzip", "-o", "/tmp/base.apk", "*.dex", "-d", "/tmp/extracted/"
        ], capture_output=True)
        
        dex_files = []
        if os.path.exists("/tmp/extracted"):
            for f in os.listdir("/tmp/extracted"):
                if f.endswith(".dex"):
                    dex_files.append(f"/tmp/extracted/{f}")
        
        print(f"[+] 提取完成: {len(dex_files)}个DEX文件")
        return dex_files

    def _frida_dump(self) -> List[str]:
        """Frida内存Dump"""
        if not frida:
            print("[!] Frida未安装")
            return []
        
        try:
            device = frida.get_usb_device()
            pid = device.spawn([self.package_name])
            session = device.attach(pid)
            
            script = session.create_script("""
                var dumped = [];
                
                function dump_dex() {
                    var modules = Process.enumerateModules();
                    modules.forEach(function(module) {
                        if (module.name.indexOf("libjiagu") !== -1 ||
                            module.name.indexOf("libsecexe") !== -1) {
                            console.log("[*] Found shell: " + module.name);
                        }
                    });
                    
                    // Hook open寻找DEX
                    var open = Module.findExportByName(null, "open");
                    Interceptor.attach(open, {
                        onEnter: function(args) {
                            var path = Memory.readUtf8String(args[0]);
                            if (path.indexOf(".dex") !== -1) {
                                console.log("[*] DEX opened: " + path);
                            }
                        }
                    });
                }
                
                dump_dex();
            """)
            
            script.load()
            device.resume(pid)
            
            print("[*] Frida脱壳注入完成，操作APP触发加载...")
            return ["/tmp/dumped/"]
            
        except Exception as e:
            print(f"[!] Frida脱壳失败: {e}")
            return []

    def crack_vip(self) -> bool:
        """直接破解VIP"""
        print(f"[*] 开始VIP破解: {self.package_name}")
        
        if not frida:
            print("[!] Frida未安装")
            return False
        
        try:
            device = frida.get_usb_device()
            pid = device.spawn([self.package_name])
            session = device.attach(pid)
            
            script = session.create_script("""
                Java.perform(function() {
                    console.log("[*] VIP破解注入开始...");
                    
                    // Hook SharedPreferences
                    var SharedPreferences = Java.use("android.content.SharedPreferences");
                    var Editor = Java.use("android.content.SharedPreferences$Editor");
                    
                    SharedPreferences.getBoolean.implementation = function(key, defValue) {
                        if (key && (key.indexOf("vip") !== -1 || 
                                   key.indexOf("auth") !== -1 ||
                                   key.indexOf("premium") !== -1)) {
                            console.log("[+] Forcing " + key + " = true");
                            return true;
                        }
                        return this.getBoolean(key, defValue);
                    };
                    
                    // Hook Editor.putBoolean
                    Editor.putBoolean.implementation = function(key, value) {
                        if (key && (key.indexOf("vip") !== -1 || 
                                   key.indexOf("auth") !== -1)) {
                            console.log("[+] Intercepted putBoolean: " + key + " = true");
                            return this.putBoolean(key, true);
                        }
                        return this.putBoolean(key, value);
                    };
                    
                    // 自动枚举Hook
                    Java.enumerateLoadedClasses({
                        onMatch: function(className) {
                            if (className.match(/vip|premium|auth|license|member/i)) {
                                try {
                                    var cls = Java.use(className);
                                    var methods = cls.class.getDeclaredMethods();
                                    methods.forEach(function(method) {
                                        var name = method.getName();
                                        if (name.match(/isVip|check|verify|auth|isMember|isPremium/i)) {
                                            cls[name].implementation = function() {
                                                console.log("[+] Hooked: " + className + "." + name);
                                                return true;
                                            };
                                        }
                                    });
                                } catch(e) {}
                            }
                        },
                        onComplete: function() {
                            console.log("[*] VIP破解注入完成");
                        }
                    });
                });
            """)
            
            script.on('message', lambda msg: print(f"[*] {msg['payload']}"))
            script.load()
            device.resume(pid)
            
            self.session = session
            print(f"[+] VIP破解已激活: {self.package_name}")
            print("[*] 按Ctrl+C停止...")
            
            # 保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                session.detach()
                print("\n[*] 已停止")
            
            return True
            
        except Exception as e:
            print(f"[!] VIP破解失败: {e}")
            return False

    def bypass_network_auth(self) -> bool:
        """绕过网络验证"""
        print("[*] 网络验证绕过需要mitmproxy，请手动设置代理")
        print("[*] 或使用Frida Hook网络请求")
        
        if not frida:
            return False
        
        try:
            device = frida.get_usb_device()
            pid = device.spawn([self.package_name])
            session = device.attach(pid)
            
            script = session.create_script("""
                Java.perform(function() {
                    // Hook OkHttp响应
                    try {
                        var Response = Java.use("okhttp3.Response");
                        var ResponseBody = Java.use("okhttp3.ResponseBody");
                        var MediaType = Java.use("okhttp3.MediaType");
                        
                        Response.body.implementation = function() {
                            var original = this.body.value;
                            var content = original.string();
                            
                            var modified = content
                                .replace('"status":0', '"status":1')
                                .replace('"status": false', '"status": true')
                                .replace('"vip":false', '"vip":true')
                                .replace('"vip": false', '"vip": true')
                                .replace('"code":0', '"code":1')
                                .replace('"success":false', '"success":true');
                            
                            return ResponseBody.create(
                                MediaType.parse("application/json"),
                                modified
                            );
                        };
                    } catch(e) {}
                    
                    // Hook HttpURLConnection
                    try {
                        var HttpURLConnection = Java.use("java.net.HttpURLConnection");
                        HttpURLConnection.getResponseCode.implementation = function() {
                            return 200;
                        };
                    } catch(e) {}
                    
                    console.log("[*] 网络响应Hook已注入");
                });
            """)
            
            script.load()
            device.resume(pid)
            
            print("[+] 网络验证绕过已激活")
            return True
            
        except Exception as e:
            print(f"[!] 网络绕过失败: {e}")
            return False

    def decrypt_lua_scripts(self) -> bool:
        """解密Lua脚本"""
        print(f"[*] 开始Lua脚本提取: {self.package_name}")
        
        if not frida:
            return False
        
        try:
            device = frida.get_usb_device()
            session = device.attach(self.package_name)
            
            # 创建输出目录
            os.makedirs("/tmp/lua_dump", exist_ok=True)
            
            script = session.create_script("""
                var dumpDir = "/sdcard/lua_dump/";
                
                // 创建目录
                var File = Java.use("java.io.File");
                var dir = File.$new(dumpDir);
                dir.mkdirs();
                
                // Hook luaL_loadbufferx
                var luaLoad = Module.findExportByName(null, "luaL_loadbufferx");
                if (!luaLoad) {
                    // 尝试其他Lua库名
                    var modules = Process.enumerateModules();
                    modules.forEach(function(module) {
                        if (module.name.indexOf("lua") !== -1) {
                            console.log("[*] Found Lua module: " + module.name);
                        }
                    });
                }
                
                if (luaLoad) {
                    Interceptor.attach(luaLoad, {
                        onEnter: function(args) {
                            var size = args[2].toInt32();
                            var buf = args[1];
                            var data = Memory.readByteArray(buf, size);
                            
                            var filename = dumpDir + "script_" + Date.now() + ".lua";
                            var file = new File(filename, "wb");
                            file.write(data);
                            file.close();
                            
                            send({"type": "lua_dump", "file": filename, "size": size});
                        }
                    });
                }
                
                console.log("[*] Lua脚本Hook已注入");
            """)
            
            def on_message(message, data):
                if message['type'] == 'send':
                    payload = message['payload']
                    print(f"[+] Lua脚本已保存: {payload['file']} ({payload['size']} bytes)")
            
            script.on('message', on_message)
            script.load()
            
            print("[+] Lua脚本自动提取已启动")
            print("[*] 操作APP触发Lua加载即可自动保存")
            
            return True
            
        except Exception as e:
            print(f"[!] Lua提取失败: {e}")
            return False

    def modify_and_repack(self, changes: Dict[str, str]) -> Optional[str]:
        """修改并重打包APK"""
        print("[*] 开始APK修改...")
        
        decoded_dir = f"/tmp/{self.package_name}_decoded"
        output_apk = f"/tmp/{self.package_name}_modified.apk"
        
        # 1. 获取APK
        result = subprocess.run(
            ["adb", "shell", f"pm path {self.package_name}"],
            capture_output=True, text=True
        )
        apk_path = result.stdout.replace("package:", "").strip()
        
        subprocess.run(["adb", "pull", apk_path, "/tmp/target.apk"], capture_output=True)
        
        # 2. 反编译
        subprocess.run(["apktool", "d", "/tmp/target.apk", "-o", decoded_dir, "-f"], capture_output=True)
        
        # 3. 修改
        if "app_name" in changes:
            self._change_app_name(decoded_dir, changes["app_name"])
        if "icon" in changes:
            self._replace_icon(decoded_dir, changes["icon"])
        if "package" in changes:
            self._change_package(decoded_dir, changes["package"])
        
        # 4. 重打包
        subprocess.run(["apktool", "b", decoded_dir, "-o", output_apk], capture_output=True)
        
        # 5. 签名
        self._sign_apk(output_apk)
        
        print(f"[+] 修改完成: {output_apk}")
        return output_apk

    def _change_app_name(self, decoded_dir: str, new_name: str):
        """修改应用名称"""
        strings_path = os.path.join(decoded_dir, "res/values/strings.xml")
        if os.path.exists(strings_path):
            with open(strings_path, 'r', encoding='utf-8') as f:
                content = f.read()
            content = re.sub(
                r'(<string name="app_name">)([^<]+)(</string>)',
                rf'\g<1>{new_name}\g<3>',
                content
            )
            with open(strings_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[+] 应用名称已修改为: {new_name}")

    def _replace_icon(self, decoded_dir: str, icon_path: str):
        """替换图标"""
        res_dir = os.path.join(decoded_dir, "res")
        if os.path.exists(res_dir):
            for root, dirs, files in os.walk(res_dir):
                for file in files:
                    if "ic_launcher" in file or "logo" in file:
                        if file.endswith(".png"):
                            target = os.path.join(root, file)
                            subprocess.run(["cp", icon_path, target], capture_output=True)
                            print(f"[+] 图标已替换: {target}")

    def _change_package(self, decoded_dir: str, new_package: str):
        """修改包名"""
        manifest_path = os.path.join(decoded_dir, "AndroidManifest.xml")
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                content = f.read()
            
            old_package = re.search(r'package="([^"]+)"', content)
            if old_package:
                old = old_package.group(1)
                content = content.replace(f'package="{old}"', f'package="{new_package}"')
                
                with open(manifest_path, 'w') as f:
                    f.write(content)
                print(f"[+] 包名已修改: {old} -> {new_package}")

    def _sign_apk(self, apk_path: str):
        """签名APK"""
        keystore = "/tmp/debug.keystore"
        
        # 生成调试密钥（如果不存在）
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
        
        print("[+] APK已签名")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="APK Crack Engine - 直接执行版")
    parser.add_argument("package", help="目标APK包名")
    parser.add_argument("--vip", action="store_true", help="破解VIP限制")
    parser.add_argument("--unpack", action="store_true", help="脱壳")
    parser.add_argument("--network", action="store_true", help="绕过网络验证")
    parser.add_argument("--lua", action="store_true", help="解密Lua脚本")
    parser.add_argument("--modify", nargs='+', help="修改APK (name=xxx icon=xxx package=xxx)")
    parser.add_argument("--all", action="store_true", help="执行全部破解")
    
    args = parser.parse_args()
    
    cracker = APKCracker(args.package)
    
    if args.all:
        print("[*] 执行全量破解...")
        cracker.auto_unpack()
        cracker.crack_vip()
        cracker.bypass_network_auth()
        print("[+] 全量破解完成")
    elif args.vip:
        cracker.crack_vip()
    elif args.unpack:
        cracker.auto_unpack()
    elif args.network:
        cracker.bypass_network_auth()
    elif args.lua:
        cracker.decrypt_lua_scripts()
    elif args.modify:
        changes = dict(m.split("=") for m in args.modify)
        cracker.modify_and_repack(changes)
    else:
        cracker.analyze()


if __name__ == "__main__":
    main()
