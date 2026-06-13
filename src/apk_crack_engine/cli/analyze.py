"""analyze 子命令."""

import typer
from apk_crack_engine.analysis.apk_analyzer import APKAnalyzer
from apk_crack_engine.core.logger import logger

app = typer.Typer(help="分析 APK")


@app.command(name="full")
def analyze_full(
    package: str = typer.Argument(..., help="目标包名"),
    apk: str = typer.Option(None, "--apk", help="APK 路径"),
) -> None:
    """执行完整分析."""
    logger.info(f"分析 APK: {package}")
    analyzer = APKAnalyzer(package, apk)
    report = analyzer.full_analysis()
    analyzer.print_report()


@app.command(name="shell")
def analyze_shell(
    apk: str = typer.Argument(..., help="APK 路径"),
) -> None:
    """检测壳类型."""
    from apk_crack_engine.analysis.shell_detector import shell_detector
    from pathlib import Path

    result = shell_detector.detect_from_apk(Path(apk))
    typer.echo(f"壳类型: {result}")


@app.command(name="protection")
def analyze_protection(
    apk: str = typer.Argument(..., help="APK 路径"),
) -> None:
    """分析保护措施."""
    from apk_crack_engine.analysis.protection import ProtectionAnalyzer
    from pathlib import Path

    analyzer = ProtectionAnalyzer()
    manifest = analyzer.analyze_manifest(Path(apk))
    libs = analyzer.analyze_native_libs(Path(apk))
    strings = analyzer.analyze_strings(Path(apk))

    typer.echo("=" * 50)
    typer.echo("保护措施分析")
    typer.echo("=" * 50)
    typer.echo(f"权限数: {len(manifest.get('permissions', []))}")
    typer.echo(f"Native 库: {len(libs)}")
    typer.echo(f"URL 数量: {len(strings.get('urls', []))}")
    typer.echo(f"IP 数量: {len(strings.get('ips', []))}")


__all__ = ["app"]
