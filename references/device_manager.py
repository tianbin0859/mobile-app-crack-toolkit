import subprocess, json, time, os
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

class DeviceType(Enum):
    USB = "usb"
    EMULATOR = "emulator"
    CLOUD = "cloud"
    WIFI = "wifi"

class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"

@dataclass
class Device:
    id: str
    name: str
    type: DeviceType
    status: DeviceStatus
    android_version: str = ""
    api_level: int = 0
    abi: str = ""
    is_rooted: bool = False
    frida_server: bool = False
    properties: Dict = field(default_factory=dict)

@dataclass
class BatchResult:
    device_id: str
    success: bool
    output: str
    error: str = ""
    duration: float = 0.0

class DeviceManager:
    """远程设备管理器 - 多设备并发控制"""
    
    def __init__(self, max_workers: int = 10):
        self.devices: Dict[str, Device] = {}
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._refresh_devices()
    
    def _refresh_devices(self):
        """刷新设备列表"""
        try:
            result = subprocess.run(
                ["adb", "devices", "-l"],
                capture_output=True, text=True, timeout=10
            )
            
            lines = result.stdout.strip().split("\n")[1:]  # 跳过标题
            
            for line in lines:
                if not line.strip():
                    continue
                    
                parts = line.split()
                device_id = parts[0]
                status = parts[1]
                
                # 解析额外信息
                props = {}
                for part in parts[2:]:
                    if ":" in part:
                        k, v = part.split(":", 1)
                        props[k] = v
                
                # 判断设备类型
                device_type = DeviceType.USB
                if "emulator" in device_id.lower():
                    device_type = DeviceType.EMULATOR
                elif ":" in device_id:
                    device_type = DeviceType.WIFI
                
                # 获取详细信息
                device = self._get_device_info(device_id, device_type, status, props)
                self.devices[device_id] = device
                
        except Exception as e:
            print(f"⚠️ 刷新设备失败: {e}")
    
    def _get_device_info(self, device_id: str, device_type: DeviceType,
                        status: str, props: Dict) -> Device:
        """获取设备详细信息"""
        device_status = DeviceStatus.ONLINE if status == "device" else DeviceStatus.OFFLINE
        
        # 获取Android版本
        android_version = ""
        api_level = 0
        try:
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "getprop", "ro.build.version.release"],
                capture_output=True, text=True, timeout=5
            )
            android_version = result.stdout.strip()
            
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "getprop", "ro.build.version.sdk"],
                capture_output=True, text=True, timeout=5
            )
            api_level = int(result.stdout.strip())
        except:
            pass
        
        # 检查root
        is_rooted = False
        try:
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "su", "-c", "id"],
                capture_output=True, text=True, timeout=5
            )
            is_rooted = "uid=0" in result.stdout
        except:
            pass
        
        # 检查Frida-Server
        frida_server = False
        try:
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "ps", "|", "grep", "frida-server"],
                capture_output=True, text=True, timeout=5
            )
            frida_server = "frida-server" in result.stdout
        except:
            pass
        
        return Device(
            id=device_id,
            name=props.get("model", device_id),
            type=device_type,
            status=device_status,
            android_version=android_version,
            api_level=api_level,
            abi=props.get("abi", ""),
            is_rooted=is_rooted,
            frida_server=frida_server,
            properties=props
        )
    
    def list_devices(self, status: Optional[DeviceStatus] = None) -> List[Device]:
        """列出设备"""
        self._refresh_devices()
        
        devices = list(self.devices.values())
        if status:
            devices = [d for d in devices if d.status == status]
        
        return devices
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """获取设备信息"""
        return self.devices.get(device_id)
    
    def connect_device(self, device_id: str, mode: str = "usb") -> bool:
        """连接设备"""
        try:
            if mode == "wifi":
                # 通过WiFi连接
                subprocess.run(
                    ["adb", "connect", device_id],
                    capture_output=True, text=True, timeout=10
                )
            
            self._refresh_devices()
            return device_id in self.devices
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def disconnect_device(self, device_id: str) -> bool:
        """断开设备"""
        try:
            if ":" in device_id:
                subprocess.run(
                    ["adb", "disconnect", device_id],
                    capture_output=True, text=True, timeout=10
                )
            
            if device_id in self.devices:
                del self.devices[device_id]
            
            return True
            
        except Exception as e:
            print(f"❌ 断开失败: {e}")
            return False
    
    def execute(self, device_id: str, command: str,
               timeout: int = 60) -> BatchResult:
        """在设备上执行命令"""
        start = time.time()
        
        try:
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", command],
                capture_output=True, text=True, timeout=timeout
            )
            
            return BatchResult(
                device_id=device_id,
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                duration=time.time() - start
            )
            
        except Exception as e:
            return BatchResult(
                device_id=device_id,
                success=False,
                output="",
                error=str(e),
                duration=time.time() - start
            )
    
    def execute_batch(self, device_ids: List[str], command: str,
                     callback: Optional[Callable] = None) -> List[BatchResult]:
        """批量执行命令"""
        results = []
        
        futures = {
            self.executor.submit(self.execute, did, command): did
            for did in device_ids
        }
        
        for future in as_completed(futures):
            did = futures[future]
            try:
                result = future.result()
                results.append(result)
                
                if callback:
                    callback(result)
                    
            except Exception as e:
                results.append(BatchResult(
                    device_id=did,
                    success=False,
                    output="",
                    error=str(e)
                ))
        
        return results
    
    def install_apk(self, device_id: str, apk_path: str) -> bool:
        """安装APK"""
        try:
            result = subprocess.run(
                ["adb", "-s", device_id, "install", "-r", apk_path],
                capture_output=True, text=True, timeout=60
            )
            
            success = "Success" in result.stdout
            if success:
                print(f"✅ 安装成功: {device_id}")
            else:
                print(f"❌ 安装失败: {result.stderr}")
            
            return success
            
        except Exception as e:
            print(f"❌ 安装异常: {e}")
            return False
    
    def install_batch(self, device_ids: List[str], apk_path: str) -> Dict[str, bool]:
        """批量安装APK"""
        results = {}
        
        for did in device_ids:
            results[did] = self.install_apk(did, apk_path)
        
        return results
    
    def screenshot(self, device_id: str, output_path: Optional[str] = None) -> str:
        """截图"""
        try:
            # 截图到设备
            subprocess.run(
                ["adb", "-s", device_id, "shell", "screencap", "-p", "/data/local/tmp/screen.png"],
                capture_output=True, text=True, timeout=10
            )
            
            # 拉取到本地
            if not output_path:
                output_path = "/tmp/screenshot_" + device_id.replace(":", "_") + ".png"
            
            subprocess.run(
                ["adb", "-s", device_id, "pull", "/data/local/tmp/screen.png", output_path],
                capture_output=True, text=True, timeout=10
            )
            
            print(f"✅ 截图保存: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 截图失败: {e}")
            return ""
    
    def push_file(self, device_id: str, local_path: str,
                  remote_path: str) -> bool:
        """推送文件"""
        try:
            result = subprocess.run(
                ["adb", "-s", device_id, "push", local_path, remote_path],
                capture_output=True, text=True, timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ 推送失败: {e}")
            return False
    
    def pull_file(self, device_id: str, remote_path: str,
                  local_path: str) -> bool:
        """拉取文件"""
        try:
            result = subprocess.run(
                ["adb", "-s", device_id, "pull", remote_path, local_path],
                capture_output=True, text=True, timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ 拉取失败: {e}")
            return False
    
    def start_frida_server(self, device_id: str,
                          server_path: str = "/data/local/tmp/frida-server") -> bool:
        """启动Frida-Server"""
        try:
            # 检查是否存在
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "ls", server_path],
                capture_output=True, text=True, timeout=5
            )
            
            if "No such file" in result.stderr:
                print(f"⚠️ Frida-Server未安装: {device_id}")
                return False
            
            # 启动服务
            cmd = f"{server_path} &"
            subprocess.run(
                ["adb", "-s", device_id, "shell", "su", "-c", cmd],
                capture_output=True, text=True, timeout=5
            )
            
            # 验证
            time.sleep(1)
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "ps", "|", "grep", "frida-server"],
                capture_output=True, text=True, timeout=5
            )
            
            if "frida-server" in result.stdout:
                print(f"✅ Frida-Server已启动: {device_id}")
                return True
            else:
                print(f"❌ Frida-Server启动失败: {device_id}")
                return False
                
        except Exception as e:
            print(f"❌ 启动异常: {e}")
            return False
    
    def get_device_summary(self) -> Dict:
        """获取设备摘要"""
        self._refresh_devices()
        
        total = len(self.devices)
        online = sum(1 for d in self.devices.values() if d.status == DeviceStatus.ONLINE)
        rooted = sum(1 for d in self.devices.values() if d.is_rooted)
        frida = sum(1 for d in self.devices.values() if d.frida_server)
        
        return {
            "total": total,
            "online": online,
            "offline": total - online,
            "rooted": rooted,
            "frida_ready": frida,
            "devices": [
                {
                    "id": d.id,
                    "name": d.name,
                    "type": d.type.value,
                    "status": d.status.value,
                    "android": d.android_version,
                    "rooted": d.is_rooted,
                    "frida": d.frida_server
                }
                for d in self.devices.values()
            ]
        }

# 便捷函数
def list_devices() -> List[Device]:
    """快速列出设备"""
    manager = DeviceManager()
    return manager.list_devices()

def execute_on_all(command: str, callback: Optional[Callable] = None) -> List[BatchResult]:
    """在所有设备上执行命令"""
    manager = DeviceManager()
    devices = manager.list_devices(DeviceStatus.ONLINE)
    device_ids = [d.id for d in devices]
    
    if not device_ids:
        print("⚠️ 无在线设备")
        return []
    
    return manager.execute_batch(device_ids, command, callback)
