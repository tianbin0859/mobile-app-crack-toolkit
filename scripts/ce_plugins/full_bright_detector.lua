-- full_bright_detector.lua - Cheat Engine 全亮时刻自动检测插件 v1.0
-- 自动检测目标程序功能加载完成的全亮时刻
--
-- 用法:
--   1. 将本文件放入Cheat Engine的autorun目录
--   2. 或手动加载: Table -> Load -> 选择本文件
--   3. 目标进程启动后自动检测

local FBD = {}
FBD.version = "1.0.0"
FBD.targetProcess = nil
FBD.isMonitoring = false
FBD.thresholds = {
    memoryDelta = 1024 * 1024,      -- 内存变化阈值: 1MB
    networkIdle = 5,               -- 网络空闲阈值: 5秒
    dllCount = 10,                  -- DLL加载数量阈值
    checkInterval = 1000,          -- 检测间隔: 1000ms
    stableCount = 3,                -- 稳定次数: 连续3次满足条件
}
FBD.stats = {
    lastMemorySize = 0,
    lastNetworkTime = 0,
    dllList = {},
    stableCounter = 0,
    startTime = 0,
}

-- 日志输出
function FBD.log(level, msg)
    local timestamp = os.date("%H:%M:%S")
    print(string.format("[FBD %s] [%s] %s", timestamp, level, msg))
end

-- 获取进程内存使用
function FBD.getMemorySize(pid)
    local regions = getMemoryRegionList()
    local total = 0
    for i = 1, #regions do
        if regions[i].isReadable then
            total = total + regions[i].size
        end
    end
    return total
end

-- 获取已加载DLL列表
function FBD.getLoadedDLLs()
    local modules = getModuleList()
    local dlls = {}
    for i = 1, #modules do
        table.insert(dlls, modules[i].name)
    end
    return dlls
end

-- 检测网络活动 (通过检查特定端口连接)
function FBD.checkNetworkActivity()
    -- 简化版: 检查是否有网络相关API被调用
    -- 实际实现需要Hook或监控网络API
    return false
end

-- 全亮时刻检测主逻辑
function FBD.detectFullBright()
    local currentMemory = FBD.getMemorySize()
    local memoryDelta = math.abs(currentMemory - FBD.stats.lastMemorySize)
    local currentDLLs = FBD.getLoadedDLLs()
    local dllCount = #currentDLLs
    
    FBD.log("INFO", string.format("Memory: %d KB, Delta: %d KB, DLLs: %d", 
        currentMemory / 1024, memoryDelta / 1024, dllCount))
    
    -- 条件1: 内存变化率低于阈值 (功能加载完成，不再大量分配内存)
    local memoryStable = memoryDelta < FBD.thresholds.memoryDelta
    
    -- 条件2: DLL加载数量稳定 (不再加载新DLL)
    local dllStable = dllCount >= FBD.thresholds.dllCount
    
    -- 条件3: 运行时间足够 (至少10秒)
    local timeStable = (os.time() - FBD.stats.startTime) > 10
    
    if memoryStable and dllStable and timeStable then
        FBD.stats.stableCounter = FBD.stats.stableCounter + 1
        FBD.log("INFO", string.format("Stable check: %d/%d", 
            FBD.stats.stableCounter, FBD.thresholds.stableCount))
        
        if FBD.stats.stableCounter >= FBD.thresholds.stableCount then
            return true
        end
    else
        FBD.stats.stableCounter = 0
    end
    
    FBD.stats.lastMemorySize = currentMemory
    return false
end

-- 自动Dump内存
function FBD.autoDump()
    FBD.log("INFO", "=== FULL BRIGHT DETECTED ===")
    FBD.log("INFO", "Auto-dumping memory...")
    
    -- 挂起进程
    suspendProcess(FBD.targetProcess)
    FBD.log("INFO", "Process suspended")
    
    -- 生成文件名
    local filename = string.format("%s_dump_%s.bin", 
        FBD.targetProcess, os.date("%Y%m%d_%H%M%S"))
    
    -- 执行Dump
    local regions = getMemoryRegionList()
    local dumpFile = io.open(filename, "wb")
    local totalSize = 0
    local regionCount = 0
    
    for i = 1, #regions do
        local region = regions[i]
        if region.isReadable and not region.isGuard then
            local data = readBytes(region.base, region.size, true)
            if data then
                dumpFile:write(data)
                totalSize = totalSize + region.size
                regionCount = regionCount + 1
            end
        end
    end
    
    dumpFile:close()
    
    -- 恢复进程
    resumeProcess(FBD.targetProcess)
    FBD.log("INFO", "Process resumed")
    
    FBD.log("INFO", string.format("Dump complete: %s", filename))
    FBD.log("INFO", string.format("Regions: %d, Total: %d MB", 
        regionCount, totalSize / (1024 * 1024)))
    
    -- 播放提示音
    beep()
    
    return filename
