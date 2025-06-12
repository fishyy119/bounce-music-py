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

    def change_restitution(
        self, pos: Vec2, vel: Vec2, norm: Vec2, t_f: float
    ) -> float | None:
        """根据期望的时间，计算期望恢复系数，输入反弹前速度vel与外法向norm"""
        if not isinstance(self.boundary, CircleBoundary):
            raise NotImplementedError

        acc = Vec2(0, -self.g)  # 重力加速度
        r_f = pos + vel * t_f + 0.5 * acc * t_f**2
        A = t_f**2
        B = 2 * t_f * r_f.dot(norm)
        C = r_f.dot(r_f) - (self.boundary.radius - self.ball.radius) ** 2

        roots = np.roots([A, B, C])  # 返回所有复数根
        real_roots = roots[np.isreal(roots)].real  # 保持为np数组，只取实根

        # 理论公式：k = -(1+e)*vel.dot(norm)
        k = real_roots / (-vel.dot(norm)) - 1
        print(f"{k=}")
        k = k[k > 0]  # 只保留正值

        # 设定选取最小值和最大值的比例，例如 p 选最小值，1-p 选最大值
        p = 1
        if len(k) > 0:
            return min(k) if np.random.rand() < p else max(k)
        else:
            return None

    def step(self, dt: float) -> bool:
        self.ball.update(dt)
        # print(f"{self.ball.vel=}")
        if self.boundary.is_colliding(self.ball):
            if not self.bounce_flag:
                new_e = self.change_restitution(
                    self.ball.pos,
                    self.ball.vel,
                    self.boundary.get_normal(self.ball.pos),
                    1.5,
                )
                self.ball.vel = self.boundary.reflect(self.ball, override_e=new_e)
                self.bounce_flag = True
                return True  # 表示发生碰撞
            return False
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
