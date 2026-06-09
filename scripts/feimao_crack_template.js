// 飞猫助手去收费Hook脚本模板
// 适配: com.nx.main (飞猫助手)
// 保护: gold 1.12 Lua混淆 + 自定义加密 + RSA+对称加密

function hook_lua_load() {
    var module = Process.findModuleByName("libassist.so");
    if (!module) {
        console.log("[-] libassist.so not found, waiting...");
        setTimeout(hook_lua_load, 1000);
        return;
    }
    
    var luaL_loadbufferx = Module.findExportByName("libassist.so", "luaL_loadbufferx");
    if (!luaL_loadbufferx) {
        console.log("[-] luaL_loadbufferx not found");
        return;
    }
    
    console.log("[+] Hooking luaL_loadbufferx at", luaL_loadbufferx);
    
    Interceptor.attach(luaL_loadbufferx, {
        onEnter: function(args) {
            var L = args[0];
            var buff = args[1];
            var size = args[2].toInt32();
            var name = Memory.readUtf8String(args[3]);
            
            console.log("[*] Loading Lua:", name, "size:", size);
            
            // 检查是否是加密脚本（自定义格式 0x86 0x4c 0x55 0x41）
            var header = Memory.readByteArray(buff, 4);
            var headerHex = Array.from(new Uint8Array(header))
                .map(b => b.toString(16).padStart(2, '0')).join(' ');
            console.log("[*] Header:", headerHex);
            
            // 保存解密后的脚本
            if (size > 100) {
                var scriptData = Memory.readByteArray(buff, size);
                var filename = "/sdcard/lua_" + name.replace(/[^a-zA-Z0-9]/g, '_') + ".lua";
                var file = new File(filename, "wb");
                file.write(scriptData);
                file.close();
                console.log("[+] Saved to:", filename);
            }
        }
    });
}

function hook_exit() {
    var exit_addr = Module.findExportByName(null, "exit");
    if (exit_addr) {
        console.log("[+] Hooking exit() at", exit_addr);
        Interceptor.attach(exit_addr, {
            onEnter: function(args) {
                console.log("[!] exit() intercepted! code:", args[0]);
                args[0] = ptr(0);
                console.log("[*] Changed exit code to 0");
            }
        });
    }
}

function hook_network() {
    // Hook HTTP请求，模拟成功响应
    Java.perform(function() {
        try {
            var URL = Java.use("java.net.URL");
            URL.openConnection.overload().implementation = function() {
                console.log("[*] URL.openConnection:", this.toString());
                return this.openConnection.overload().call(this);
            };
        } catch(e) {}
        
        // Hook OkHttp
        try {
            var Response = Java.use("okhttp3.Response");
            Response.body.implementation = function() {
                var body = this.body.value;
                console.log("[*] Response body intercepted");
                return body;
            };
        } catch(e) {}
    });
}

function bypass_auth() {
    // Hook可能的授权检查方法
    Java.perform(function() {
        // 通用：Hook所有返回boolean的方法（可能包含isVip/isAuth等）
        Java.enumerateLoadedClasses({
            onMatch: function(className) {
                if (className.indexOf("com.nx") !== -1) {
                    try {
                        var clazz = Java.use(className);
                        var methods = clazz.class.getDeclaredMethods();
                        methods.forEach(function(method) {
                            var name = method.getName();
                            if (name.toLowerCase().indexOf("check") !== -1 ||
                                name.toLowerCase().indexOf("auth") !== -1 ||
                                name.toLowerCase().indexOf("vip") !== -1 ||
                                name.toLowerCase().indexOf("verify") !== -1) {
                                console.log("[*] Found method:", className + "." + name);
                            }
                        });
                    } catch(e) {}
                }
            },
            onComplete: function() {}
        });
    });
}

console.log("[*] Feimao Crack Script Loaded");
console.log("[*] Target: com.nx.main");

hook_lua_load();
hook_exit();
hook_network();
bypass_auth();

console.log("[+] All hooks installed");