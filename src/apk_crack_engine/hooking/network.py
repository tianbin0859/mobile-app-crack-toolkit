"""网络验证绕过 Hook 模块."""

from typing import Optional, Callable, Any
from apk_crack_engine.core.logger import logger
from apk_crack_engine.utils.frida_utils import frida_client, FRIDA_AVAILABLE


# 网络绕过 Hook 脚本模板
NETWORK_HOOK_SCRIPT = """
Java.perform(function() {
    console.log("[*] 网络验证绕过 Hook 注入...");

    // 1. Hook OkHttp 响应
    try {
        var Response = Java.use("okhttp3.Response");
        var ResponseBody = Java.use("okhttp3.ResponseBody");
        var MediaType = Java.use("okhttp3.MediaType");

        Response.body.implementation = function() {
            var original = this.body.value;
            var content = original.string();

            var modified = content
                .replace('"status":0', '"status":1')
                .replace('"status": false', '"status": true')
                .replace('"vip":false', '"vip":true')
                .replace('"vip": false', '"vip": true')
                .replace('"code":0', '"code":1')
                .replace('"success":false', '"success":true');

            return ResponseBody.create(
                MediaType.parse("application/json"),
                modified
            );
        };
        console.log("[+] OkHttp 响应 Hook 已注入");
    } catch(e) {
        console.log("[!] OkHttp Hook 失败: " + e);
    }

    // 2. Hook HttpURLConnection
    try {
        var HttpURLConnection = Java.use("java.net.HttpURLConnection");
        HttpURLConnection.getResponseCode.implementation = function() {
            return 200;
        };
        console.log("[+] HttpURLConnection Hook 已注入");
    } catch(e) {
        console.log("[!] HttpURLConnection Hook 失败: " + e);
    }

    // 3. Hook WebView 响应
    try {
        var WebViewClient = Java.use("android.webkit.WebViewClient");
        WebViewClient.onPageFinished.implementation = function(view, url) {
            if (url && url.indexOf("auth") !== -1) {
                view.evaluateJavascript(
                    'document.body.innerHTML = document.body.innerHTML.replace("未授权", "已授权")',
                    null
                );
            }
            this.onPageFinished(view, url);
        };
        console.log("[+] WebView Hook 已注入");
    } catch(e) {
        console.log("[!] WebView Hook 失败: " + e);
    }

    console.log("[*] 网络验证绕过 Hook 注入完成");
});
"""


class NetworkBypassHook:
    """网络验证绕过 Hook."""

    def __init__(self, package_name: str) -> None:
        self.package_name = package_name
        self._session: Optional[Any] = None

    def run(self, on_message: Optional[Callable] = None) -> bool:
        """执行网络绕过 Hook.

        Args:
            on_message: 消息回调

        Returns:
            是否成功
        """
        if not FRIDA_AVAILABLE:
            logger.error("Frida 未安装")
            return False

        try:
            session = frida_client.spawn_and_attach(self.package_name)
            script = frida_client.load_script(session, NETWORK_HOOK_SCRIPT, on_message)

            pid = frida_client.spawn(self.package_name)
            frida_client.resume(pid)

            self._session = session
            logger.info(f"网络验证绕过已注入: {self.package_name}")
            return True

        except Exception as e:
            logger.error(f"网络验证绕过失败: {e}")
            return False

    def stop(self) -> None:
        """停止 Hook."""
        if self._session:
            frida_client.detach()
            self._session = None
            logger.info("网络验证绕过已停止")


__all__ = ["NetworkBypassHook", "NETWORK_HOOK_SCRIPT"]
