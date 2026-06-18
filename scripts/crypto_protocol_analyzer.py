#!/usr/bin/env python3
"""
crypto_protocol_analyzer.py - 加密协议自动分析工具
基于黑曼巴6.16实战经验开发

功能:
    1. 自动识别加密算法（AES/XOR/ChaCha20等）
    2. 尝试常见密钥派生方式
    3. 自动尝试多种解密组合
    4. 分析协议结构（帧大小、字段偏移）
    5. 生成伪造响应

用法:
    # 分析加密协议
    python crypto_protocol_analyzer.py --data capture.bin --frame-size 384 --analyze
    
    # 自动尝试解密
    python crypto_protocol_analyzer.py --data capture.bin --key "FDTls6gNyx7klaeNPt04k1TNO5la7bI2" --auto-brute
    
    # 生成伪造响应
    python crypto_protocol_analyzer.py --frame-size 384 --generate-response --output response.bin

依赖:
    - pip install pycryptodome
"""

import argparse
import os
import sys
import struct
import hashlib
import hmac
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from itertools import product

class CryptoDetector:
    """加密算法检测器"""
    
    # 常见加密特征
    CRYPTO_SIGNATURES = {
        'AES': {
            'block_size': 16,
            'key_sizes': [16, 24, 32],
            'iv_size': 16,
        },
        'ChaCha20': {
            'key_size': 32,
            'nonce_size': 12,
        },
        'XOR': {
            'variable': True,
        },
    }
    
    @staticmethod
    def detect_algorithm(data: bytes) -> Dict[str, any]:
        """检测可能的加密算法"""
        result = {
            'algorithms': [],
            'block_size': 0,
            'key_size': 0,
        }
        
        # 检查块大小
        if len(data) % 16 == 0:
            result['block_size'] = 16
            result['algorithms'].append('AES-128/192/256')
        elif len(data) % 8 == 0:
            result['block_size'] = 8
            result['algorithms'].append('DES/3DES')
        
        # 检查熵值
        entropy = CryptoDetector._calculate_entropy(data)
        if entropy > 7.5:
            result['algorithms'].append('High entropy (likely encrypted)')
        
        return result
    
    @staticmethod
    def _calculate_entropy(data: bytes) -> float:
        """计算熵值"""
        if not data:
            return 0.0
        
        entropy = 0.0
        for x in range(256):
            p_x = data.count(x) / len(data)
            if p_x > 0:
                entropy += - p_x * (p_x.bit_length() - 1)
        
        return entropy


class KeyDeriver:
    """密钥派生器"""
    
    @staticmethod
    def derive_keys(base_key: str or bytes) -> List[bytes]:
        """派生多种可能的密钥"""
        if isinstance(base_key, str):
            base_key = base_key.encode('utf-8')
        
        keys = []
        
        # 原始密钥
        keys.append(base_key)
        
        # MD5
        keys.append(hashlib.md5(base_key).digest())
        
        # SHA1
        keys.append(hashlib.sha1(base_key).digest()[:16])  # AES-128
        keys.append(hashlib.sha1(base_key).digest()[:24])  # AES-192
        keys.append(hashlib.sha1(base_key).digest())  # AES-256
        
        # SHA256
        keys.append(hashlib.sha256(base_key).digest()[:16])
        keys.append(hashlib.sha256(base_key).digest()[:24])
        keys.append(hashlib.sha256(base_key).digest())
        
        # Base64解码尝试
        import base64
        try:
            decoded = base64.b64decode(base_key)
            keys.append(decoded)
        except:
            pass
        
        return keys


