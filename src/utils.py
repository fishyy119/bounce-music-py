from math import hypot

from typing import List, Tuple, TypeAlias, Union, overload
from dataclasses import dataclass

ScreenReturn: TypeAlias = Union["Vec2", float, None]


@dataclass
class Vec2:
    x: float
    y: float

    @property
    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

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


class CoordinateTransformer:
    def __init__(self, screen_size: tuple[int, int], ppm: float):
        self.width, self.height = screen_size
        # self.screen_center = screen_center  # 屏幕中心在屏幕坐标系下坐标
        self.ppm = ppm  # pixels / meter

    @property
    def screen_center(self) -> Vec2:
        return Vec2(self.width // 2, self.height // 2)

    @overload
    def to_screen(self, value: Vec2) -> Vec2: ...
    @overload
    def to_screen(self, value: float) -> float: ...
    def to_screen(self, value: ScreenReturn) -> ScreenReturn:
        if isinstance(value, Vec2):
            # 将仿真坐标转换为屏幕坐标
            x = self.screen_center.x + value.x * self.ppm
            y = self.screen_center.y - value.y * self.ppm  # y轴翻转
            return Vec2(x, y)
        elif isinstance(value, (float, int)):
            return value * self.ppm

    def to_sim(self, pos: Vec2) -> Vec2:
        # 将屏幕坐标转换为仿真坐标
        x = (pos.x - self.screen_center.x) / self.ppm
        y = -(pos.y - self.screen_center.y) / self.ppm  # y轴翻转
        return Vec2(x, y)

    def update_screen_size(self, new_size: tuple[int, int]):
        self.width, self.height = new_size


class Metronome:
    def __init__(self):
        self.last_tick = 0

    def __call__(self, ms: int):
        print(f"{ms / 1000:.2f} - {(ms - self.last_tick) / 1000:.2f}")
        self.last_tick = ms
