"""VIP 破解 Hook 模块."""

from typing import Optional, Callable, Any
from apk_crack_engine.core.logger import logger
from apk_crack_engine.utils.frida_utils import frida_client, FRIDA_AVAILABLE
from apk_crack_engine.core.exceptions import FridaError


# VIP Hook 脚本模板
VIP_HOOK_SCRIPT = """
Java.perform(function() {
    console.log("[*] VIP Hook 注入开始...");
    var hooked = 0;
    var failed = 0;

    // 1. Hook SharedPreferences
    try {
        var SharedPreferences = Java.use("android.content.SharedPreferences");
        var Editor = Java.use("android.content.SharedPreferences$Editor");

        SharedPreferences.getBoolean.implementation = function(key, defValue) {
            if (key && (key.toLowerCase().indexOf("vip") !== -1 ||
                       key.toLowerCase().indexOf("auth") !== -1 ||
                       key.toLowerCase().indexOf("premium") !== -1 ||
                       key.toLowerCase().indexOf("member") !== -1)) {
                console.log("[+] SharedPrefs: " + key + " = true");
                return true;
            }
            return this.getBoolean(key, defValue);
        };
        hooked++;
    } catch(e) { failed++; }

    // 2. 自动枚举 Hook
    Java.enumerateLoadedClasses({
        onMatch: function(className) {
            if (className.match(/vip|premium|auth|license|member|permission/i)) {
                try {
                    var cls = Java.use(className);
                    var methods = cls.class.getDeclaredMethods();
                    methods.forEach(function(method) {
                        var name = method.getName();
                        var returnType = method.getReturnType().getName();

                        if (name.match(/isVip|check|verify|auth|isMember|isPremium|canUse|isExpired/i)) {
                            if (returnType === "boolean") {
                                cls[name].implementation = function() {
                                    console.log("[+] Hooked: " + className + "." + name);
                                    return true;
                                };
                                hooked++;
                            } else if (returnType === "java.lang.String") {
                                cls[name].implementation = function() {
                                    console.log("[+] Hooked: " + className + "." + name);
                                    return "premium";
                                };
                                hooked++;
                            }
                        }
                    });
                } catch(e) {}
            }
        },
        onComplete: function() {
            console.log("[*] Hook 完成: " + hooked + " 成功, " + failed + " 失败");
        }
    });

    // 3. Hook Toast 显示
    try {
        var Toast = Java.use("android.widget.Toast");
        Toast.makeText.overload('android.content.Context', 'java.lang.CharSequence', 'int').implementation = function(context, text, duration) {
            if (text && text.toString().indexOf("VIP") !== -1) {
                return this.makeText(context, "VIP 破解已激活", duration);
            }
            return this.makeText(context, text, duration);
        };
    } catch(e) {}
});
"""


class VIPHook:
    """VIP 破解 Hook."""

    def __init__(self, package_name: str) -> None:
        self.package_name = package_name
        self._session: Optional[Any] = None
        self._script: Optional[Any] = None

    def run(self, on_message: Optional[Callable] = None) -> bool:
        """执行 VIP Hook.

        Args:
            on_message: 消息回调函数

        Returns:
            是否成功
        """
        if not FRIDA_AVAILABLE:
            logger.error("Frida 未安装")
            return False

        try:
            session = frida_client.spawn_and_attach(self.package_name)
            script = frida_client.load_script(session, VIP_HOOK_SCRIPT, on_message)

            # 恢复进程
            device = frida_client.get_device()
            pid = frida_client.spawn(self.package_name)
            device.resume(pid)

            self._session = session
            self._script = script

            logger.info(f"VIP Hook 已注入: {self.package_name}")
            return True

        except Exception as e:
            logger.error(f"VIP Hook 失败: {e}")
            return False

    def stop(self) -> None:
        """停止 Hook."""
        if self._session:
            frida_client.detach()
            self._session = None
            self._script = None
            logger.info("VIP Hook 已停止")


__all__ = ["VIPHook", "VIP_HOOK_SCRIPT"]
