/**
 * VMP执行Trace脚本
 * 功能：跟踪虚拟机执行流程，还原原始指令
 */

// 配置
var CONFIG = {
    logFile: "/sdcard/vmp_trace.log",
    maxLogSize: 10 * 1024 * 1024,  // 10MB
    traceInstructions: true,
    traceMemory: true,
    traceCalls: true
};

var logBuffer = [];
var instructionCount = 0;

function log(msg) {
    var timestamp = new Date().toISOString();
    var line = `[${timestamp}] ${msg}`;
    logBuffer.push(line);
    
    // 批量写入文件
    if (logBuffer.length >= 100) {
        flushLog();
    }
}

function flushLog() {
    if (logBuffer.length === 0) return;
    
    var file = new File(CONFIG.logFile, "a");
    file.write(logBuffer.join("\n") + "\n");
    file.close();
    logBuffer = [];
}

// 监控VM解释器
function hookVMInterpreter() {
    // 常见的VM解释器函数名
    var vmFunctions = [
        "vm_execute",
        "vm_run",
        "vm_interp",
        "execute_instruction",
        "vm_dispatch",
        "run_vm",
        "virtual_machine_run"
    ];
    
    vmFunctions.forEach(function(funcName) {
        var addr = Module.findExportByName(null, funcName);
        if (addr) {
            console.log(`[+] Found VM interpreter: ${funcName} @ ${addr}`);
            hookVMFunction(addr, funcName);
        }
    });
}

function hookVMFunction(addr, name) {
    Interceptor.attach(addr, {
        onEnter: function(args) {
            this.startTime = Date.now();
            
            if (CONFIG.traceInstructions) {
                // 尝试读取VM上下文
                var ctx = args[0];  // VM上下文指针
                if (ctx) {
                    try {
                        var pc = Memory.readPointer(ctx.add(0));  // 程序计数器
                        var opcode = Memory.readU8(pc);
                        log(`VM_${name} ENTER pc=${pc} opcode=0x${opcode.toString(16)}`);
                    } catch(e) {
                        log(`VM_${name} ENTER (context unreadable)`);
                    }
                }
            }
        },
        onLeave: function(retval) {
            var duration = Date.now() - this.startTime;
            log(`VM_${name} LEAVE ret=${retval} duration=${duration}ms`);
        }
    });
}

// 监控内存访问
function hookMemoryAccess() {
    if (!CONFIG.traceMemory) return;
    
    // Hook malloc/free
    var malloc = Module.findExportByName(null, "malloc");
    var free = Module.findExportByName(null, "free");
    
    if (malloc) {
        Interceptor.attach(malloc, {
            onLeave: function(retval) {
                log(`malloc(size=${this.size}) -> ${retval}`);
            }
        });
    }
    
    if (free) {
        Interceptor.attach(free, {
            onEnter: function(args) {
                log(`free(${args[0]})`);
            }
        });
    }
    
    // Hook memcpy/memmove
    var memcpy = Module.findExportByName(null, "memcpy");
    if (memcpy) {
        Interceptor.attach(memcpy, {
            onEnter: function(args) {
                var dest = args[0];
                var src = args[1];
                var len = args[2].toInt32();
                
                if (len < 100) {
                    try {
                        var data = Memory.readByteArray(src, len);
                        log(`memcpy(${dest}, ${src}, ${len}) data=${hexdump(data)}`);
                    } catch(e) {
                        log(`memcpy(${dest}, ${src}, ${len})`);
                    }
                } else {
                    log(`memcpy(${dest}, ${src}, ${len}) [large]`);
                }
            }
        });
    }
}

// 监控JNI调用
function hookJNI() {
    if (!CONFIG.traceCalls) return;
    
    var jniFunctions = [
        "JNI_GetMethodID",
        "JNI_GetStaticMethodID",
        "JNI_CallVoidMethod",
        "JNI_CallObjectMethod",
        "JNI_CallIntMethod",
        "JNI_CallBooleanMethod"
    ];
    
    jniFunctions.forEach(function(funcName) {
        var addr = Module.findExportByName(null, funcName);
        if (addr) {
            Interceptor.attach(addr, {
                onEnter: function(args) {
                    log(`JNI: ${funcName}`);
                }
            });
        }
    });
}

// 辅助函数
function hexdump(buffer) {
    var hex = [];
    for (var i = 0; i < Math.min(buffer.length, 32); i++) {
        hex.push(("0" + (buffer[i] & 0xFF).toString(16)).slice(-2));
    }
    return hex.join(" ");
}

// 定期刷新日志
setInterval(flushLog, 5000);

// 主入口
function main() {
    console.log("[*] VMP Trace starting...");
    console.log(`[*] Log file: ${CONFIG.logFile}`);
    
    hookVMInterpreter();
    hookMemoryAccess();
    hookJNI();
    
    console.log("[+] Hooks installed");
    
    // 程序退出时刷新日志
    Process.setExceptionHandler(function(details) {
        console.log("[!] Exception caught, flushing log...");
        flushLog();
        return false;
    });
}

main();
