"""crack 子命令."""

import typer
from typing import Optional
from apk_crack_engine.core.logger import logger
from apk_crack_engine.engine.offline import OfflineEngine
from apk_crack_engine.engine.online import OnlineEngine
from apk_crack_engine.engine.emulator import EmulatorEngine
from apk_crack_engine.engine.cloud import CloudEngine
from apk_crack_engine.integrity.checker import check_integrity

app = typer.Typer(help="破解 APK")


@app.command(name="offline")
def crack_offline(
    package: str = typer.Argument(..., help="目标包名"),
    apk: Optional[str] = typer.Option(None, "--apk", help="APK 路径"),
) -> None:
    """离线破解模式."""
    logger.info(f"离线破解: {package}")
    engine = OfflineEngine(package, apk)
    result = engine.crack()

    if result.success:
        typer.echo(f"✅ 破解成功! 输出: {result.output_path}")
        # 完整性校验
        if result.output_path:
            report = check_integrity(result.output_path, "apk")
            typer.echo(f"完整性评分: {report['integrity_score']}/100")
    else:
        typer.echo(f"❌ 破解失败: {result.error}")


@app.command(name="online")
def crack_online(
    package: str = typer.Argument(..., help="目标包名"),
    mode: str = typer.Option("vip", "--mode", help="破解模式 (vip/network/lua/anti_detect)"),
) -> None:
    """在线 Frida 破解模式."""
    logger.info(f"在线破解: {package} (模式: {mode})")
    engine = OnlineEngine(package)
    result = engine.crack(mode)

    if result.success:
        typer.echo(f"✅ 破解成功! 方法: {result.method}")
    else:
        typer.echo(f"❌ 破解失败: {result.error}")


@app.command(name="emulator")
def crack_emulator(
    package: str = typer.Argument(..., help="目标包名"),
) -> None:
    """模拟器绕过模式."""
    logger.info(f"模拟器绕过: {package}")
    engine = EmulatorEngine(package)
    result = engine.crack()

    if result.success:
        typer.echo(f"✅ 模拟器绕过成功!")
    else:
        typer.echo(f"❌ 模拟器绕过失败: {result.error}")


@app.command(name="cloud")
def crack_cloud(
    package: str = typer.Argument(..., help="目标包名"),
    ip: str = typer.Option(..., "--ip", help="云手机 IP"),
    port: int = typer.Option(5555, "--port", help="云手机端口"),
) -> None:
    """云手机破解模式."""
    logger.info(f"云手机破解: {package} @ {ip}:{port}")
    engine = CloudEngine(package, ip=ip, port=port)
    result = engine.crack()

    if result.success:
        typer.echo(f"✅ 云手机破解成功!")
    else:
        typer.echo(f"❌ 云手机破解失败: {result.error}")

    engine.disconnect()


@app.command(name="auto")
def crack_auto(
    package: str = typer.Argument(..., help="目标包名"),
    apk: Optional[str] = typer.Option(None, "--apk", help="APK 路径"),
) -> None:
    """自动选择最优模式破解."""
    logger.info(f"自动破解: {package}")

    # 按优先级尝试引擎
    engines = [
        OnlineEngine(package, apk),
        OfflineEngine(package, apk),
        EmulatorEngine(package, apk),
    ]

    for engine in engines:
        if engine.is_available():
            typer.echo(f"使用引擎: {engine.name} (预估成功率: {engine.success_rate:.0%})")
            result = engine.crack()
            if result.success:
                typer.echo(f"✅ 破解成功! 方法: {result.method}")
                if result.output_path:
                    typer.echo(f"输出: {result.output_path}")
                return
            else:
                typer.echo(f"⚠️ 引擎 {engine.name} 失败: {result.error}")

    typer.echo("❌ 所有引擎均失败")


__all__ = ["app"]
