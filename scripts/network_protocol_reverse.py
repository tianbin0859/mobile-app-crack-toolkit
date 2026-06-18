#!/usr/bin/env python3
"""
network_protocol_reverse.py - 网络协议逆向分析工具

功能:
    1. 自动识别协议类型（HTTP/HTTPS/WebSocket/Protobuf/自定义二进制）
    2. 流量捕获与解析
    3. 请求签名分析（mTOP、自定义签名）
    4. 生成Frida Hook脚本拦截协议
    5. 协议重放与伪造

用法:
    # 分析协议
    python network_protocol_reverse.py --pcap traffic.pcap --analyze
    
    # 生成Frida Hook
    python network_protocol_reverse.py --target com.example.app --generate-hook
    
    # 重放请求
    python network_protocol_reverse.py --request request.json --replay

依赖:
    - pip install scapy requests
"""

import argparse
import os
import sys
import json
import re
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class ProtocolDetector:
    """协议检测器"""
    
    # 协议特征
    PROTOCOL_SIGNATURES = {
        'HTTP': {
            'patterns': [b'HTTP/', b'GET ', b'POST ', b'PUT ', b'DELETE '],
            'ports': [80, 8080, 8000],
        },
        'HTTPS': {
            'patterns': [b'\x16\x03'],  # TLS记录头
            'ports': [443, 8443],
        },
        'WebSocket': {
            'patterns': [b'Upgrade: websocket'],
            'ports': [80, 443, 8080],
        },
        'Protobuf': {
            'patterns': [],  # 二进制，无固定特征
            'ports': [],
        },
        'JSON': {
            'patterns': [b'{', b'['],
            'ports': [],
        },
        'XML': {
            'patterns': [b'<?xml'],
            'ports': [],
        },
    }
    
    @staticmethod
    def detect(data: bytes) -> Dict[str, any]:
        """检测协议类型"""
        result = {
            'protocol': 'Unknown',
            'confidence': 0.0,
            'features': [],
        }
        
        # 检查HTTP
        if any(pattern in data for pattern in ProtocolDetector.PROTOCOL_SIGNATURES['HTTP']['patterns']):
            result['protocol'] = 'HTTP'
            result['confidence'] = 0.95
            result['features'].append('HTTP request/response')
        
        # 检查HTTPS/TLS
        elif data[:2] == b'\x16\x03':
            result['protocol'] = 'HTTPS/TLS'
            result['confidence'] = 0.95
            result['features'].append('TLS handshake')
        
        # 检查WebSocket
        elif b'websocket' in data.lower():
            result['protocol'] = 'WebSocket'
            result['confidence'] = 0.90
            result['features'].append('WebSocket upgrade')
        
        # 检查JSON
        elif data.strip().startswith(b'{') or data.strip().startswith(b'['):
            result['protocol'] = 'JSON'
            result['confidence'] = 0.85
            result['features'].append('JSON format')
        
        # 检查XML
        elif data.strip().startswith(b'<?xml'):
            result['protocol'] = 'XML'
            result['confidence'] = 0.85
            result['features'].append('XML format')
        
        # 检查Protobuf（二进制）
        elif ProtocolDetector._is_protobuf(data):
            result['protocol'] = 'Protobuf'
            result['confidence'] = 0.70
            result['features'].append('Binary protocol')
        
        return result
    
    @staticmethod
    def _is_protobuf(data: bytes) -> bool:
        """检查是否为Protobuf格式"""
        # Protobuf特征：varint编码的字段标签
        if len(data) < 3:
            return False
        
        # 检查前几个字节是否符合varint编码
        try:
            pos = 0
            tag_count = 0
            for _ in range(5):  # 检查前5个字段
                if pos >= len(data):
                    break
                
                # 解析varint
                tag = data[pos] & 0x7F
                if data[pos] & 0x80:
                    tag |= (data[pos + 1] & 0x7F) << 7
                    pos += 1
                
                # 检查字段号是否合理（1-50000）
                field_number = tag >> 3
                wire_type = tag & 0x07
                
                if 1 <= field_number <= 50000 and wire_type <= 5:
                    tag_count += 1
                
                pos += 1
            
            return tag_count >= 2
        except:
            return False


