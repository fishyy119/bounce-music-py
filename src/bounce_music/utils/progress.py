"""提供采用 tqdm 信息布局的 Rich 进度条。"""

from collections.abc import Iterable, Iterator, Sized

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    Task,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.text import Text

from .cli import stderr_console


def _format_count(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:g}"


class _CountColumn(ProgressColumn):
    """显示 tqdm 风格的已完成数/总数。"""

    def render(self, task: Task) -> Text:
        total = "?" if task.total is None else _format_count(task.total)
        return Text(f"{_format_count(task.completed)}/{total}", style="progress.download")


class RateColumn(ProgressColumn):
    """按任务 unit 字段显示正向速率或单次耗时。"""

    def render(self, task: Task) -> Text:
        unit = str(task.fields.get("unit", "it"))
        speed = task.finished_speed if task.finished else task.speed
        if speed is None or speed <= 0:
            value = f"--{unit}/s"
        elif speed >= 1:
            value = f"{speed:.2f}{unit}/s"
        else:
            value = f"{1 / speed:.2f}s/{unit}"
        return Text(value, style="progress.data.speed")


class _DetailColumn(ProgressColumn):
    """显示通过 task.fields 传入的可选详情。"""

    def render(self, task: Task) -> Text:
        detail = task.fields.get("detail")
        return Text(f", {detail}", style="dim") if detail else Text()


def create_progress(
    *,
    console: Console | None = None,
    transient: bool = False,
    refresh_per_second: float = 10,
) -> Progress:
    """创建统一写入 stderr 的 tqdm 风格 Rich 进度条。"""
    return Progress(
        TextColumn("{task.description}", style="progress.description", markup=False),
        TaskProgressColumn(
            text_format="{task.percentage:>3.0f}%|",
            text_format_no_percentage="  ?%|",
        ),
        BarColumn(bar_width=None),
        TextColumn("|"),
        _CountColumn(),
        TextColumn("["),
        TimeElapsedColumn(),
        TextColumn("<"),
        TimeRemainingColumn(compact=True),
        TextColumn(","),
        RateColumn(),
        _DetailColumn(),
        TextColumn("]"),
        console=console or stderr_console,
        transient=transient,
        refresh_per_second=refresh_per_second,
        expand=True,
    )


def _infer_total(iterable: Iterable[object], total: float | None) -> float | None:
    if total is not None:
        return total
    if isinstance(iterable, Sized):
        return float(len(iterable))
    return None


def track[T](
    iterable: Iterable[T],
    *,
    description: str = "",
    total: float | None = None,
    unit: str = "it",
    detail: str = "",
    transient: bool = False,
    progress: Progress | None = None,
) -> Iterator[T]:
    """迭代对象并更新进度；可复用一个已启动的 Progress 作为子任务。"""
    resolved_total = _infer_total(iterable, total)
    owns_progress = progress is None
    active_progress = progress or create_progress(transient=transient)

    if owns_progress:
        active_progress.start()

    task_id = active_progress.add_task(
        description,
        total=resolved_total,
        unit=unit,
        detail=detail,
    )
    try:
        for item in iterable:
            yield item
            active_progress.advance(task_id)
    finally:
        if transient and not owns_progress:
            active_progress.remove_task(task_id)
        if owns_progress:
            active_progress.stop()
