from boundary import Boundary, CircleBoundary
from body import Ball
from utils import Vec2
import numpy as np


class Simulator:
    def __init__(self, ball: Ball, boundary: Boundary, gravity: float = 9.81) -> None:
        self.ball = ball
        self.boundary = boundary
        self.g = gravity
        self.ball.acc = Vec2(0, -self.g)  # 设置重力加速度
        self.bounce_flag = False

    def change_restitution(self, pos: Vec2, vel: Vec2, t_f: float) -> float:
        """根据期望的时间，修改恢复系数"""
        g = self.g
        a = vel.vec_len() ** 2 * t_f**2
        b = 2 * t_f * vel.dot(pos) - vel.y * g * t_f**3
        c = g**2 * t_f**4 / 4 - pos.y * g * t_f**2

        roots = np.roots([a, b, c])  # 返回所有复数根
        real_roots = [r for r in roots if np.isreal(r)]  # 筛选实数根

        return min(real_roots) if real_roots else -1

    def step(self, dt: float) -> bool:
        self.ball.update(dt)
        print(f"{self.ball.vel=}")
        if self.boundary.is_colliding(self.ball):
            if not self.bounce_flag:
                self.ball.vel = self.boundary.reflect(self.ball)
                self.bounce_flag = True
            return True  # 表示发生碰撞
        self.bounce_flag = False
        return False


if __name__ == "__main__":
    # Example usage
    ball = Ball(pos=Vec2(0, 0), vel=Vec2(0, 0), acc=Vec2(0, -9.81))
    boundary = CircleBoundary(center=Vec2(0, 0), radius=50)
    simulator = Simulator(ball, boundary)

    dt = 0.001
    for _ in range(10000):
        simulator.step(dt)
        # if
        #     print(f"Ball position: {ball.pos}, velocity: {ball.vel}")
        # else:
        #     print("No collision")
