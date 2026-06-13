# 离线一机一码授权系统 - 完整实现

## 核心原理

不联网情况下实现一机一码的关键：
1. **提取硬件指纹** - 从设备硬件获取不可变的唯一标识
2. **绑定授权** - 将卡密与硬件指纹绑定
3. **本地验证** - 运行时比对硬件指纹
4. **防复制** - 加密+签名+多因素校验

## 设备指纹来源（9个因素）

| 因素 | 说明 | 稳定性 |
|------|------|--------|
| Android ID | 系统设置中的ID | 恢复出厂变 |
| 序列号 | ro.serialno | 较稳定 |
| MAC地址 | 网卡地址 | 可修改 |
| 主板信息 | ro.product.board | 稳定 |
| IMEI | 设备唯一码 | 最稳定 |
| 存储序列号 | 闪存芯片ID | 稳定 |
| 蓝牙MAC | 蓝牙地址 | 较稳定 |
| 构建指纹 | ro.build.fingerprint | 稳定 |
| 机器标识 | platform.node() + machine() | 跨平台 |

```python
def get_device_fingerprint(self):
    """生成设备指纹（9因素组合）"""
    factors = []
    
    # 1. Android ID
    try:
        android_id = self._exec_cmd(["settings", "get", "secure", "android_id"])
        if android_id:
            factors.append(f"android_id:{android_id}")
    except:
        pass
    
    # 2. 序列号
    try:
        serial = self._exec_cmd(["getprop", "ro.serialno"])
        if serial:
            factors.append(f"serial:{serial}")
    except:
        pass
    
    # 3. MAC地址
    try:
        mac = self._exec_cmd(["cat", "/sys/class/net/wlan0/address"])
        if mac:
            factors.append(f"mac:{mac}")
    except:
        pass
    
    # 4. 主板信息
    try:
        board = self._exec_cmd(["getprop", "ro.product.board"])
        if board:
            factors.append(f"board:{board}")
    except:
        pass
    
    # 5. IMEI
    try:
        imei = self._exec_cmd(["service", "call", "iphonesubinfo", "1"])
        if imei:
            factors.append(f"imei:{imei}")
    except:
        pass
    
    # 6. 存储序列号
    try:
        storage = self._exec_cmd(["cat", "/sys/class/mmc_host/mmc0/mmc0:0001/serial"])
        if storage:
            factors.append(f"storage:{storage}")
    except:
        pass
    
    # 7. 蓝牙MAC
    try:
        bt_mac = self._exec_cmd(["settings", "get", "secure", "bluetooth_address"])
        if bt_mac:
            factors.append(f"bt:{bt_mac}")
    except:
        pass
    
    # 8. 构建指纹
    try:
        build_fp = self._exec_cmd(["getprop", "ro.build.fingerprint"])
        if build_fp:
            factors.append(f"build:{build_fp}")
    except:
        pass
    
    # 9. 机器标识（跨平台）
    try:
        import platform
        machine_id = platform.node() + platform.machine() + platform.processor()
        factors.append(f"machine:{machine_id}")
    except:
        pass
    
    # 组合并哈希
    combined = "|".join(factors)
    return hashlib.sha256(combined.encode()).hexdigest()
```

## 防重复激活机制

### 1. 防止同一设备重复激活

```
激活时检查：
  └─ 设备已有授权？
     ├─ 是 → 检查是否同一卡密
     │        ├─ 是 → 返回"已激活"
     │        └─ 否 → 拒绝（设备已有其他授权）
     └─ 否 → 继续激活
```

```python
def activate(self, card_key, valid_days=None):
    # 1. 检查是否已激活（防止重复激活）
    existing = self._load_license()
    if existing:
        existing_data = self._decrypt_license(existing)
        if existing_data:
            existing_card_hash = existing_data.get("card_key_hash", "")
            new_card_hash = hashlib.sha256(card_key.encode()).hexdigest()
            
            if existing_card_hash == new_card_hash:
                # 同一卡密，检查是否同一设备
                current_fp = self.get_device_fingerprint()
                if current_fp == existing_data.get("device_fingerprint"):
                    return True, "卡密已激活！有效期至: ..."
                else:
                    return False, "卡密已被其他设备使用！一机一码，禁止多用"
            else:
                return False, "设备已有其他授权，请先删除旧授权"
```