end

-- 开始监控
function FBD.startMonitoring(processName)
    FBD.targetProcess = processName
    FBD.isMonitoring = true
    FBD.stats.startTime = os.time()
    FBD.stats.lastMemorySize = 0
    FBD.stats.stableCounter = 0
    
    FBD.log("INFO", string.format("Starting Full Bright Detection for: %s", processName))
    FBD.log("INFO", string.format("Thresholds: MemoryDelta=%dKB, StableCount=%d", 
        FBD.thresholds.memoryDelta / 1024, FBD.thresholds.stableCount))
    
    -- 创建监控线程
    createThread(function()
        while FBD.isMonitoring do
            if FBD.detectFullBright() then
                local dumpFile = FBD.autoDump()
                FBD.log("INFO", string.format("Auto-dump saved: %s", dumpFile))
                FBD.isMonitoring = false
                break
            end
            sleep(FBD.thresholds.checkInterval)
        end
    end)
end

-- 停止监控
function FBD.stopMonitoring()
    FBD.isMonitoring = false
    FBD.log("INFO", "Monitoring stopped")
end

-- 手动触发Dump
function FBD.manualDump()
    FBD.log("INFO", "Manual dump triggered")
    return FBD.autoDump()
end

-- 配置阈值
function FBD.configure(config)
    if config.memoryDelta then
        FBD.thresholds.memoryDelta = config.memoryDelta
    end
    if config.stableCount then
        FBD.thresholds.stableCount = config.stableCount
    end
    if config.checkInterval then
        FBD.thresholds.checkInterval = config.checkInterval
    end
    FBD.log("INFO", "Configuration updated")
end

-- 注册CE菜单项
function FBD.registerMenu()
    local menu = getMainForm().Menu
    local items = menu.Items
    
    -- 创建FBD菜单
    local fbdMenu = createMenuItem(menu)
    fbdMenu.Caption = "全亮检测 (FBD)"
    
    -- 开始监控
    local startItem = createMenuItem(fbdMenu)
    startItem.Caption = "开始监控"
    startItem.OnClick = function()
        local process = getOpenedProcessID()
        if process > 0 then
            FBD.startMonitoring(process)
        else
            FBD.log("ERROR", "No process opened")
        end
    end
    fbdMenu.add(startItem)
    
    -- 停止监控
    local stopItem = createMenuItem(fbdMenu)
    stopItem.Caption = "停止监控"
    stopItem.OnClick = function()
        FBD.stopMonitoring()
    end
    fbdMenu.add(stopItem)
    
    -- 手动Dump
    local dumpItem = createMenuItem(fbdMenu)
    dumpItem.Caption = "手动Dump"
    dumpItem.OnClick = function()
        FBD.manualDump()
    end
    fbdMenu.add(dumpItem)
    
    -- 配置
    local configItem = createMenuItem(fbdMenu)
    configItem.Caption = "配置阈值"
    configItem.OnClick = function()
        -- 弹出配置对话框
        local form = createForm()
        form.Caption = "FBD Configuration"
        form.Width = 300
        form.Height = 200
        
        local label = createLabel(form)
        label.Caption = "Memory Delta Threshold (KB):"
        label.Top = 10
        label.Left = 10
        
        local edit = createEdit(form)
        edit.Text = tostring(FBD.thresholds.memoryDelta / 1024)
        edit.Top = 30
        edit.Left = 10
        edit.Width = 200
        
        local btn = createButton(form)
        btn.Caption = "Apply"
        btn.Top = 70
        btn.Left = 10
        btn.OnClick = function()
            local value = tonumber(edit.Text)
            if value then
                FBD.configure({memoryDelta = value * 1024})
            end
            form.close()
        end
        
        form.show()
    end
    fbdMenu.add(configItem)
    
    items.add(fbdMenu)
    FBD.log("INFO", "Menu registered")
end

-- 初始化
function FBD.init()
    FBD.log("INFO", string.format("Full Bright Detector v%s loaded", FBD.version))
    FBD.registerMenu()
end

-- 自动初始化
FBD.init()

-- 导出全局函数
_G.FBD = FBD
