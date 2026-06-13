# macOS环境配置指南

## 场景

brew不可用 + 网络受限 + Java未安装时的APK破解环境搭建。

## 问题诊断表

| 问题 | 诊断命令 | 解决方案 |
|------|----------|----------|
| brew未安装 | `which brew` | 手动安装或使用Python替代 |
| apktool缺失 | `which apktool` | 直接下载jar |
| Java缺失 | `java -version` | 下载OpenJDK tar.gz |
| 网络超时 | curl速度 < 100KB/s | Python断点续传 |
| VPN运行但终端不走代理 | `scutil --proxy` | 手动配置代理 |

## 后台下载大文件

```python
import urllib.request
import os

def download_with_resume(url, output, timeout=300):
    downloaded = os.path.getsize(output) if os.path.exists(output) else 0
    req = urllib.request.Request(url)
    if downloaded > 0:
        req.add_header('Range', f'bytes={downloaded}-')
    
    with urllib.request.urlopen(req, timeout=timeout) as response:
        with open(output, 'ab' if downloaded else 'wb') as f:
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                f.write(chunk)
    return output
```

## 网络诊断流程

```
1. 检查VPN: ps aux | grep -iE "clash|vpn|proxy"
2. 测试GitHub: curl -s https://api.github.com | head -1
3. 测试Google: curl -s https://www.google.com | head -1
4. 判断模式:
   - GitHub通 + Google不通 = VPN分流模式
   - 都不通 = VPN未运行
   - 都通 = 网络正常
5. 检查代理端口:
   for port in 7890 7891 8080 1080; do
     echo > /dev/tcp/127.0.0.1/$port 2>/dev/null && echo "Port $port open"
   done
6. 配置终端代理:
   export ALL_PROXY=socks5://127.0.0.1:7890
   export HTTP_PROXY=http://127.0.0.1:7890
```

## 环境预检代码

```python
def environment_check():
    import shutil
    checks = {
        "adb": shutil.which("adb"),
        "frida": shutil.which("frida"),
        "apktool": shutil.which("apktool"),
        "java": shutil.which("java"),
        "python3": shutil.which("python3"),
    }
    
    if checks["adb"] and checks["frida"]:
        return "online_hook"
    elif checks["apktool"] and checks["java"]:
        return "offline_modify"
    elif checks["python3"]:
        return "python_only"
    else:
        return "insufficient"
```
