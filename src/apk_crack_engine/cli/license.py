"""license 子命令."""

import typer
from typing import Optional
from apk_crack_engine.license.generator import LicenseGenerator
from apk_crack_engine.license.validator import LicenseManager
from apk_crack_engine.core.logger import logger

app = typer.Typer(help="授权管理")


@app.command(name="generate")
def license_generate(
    days: int = typer.Option(30, "--days", "-d", help="有效天数"),
    count: int = typer.Option(1, "--count", "-c", help="生成数量"),
    bind: bool = typer.Option(True, "--bind/--no-bind", help="是否绑定机器"),
) -> None:
    """生成卡密."""
    logger.info(f"生成 {count} 个卡密 (有效期 {days} 天)")
    gen = LicenseGenerator()
    licenses = gen.generate_batch(count, days, bind)
    for key in licenses:
        typer.echo(key)


@app.command(name="verify")
def license_verify(
    key: str = typer.Argument(..., help="卡密"),
    device: Optional[str] = typer.Option(None, "--device", help="设备ID"),
) -> None:
    """验证卡密."""
    manager = LicenseManager()
    valid, message = manager.verify(key, device)
    if valid:
        typer.echo(f"✅ {message}")
    else:
        typer.echo(f"❌ {message}")


@app.command(name="activate")
def license_activate(
    key: str = typer.Argument(..., help="卡密"),
    device: str = typer.Option(..., "--device", help="设备ID"),
) -> None:
    """激活卡密."""
    manager = LicenseManager()
    success, message = manager.activate(key, device)
    if success:
        typer.echo(f"✅ {message}")
    else:
        typer.echo(f"❌ {message}")


@app.command(name="info")
def license_info(
    key: str = typer.Argument(..., help="卡密"),
) -> None:
    """查看卡密信息."""
    manager = LicenseManager()
    info = manager.get_license_info(key)
    if info:
        for k, v in info.items():
            typer.echo(f"{k}: {v}")
    else:
        typer.echo("无法获取卡密信息")


__all__ = ["app"]