class CryptoBruteForcer:
    """加密暴力破解器"""
    
    def __init__(self, ciphertext: bytes, keys: List[bytes]):
        self.ciphertext = ciphertext
        self.keys = keys
        self.results = []
        
    def brute_force_aes(self) -> List[Dict]:
        """暴力尝试AES多种模式"""
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad
        
        modes = [
            ('ECB', AES.MODE_ECB),
            ('CBC', AES.MODE_CBC),
            ('CTR', AES.MODE_CTR),
        ]
        
        results = []
        
        for key in self.keys:
            for mode_name, mode in modes:
                try:
                    if mode == AES.MODE_ECB:
                        cipher = AES.new(key, mode)
                    elif mode == AES.MODE_CBC:
                        iv = b'\x00' * 16
                        cipher = AES.new(key, mode, iv=iv)
                    elif mode == AES.MODE_CTR:
                        cipher = AES.new(key, mode, nonce=b'\x00' * 8)
                    
                    plaintext = cipher.decrypt(self.ciphertext)
                    
                    # 检查解密结果是否有效
                    if self._is_valid_plaintext(plaintext):
                        results.append({
                            'algorithm': f'AES-{len(key)*8}-{mode_name}',
                            'key': key.hex(),
                            'plaintext': plaintext[:64],
                            'valid': True,
                        })
                except Exception as e:
                    pass
        
        return results
    
    def brute_force_xor(self) -> List[Dict]:
        """暴力尝试XOR"""
        results = []
        
        for key in self.keys:
            # 重复密钥XOR
            repeated_key = (key * (len(self.ciphertext) // len(key) + 1))[:len(self.ciphertext)]
            plaintext = bytes(a ^ b for a, b in zip(self.ciphertext, repeated_key))
            
            if self._is_valid_plaintext(plaintext):
                results.append({
                    'algorithm': 'XOR-repeated',
                    'key': key.hex(),
                    'plaintext': plaintext[:64],
                    'valid': True,
                })
        
        return results
    
    def _is_valid_plaintext(self, data: bytes) -> bool:
        """检查是否为有效明文"""
        # 检查可打印字符比例
        printable_count = sum(1 for b in data if 32 <= b <= 126 or b in [0, 9, 10, 13])
        ratio = printable_count / len(data)
        
        return ratio > 0.8
    
    def run_all(self) -> List[Dict]:
        """运行所有破解尝试"""
        print(f"[*] 开始暴力破解: {len(self.keys)} 个密钥")
        
        results = []
        results.extend(self.brute_force_aes())
        results.extend(self.brute_force_xor())
        
        self.results = results
        
        print(f"[+] 找到 {len(results)} 个有效解密")
        
        return results


class ProtocolAnalyzer:
    """协议分析器"""
    
    def __init__(self, data: bytes):
        self.data = data
        
    def analyze_structure(self, frame_size: int) -> Dict[str, any]:
        """分析协议结构"""
        print(f"[*] 分析协议结构: 帧大小={frame_size}")
        
        result = {
            'frame_size': frame_size,
            'frame_count': len(self.data) // frame_size,
            'fields': [],
        }
        
        # 分析第一个帧
        if len(self.data) >= frame_size:
            frame = self.data[:frame_size]
            
            # 检查常见字段
            # 1. 长度字段（前4字节）
            length = struct.unpack('<I', frame[:4])[0]
            result['fields'].append({
                'offset': 0,
                'size': 4,
                'type': 'length',
                'value': length,
            })
            
            # 2. 版本/类型字段
            version = frame[4:8]
            result['fields'].append({
                'offset': 4,
                'size': 4,
                'type': 'version/type',
                'value': version.hex(),
            })
            
            # 3. 检查固定模式
            for i in range(0, frame_size, 4):
                chunk = frame[i:i+4]
                if chunk == b'\x00\x00\x00\x00':
                    result['fields'].append({
                        'offset': i,
                        'size': 4,
                        'type': 'zero_padding',
                    })
        
        return result


class ResponseGenerator:
    """响应生成器"""
    
    @staticmethod
    def generate_success_response(frame_size: int, protocol_type: str = 'generic') -> bytes:
        """生成成功响应"""
        response = bytearray(frame_size)
        
        if protocol_type == 'generic':
            # 通用成功响应
            # Header: 成功标志
            response[0] = 0x00
            response[1] = 0x01
            # 状态码: 0 (成功)
            response[4] = 0x00
            response[5] = 0x00
            response[6] = 0x00
            response[7] = 0x00
        
        return bytes(response)
    
    @staticmethod
    def generate_error_response(frame_size: int, error_code: int) -> bytes:
        """生成错误响应"""
        response = bytearray(frame_size)
        
        # 错误码
        response[4:8] = struct.pack('<I', error_code)
        
        return bytes(response)


def main():
    parser = argparse.ArgumentParser(
        description="加密协议自动分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 分析加密协议
    python crypto_protocol_analyzer.py --data capture.bin --frame-size 384 --analyze
    
    # 自动尝试解密
    python crypto_protocol_analyzer.py --data capture.bin --key "FDTls6gNyx7klaeNPt04k1TNO5la7bI2" --auto-brute
    
    # 生成伪造响应
    python crypto_protocol_analyzer.py --frame-size 384 --generate-response --output response.bin
        """
    )
    
    parser.add_argument("--data", help="捕获的数据文件")
    parser.add_argument("--key", help="基础密钥/卡密")
    parser.add_argument("--frame-size", type=int, default=384, help="帧大小")
    parser.add_argument("--output", "-o", default="./crypto_output", help="输出目录")
    parser.add_argument("--analyze", action="store_true", help="分析协议")
    parser.add_argument("--auto-brute", action="store_true", help="自动暴力破解")
    parser.add_argument("--generate-response", action="store_true", help="生成伪造响应")
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 分析协议
    if args.data and args.analyze:
        with open(args.data, 'rb') as f:
            data = f.read()
        
        print(f"[*] 分析数据: {len(data)} 字节")
        
        # 检测加密算法
        detection = CryptoDetector.detect_algorithm(data)
        print(f"[+] 加密检测:")
        print(f"    可能算法: {', '.join(detection['algorithms'])}")
        print(f"    块大小: {detection['block_size']}")
        
        # 分析协议结构
        analyzer = ProtocolAnalyzer(data)
        structure = analyzer.analyze_structure(args.frame_size)
        print(f"\n[+] 协议结构:")
        print(f"    帧大小: {structure['frame_size']}")
        print(f"    帧数量: {structure['frame_count']}")
        print(f"    字段:")
        for field in structure['fields']:
            print(f"      偏移{field['offset']}: {field['type']} = {field.get('value', 'N/A')}")
    
    # 自动暴力破解
    if args.data and args.key and args.auto_brute:
        with open(args.data, 'rb') as f:
            data = f.read()
        
        # 派生密钥
        keys = KeyDeriver.derive_keys(args.key)
        print(f"[*] 派生 {len(keys)} 个密钥")
        
        # 提取密文（跳过头部）
        ciphertext = data[16:] if len(data) > 16 else data
        
        # 暴力破解
        brute_forcer = CryptoBruteForcer(ciphertext, keys)
        results = brute_forcer.run_all()
        
        print(f"\n[+] 破解结果:")
        for i, result in enumerate(results[:5]):
            print(f"    {i+1}. {result['algorithm']}")
            print(f"       密钥: {result['key']}")
            print(f"       明文: {result['plaintext'][:32]}...")
    
    # 生成伪造响应
    if args.generate_response:
        response = ResponseGenerator.generate_success_response(args.frame_size)
        output_path = os.path.join(args.output, "fake_response.bin")
        with open(output_path, 'wb') as f:
            f.write(response)
        print(f"[+] 生成伪造响应: {output_path}")
    
    print("\n[+] 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
