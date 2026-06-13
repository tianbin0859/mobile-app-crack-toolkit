"""Lua 脚本提取 Hook 模块."""

from typing import Optional, Callable, Any
from pathlib import Path
from apk_crack_engine.core.logger import logger
from apk_crack_engine.core.config import settings
from apk_crack_engine.utils.frida_utils import frida_client, FRIDA_AVAILABLE


# Lua 提取 Hook 脚本模板
LUA_HOOK_SCRIPT = """
var dumpDir = "/sdcard/lua_dump/";

// 创建目录
var File = Java.use("java.io.File");
var dir = File.$new(dumpDir);
dir.mkdirs();

// Hook luaL_loadbufferx
var luaLoad = Module.findExportByName(null, "luaL_loadbufferx");
if (!luaLoad) {
    // 尝试其他 Lua 库名
    var modules = Process.enumerateModules();
    modules.forEach(function(module) {
        if (module.name.indexOf("lua") !== -1) {
            console.log("[*] Found Lua module: " + module.name);
        }
    });
}

if (luaLoad) {
    Interceptor.attach(luaLoad, {
        onEnter: function(args) {
            var size = args[2].toInt32();
            var buf = args[1];
            var data = Memory.readByteArray(buf, size);

            var filename = dumpDir + "script_" + Date.now() + ".lua";
            var file = new File(filename, "wb");
            file.write(data);
            file.close();

            send({"type": "lua_dump", "file": filename, "size": size});
        }
    });
    console.log("[*] Lua 脚本 Hook 已注入");
} else {
    console.log("[!] 未找到 luaL_loadbufferx");
}
"""


class LuaExtractor:
    """Lua 脚本提取器."""

    def __init__(self, package_name: str) -> None:
        self.package_name = package_name
        self._session: Optional[Any] = None
        self.output_dir = settings.work_dir / "lua_dump"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, on_message: Optional[Callable] = None) -> bool:
        """执行 Lua 提取.

        Args:
            on_message: 消息回调

        Returns:
            是否成功
        """
        if not FRIDA_AVAILABLE:
            logger.error("Frida 未安装")
            return False

        def default_handler(message: dict, data: Any) -> None:
            if message["type"] == "send":
                payload = message["payload"]
                logger.info(f"Lua 脚本已提取: {payload['file']} ({payload['size']} bytes)")

        handler = on_message or default_handler

        try:
            session = frida_client.spawn_and_attach(self.package_name)
            script = frida_client.load_script(session, LUA_HOOK_SCRIPT, handler)

            pid = frida_client.spawn(self.package_name)
            frida_client.resume(pid)

            self._session = session
            logger.info(f"Lua 提取已启动: {self.package_name}")
            return True

        except Exception as e:
            logger.error(f"Lua 提取失败: {e}")
            return False

    def stop(self) -> None:
        """停止提取."""
        if self._session:
            frida_client.detach()
            self._session = None
            logger.info("Lua 提取已停止")


__all__ = ["LuaExtractor", "LUA_HOOK_SCRIPT"]