class SignatureAnalyzer:
    """请求签名分析器"""
    
    # 常见签名算法特征
    SIGNATURE_PATTERNS = {
        'MD5': {
            'length': 32,
            'pattern': re.compile(r'^[a-f0-9]{32}$'),
        },
        'SHA1': {
            'length': 40,
            'pattern': re.compile(r'^[a-f0-9]{40}$'),
        },
        'SHA256': {
            'length': 64,
            'pattern': re.compile(r'^[a-f0-9]{64}$'),
        },
        'HMAC-SHA1': {
            'length': 40,
            'pattern': re.compile(r'^[a-f0-9]{40}$'),
        },
        'mTOP': {
            'pattern': re.compile(r'x-sign|x-mini-wua|x-sgext|x-umid'),
        },
    }
    
    def __init__(self):
        self.signatures = []
        
    def analyze_request(self, request_data: Dict) -> List[Dict]:
        """分析请求中的签名"""
        signatures = []
        
        # 检查URL参数
        url = request_data.get('url', '')
        query_params = self._parse_query_params(url)
        
        for key, value in query_params.items():
            sig_type = self._detect_signature_type(value)
            if sig_type:
                signatures.append({
                    'location': f'URL参数: {key}',
                    'value': value,
                    'type': sig_type,
                    'key': key,
                })
        
        # 检查Headers
        headers = request_data.get('headers', {})
        for key, value in headers.items():
            sig_type = self._detect_signature_type(value)
            if sig_type:
                signatures.append({
                    'location': f'Header: {key}',
                    'value': value,
                    'type': sig_type,
                    'key': key,
                })
        
        # 检查Body
        body = request_data.get('body', '')
        if isinstance(body, str):
            for key, value in self._parse_query_params(body).items():
                sig_type = self._detect_signature_type(value)
                if sig_type:
                    signatures.append({
                        'location': f'Body参数: {key}',
                        'value': value,
                        'type': sig_type,
                        'key': key,
                    })
        
        self.signatures = signatures
        return signatures
    
    def _parse_query_params(self, url: str) -> Dict[str, str]:
        """解析URL参数"""
        params = {}
        
        # 提取查询字符串
        if '?' in url:
            query = url.split('?')[1]
        else:
            query = url
        
        # 解析参数
        for pair in query.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[key] = value
        
        return params
    
    def _detect_signature_type(self, value: str) -> Optional[str]:
        """检测签名类型"""
        if not value or len(value) < 8:
            return None
        
        for sig_type, config in self.SIGNATURE_PATTERNS.items():
            if 'pattern' in config:
                if config['pattern'].match(value):
                    return sig_type
            if 'length' in config:
                if len(value) == config['length']:
                    return sig_type
        
        return None
    
    def generate_frida_hook(self, target_package: str, output_path: str):
        """生成Frida Hook脚本"""
        script = f'''// 网络协议Hook脚本
// 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
// 目标应用: {target_package}

function hook_network() {{
    console.log('[*] 网络协议Hook启动');
    
    // Hook OkHttp (Android)
    try {{
        var OkHttpClient = Java.use('okhttp3.OkHttpClient');
        var Request = Java.use('okhttp3.Request');
        var Response = Java.use('okhttp3.Response');
        
        // Hook请求构建
        Request.Builder.build.implementation = function() {{
            var request = this.build();
            console.log('[HTTP] URL: ' + request.url().toString());
            console.log('[HTTP] Headers: ' + request.headers().toString());
            return request;
        }};
        
        console.log('[+] OkHttp已Hook');
    }} catch(e) {{
        console.log('[-] OkHttp Hook失败: ' + e);
    }}
    
    // Hook URLConnection (Java标准库)
    try {{
        var URLConnection = Java.use('java.net.URLConnection');
        URLConnection.connect.implementation = function() {{
            console.log('[HTTP] URLConnection.connect: ' + this.getURL().toString());
            return this.connect();
        }};
        
        console.log('[+] URLConnection已Hook');
    }} catch(e) {{
        console.log('[-] URLConnection Hook失败: ' + e);
    }}
    
    // Hook Native层 (OpenSSL/BoringSSL)
    try {{
        var SSL_write = Module.findExportByName(null, 'SSL_write');
        if (SSL_write) {{
            Interceptor.attach(SSL_write, {{
                onEnter: function(args) {{
                    var data = Memory.readByteArray(args[1], args[2].toInt32());
                    console.log('[SSL_write] Data: ' + data.length + ' bytes');
                }}
            }});
            console.log('[+] SSL_write已Hook');
        }}
    }} catch(e) {{
        console.log('[-] SSL_write Hook失败: ' + e);
    }}
}}

// 主入口
function main() {{
    console.log('[*] 网络协议逆向工具启动');
    console.log('[*] 目标应用: {target_package}');
    hook_network();
}}

setImmediate(main);
'''
        
        with open(output_path, 'w') as f:
            f.write(script)
        
        print(f"[+] 生成Frida Hook脚本: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="网络协议逆向分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 分析协议
    python network_protocol_reverse.py --pcap traffic.pcap --analyze
    
    # 生成Frida Hook
    python network_protocol_reverse.py --target com.example.app --generate-hook
    
    # 分析请求签名
    python network_protocol_reverse.py --request request.json --analyze-signature
        """
    )
    
    parser.add_argument("--pcap", help="PCAP流量文件")
    parser.add_argument("--target", help="目标应用包名")
    parser.add_argument("--request", help="请求JSON文件")
    parser.add_argument("--output", "-o", default="./protocol_output", help="输出目录")
    parser.add_argument("--analyze", action="store_true", help="分析协议")
    parser.add_argument("--analyze-signature", action="store_true", help="分析签名")
    parser.add_argument("--generate-hook", action="store_true", help="生成Frida Hook")
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 分析协议
    if args.pcap and args.analyze:
        print(f"[*] 分析PCAP: {args.pcap}")
        # 简化：读取文件并检测协议
        with open(args.pcap, 'rb') as f:
            data = f.read(65536)
        
        detection = ProtocolDetector.detect(data)
        print(f"[+] 协议检测:")
        print(f"    协议: {detection['protocol']}")
        print(f"    置信度: {detection['confidence']}")
        print(f"    特征: {', '.join(detection['features'])}")
    
    # 分析签名
    if args.request and args.analyze_signature:
        print(f"[*] 分析请求签名: {args.request}")
        
        with open(args.request, 'r') as f:
            request_data = json.load(f)
        
        analyzer = SignatureAnalyzer()
        signatures = analyzer.analyze_request(request_data)
        
        print(f"[+] 发现 {len(signatures)} 个签名:")
        for sig in signatures:
            print(f"    {sig['location']}: {sig['type']} = {sig['value'][:32]}...")
    
    # 生成Hook
    if args.target and args.generate_hook:
        analyzer = SignatureAnalyzer()
        hook_path = os.path.join(args.output, "network_hook.js")
        analyzer.generate_frida_hook(args.target, hook_path)
    
    print("\n[+] 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
