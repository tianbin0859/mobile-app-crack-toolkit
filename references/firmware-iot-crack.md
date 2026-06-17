# 固件/IoT 破解实战指南

## 适用场景
- 路由器固件逆向分析
- 智能家居设备破解
- 嵌入式设备漏洞挖掘
- 提取固件中的密钥/证书

## 核心工具链

| 工具 | 用途 | 安装 |
|------|------|------|
| binwalk | 固件提取和分析 | pip install binwalk |
| firmware-mod-kit | 固件修改套件 | 源码编译 |
| firmadyne | 固件仿真 | Docker |
| qemu | 跨架构仿真 | apt install qemu |
| ghidra | 固件反编译 | 已安装 |
| ida | 高级反编译 | 商业软件 |
| flashrom | 硬件读取 | apt install flashrom |
| uart/serial | 串口调试 | 硬件工具 |

## 标准流程

### 1. 获取固件
```bash
# 方法1：从官网下载
wget https://vendor.com/firmware/router_v1.0.bin

# 方法2：从设备提取（需 root 或漏洞）
# 通过 Web 界面备份功能下载
# 或通过命令行 cat /dev/mtdblock0 > /tmp/firmware.bin

# 方法3：硬件读取（SPI Flash）
# 使用 CH341A 编程器 + flashrom
flashrom -p ch341a_spi -r firmware.bin
```

### 2. 固件分析（binwalk）
```bash
# 扫描固件结构
binwalk firmware.bin

# 输出示例：
# DECIMAL       HEXADECIMAL     DESCRIPTION
# 0             0x0             TRX firmware header, little endian
# 28            0x1C            LZMA compressed data
# 131072        0x20000         Squashfs filesystem, little endian

# 自动提取
binwalk -e firmware.bin
# 输出到 _firmware.bin.extracted/

# 深度提取（递归）
binwalk -e -M firmware.bin
```

### 3. 文件系统分析
```bash
cd _firmware.bin.extracted/

# 查看文件系统
ls squashfs-root/
# bin/  etc/  lib/  usr/  sbin/  www/

# 搜索敏感文件
grep -r "password" squashfs-root/etc/
grep -r "admin" squashfs-root/etc/
find squashfs-root/ -name "*.pem" -o -name "*.key"

# 分析启动脚本
cat squashfs-root/etc/init.d/rcS
cat squashfs-root/etc/inittab
```

### 4. 二进制分析
```bash
# 定位关键程序
file squashfs-root/bin/busybox
file squashfs-root/usr/sbin/httpd

# 查看字符串
strings squashfs-root/usr/sbin/httpd | grep -i "password\|auth\|login"

# 反编译（Ghidra）
# 1. 新建项目
# 2. File -> Import File -> 选择目标二进制
# 3. 选择架构（MIPS/ARM/x86）
# 4. 分析 -> 自动分析
```

### 5. 固件修改和重打包
```bash
# 修改文件系统
# 例如：添加后门账号
echo 'backdoor:$1$xyz$abc123:0:0::/root:/bin/sh' >> squashfs-root/etc/passwd

# 重新打包 Squashfs
mksquashfs squashfs-root/ new_filesystem.bin -comp xz

# 替换原固件中的文件系统
# 使用 dd 或 binwalk 的 -we 选项

# 完整重打包（使用 firmware-mod-kit）
cd firmware-mod-kit/trunk/
./extract_firmware.sh firmware.bin work_dir/
# 修改 work_dir/
./build_firmware.sh work_dir/ new_firmware.bin
```

### 6. 固件仿真（firmadyne）
```bash
# 使用 firmadyne 仿真固件
git clone https://github.com/firmadyne/firmadyne.git
cd firmadyne

# 提取固件
./sources/extractor/extractor.py -b brand firmware.bin images/

# 获取镜像信息
./scripts/getArch.sh ./images/brand.tar.gz

# 创建 QEMU 镜像
./scripts/makeImage.sh -i 1 -s 128M

# 设置网络
./scripts/inferNetwork.sh 1

# 启动仿真
./scratch/1/run.sh

# 访问仿真设备
# 默认 IP: 192.168.0.1
```

