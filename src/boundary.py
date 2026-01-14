from abc import ABC, abstractmethod

from .body import Ball
from .utils import Vec2


class Boundary(ABC):
    restitution: float

    @abstractmethod
    def get_normal(self, pos: Vec2) -> Vec2:
        """获取单位外法向量"""

    @abstractmethod
    def reflect(self, ball: Ball, override_e: float | None = None) -> Vec2:
        """返回小球碰撞后的速度向量，不修改小球成员"""

    @abstractmethod
    def is_colliding(self, ball: Ball) -> bool:
        """判断小球是否与边界碰撞"""


class CircleBoundary(Boundary):
    def __init__(self, center: Vec2, radius: float, restitution: float = 1.0):
        self.center = center
        self.radius = radius
        self.restitution = restitution

    def get_normal(self, pos: Vec2) -> Vec2:
        # 返回单位外法向量
        return (pos - self.center).normalized()

    def is_colliding(self, ball: Ball) -> bool:
        return (ball.pos - self.center).vec_len() >= self.radius - ball.radius

    def reflect(self, ball: Ball, override_e: float | None = None) -> Vec2:
        # 反射逻辑：速度沿法线反弹
        # 反射公式 v' = v - (1 + e)(v·n)n
        e = override_e if override_e is not None else self.restitution
        normal = self.get_normal(ball.pos)
        reflected = ball.vel - (1 + e) * ball.vel.dot(normal) * normal
        return reflected
