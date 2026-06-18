#!/usr/bin/env python3
"""
protocol_fuzzer.py - 网络协议模糊测试工具
基于黑曼巴6.16实战经验开发

功能:
    1. 自动生成变异协议帧
    2. 测试多种响应解析
    3. 自动检测异常行为
    4. 支持自定义变异策略
    5. 生成测试报告

用法:
    # 基本模糊测试
    python protocol_fuzzer.py --target 127.0.0.1:8080 --frame-size 384 --count 100
    
    # 基于捕获数据变异
    python protocol_fuzzer.py --target 127.0.0.1:8080 --base-frame capture.bin --count 50
    
    # 自定义变异策略
    python protocol_fuzzer.py --target 127.0.0.1:8080 --strategy bitflip --count 200

依赖:
    - 无（纯Python实现）
"""

import argparse
import os
import sys
import socket
import struct
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from enum import Enum

class MutationStrategy(Enum):
    """变异策略"""
    BITFLIP = "bitflip"          # 位翻转
    BYTEFLIP = "byteflip"        # 字节翻转
    ARITHMETIC = "arithmetic"    # 算术变异
    INTERESTING = "interesting"  # 有趣值
    RANDOM = "random"            # 完全随机
    LENGTH = "length"            # 长度变异
    CHECKSUM = "checksum"        # 校验和变异

