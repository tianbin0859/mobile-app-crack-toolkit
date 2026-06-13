# ELF注入型外挂分析指南

## 文件结构识别

### 自解压脚本特征
```bash
file script.sh
# 输出: a /system/bin/sh script executable (binary data)

# 关键特征
- Shell脚本头 (#!/system/bin/sh)
- 随机目录选择
- gzip压缩的ELF数据
- 执行后自删除 (trap rm)
```

### 提取方法
```python
import gzip

with open('script.sh', 'rb') as f:
    data = f.read()

# 找到gzip魔数
pos = data.find(b'\x1f\x8b')
if pos != -1:
    elf_data = gzip.decompress(data[pos:])
    with open('extracted_elf', 'wb') as f:
        f.write(elf_data)
```

## ELF分析流程

### 1. 基本信息
```bash
file extracted_elf
readelf -h extracted_elf
readelf -l extracted_elf
readelf -S extracted_elf
```

### 2. 字符串分析
```bash
strings extracted_elf | grep -i "http\|https\|api\|auth\|vip\|license\|server\|verify"
```

### 3. 导入/导出函数
```bash
readelf -s extracted_elf | grep -i "ptrace\|mmap\|mprotect\|egl\|gles\|vulkan"
```

## 注入机制识别

| 特征 | 说明 |
|------|------|
| ptrace | 进程附加/内存读写 |
| mmap/mprotect | 内存分配/权限修改 |
| process_vm_writev | 跨进程内存写入 |
| dlopen/dlsym | 动态库加载 |
| pthread_create | 创建远程线程 |

## 游戏Hook识别

| API | 用途 |
|-----|------|
| eglSwapBuffers | OpenGL ES帧缓冲交换 |
| glDrawArrays/glDrawElements | 绘制调用 |
| vkQueuePresentKHR | Vulkan呈现 |
| ANativeWindow_swapBuffers | Native窗口 |

## 网络验证定位

### 常见模式
```
POST /api/login
POST /api/auth
POST /api/verify
POST /api/heartbeat
GET /api/config
```

### 字符串搜索
```bash
strings extracted_elf | grep -E "http://|https://|/api/|/auth|/verify"
```

## Patch方法

### 服务器地址修改
```python
with open('extracted_elf', 'rb') as f:
    data = bytearray(f.read())

# 替换服务器地址
old = b'hash.wskxc.cn\x00'
new = b'127.0.0.1\x00\x00\x00\x00\x00\x00\x00'

pos = data.find(old)
if pos != -1:
    data[pos:pos+len(new)] = new
```

### 重新打包
```python
import gzip

# 压缩修改后的ELF
with open('patched.sh', 'wb') as out:
    out.write(b'#!/system/bin/sh\n')
    out.write(gzip.compress(bytes(data)))
```

## 验证修改

```bash
# 1. 检查字符串是否替换成功
strings patched_elf | grep "127.0.0.1"

# 2. 检查原地址是否清除
strings patched_elf | grep "wskxc.cn"
# 应无输出
```

## 部署方法

### 推送到设备
```bash
adb push patched.sh /data/local/tmp/
adb shell chmod +x /data/local/tmp/patched.sh
```

### 运行（需要Root）
```bash
adb shell su -c "sh /data/local/tmp/patched.sh"
```

### 本地假服务器（可选）
```python
import http.server

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"code":0,"vip":true}')

httpd = http.server.HTTPServer(('127.0.0.1', 80), Handler)
httpd.serve_forever()
```
