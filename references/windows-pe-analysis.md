# Windows PE文件分析指南

## 识别文件类型

```bash
# 基础识别
file xxx.exe

# PE详细信息
readpe xxx.exe

# 节表信息 (检测加壳)
objdump -h xxx.exe
```

## 加壳识别对照表

| 壳类型 | 节名特征 | 工具 |
|--------|----------|------|
| UPX | `.upx0`, `.upx1` | upx -d |
| VMProtect | `.vmp0`, `.vmp1`, `.vmps0`, `.vmps1` | VMPDump |
| Themida | `.themida`, `.winlice` | 手动Dump |
| Enigma | `.enigma1`, `.enigma2` | 手动Dump |
| ASPack | `.aspack` | ASPackDie |
| NSIS | `.ndata` | 7z提取 |

## 静态分析流程

### 1. 字符串提取
```bash
# 提取所有可读字符串
strings xxx.exe > strings.txt

# 过滤关键词
grep -i "license\|key\|serial\|activate\|register\|vip\|premium\|http\|api" strings.txt
```

### 2. 资源提取
```bash
# 使用wrestool或 Resource Hacker
wrestool -l xxx.exe
wrestool -x xxx.exe -o resources/
```

### 3. 导入表分析
```bash
# 查看DLL依赖和API
readpe -i xxx.exe
```

## 动态分析准备

### 虚拟机安装 (macOS)
```bash
# 方案1: VirtualBox (免费)
brew install --cask virtualbox

# 方案2: UTM (免费，界面友好)
brew install --cask utm

# 方案3: VMware Fusion (付费但性能最好)
```

### Windows镜像
- 官方: https://www.microsoft.com/software-download/windows10
- 或已激活精简版

## 常见破解路径

### 路径1: 安装包提取 (NSIS)
```bash
7z x setup.exe -oextracted/
# 分析提取出的主程序
```

### 路径2: 字符串Patch
```bash
# 定位验证字符串偏移
strings -t x xxx.exe | grep "Trial"
# 用十六进制编辑器修改
```

### 路径3: x64dbg调试
1. 打开程序
2. 搜索字符串引用
3. 定位验证函数
4. 修改跳转逻辑 (nop/jmp)

### 路径4: dnSpy反编译 (.NET程序)
1. 用dnSpy打开
2. 定位验证类/方法
3. 修改IL代码
4. 保存修改

## Electron应用特殊处理

```bash
# 1. 提取ASAR
npx asar extract resources/app.asar resources/app/

# 2. 搜索授权代码
grep -r "vip\|license\|auth" resources/app/ --include="*.js"

# 3. 修改JS (将验证函数改为返回true)
# 例如: isVip() { return true; }

# 4. 重新打包
npx asar pack resources/app/ resources/app.asar
```

## 脱壳流程 (VMProtect)

### 工具准备
- x64dbg + Scylla插件
- VMPDump (专用脱壳器)
- 或手动Dump + 修复导入表

### 步骤
1. x64dbg附加程序
2. 找到OEP (原始入口点)
3. 内存Dump
4. Scylla修复导入表
5. 保存脱壳后的文件

## 限制说明

| 限制 | 说明 |
|------|------|
| macOS无法直接运行PE | 需要虚拟机或Wine |
| 强壳需Windows环境 | VMP/Themida脱壳必须在Windows |
| 7z工具缺失 | 部分系统未安装p7zip |
| BCJ2压缩 | NSIS的7z数据可能使用BCJ2过滤器 |
