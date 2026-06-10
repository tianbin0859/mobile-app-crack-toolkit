# 离线授权码系统

## 核心特点

- **无需联网**: 纯本地验证，不依赖服务器
- **防伪造**: HMAC-SHA256签名验证
- **防篡改**: AES-256加密 + PBKDF2密钥派生
- **易读格式**: XXXX-XXXX-XXXX 格式

## 技术原理

```
授权码结构:
[Base32编码]
  └── [盐(16B) + AES加密数据]
        └── [HMAC签名(16B) + JSON授权数据]
              └── {"ver":1, "exp":过期时间, "feat":[功能], "dev":设备数}
```

## 生成器 (Python)

```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64, json, hmac, hashlib, struct

MASTER_KEY = b"YourSecretKey123"

def generate_license_key(days=30, features=None, max_devices=1):
    """生成离线授权码"""
    import os, time
    
    # 1. 生成授权数据
    license_data = {
        "ver": 1,
        "exp": int(time.time()) + days * 86400,
        "feat": features or ["basic"],
        "dev": max_devices,
        "gen": int(time.time())
    }
    
    # 2. 生成盐
    salt = os.urandom(16)
    
    # 3. 派生密钥
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32, salt=salt, iterations=100000
    )
    key = base64.urlsafe_b64encode(kdf.derive(MASTER_KEY))
    
    # 4. AES加密
    from cryptography.fernet import Fernet
    f = Fernet(key)
    encrypted = f.encrypt(json.dumps(license_data).encode())
    
    # 5. HMAC签名
    sig = hmac.new(MASTER_KEY, encrypted, hashlib.sha256).digest()[:16]
    
    # 6. 组合并编码
    final = salt + sig + encrypted
    encoded = base64.b32encode(final).decode()
    
    # 7. 格式化
    return '-'.join([encoded[i:i+4] for i in range(0, 56, 4)])

def verify_license_key(license_key, device_id=None):
    """验证离线授权码"""
    try:
        # 解码
        encoded = license_key.replace('-', '').upper()
        padding = 8 - (len(encoded) % 8)
        if padding != 8:
            encoded += '=' * padding
        final = base64.b32decode(encoded)
        
        # 提取组件
        salt, sig, encrypted = final[:16], final[16:32], final[32:]
        
        # 验证签名
        expected = hmac.new(MASTER_KEY, encrypted, hashlib.sha256).digest()[:16]
        if sig != expected:
            return False, "签名无效"
        
        # 解密
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32, salt=salt, iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(MASTER_KEY))
        f = Fernet(key)
        data = json.loads(f.decrypt(encrypted))
        
        # 验证过期
        if time.time() > data["exp"]:
            return False, "授权已过期"
        
        return True, data
    except Exception as e:
        return False, str(e)
```

## iOS客户端验证 (Objective-C++)

```objc
#import <Foundation/Foundation.h>
#import <CommonCrypto/CommonCrypto.h>

@interface OfflineAuthManager : NSObject
+ (instancetype)sharedInstance;
- (BOOL)verifyLicenseKey:(NSString *)key;
- (BOOL)hasFeature:(NSString *)feature;
- (NSInteger)daysRemaining;
@end

@implementation OfflineAuthManager {
    NSDictionary *_licenseInfo;
}

+ (instancetype)sharedInstance {
    static OfflineAuthManager *instance;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ instance = [[self alloc] init]; });
    return instance;
}

- (BOOL)verifyLicenseKey:(NSString *)key {
    // 1. 移除分隔符
    NSString *encoded = [[key stringByReplacingOccurrencesOfString:@"-" withString:@""] uppercaseString];
    
    // 2. Base32解码
    NSData *final = [self base32Decode:encoded];
    if (!final || final.length < 32) return NO;
    
    // 3. 提取组件
    NSData *salt = [final subdataWithRange:NSMakeRange(0, 16)];
    NSData *sig = [final subdataWithRange:NSMakeRange(16, 16)];
    NSData *encrypted = [final subdataWithRange:NSMakeRange(32, final.length - 32)];
    
    // 4. 验证HMAC
    NSData *expected = [self hmacSHA256:encrypted key:[self masterKey]];
    expected = [expected subdataWithRange:NSMakeRange(0, 16)];
    if (![sig isEqualToData:expected]) return NO;
    
    // 5. 派生密钥并解密
    NSData *derived = [self pbkdf2:salt];
    NSData *decrypted = [self aesDecrypt:encrypted key:derived];
    
    // 6. 解析JSON
    NSError *error;
    _licenseInfo = [NSJSONSerialization JSONObjectWithData:decrypted options:0 error:&error];
    if (error) return NO;
    
    // 7. 验证过期
    NSTimeInterval exp = [_licenseInfo[@"exp"] doubleValue];
    if ([[NSDate date] timeIntervalSince1970] > exp) return NO;
    
    return YES;
}

- (BOOL)hasFeature:(NSString *)feature {
    NSArray *features = _licenseInfo[@"feat"];
    return [features containsObject:feature];
}

- (NSInteger)daysRemaining {
    NSTimeInterval exp = [_licenseInfo[@"exp"] doubleValue];
    NSTimeInterval now = [[NSDate date] timeIntervalSince1970];
    return (NSInteger)((exp - now) / 86400);
}

// 辅助方法实现...
@end
```

## 批量生成工具

```python
import qrcode
from PIL import Image

def generate_batch(count=10, days=30, features=None):
    """批量生成授权码"""
    licenses = []
    for i in range(count):
        key = generate_license_key(days, features)
        licenses.append({
            "id": i + 1,
            "key": key,
            "days": days,
            "features": features or ["basic"],
            "status": "未使用"
        })
    return licenses

def export_to_csv(licenses, filename="licenses.csv"):
    """导出到CSV"""
    import csv
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "key", "days", "features", "status"])
        writer.writeheader()
        writer.writerows(licenses)

def generate_qr(license_key, filename="qr.png"):
    """生成二维码"""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(license_key)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)
```

## 安全建议

1. **主密钥保护**: MASTER_KEY需要混淆保护，不要硬编码
2. **代码混淆**: 验证逻辑需要混淆防止逆向
3. **设备绑定**: 使用设备唯一标识符（IDFV/IDFA）
4. **时间安全**: 防止用户修改系统时间（NTP校验）
5. **反调试**: 添加反调试检测
