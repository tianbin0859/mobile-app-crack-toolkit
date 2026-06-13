"""CLI 主入口."""

import typer
from apk_crack_engine.core.logger import setup_logging
from apk_crack_engine.cli import crack, analyze, unpack, license, batch

# 初始化日志
setup_logging()

app = typer.Typer(
    name="apk-crack",
    help="APK Crack Engine - 专业 Android 逆向工程工具",
    no_args_is_help=True,
)

# 注册子命令
app.add_typer(crack.app, name="crack", help="破解 APK")
app.add_typer(analyze.app, name="analyze", help="分析 APK")
app.add_typer(unpack.app, name="unpack", help="脱壳 APK")
app.add_typer(license.app, name="license", help="授权管理")
app.add_typer(batch.app, name="batch", help="批量处理")


@app.callback()
def main() -> None:
    """APK Crack Engine CLI."""
    pass


if __name__ == "__main__":
    app()
