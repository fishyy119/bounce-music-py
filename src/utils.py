from dataclasses import dataclass
from math import hypot
from pathlib import Path
from typing import (
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    overload,
)

from rich import print

PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_PATH = PROJECT_ROOT / "assets"


class XYProtocol(Protocol):
    x: float
    y: float


@dataclass
class Vec2:
    x: float
    y: float

    @property
    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @classmethod
    def from_hydra(cls, data: XYProtocol) -> "Vec2":
        return cls(x=data.x, y=data.y)

    @classmethod
    def from_tuple(cls, data: Sequence[float]) -> "Vec2":
        return cls(x=data[0], y=data[1])

    @overload
    def __getitem__(self, index: int) -> float: ...
    @overload
    def __getitem__(self, index: slice) -> list[float]: ...
    def __getitem__(self, index: int | slice) -> float | List[float]:
        data = [self.x, self.y]
        return data[index]

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Vec2":
        return self.__mul__(scalar)

    def dot(self, other: "Vec2") -> float:
        return self.x * other.x + self.y * other.y

    def vec_len(self) -> float:
        return hypot(self.x, self.y)

    def normalized(self) -> "Vec2":
        len_ = self.vec_len()
        return Vec2(self.x / len_, self.y / len_) if len_ != 0 else Vec2(0, 0)

    def __repr__(self) -> str:
        return f"Vec2{{x:{self.x:.3f}, y:{self.y:.3f}}}"


class OnlineStats:
    def __init__(self):
        self.n = 0
        self.mean = 0.0  # 均值
        self.m2 = 0.0  # 和方差相差一个除数n
        self.max = float("-inf")
        self.min = float("inf")

    def update(self, x: float):
        self.n += 1

        # mean / variance
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.m2 += delta * delta2

        # min / max
        if x > self.max:
            self.max = x
        if x < self.min:
            self.min = x

    @property
    def variance(self):
        return self.m2 / self.n if self.n > 0 else 0.0

    @property
    def std(self):
        return self.variance**0.5

    def print_stats(self):
        print(
            f"{self.mean:.4f}±{self.std:.4f}",
            f"[{self.min:.4f}, {self.max:.4f}]",
            f"(n={self.n})",
        )


T = TypeVar("T")


class PeekableIterator(Generic[T]):
    def __init__(self, iterable: Iterable[T]):
        self._it: Iterator[T] = iter(iterable)
        self._cache: Optional[T] = None

    def peek(self) -> T:
        if self._cache is None:
            self._cache = next(self._it)
        return self._cache

    def consume(self) -> None:
        if self._cache is not None:
            self._cache = None
