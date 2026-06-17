# 云手机/远程真机模块实战指南

## 适用场景
- 无实体设备，远程破解 Android/iOS
- 批量设备管理，多账号并发
- 绕过本地环境检测（云手机无 root 痕迹）

## 核心平台

| 平台 | 类型 | 价格 | 特点 |
|------|------|------|------|
| 雷电云手机 | Android | ¥15-50/月 | 稳定，支持 root |
| 红手指 | Android | ¥10-30/月 | 老牌，游戏专用 |
| 爱云兔 | Android | ¥20-60/月 | 高性能 |
| 腾讯 WeTest | Android/iOS | 按量计费 | 企业级 |
| AWS Device Farm | Android/iOS | $0.17/分钟 | 国际品牌 |
| 百度 MTJ | Android | 免费额度 | 测试为主 |
| 自己搭建 | Android | 硬件成本 | 完全可控 |

## 标准流程

### 1. 连接云手机（ADB）
```bash
# 云手机提供 ADB 连接信息
adb connect cloud.phone.ip:5555

# 验证连接
adb devices
# 输出: cloud.phone.ip:5555 device

# 获取 root
adb shell su -c "whoami"
# 输出: root
```

### 2. 远程 Frida 注入
```bash
# 推送 frida-server
adb push frida-server /data/local/tmp/
adb shell chmod 755 /data/local/tmp/frida-server

# 启动 frida-server
adb shell "/data/local/tmp/frida-server &"

# 本地连接远程 frida
frida -H cloud.phone.ip:27042 -f com.game.package

# 或使用 Python 远程连接
import frida

device = frida.get_device_manager().add_remote_device("cloud.phone.ip:27042")
process = device.spawn(["com.game.package"])
session = device.attach(process)
```

### 3. 批量设备管理
```python
#!/usr/bin/env python3
import frida
import concurrent.futures
from dataclasses import dataclass

@dataclass
class CloudDevice:
    ip: str
    port: int = 27042
    name: str = ""
    
class CloudDeviceManager:
    def __init__(self):
        self.devices = []
        
    def add_device(self, ip: str, name: str = ""):
        """添加设备"""
        device = CloudDevice(ip=ip, name=name)
        self.devices.append(device)
        print(f"[+] 添加设备: {name} ({ip})")
        
    def connect_device(self, device: CloudDevice) -> frida.Device:
        """连接单个设备"""
        try:
            remote_device = frida.get_device_manager().add_remote_device(f"{device.ip}:{device.port}")
            print(f"[+] 已连接 {device.name}")
            return remote_device
        except Exception as e:
            print(f"[-] 连接失败 {device.name}: {e}")
            return None
            
    def batch_inject(self, package_name: str, script_code: str, max_workers: int = 5):
        """批量注入脚本"""
        def inject_to_device(device):
            remote = self.connect_device(device)
            if not remote:
                return None
                
            try:
                pid = remote.spawn([package_name])
                session = remote.attach(pid)
                script = session.create_script(script_code)
                script.load()
                remote.resume(pid)
                return {"device": device.name, "status": "success"}
            except Exception as e:
                return {"device": device.name, "status": "failed", "error": str(e)}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(inject_to_device, self.devices))
            
        return results
    
    def batch_screenshot(self, output_dir: str = "./screenshots"):
        """批量截图"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        for device in self.devices:
            remote = self.connect_device(device)
            if not remote:
                continue
                
            # 使用 adb 截图
            import subprocess
            subprocess.run([
                "adb", "-s", f"{device.ip}:5555", "shell", "screencap", "/sdcard/screen.png"
            ])
            subprocess.run([
                "adb", "-s", f"{device.ip}:5555", "pull", "/sdcard/screen.png",
                f"{output_dir}/{device.name}.png"
            ])

if __name__ == "__main__":
    manager = CloudDeviceManager()
    manager.add_device("192.168.1.101", "device_01")
    manager.add_device("192.168.1.102", "device_02")
    manager.add_device("192.168.1.103", "device_03")
    
    # 批量注入
    script = """
    Java.perform(function() {
        console.log("[+] Injected");
    });
    """
    results = manager.batch_inject("com.game.package", script)
    print(results)
```

### 4. 自建云手机（基于 Docker）
```bash
# 使用 redroid 项目（Android 容器化）
docker run -itd --rm \
    --privileged \
    -v ~/data:/data \
    -p 5555:5555 \
    redroid/redroid:11.0.0-latest \
    androidboot.hardware=redroid \
    androidboot.redroid_width=1080 \
    androidboot.redroid_height=1920 \
    androidboot.redroid_fps=60 \
    androidboot.redroid_dpi=480 \
    androidboot.redroid_gpu_mode=guest \
    androidboot.redroid_magisk=1

# 连接
adb connect localhost:5555
```

## 常见问题

### Q: 云手机没有 root？
- 选择支持 root 的云手机（雷电、红手指）
- 或自建 redroid 容器（默认 root）

### Q: ADB 连接不稳定？
- 使用 frida 的远程设备功能
- 或配置 VPN/专线连接

### Q: 云手机检测？
- 部分游戏检测云手机环境
- 使用 Magisk + Hide 模块
- 或修改 build.prop 伪装真机

## 参考
- redroid: https://github.com/remote-android/redroid-doc (⭐ 2.5k)
- frida remote: https://frida.re/docs/android/