class ProtocolFuzzer:
    """协议模糊测试器"""
    
    # 有趣值列表
    INTERESTING_VALUES = [
        0, 1, -1,
        0x7F, 0x80, 0xFF,
        0x7FFF, 0x8000, 0xFFFF,
        0x7FFFFFFF, 0x80000000, 0xFFFFFFFF,
    ]
    
    def __init__(self, target: str, frame_size: int = 384):
        self.target_host, self.target_port = target.split(':')
        self.target_port = int(self.target_port)
        self.frame_size = frame_size
        self.results = []
        
    def connect(self) -> Optional[socket.socket]:
        """连接目标"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.target_host, self.target_port))
            return sock
        except Exception as e:
            print(f"[-] 连接失败: {e}")
            return None
    
    def send_frame(self, frame: bytes) -> Optional[bytes]:
        """发送帧并接收响应"""
        sock = self.connect()
        if not sock:
            return None
        
        try:
            sock.sendall(frame)
            response = sock.recv(4096)
            return response
        except Exception as e:
            print(f"[-] 发送失败: {e}")
            return None
        finally:
            sock.close()
    
    def mutate_bitflip(self, data: bytes) -> bytes:
        """位翻转变异"""
        data = bytearray(data)
        # 随机翻转1-3个位
        for _ in range(random.randint(1, 3)):
            byte_pos = random.randint(0, len(data) - 1)
            bit_pos = random.randint(0, 7)
            data[byte_pos] ^= (1 << bit_pos)
        return bytes(data)
    
    def mutate_byteflip(self, data: bytes) -> bytes:
        """字节翻转变异"""
        data = bytearray(data)
        # 随机翻转1-3个字节
        for _ in range(random.randint(1, 3)):
            pos = random.randint(0, len(data) - 1)
            data[pos] ^= 0xFF
        return bytes(data)
    
    def mutate_arithmetic(self, data: bytes) -> bytes:
        """算术变异"""
        data = bytearray(data)
        # 随机选择位置进行加减
        for _ in range(random.randint(1, 3)):
            pos = random.randint(0, len(data) - 1)
            delta = random.choice([-1, 1, -16, 16, -32, 32])
            data[pos] = (data[pos] + delta) & 0xFF
        return bytes(data)
    
    def mutate_interesting(self, data: bytes) -> bytes:
        """有趣值变异"""
        data = bytearray(data)
        # 插入有趣值
        for _ in range(random.randint(1, 2)):
            pos = random.randint(0, len(data) - 4)
            value = random.choice(self.INTERESTING_VALUES)
            data[pos:pos+4] = struct.pack('<i', value)
        return bytes(data)
    
    def mutate_random(self, data: bytes) -> bytes:
        """完全随机变异"""
        return bytes(random.randint(0, 255) for _ in range(len(data)))
    
    def mutate_length(self, data: bytes) -> bytes:
        """长度变异"""
        # 随机增减长度
        new_length = len(data) + random.choice([-10, -5, 5, 10, 100])
        new_length = max(1, new_length)
        
        if new_length > len(data):
            return data + bytes(random.randint(0, 255) for _ in range(new_length - len(data)))
        else:
            return data[:new_length]
    
    def mutate_checksum(self, data: bytes) -> bytes:
        """校验和变异"""
        data = bytearray(data)
        # 假设最后4字节是校验和
        if len(data) >= 4:
            data[-4:] = bytes(random.randint(0, 255) for _ in range(4))
        return bytes(data)
    
    def mutate(self, data: bytes, strategy: MutationStrategy) -> bytes:
        """根据策略变异"""
        mutators = {
            MutationStrategy.BITFLIP: self.mutate_bitflip,
            MutationStrategy.BYTEFLIP: self.mutate_byteflip,
            MutationStrategy.ARITHMETIC: self.mutate_arithmetic,
            MutationStrategy.INTERESTING: self.mutate_interesting,
            MutationStrategy.RANDOM: self.mutate_random,
            MutationStrategy.LENGTH: self.mutate_length,
            MutationStrategy.CHECKSUM: self.mutate_checksum,
        }
        
        mutator = mutators.get(strategy, self.mutate_random)
        return mutator(data)
    
    def fuzz(self, base_frame: Optional[bytes] = None, 
             strategy: MutationStrategy = MutationStrategy.RANDOM,
             count: int = 100) -> List[Dict]:
        """执行模糊测试"""
        print(f"[*] 开始模糊测试: {self.target_host}:{self.target_port}")
        print(f"    策略: {strategy.value}")
        print(f"    次数: {count}")
        
        # 生成基础帧
        if base_frame:
            data = base_frame
        else:
            data = bytes(random.randint(0, 255) for _ in range(self.frame_size))
        
        results = []
        
        for i in range(count):
            # 变异
            mutated = self.mutate(data, strategy)
            
            # 发送
            response = self.send_frame(mutated)
            
            # 记录结果
            result = {
                'iteration': i + 1,
                'mutated': mutated.hex()[:64],
                'response': response.hex()[:64] if response else None,
                'response_length': len(response) if response else 0,
                'strategy': strategy.value,
            }
            
            results.append(result)
            
            # 打印进度
            if (i + 1) % 10 == 0:
                print(f"    进度: {i+1}/{count}")
            
            # 检查异常响应
            if response and len(response) > 0:
                # 检查是否不是错误码8
                if len(response) >= 4:
                    error_code = struct.unpack('<I', response[:4])[0]
                    if error_code != 8:
                        print(f"\n[!] 发现异常响应: 错误码={error_code}")
                        print(f"    请求: {mutated.hex()[:64]}")
                        print(f"    响应: {response.hex()[:64]}")
            
            # 延迟
            time.sleep(0.1)
        
        self.results = results
        
        print(f"\n[+] 模糊测试完成: {count} 次")
        
        return results
    
    def generate_report(self, output_path: str):
        """生成测试报告"""
        if not self.results:
            print("[-] 无测试结果")
            return
        
        with open(output_path, 'w') as f:
            f.write("# 协议模糊测试报告\n\n")
            f.write(f"目标: {self.target_host}:{self.target_port}\n")
            f.write(f"帧大小: {self.frame_size}\n")
            f.write(f"测试次数: {len(self.results)}\n\n")
            
            # 统计响应
            response_lengths = [r['response_length'] for r in self.results if r['response']]
            if response_lengths:
                f.write(f"平均响应长度: {sum(response_lengths)/len(response_lengths):.1f}\n")
                f.write(f"最大响应长度: {max(response_lengths)}\n")
                f.write(f"最小响应长度: {min(response_lengths)}\n\n")
            
            # 异常响应
            f.write("## 异常响应\n\n")
            for result in self.results:
                if result['response'] and result['response_length'] > 0:
                    # 检查错误码
                    if len(result['response']) >= 4:
                        error_code = struct.unpack('<I', bytes.fromhex(result['response'][:8])[0:4])[0]
                        if error_code != 8:
                            f.write(f"- 迭代 {result['iteration']}: 错误码={error_code}\n")
                            f.write(f"  请求: {result['mutated']}\n")
                            f.write(f"  响应: {result['response']}\n\n")
        
        print(f"[+] 生成报告: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="网络协议模糊测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本模糊测试
    python protocol_fuzzer.py --target 127.0.0.1:8080 --frame-size 384 --count 100
    
    # 基于捕获数据变异
    python protocol_fuzzer.py --target 127.0.0.1:8080 --base-frame capture.bin --count 50
    
    # 自定义变异策略
    python protocol_fuzzer.py --target 127.0.0.1:8080 --strategy bitflip --count 200
        """
    )
    
    parser.add_argument("--target", required=True, help="目标地址（格式: host:port）")
    parser.add_argument("--frame-size", type=int, default=384, help="帧大小")
    parser.add_argument("--base-frame", help="基础帧文件")
    parser.add_argument("--strategy", choices=[s.value for s in MutationStrategy], default="random", help="变异策略")
    parser.add_argument("--count", type=int, default=100, help="测试次数")
    parser.add_argument("--output", "-o", default="./fuzzer_report.md", help="输出报告路径")
    
    args = parser.parse_args()
    
    # 加载基础帧
    base_frame = None
    if args.base_frame:
        with open(args.base_frame, 'rb') as f:
            base_frame = f.read()
        print(f"[*] 加载基础帧: {len(base_frame)} 字节")
    
    # 创建模糊测试器
    fuzzer = ProtocolFuzzer(args.target, args.frame_size)
    
    # 执行模糊测试
    strategy = MutationStrategy(args.strategy)
    results = fuzzer.fuzz(base_frame, strategy, args.count)
    
    # 生成报告
    fuzzer.generate_report(args.output)
    
    print("\n[+] 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
