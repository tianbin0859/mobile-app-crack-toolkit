"""反检测绕过 Hook 模块."""

from typing import Optional, Callable, Any
from apk_crack_engine.core.logger import logger
from apk_crack_engine.utils.frida_utils import frida_client, FRIDA_AVAILABLE


# 反检测绕过脚本模板
ANTI_DETECT_SCRIPT = """
Java.perform(function() {
    console.log("[*] 反检测绕过 Hook 注入...");

    // 1. Hook Build 类 - 模拟器检测绕过
    try {
        var Build = Java.use("android.os.Build");
        Build.FINGERPRINT.value = "google/occam/mako:10/QP1A.191005.011/5765588:user/release-keys";
        Build.MANUFACTURER.value = "Google";
        Build.MODEL.value = "Pixel 4";
        Build.PRODUCT.value = "occam";
        Build.BOARD.value = "mako";
        Build.DEVICE.value = "mako";
        Build.HARDWARE.value = "mako";
        Build.BRAND.value = "google";
        console.log("[+] Build 信息已伪造");
    } catch(e) {
        console.log("[!] Build Hook 失败: " + e);
    }

    // 2. Hook TelephonyManager
    try {
        var TelephonyManager = Java.use("android.telephony.TelephonyManager");
        TelephonyManager.getDeviceId.implementation = function() {
            return "353918050000000";
        };
        TelephonyManager.getSubscriberId.implementation = function() {
            return "310260000000000";
        };
        TelephonyManager.getSimSerialNumber.implementation = function() {
            return "89014103211118510720";
        };
        console.log("[+] TelephonyManager 已 Hook");
    } catch(e) {
        console.log("[!] TelephonyManager Hook 失败: " + e);
    }

    // 3. Hook WifiInfo
    try {
        var WifiInfo = Java.use("android.net.wifi.WifiInfo");
        WifiInfo.getMacAddress.implementation = function() {
            return "02:00:00:00:00:00";
        };
        console.log("[+] WifiInfo 已 Hook");
    } catch(e) {
        console.log("[!] WifiInfo Hook 失败: " + e);
    }

    // 4. Hook SensorManager - 模拟器传感器检测
    try {
        var SensorManager = Java.use("android.hardware.SensorManager");
        SensorManager.getSensorList.implementation = function(type) {
            var sensors = this.getSensorList(type);
            // 确保有传感器数据
            if (sensors.size() === 0) {
                console.log("[!] 模拟器传感器缺失");
            }
            return sensors;
        };
        console.log("[+] SensorManager 已 Hook");
    } catch(e) {
        console.log("[!] SensorManager Hook 失败: " + e);
    }

    // 5. Hook Debug - 反调试检测
    try {
        var Debug = Java.use("android.os.Debug");
        Debug.isDebuggerConnected.implementation = function() {
            return false;
        };
        console.log("[+] Debug 反调试已 Hook");
    } catch(e) {
        console.log("[!] Debug Hook 失败: " + e);
    }

    // 6. Hook PackageManager - 签名检测绕过
    try {
        var PackageManager = Java.use("android.content.pm.PackageManager");
        var Signature = Java.use("android.content.pm.Signature");
        PackageManager.getPackageSignatures.implementation = function(packageName) {
            var sigs = this.getPackageSignatures(packageName);
            console.log("[*] 签名请求: " + packageName);
            return sigs;
        };
        console.log("[+] PackageManager 签名检测已 Hook");
    } catch(e) {
        console.log("[!] PackageManager Hook 失败: " + e);
    }

    console.log("[*] 反检测绕过 Hook 注入完成");
});
"""


class AntiDetectHook:
    """反检测绕过 Hook."""

    def __init__(self, package_name: str) -> None:
        self.package_name = package_name
        self._session: Optional[Any] = None

    def run(self, on_message: Optional[Callable] = None) -> bool:
        """执行反检测绕过.

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
            script = frida_client.load_script(session, ANTI_DETECT_SCRIPT, on_message)

            pid = frida_client.spawn(self.package_name)
            frida_client.resume(pid)

            self._session = session
            logger.info(f"反检测绕过已注入: {self.package_name}")
            return True

        except Exception as e:
            logger.error(f"反检测绕过失败: {e}")
            return False

    def stop(self) -> None:
        """停止 Hook."""
        if self._session:
            frida_client.detach()
            self._session = None
            logger.info("反检测绕过已停止")


__all__ = ["AntiDetectHook", "ANTI_DETECT_SCRIPT"]