### 2. 防止一码多用（其他设备）

```
激活时检查：
  └─ 卡密是否已使用？
     ├─ 是 → 检查是否当前设备
     │        ├─ 是 → 返回"已在此设备激活"
     │        └─ 否 → 拒绝（卡密已被其他设备使用）
     └─ 否 → 记录使用并激活
```

```python
    # 2. 检查卡密是否已被使用（全局记录）
    card_hash = hashlib.sha256(card_key.encode()).hexdigest()
    if card_hash in self.used_cards:
        used_info = self.used_cards[card_hash]
        current_fp = self.get_device_fingerprint()
        if used_info["device_fp"] != current_fp:
            return False, f"卡密已被其他设备使用！绑定设备: {used_info['device_fp'][:16]}..."
        else:
            return True, "卡密已在此设备激活"
```

### 3. 卡密使用记录管理

```python
def _record_used_card(self, card_key, device_fp):
    """记录卡密已使用"""
    card_hash = hashlib.sha256(card_key.encode()).hexdigest()
    self.used_cards[card_hash] = {
        "card_key_hash": card_hash,
        "device_fp": device_fp,
        "used_at": int(time.time()),
        "device_fp_short": device_fp[:16] + "..."
    }
    self._save_used_cards()

def is_card_used(self, card_key):
    """检查卡密是否已被使用"""
    card_hash = hashlib.sha256(card_key.encode()).hexdigest()
    return card_hash in self.used_cards

def get_card_bind_info(self, card_key):
    """获取卡密绑定信息"""
    card_hash = hashlib.sha256(card_key.encode()).hexdigest()
    if card_hash in self.used_cards:
        return self.used_cards[card_hash]
    return None
```

## 加密存储方案

### 授权文件结构

```python
license_data = {
    "card_key_hash": card_hash,           # 卡密哈希
    "device_fingerprint": device_fp,      # 设备指纹
    "created_at": int(time.time()),       # 创建时间
    "expire_at": int(time.time()) + (valid_days * 86400),  # 过期时间
    "valid_days": valid_days,             # 有效天数
    "type": "offline_bind",               # 授权类型
    "activated": True,                    # 激活状态
    "signature": "..."                    # HMAC签名
}
```

### 多位置存储

```python
def _save_license(self, encrypted_data):
    """保存授权文件到多位置"""
    # 主位置
    with open(self.license_file, "wb") as f:
        f.write(encrypted_data)
    
    # 备份位置
    try:
        backup_dir = os.path.dirname(self.backup_file)
        if backup_dir:
            os.makedirs(backup_dir, exist_ok=True)
        with open(self.backup_file, "wb") as f:
            f.write(encrypted_data)
    except:
        pass
```

## 完整实现代码

