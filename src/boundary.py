from abc import ABC, abstractmethod
from typing import Tuple

import numpy as np
from jaxtyping import Float
from manim import VMobject

from src.utils.shape import (
    ellipse_boundary_to_manim,  # pyright: ignore[reportUnknownVariableType]
)

from .body import Ball
from .models.manim import MetaEllipse
from .utils.usable_class import Mat2, Vec2

"""
由于只有极少数圆、矩形等边界能够在处理小球自身半径的同时不影响形状，
因此所有边界类的尺寸参数均描述为小球的圆心限制边界
在渲染时再进行膨胀处理
"""


class Boundary(ABC):
    restitution: float

    @abstractmethod
    def get_normal(self, pos: Vec2) -> Vec2:
        """获取单位外法向量"""

    @abstractmethod
    def is_colliding(self, ball: Ball) -> bool:
        """判断小球是否与边界碰撞"""

    @abstractmethod
    def calc_desired_restitution(self, t_f: float, pos: Vec2, vel: Vec2, acc: Vec2) -> Float[np.ndarray, "n"] | None:
        """
        根据期望的时间，计算期望恢复系数，输入反弹前速度vel与外法向norm

        Args:
            t_f (float): 期望时间
            pos (Vec2): 当前位置（碰撞点）
            vel (Vec2): 当前速度（碰撞前）
            acc (Vec2): 常值加速度

        Returns:
            float | None: 解析求解得到的期望恢复系数
        """

    def reflect(self, ball: Ball, override_e: float | None = None) -> Vec2:
        """返回小球碰撞后的速度向量，不修改小球成员"""
        # 反射逻辑：速度沿法线反弹
        # 反射公式 v' = v - (1 + e)(v·n)n
        e = override_e if override_e is not None else self.restitution
        normal = self.get_normal(ball.pos)
        reflected = ball.vel - (1 + e) * ball.vel.dot(normal) * normal
        return reflected


class EllipseBoundary(Boundary):
    def __init__(
        self,
        Q: Mat2,
        center: Vec2 = Vec2(0.0, 0.0),
        restitution: float = 1.0,
    ):
        self.center = center
        self.Q = Q
        self.restitution = restitution

    def get_normal(self, pos: Vec2) -> Vec2:
        p_rel = pos - self.center
        n_unnormalized = self.Q @ p_rel
        return Vec2.from_numpy(n_unnormalized).normalized()

    def is_colliding(self, ball: Ball) -> bool:
        p_rel = ball.pos - self.center
        return (p_rel @ self.Q @ p_rel >= 1).item()

    def calc_desired_restitution(self, t_f: float, pos: Vec2, vel: Vec2, acc: Vec2) -> Float[np.ndarray, "n"] | None:
        norm = self.get_normal(pos)  # 碰撞点外法向方向

        r_f = pos + vel * t_f + 0.5 * acc * t_f**2
        A = t_f**2 * (norm @ self.Q @ norm)
        B = 2 * t_f * (r_f @ self.Q @ norm)
        C = r_f @ self.Q @ r_f - 1

        roots = np.roots([A.item(), B.item(), C.item()])  # 返回所有复数根
        real_roots = roots[np.isreal(roots)].real  # 保持为np数组，只取实根

        # 理论公式：k = -(1+e)*vel.dot(norm)
        k = real_roots / (-vel.dot(norm)) - 1
        k = k[k > 0]  # 只保留正值

        return k if len(k) > 0 else None

    def to_manim_meta(self) -> MetaEllipse:
        return MetaEllipse(
            Q11=self.Q[0, 0],
            Q12=self.Q[0, 1],
            Q21=self.Q[1, 0],
            Q22=self.Q[1, 1],
        )

    def to_manim_object(self, ball_r: float, color: str, grid_res: int = 400) -> VMobject:
        return ellipse_boundary_to_manim(self.Q, self.center, ball_r, grid_res, color=color)

    def calc_manim_wh(self) -> Tuple[float, float]:
        # TODO: 考虑旋转
        a = 1 / np.sqrt(self.Q[0, 0])
        b = 1 / np.sqrt(self.Q[1, 1])
        return a * 2.4, b * 2.4

    @classmethod
    def from_manim_meta(cls, meta: MetaEllipse) -> "EllipseBoundary":
        Q = np.array([[meta.Q11, meta.Q12], [meta.Q21, meta.Q22]])
        return cls(Q=Q)

    @classmethod
    def from_ab(
        cls,
        a: float,
        b: float,
        center: Vec2 = Vec2(0.0, 0.0),
        restitution: float = 1.0,
    ) -> "EllipseBoundary":
        Q = np.array([[1 / a**2, 0.0], [0.0, 1 / b**2]])
        return cls(center=center, Q=Q, restitution=restitution)


class CircleBoundary(EllipseBoundary):
    def __init__(self, center: Vec2, radius: float, restitution: float = 1.0):
        self.center = center
        self.radius = radius
        self.restitution = restitution

        Q = np.array([[1 / radius**2, 0.0], [0.0, 1 / radius**2]])
        super().__init__(center=center, Q=Q, restitution=restitution)

    def get_normal(self, pos: Vec2) -> Vec2:
        return (pos - self.center).normalized()

    def is_colliding(self, ball: Ball) -> bool:
        return (ball.pos - self.center).vec_len() >= self.radius