### 7. 自动化 Python 脚本
```python
#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path

class FirmwareAnalyzer:
    def __init__(self, firmware_path: str):
        self.firmware = Path(firmware_path)
        self.work_dir = Path("firmware_analysis")
        self.work_dir.mkdir(exist_ok=True)
        
    def analyze(self) -> dict:
        """完整分析流程"""
        result = {
            'file': str(self.firmware),
            'size': self.firmware.stat().st_size,
            'signatures': self._scan_signatures(),
            'filesystem': self._extract_filesystem(),
            'binaries': self._analyze_binaries(),
            'secrets': self._find_secrets()
        }
        
        with open(self.work_dir / 'analysis.json', 'w') as f:
            json.dump(result, f, indent=2)
            
        return result
    
    def _scan_signatures(self) -> list:
        """扫描固件签名"""
        result = subprocess.run(
            ['binwalk', str(self.firmware)],
            capture_output=True, text=True
        )
        
        signatures = []
        for line in result.stdout.split('\n'):
            if 'DESCRIPTION' in line:
                continue
            if line.strip() and line[0].isdigit():
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    signatures.append({
                        'offset': parts[0],
                        'hex': parts[1],
                        'desc': parts[2]
                    })
                    
        return signatures
    
    def _extract_filesystem(self) -> dict:
        """提取文件系统"""
        extract_dir = self.work_dir / 'extracted'
        extract_dir.mkdir(exist_ok=True)
        
        subprocess.run([
            'binwalk', '-e', '-M', '-C', str(extract_dir),
            str(self.firmware)
        ], capture_output=True)
        
        # 分析文件系统类型
        fs_types = []
        for root, dirs, files in os.walk(extract_dir):
            for d in dirs:
                if d in ['squashfs-root', 'cramfs-root', 'jffs2-root']:
                    fs_types.append(d)
                    
        return {'extracted_to': str(extract_dir), 'filesystems': fs_types}
    
    def _analyze_binaries(self) -> list:
        """分析关键二进制"""
        binaries = []
        extract_dir = self.work_dir / 'extracted'
        
        for bin_file in extract_dir.rglob('*'):
            if bin_file.is_file():
                result = subprocess.run(
                    ['file', str(bin_file)],
                    capture_output=True, text=True
                )
                if 'ELF' in result.stdout or 'executable' in result.stdout:
                    binaries.append({
                        'path': str(bin_file.relative_to(extract_dir)),
                        'type': result.stdout.strip()
                    })
                    
        return binaries
    
    def _find_secrets(self) -> list:
        """搜索敏感信息"""
        secrets = []
        extract_dir = self.work_dir / 'extracted'
        
        keywords = ['password', 'secret', 'key', 'token', 'admin', 'root']
        
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = Path(root) / file
                try:
                    content = file_path.read_text(errors='ignore')
                    for kw in keywords:
                        if kw in content.lower():
                            secrets.append({
                                'file': str(file_path.relative_to(extract_dir)),
                                'keyword': kw
                            })
                            break
                except:
                    continue
                    
        return secrets
    
    def modify_and_repack(self, modifications: dict) -> Path:
        """修改并重新打包"""
        # 应用修改
        extract_dir = self.work_dir / 'extracted'
        
        for file_path, new_content in modifications.items():
            target = extract_dir / file_path
            target.write_text(new_content)
            
        # 重新打包（简化版，实际需根据固件类型处理）
        output = self.work_dir / 'modified_firmware.bin'
        
        # 使用 binwalk 的 -we 或 firmware-mod-kit
        # 这里简化处理
        subprocess.run([
            'tar', 'czf', str(output), '-C', str(extract_dir), '.'
        ])
        
        return output

if __name__ == "__main__":
    analyzer = FirmwareAnalyzer("firmware.bin")
    result = analyzer.analyze()
    
    print(f"[+] 分析完成: {result['file']}")
    print(f"    大小: {result['size']} bytes")
    print(f"    签名: {len(result['signatures'])} 个")
    print(f"    敏感信息: {len(result['secrets'])} 处")
```

## 常见问题

### Q: 固件加密？
- 从设备内存中提取解密后的固件
- 分析 bootloader 解密逻辑
- 寻找密钥硬编码

### Q: 非标准文件系统？
- 使用 binwalk 的 -I 选项自定义签名
- 手动分析分区表
- 参考设备 datasheet

### Q: 硬件读取失败？
- 检查电压（3.3V vs 1.8V）
- 确认芯片型号和引脚定义
- 使用逻辑分析仪抓包

## 参考项目
- binwalk: https://github.com/ReFirmLabs/binwalk (⭐ 10k+)
- firmadyne: https://github.com/firmadyne/firmadyne (⭐ 1.5k)
- firmware-mod-kit: https://github.com/rampageX/firmware-mod-kit (⭐ 2k)
- flashrom: https://flashrom.org/