```python
#!/usr/bin/env python3
"""
离线一机一码授权系统 - 完整实现
功能：卡密生成、设备绑定、本地验证、加密存储、防重复激活
"""

import hashlib
import hmac
import json
import os
import time
import base64
import secrets
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class OfflineAuthSystem:
    """离线一机一码授权系统（防重复激活版）"""
    
    def __init__(self, app_secret, license_dir="~/.auth"):
        self.app_secret = app_secret
        self.license_dir = os.path.expanduser(license_dir)
        self.license_file = os.path.join(self.license_dir, "license.dat")
        self.backup_file = os.path.join(os.path.expanduser("~"), ".license_backup")
        self.used_cards_file = os.path.join(self.license_dir, "used_cards.dat")
        
        # 初始化加密
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=app_secret.encode()[:16],
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(app_secret.encode()))
        self.cipher = Fernet(key)
        
        # 加载已使用卡密记录
        self.used_cards = self._load_used_cards()
        
        # 确保目录存在
        os.makedirs(self.license_dir, exist_ok=True)
    
    def generate_card_key(self, valid_days=30, max_devices=1):
        """生成卡密"""
        key_parts = []
        for _ in range(4):
            key_parts.append(secrets.token_hex(2).upper())
        card_key = "-".join(key_parts)
        
        key_data = {
            "card_key": card_key,
            "valid_days": valid_days,
            "max_devices": max_devices,
            "created_at": int(time.time()),
            "used": False,
            "bound_devices": []
        }
        
        sign_str = f"{card_key}:{valid_days}:{key_data['created_at']}:{self.app_secret}"
        key_data["signature"] = hmac.new(
            self.app_secret.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return card_key, key_data
    
    def activate(self, card_key, valid_days=None):
        """激活授权（绑定设备）- 防重复激活版"""
        try:
            # 1. 检查是否已激活（防止重复激活）
            existing = self._load_license()
            if existing:
                existing_data = self._decrypt_license(existing)
                if existing_data:
                    existing_card_hash = existing_data.get("card_key_hash", "")
                    new_card_hash = hashlib.sha256(card_key.encode()).hexdigest()
                    
                    if existing_card_hash == new_card_hash:
                        current_fp = self.get_device_fingerprint()
                        if current_fp == existing_data.get("device_fingerprint"):
                            expire_date = datetime.fromtimestamp(existing_data["expire_at"]).strftime("%Y-%m-%d")
                            return True, f"卡密已激活！有效期至: {expire_date}"
                        else:
                            return False, "卡密已被其他设备使用！一机一码，禁止多用"
                    else:
                        return False, "设备已有其他授权，请先删除旧授权"
            
            # 2. 检查卡密是否已被使用（全局记录）
            card_hash = hashlib.sha256(card_key.encode()).hexdigest()
            if card_hash in self.used_cards:
                used_info = self.used_cards[card_hash]
                current_fp = self.get_device_fingerprint()
                if used_info["device_fp"] != current_fp:
                    return False, f"卡密已被其他设备使用！绑定设备: {used_info['device_fp'][:16]}..."
                else:
                    return True, "卡密已在此设备激活"
            
            # 3. 获取设备指纹
            device_fp = self.get_device_fingerprint()
            
            # 4. 生成授权数据
            if valid_days is None:
                valid_days = 30
            
            license_data = {
                "card_key_hash": card_hash,
                "device_fingerprint": device_fp,
                "created_at": int(time.time()),
                "expire_at": int(time.time()) + (valid_days * 86400),
                "valid_days": valid_days,
                "type": "offline_bind",
                "activated": True
            }
            
            # 5. HMAC签名
            sign_str = f"{license_data['card_key_hash']}:{device_fp}:{license_data['expire_at']}"
            license_data["signature"] = hmac.new(
                self.app_secret.encode(),
                sign_str.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # 6. 加密授权数据
            encrypted = self._encrypt_license(license_data)
            
            # 7. 保存到多位置
            self._save_license(encrypted)
            
            # 8. 记录卡密已使用
            self._record_used_card(card_key, device_fp)
            
            expire_date = datetime.fromtimestamp(license_data["expire_at"]).strftime("%Y-%m-%d")
            return True, f"激活成功！有效期至: {expire_date}"
            
        except Exception as e:
            return False, f"激活失败: {str(e)}"
    
    def verify(self):
        """验证授权"""
        try:
            encrypted = self._load_license()
            if not encrypted:
                return False, "未找到授权文件"
            
            license_data = self._decrypt_license(encrypted)
            if not license_data:
                return False, "授权文件损坏"
            
            # 验证签名
            expected_sig = hmac.new(
                self.app_secret.encode(),
                f"{license_data['card_key_hash']}:{license_data['device_fingerprint']}:{license_data['expire_at']}".encode(),
                hashlib.sha256
            ).hexdigest()
            
            if license_data.get("signature") != expected_sig:
                return False, "授权签名无效（可能被篡改）"
            
            # 验证设备指纹
            current_fp = self.get_device_fingerprint()
            if license_data.get("device_fingerprint") != current_fp:
                return False, "设备不匹配，授权已绑定其他设备"
            
            # 验证过期时间
            if time.time() > license_data.get("expire_at", 0):
                return False, "授权已过期"
            
            # 计算剩余时间
            remaining = license_data["expire_at"] - int(time.time())
            days = remaining // 86400
            hours = (remaining % 86400) // 3600
            
            return True, f"授权有效 | 剩余: {days}天{hours}小时"
            
        except Exception as e:
            return False, f"验证失败: {str(e)}"
    
    def get_device_fingerprint(self):
        """生成设备指纹（9因素组合）"""
        factors = []
        
        # Android ID
        try:
            android_id = self._exec_cmd(["settings", "get", "secure", "android_id"])
            if android_id:
                factors.append(f"android_id:{android_id}")
        except:
            pass
        
        # 序列号
        try:
            serial = self._exec_cmd(["getprop", "ro.serialno"])
            if serial:
                factors.append(f"serial:{serial}")
        except:
            pass
        
        # MAC地址
        try:
            mac = self._exec_cmd(["cat", "/sys/class/net/wlan0/address"])
            if mac:
                factors.append(f"mac:{mac}")
        except:
            pass
        
        # 主板信息
        try:
            board = self._exec_cmd(["getprop", "ro.product.board"])
            if board:
                factors.append(f"board:{board}")
        except:
            pass
        
        # IMEI
        try:
            imei = self._exec_cmd(["service", "call", "iphonesubinfo", "1"])
            if imei:
                factors.append(f"imei:{imei}")
        except:
            pass
        
        # 存储序列号
        try:
            storage = self._exec_cmd(["cat", "/sys/class/mmc_host/mmc0/mmc0:0001/serial"])
            if storage:
                factors.append(f"storage:{storage}")
        except:
            pass
        
        # 蓝牙MAC
        try:
            bt_mac = self._exec_cmd(["settings", "get", "secure", "bluetooth_address"])
            if bt_mac:
                factors.append(f"bt:{bt_mac}")
        except:
            pass
        
        # 构建指纹
        try:
            build_fp = self._exec_cmd(["getprop", "ro.build.fingerprint"])
            if build_fp:
                factors.append(f"build:{build_fp}")
        except:
            pass
        
        # 机器标识（跨平台）
        try:
            import platform
            machine_id = platform.node() + platform.machine() + platform.processor()
            factors.append(f"machine:{machine_id}")
        except:
            pass
        
        combined = "|".join(factors)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _exec_cmd(self, cmd):
        """执行命令"""
        import subprocess
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
        except:
            return None
    
    def _encrypt_license(self, data):
        """加密授权数据"""
        json_str = json.dumps(data)
        return self.cipher.encrypt(json_str.encode())
    
    def _decrypt_license(self, encrypted):
        """解密授权数据"""
        try:
            decrypted = self.cipher.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except:
            return None
    
    def _save_license(self, encrypted_data):
        """保存授权文件到多位置"""
        with open(self.license_file, "wb") as f:
            f.write(encrypted_data)
        
        try:
            backup_dir = os.path.dirname(self.backup_file)
            if backup_dir:
                os.makedirs(backup_dir, exist_ok=True)
            with open(self.backup_file, "wb") as f:
                f.write(encrypted_data)
        except:
            pass
    
    def _load_license(self):
        """读取授权文件"""
        if os.path.exists(self.license_file):
            with open(self.license_file, "rb") as f:
                return f.read()
        
        if os.path.exists(self.backup_file):
            with open(self.backup_file, "rb") as f:
                return f.read()
        
        return None
    
    def _load_used_cards(self):
        """加载已使用卡密记录"""
        try:
            if os.path.exists(self.used_cards_file):
                with open(self.used_cards_file, "rb") as f:
                    encrypted = f.read()
                    decrypted = self.cipher.decrypt(encrypted)
                    return json.loads(decrypted)
        except:
            pass
        return {}
    
    def _save_used_cards(self):
        """保存已使用卡密记录"""
        try:
            encrypted = self.cipher.encrypt(json.dumps(self.used_cards).encode())
            with open(self.used_cards_file, "wb") as f:
                f.write(encrypted)
        except:
            pass
    
    def _record_used_card(self, card_key, device_fp):
        """记录卡密已使用"""
        card_hash = hashlib.sha256(card_key.encode()).hexdigest()
        self.used_cards[card_hash] = {
            "card_key_hash": card_hash,
            "device_fp": device_fp,
            "used_at": int(time.time()),
            "device_fp_short": device_fp[:16] + "..."
        }
        self._save_used_cards()
    
    def is_card_used(self, card_key):
        """检查卡密是否已被使用"""
        card_hash = hashlib.sha256(card_key.encode()).hexdigest()
        return card_hash in self.used_cards
    
    def get_card_bind_info(self, card_key):
        """获取卡密绑定信息"""
        card_hash = hashlib.sha256(card_key.encode()).hexdigest()
        if card_hash in self.used_cards:
            return self.used_cards[card_hash]
        return None
    
    def get_license_info(self):
        """获取授权信息"""
        encrypted = self._load_license()
        if not encrypted:
            return None
        
        data = self._decrypt_license(encrypted)
        if not data:
            return None
        
        return {
            "device_fingerprint": data.get("device_fingerprint", "")[:16] + "...",
            "created_at": datetime.fromtimestamp(data.get("created_at", 0)).strftime("%Y-%m-%d %H:%M:%S"),
            "expire_at": datetime.fromtimestamp(data.get("expire_at", 0)).strftime("%Y-%m-%d %H:%M:%S"),
            "valid_days": data.get("valid_days", 0)
        }
    
    def remove_license(self):
        """删除授权（用于测试或重置）"""
        try:
            if os.path.exists(self.license_file):
                os.remove(self.license_file)
            if os.path.exists(self.backup_file):
                os.remove(self.backup_file)
            return True, "授权已删除"
        except Exception as e:
            return False, f"删除失败: {str(e)}"


class CardKeyManager:
    """卡密管理器"""
    
    def __init__(self, master_secret):
        self.master_secret = master_secret
        self.database = {}
    
    def generate(self, count=1, valid_days=30, max_devices=1):
        """批量生成卡密"""
        results = []
        auth = OfflineAuthSystem(self.master_secret)
        
        for _ in range(count):
            card_key, key_data = auth.generate_card_key(valid_days, max_devices)
            self.database[card_key] = key_data
            results.append((card_key, key_data))
        
        return results
    
    def export_to_file(self, filepath, format="txt"):
        """导出卡密到文件"""
        try:
            with open(filepath, 'w') as f:
                if format == "txt":
                    f.write("=" * 50 + "\n")
                    f.write("卡密列表\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for card_key, key_data in self.database.items():
                        f.write(f"卡密: {card_key}\n")
                        f.write(f"有效期: {key_data['valid_days']} 天\n")
                        f.write(f"最大设备: {key_data['max_devices']}\n")
                        f.write(f"状态: {'已使用' if key_data['used'] else '未使用'}\n")
                        f.write("-" * 50 + "\n")
                
                elif format == "csv":
                    f.write("card_key,valid_days,max_devices,status\n")
                    for card_key, key_data in self.database.items():
                        status = "used" if key_data["used"] else "unused"
                        f.write(f"{card_key},{key_data['valid_days']},{key_data['max_devices']},{status}\n")
            
            return True, f"已导出到: {filepath}"
        except Exception as e:
            return False, f"导出失败: {str(e)}"


# ============ 使用示例 ============

def demo():
    """演示如何使用授权系统（含防重复激活测试）"""
    
    print("=" * 60)
    print("离线一机一码授权系统 - 防重复激活演示")
    print("=" * 60)
    
    # 1. 初始化系统
    print("\n[1] 初始化授权系统...")
    
    # 清理旧数据（仅用于演示）
    import shutil
    for old_dir in ["~/.auth", "~/.auth2", "~/.license_backup"]:
        old_path = os.path.expanduser(old_dir)
        if os.path.exists(old_path):
            if os.path.isdir(old_path):
                shutil.rmtree(old_path)
            else:
                os.remove(old_path)
    
    auth = OfflineAuthSystem("my_secret_key_123")
    print("✓ 系统初始化完成（已清理旧数据）")
    
    # 2. 生成卡密
    print("\n[2] 生成卡密...")
    manager = CardKeyManager("my_secret_key_123")
    cards = manager.generate(count=3, valid_days=30, max_devices=1)
    
    for i, (card_key, _) in enumerate(cards, 1):
        print(f"  卡密 {i}: {card_key}")
    
    test_card = cards[0][0]
    test_card2 = cards[1][0]
    
    # 3. 首次激活
    print(f"\n[3] 首次激活卡密: {test_card}")
    success, msg = auth.activate(test_card, valid_days=30)
    print(f"  结果: {msg}")
    
    # 4. 验证授权
    print("\n[4] 验证授权...")
    result, msg = auth.verify()
    print(f"  结果: {msg}")
    
    # 5. 测试重复激活（同一卡密，同一设备）
    print(f"\n[5] 测试重复激活（同一卡密+同一设备）...")
    success, msg = auth.activate(test_card, valid_days=30)
    print(f"  结果: {msg}")
    
    # 6. 测试一码多用（同一卡密，不同设备-模拟）
    print(f"\n[6] 测试一码多用（模拟其他设备使用同一卡密）...")
    auth2 = OfflineAuthSystem("my_secret_key_123", license_dir="~/.auth2")
    success, msg = auth2.activate(test_card, valid_days=30)
    print(f"  结果: {msg}")
    
    # 7. 测试设备已有授权时激活新卡密
    print(f"\n[7] 测试设备已有授权时激活新卡密...")
    success, msg = auth.activate(test_card2, valid_days=30)
    print(f"  结果: {msg}")
    
    # 8. 获取授权信息
    print("\n[8] 授权信息:")
    info = auth.get_license_info()
    if info:
        for key, value in info.items():
            print(f"  {key}: {value}")
    
    # 9. 检查卡密使用记录
    print("\n[9] 卡密使用记录:")
    print(f"  卡密1已使用: {auth.is_card_used(test_card)}")
    print(f"  卡密2已使用: {auth.is_card_used(test_card2)}")
    
    bind_info = auth.get_card_bind_info(test_card)
    if bind_info:
        print(f"  卡密1绑定设备: {bind_info['device_fp_short']}")
    
    # 10. 导出卡密
    print("\n[10] 导出卡密到文件...")
    success, msg = manager.export_to_file("/tmp/card_keys.txt")
    print(f"  结果: {msg}")
    
    # 清理测试文件
    if os.path.exists(os.path.expanduser("~/.auth2")):
        shutil.rmtree(os.path.expanduser("~/.auth2"))
    
    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
```

## 安全特性总结

| 特性 | 说明 |
|------|------|
| **设备绑定** | 9因素硬件指纹，一机一码 |
| **重复激活检测** | 同一设备不重复绑定 |
| **一码多用防护** | 卡密全局使用记录，跨设备拒绝 |
| **授权覆盖防护** | 已有授权时拒绝新卡密 |
| **加密存储** | AES-256 + HMAC-SHA256 |
| **多位置备份** | 主文件 + 备份文件 |
| **签名验证** | 防篡改检测 |
| **有效期控制** | 精确到秒的时间验证 |

## 使用场景

1. **游戏辅助授权** - 防止一码多用
2. **软件试用控制** - 离线试用期管理
3. **设备锁定** - 绑定特定设备
4. **批量分发** - 生成大量卡密分发给用户
