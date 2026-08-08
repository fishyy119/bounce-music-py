"""提供可执行脚本共享的 Rich 命令行解析组件。"""

import argparse
import inspect
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any, ClassVar, Final, NoReturn, Self

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich_argparse import RichHelpFormatter

console: Final = Console(markup=False)
stderr_console: Final = Console(stderr=True, markup=False)


class ArgsValidationError(ValueError):
    """命令行参数或参数组合无效。"""


class GuideAction(argparse.Action):
    """以 Markdown 输出解析器绑定的模块使用指南并退出。"""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        del namespace, values, option_string
        guide = getattr(parser, "guide", None)
        content = inspect.cleandoc(guide or "没有可用的使用指南。")
        console.print(Markdown(content))
        parser.exit()


class RichArgumentParser(argparse.ArgumentParser):
    """统一 Rich 帮助、使用指南和参数错误样式。"""

    guide: str | None

    def __init__(self, *, guide: str | None = None, **kwargs: Any) -> None:
        kwargs.setdefault("formatter_class", RichHelpFormatter)
        super().__init__(**kwargs)
        self.guide = guide
        if guide is not None:
            self.add_argument("--guide", action=GuideAction, nargs=0, help="显示使用指南并退出")

    def error(self, message: str) -> NoReturn:
        """将参数错误写入标准错误流并以状态码 2 退出。"""
        self.print_usage(sys.stderr)
        stderr_console.print()
        stderr_console.print(
            Panel.fit(
                Text(message),
                title=Text("参数错误", style="bold red"),
                border_style="red",
            )
        )
        self.exit(2)

    def parse_args_into[T](
        self,
        factory: Callable[[argparse.Namespace], T],
        argv: Sequence[str] | None = None,
    ) -> T:
        try:
            namespace = super().parse_args(argv)
            return factory(namespace)
        except ArgsValidationError as exc:
            self.error(str(exc))


class ScriptArgs(ABC):
    """可执行脚本参数模型的抽象基类。"""

    DESCRIPTION: ClassVar[str | None] = None

    @classmethod
    @abstractmethod
    def add_arguments(cls, parser: RichArgumentParser) -> None:
        """向解析器添加当前脚本的命令行参数。"""

    @classmethod
    @abstractmethod
    def from_ns(cls, ns: argparse.Namespace) -> Self:
        """将 argparse Namespace 转换为内部参数模型。"""

    @abstractmethod
    def __post_init__(self) -> None:
        """校验转换完成后的参数。"""

    @classmethod
    def parse(cls, argv: Sequence[str] | None = None) -> Self:
        """创建解析器，解析、转换并校验参数。"""
        module = sys.modules.get(cls.__module__)
        guide = inspect.getdoc(module) if module is not None else None

        parser = RichArgumentParser(
            description=cls.DESCRIPTION,
            guide=guide,
        )
        cls.add_arguments(parser)
        return parser.parse_args_into(cls.from_ns, argv)
