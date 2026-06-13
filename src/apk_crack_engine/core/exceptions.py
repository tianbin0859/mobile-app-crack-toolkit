"""自定义异常."""


class APKCrackEngineError(Exception):
    """基础异常."""

    pass


class EnvironmentError(APKCrackEngineError):
    """环境错误."""

    pass


class ADBError(APKCrackEngineError):
    """ADB 相关错误."""

    pass


class FridaError(APKCrackEngineError):
    """Frida 相关错误."""

    pass


class APKToolError(APKCrackEngineError):
    """apktool 相关错误."""

    pass


class CrackFailedError(APKCrackEngineError):
    """破解失败错误."""

    pass


class IntegrityCheckError(APKCrackEngineError):
    """完整性校验错误."""

    pass


class LicenseError(APKCrackEngineError):
    """授权相关错误."""

    pass


class CryptoError(APKCrackEngineError):
    """加密相关错误."""

    pass


class TimeoutError(APKCrackEngineError):
    """超时错误."""

    pass


class RetryExhaustedError(APKCrackEngineError):
    """重试耗尽错误."""

    pass
