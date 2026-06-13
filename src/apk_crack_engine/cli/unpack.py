"""unpack 子命令."""

import typer
from pathlib import Path
from apk_crack_engine.utils.apk_utils import apk_utils
from apk_crack_engine.core.logger import logger

app = typer.Typer(help="脱壳 APK")


@app.command(name="dex")
def unpack_dex(
    apk: str = typer.Argument(..., help="APK 路径"),
    output: str = typer.Option(None, "--output", "-o", help="输出目录"),
) -> None:
    """提取 DEX 文件."""
    logger.info(f"提取 DEX: {apk}")
    dex_files = apk_utils.extract_dex(Path(apk), output and Path(output))
    typer.echo(f"提取 {len(dex_files)} 个 DEX 文件:")
    for f in dex_files:
        typer.echo(f"  {f}")


@app.command(name="decode")
def unpack_decode(
    apk: str = typer.Argument(..., help="APK 路径"),
    output: str = typer.Option(None, "--output", "-o", help="输出目录"),
) -> None:
    """反编译 APK."""
    logger.info(f"反编译: {apk}")
    decoded = apk_utils.decode_apk(Path(apk), output and Path(output))
    typer.echo(f"反编译完成: {decoded}")


__all__ = ["app"]
