#!/usr/bin/env python3
"""
自动化解密工具
功能：识别加密算法、提取密钥、批量解密数据
"""

from Crypto.Cipher import AES, DES, DES3, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import MD5, SHA1, SHA256
from Crypto.Util.Padding import unpad, pad
import base64
import binascii
import re
import sys


class AutoDecryptor:
    def __init__(self):
        self.keys = {}
        self.ivs = [
            b'\x00' * 16,
            b'\x01' * 16,
            b'\xff' * 16,
            b'1234567890123456',
        ]
        
    def add_key(self, name, key_data):
        """添加已知密钥"""
        if isinstance(key_data, str):
            # 尝试多种编码
            for encoding in ['utf-8', 'gbk', 'latin-1']:
                try:
                    key_data = key_data.encode(encoding)
                    break
                except:
                    continue
        self.keys[name] = key_data
        
    def identify_algorithm(self, data):
        """识别加密算法特征"""
        results = []
        
        # Base64检测
        if isinstance(data, bytes):
            try:
                decoded = base64.b64decode(data)
                if len(decoded) > 0:
                    results.append(('Base64', decoded))
            except:
                pass
                
        # Hex检测
        try:
            if re.match(r'^[0-9a-fA-F]+$', data.decode() if isinstance(data, bytes) else data):
                decoded = binascii.unhexlify(data)
                results.append(('Hex', decoded))
        except:
            pass
            
        return results
        
    def try_decrypt(self, data, algorithm=None):
        """尝试所有已知方式解密"""
        results = []
        
        if isinstance(data, str):
            data = data.encode()
            
        # 先尝试解码
        decoded_data = data
        encodings = self.identify_algorithm(data)
        for enc_name, enc_data in encodings:
            decoded_data = enc_data
            print(f"[*] Detected {enc_name} encoding")
            
        # 尝试AES
        if algorithm is None or algorithm == 'AES':
            results.extend(self._try_aes(decoded_data))
            
        # 尝试DES
        if algorithm is None or algorithm == 'DES':
            results.extend(self._try_des(decoded_data))
            
        # 尝试3DES
        if algorithm is None or algorithm == '3DES':
            results.extend(self._try_3des(decoded_data))
            
        return results
        
    def _try_aes(self, data):
        """尝试AES解密"""
        results = []
        
        for name, key in self.keys.items():
            # 确保密钥长度正确
            for key_len in [16, 24, 32]:
                if len(key) >= key_len:
                    test_key = key[:key_len]
                    
                    # ECB模式
                    try:
                        cipher = AES.new(test_key, AES.MODE_ECB)
                        decrypted = cipher.decrypt(data)
                        if self.is_valid(decrypted):
                            results.append(('AES-ECB', name, decrypted))
                    except:
                        pass
                        
                    # CBC模式
                    for iv in self.ivs:
                        try:
                            cipher = AES.new(test_key, AES.MODE_CBC, iv)
                            decrypted = cipher.decrypt(data)
                            if self.is_valid(decrypted):
                                results.append(('AES-CBC', name, decrypted))
                        except:
                            pass
                            
        return results
        
    def _try_des(self, data):
        """尝试DES解密"""
        results = []
        
        for name, key in self.keys.items():
            if len(key) >= 8:
                test_key = key[:8]
                
                # ECB
                try:
                    cipher = DES.new(test_key, DES.MODE_ECB)
                    decrypted = cipher.decrypt(data)
                    if self.is_valid(decrypted):
                        results.append(('DES-ECB', name, decrypted))
                except:
                    pass
                    
                # CBC
                for iv in self.ivs:
                    try:
                        iv_8 = iv[:8]
                        cipher = DES.new(test_key, DES.MODE_CBC, iv_8)
                        decrypted = cipher.decrypt(data)
                        if self.is_valid(decrypted):
                            results.append(('DES-CBC', name, decrypted))
                    except:
                        pass
                        
        return results
        
    def _try_3des(self, data):
        """尝试3DES解密"""
        results = []
        
        for name, key in self.keys.items():
            for key_len in [16, 24]:
                if len(key) >= key_len:
                    test_key = key[:key_len]
                    
                    try:
                        cipher = DES3.new(test_key, DES3.MODE_ECB)
                        decrypted = cipher.decrypt(data)
                        if self.is_valid(decrypted):
                            results.append(('3DES-ECB', name, decrypted))
                    except:
                        pass
                        
        return results
        
    def is_valid(self, data):
        """检查解密结果是否有效"""
        try:
            # 尝试UTF-8解码
            text = data.decode('utf-8')
            # 检查是否包含可打印字符
            if len(text) > 0:
                printable = sum(1 for c in text if c.isprintable() or c.isspace())
                if printable / len(text) > 0.8:
                    return True
        except:
            pass
            
        # 检查是否为常见文件头
        file_headers = [
            b'PK',      # ZIP
            b'\x89PNG', # PNG
            b'GIF',     # GIF
            b'\xff\xd8',# JPEG
            b'%PDF',    # PDF
            b'<?xml',   # XML
            b'{',       # JSON
        ]
        
        for header in file_headers:
            if data.startswith(header):
                return True
                
        return False
        
    def brute_force_xor(self, data, max_key=256):
        """XOR暴力破解"""
        results = []
        
        for key in range(max_key):
            decrypted = bytes([b ^ key for b in data])
            if self.is_valid(decrypted):
                results.append((key, decrypted))
                
        return results
        
    def extract_strings(self, data, min_length=4):
        """提取可读字符串"""
        if isinstance(data, str):
            data = data.encode()
            
        strings = []
        current = []
        
        for byte in data:
            if 32 <= byte <= 126:
                current.append(chr(byte))
            else:
                if len(current) >= min_length:
                    strings.append(''.join(current))
                current = []
                
        if len(current) >= min_length:
            strings.append(''.join(current))
            
        return strings


def main():
    if len(sys.argv) < 2:
        print("Usage: python auto_decryptor.py <data> [key]")
        print("Example: python auto_decryptor.py 'base64encodeddata' 'mykey'")
        sys.exit(1)
        
    data = sys.argv[1]
    
    decryptor = AutoDecryptor()
    
    if len(sys.argv) > 2:
        decryptor.add_key('user_provided', sys.argv[2])
        
    # 尝试解密
    results = decryptor.try_decrypt(data)
    
    if results:
        print(f"[+] Found {len(results)} possible decryptions:")
        for algo, key_name, decrypted in results:
            print(f"\n  Algorithm: {algo}")
            print(f"  Key: {key_name}")
            try:
                print(f"  Content: {decrypted.decode('utf-8')[:200]}")
            except:
                print(f"  Content (hex): {decrypted[:50].hex()}")
    else:
        print("[!] No valid decryption found")
        
        # 尝试XOR
        print("[*] Trying XOR brute force...")
        try:
            raw_data = base64.b64decode(data)
        except:
            raw_data = data.encode()
            
        xor_results = decryptor.brute_force_xor(raw_data)
        if xor_results:
            print(f"[+] Found {len(xor_results)} XOR matches:")
            for key, decrypted in xor_results[:5]:
                try:
                    text = decrypted.decode('utf-8')[:100]
                    print(f"  Key={key}: {text}")
                except:
                    pass


if __name__ == '__main__':
    main()
