import frida, sys, json, re
from typing import List, Dict, Callable, Optional, Any
from dataclasses import dataclass
from enum import Enum

class HookType(Enum):
    METHOD = "method"
    CONSTRUCTOR = "constructor"
    JNI = "jni"
    SYSCALL = "syscall"
    DYNAMIC = "dynamic"

@dataclass
class Hook:
    id: str
    type: HookType
    target: str
    script: str
    active: bool = False
    hits: int = 0

@dataclass
class ClassInfo:
    name: str
    methods: List[str]
    fields: List[str]
    superclass: Optional[str]

@dataclass
class MemoryRegion:
    base: int
    size: int
    protection: str
    name: str

class RuntimeExplorer:
    """运行时探索引擎 - 交互式Frida动态分析"""
    
    def __init__(self, device_id: Optional[str] = None):
        self.device = None
        self.session = None
        self.hooks: Dict[str, Hook] = {}
        self.device_id = device_id
        self._setup_device()
    
    def _setup_device(self):
        """设置Frida设备"""
        try:
            if self.device_id:
                self.device = frida.get_device(self.device_id)
            else:
                self.device = frida.get_usb_device()
        except Exception as e:
            print(f"⚠️ 设备连接失败: {e}")
    
    def attach(self, package_name: str) -> bool:
        """附加到目标应用"""
        try:
            self.session = self.device.attach(package_name)
            print(f"✅ 已附加到: {package_name}")
            return True
        except Exception as e:
            print(f"❌ 附加失败: {e}")
            return False
    
    def spawn(self, package_name: str) -> bool:
        """启动并附加"""
        try:
            pid = self.device.spawn([package_name])
            self.session = self.device.attach(pid)
            self.device.resume(pid)
            print(f"✅ 已启动并附加: {package_name} (PID: {pid})")
            return True
        except Exception as e:
            print(f"❌ 启动失败: {e}")
            return False
    
    def list_classes(self, pattern: str = "") -> List[ClassInfo]:
        """枚举类列表"""
        script = self.session.create_script("""
        Java.perform(function() {
            var classes = [];
            Java.enumerateLoadedClasses({
                onMatch: function(className) {
                    if (className.includes('%s')) {
                        try {
                            var cls = Java.use(className);
                            var methods = Object.getOwnPropertyNames(cls.__proto__);
                            classes.push({
                                name: className,
                                methods: methods.filter(m => m !== 'constructor'),
                                fields: Object.keys(cls.$fields || {}),
                                superclass: cls.$super ? cls.$super.className : null
                            });
                        } catch(e) {}
                    }
                },
                onComplete: function() {
                    send({type: 'classes', data: classes});
                }
            });
        });
        """ % pattern)
        
        classes = []
        def on_message(message, data):
            if message['type'] == 'send':
                payload = message['payload']
                if payload['type'] == 'classes':
                    classes.extend([ClassInfo(**c) for c in payload['data']])
        
        script.on('message', on_message)
        script.load()
        
        # 等待结果
        import time
        time.sleep(1)
        
        return classes
    
    def hook_method(self, class_name: str, method_name: str,
                   callback: Optional[Callable] = None,
                   args_types: Optional[List[str]] = None) -> Hook:
        """Hook指定方法"""
        hook_id = f"{class_name}.{method_name}"
        
        # 构建参数类型字符串
        args_str = ", ".join([f"arg{i}: {t}" for i, t in enumerate(args_types or [])])
        
        script_src = f"""
        Java.perform(function() {{
            var cls = Java.use('{class_name}');
            cls.{method_name}.overload({args_str}).implementation = function({", ".join([f"arg{i}" for i in range(len(args_types or []))])}) {{
                console.log('[+] {hook_id} called');
                {chr(10).join([f"console.log('  arg{i}:', arg{i});" for i in range(len(args_types or []))])}
                var result = this.{method_name}({", ".join([f"arg{i}" for i in range(len(args_types or []))])});
                console.log('  result:', result);
                return result;
            }};
        }});
        """
        
        script = self.session.create_script(script_src)
        script.load()
        
        hook = Hook(
            id=hook_id,
            type=HookType.METHOD,
            target=hook_id,
            script=script_src,
            active=True
        )
        self.hooks[hook_id] = hook
        
        print(f"✅ Hook已设置: {hook_id}")
        return hook
    
    def intercept_network(self, url_pattern: str = "",
                         callback: Optional[Callable] = None) -> Hook:
        """拦截网络请求"""
        hook_id = f"network_{url_pattern or 'all'}"
        
        script_src = f"""
        Java.perform(function() {{
            var URL = Java.use('java.net.URL');
            var HttpURLConnection = Java.use('java.net.HttpURLConnection');
            
            URL.$init.overload('java.lang.String').implementation = function(url) {{
                if (url.includes('{url_pattern}')) {{
                    console.log('[NET] URL: ' + url);
                    send({{type: 'network', url: url, method: 'GET'}});
                }}
                return this.$init(url);
            }};
        }});
        """
        
        script = self.session.create_script(script_src)
        script.load()
        
        hook = Hook(
            id=hook_id,
            type=HookType.DYNAMIC,
            target="network",
            script=script_src,
            active=True
        )
        self.hooks[hook_id] = hook
        
        print(f"✅ 网络拦截已设置: {url_pattern or '所有请求'}")
        return hook
    
    def dump_memory(self, address: int, size: int = 1024) -> bytes:
        """读取内存"""
        script = self.session.create_script(f"""
        var buf = Memory.readByteArray(ptr({address}), {size});
        send({{type: 'memory', data: buf}}, buf);
        """)
        
        result = None
        def on_message(message, data):
            nonlocal result
            if data:
                result = data
        
        script.on('message', on_message)
        script.load()
        
        import time
        time.sleep(0.5)
        
        return result or b""
    
    def list_memory_regions(self) -> List[MemoryRegion]:
        """列出内存区域"""
        script = self.session.create_script("""
        var regions = [];
        Process.enumerateRanges('r--').forEach(function(r) {
            regions.push({
                base: r.base.toString(),
                size: r.size,
                protection: r.protection,
                name: r.name || 'unknown'
            });
        });
        send({type: 'regions', data: regions});
        """)
        
        regions = []
        def on_message(message, data):
            if message['type'] == 'send':
                payload = message['payload']
                if payload['type'] == 'regions':
                    for r in payload['data']:
                        regions.append(MemoryRegion(
                            base=int(r['base'], 16),
                            size=r['size'],
                            protection=r['protection'],
                            name=r['name']
                        ))
        
        script.on('message', on_message)
        script.load()
        
        import time
        time.sleep(0.5)
        
        return regions
    
    def search_memory(self, pattern: bytes) -> List[int]:
        """搜索内存"""
        hex_pattern = pattern.hex()
        script = self.session.create_script(f"""
        var matches = [];
        Memory.scan(ptr(0), 0x7FFFFFFF, '{hex_pattern}', {{
            onMatch: function(addr, size) {{
                matches.push(addr.toString());
            }},
            onComplete: function() {{
                send({{type: 'matches', data: matches}});
            }}
        }});
        """)
        
        matches = []
        def on_message(message, data):
            if message['type'] == 'send':
                payload = message['payload']
                if payload['type'] == 'matches':
                    matches.extend([int(a, 16) for a in payload['data']])
        
        script.on('message', on_message)
        script.load()
        
        import time
        time.sleep(1)
        
        return matches
    
    def remove_hook(self, hook_id: str) -> bool:
        """移除Hook"""
        if hook_id in self.hooks:
            hook = self.hooks[hook_id]
            hook.active = False
            del self.hooks[hook_id]
            print(f"✅ Hook已移除: {hook_id}")
            return True
        return False
    
    def list_hooks(self) -> List[Hook]:
        """列出所有Hook"""
        return list(self.hooks.values())
    
    def detach(self):
        """分离会话"""
        if self.session:
            self.session.detach()
            print("✅ 已分离")

# 便捷函数
def explore(package: str, device: Optional[str] = None) -> RuntimeExplorer:
    """快速创建探索器并附加"""
    explorer = RuntimeExplorer(device)
    explorer.spawn(package)
    return explorer

def quick_hook(package: str, class_name: str, method_name: str) -> Hook:
    """快速Hook"""
    explorer = RuntimeExplorer()
    explorer.spawn(package)
    return explorer.hook_method(class_name, method_name)
