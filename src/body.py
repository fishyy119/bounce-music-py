from dataclasses import dataclass

from .models.manim import MetaBall
from .utils.usable_class import Vec2


@dataclass
class Ball:
    pos: Vec2
    vel: Vec2
    acc: Vec2
    radius: float = 3
    mass: float = 1.0
    last_pos: Vec2 | None = None

    def update(self, dt: float):
        # 欧拉法更新速度
        self.vel = self.vel + self.acc * dt
        next_pos = self.pos + self.vel * dt
        # next_pos = self.pos * 2 - self.last_pos + self.acc * (dt**2)

        self.last_pos = self.pos
        self.pos = next_pos

    def to_manim_meta(self) -> MetaBall:
        return MetaBall(
            radius=self.radius,
            initial_pos=self.pos.as_tuple,
            initial_vel=self.vel.as_tuple,
            acc=self.acc.as_tuple,
        )
