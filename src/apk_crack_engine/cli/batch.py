"""batch 子命令."""

import typer
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from apk_crack_engine.engine.offline import OfflineEngine
from apk_crack_engine.engine.online import OnlineEngine
from apk_crack_engine.core.config import settings
from apk_crack_engine.core.logger import logger

app = typer.Typer(help="批量处理")


@app.command(name="crack")
def batch_crack(
    packages: List[str] = typer.Argument(..., help="包名列表"),
    mode: str = typer.Option("auto", "--mode", help="破解模式 (auto/offline/online)"),
    parallel: bool = typer.Option(False, "--parallel", help="并行模式"),
    max_workers: int = typer.Option(4, "--workers", help="最大并行数"),
) -> None:
    """批量破解."""
    logger.info(f"批量破解 {len(packages)} 个目标")

    results = []

    if parallel:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for pkg in packages:
                if mode == "offline":
                    engine = OfflineEngine(pkg)
                else:
                    engine = OnlineEngine(pkg)
                future = executor.submit(engine.crack)
                futures[future] = pkg

            for future in as_completed(futures):
                pkg = futures[future]
                try:
                    result = future.result(timeout=settings.timeout_per_round)
                    results.append((pkg, result))
                except Exception as e:
                    logger.error(f"批量破解异常 {pkg}: {e}")
                    results.append((pkg, None))
    else:
        for pkg in packages:
            if mode == "offline":
                engine = OfflineEngine(pkg)
            else:
                engine = OnlineEngine(pkg)
            result = engine.crack()
            results.append((pkg, result))

    # 输出结果
    typer.echo("\n" + "=" * 50)
    typer.echo("批量破解结果")
    typer.echo("=" * 50)
    for pkg, result in results:
        if result and result.success:
            typer.echo(f"✅ {pkg}: 成功 ({result.method})")
        elif result:
            typer.echo(f"❌ {pkg}: 失败 ({result.error})")
        else:
            typer.echo(f"❌ {pkg}: 异常")


__all__ = ["app"]
