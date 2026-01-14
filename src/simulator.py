import numpy as np
from jaxtyping import Float

from .body import Ball
from .boundary import Boundary, CircleBoundary
from .utils import Vec2


class Simulator:
    def __init__(self, ball: Ball, boundary: Boundary, gravity: float = 9.81) -> None:
        self.time = 0
        self.ball = ball
        self.boundary = boundary
        self.g = gravity
        self.ball.acc = Vec2(0, -self.g)  # 设置重力加速度
        self.bounce_flag = False

    def reset_time(self) -> None:
        """第一段下落是不可控的，所以需要将第一次反弹视作时间起点"""
        self.time = 0

    def calc_desired_restitution(self, t_f: float) -> Float[np.ndarray, "n"] | None:
        """
        根据期望的时间，计算期望恢复系数，输入反弹前速度vel与外法向norm

        Args:
            t_f (float): 期望时间

        Returns:
            float | None: 解析求解得到的期望恢复系数
        """
        if not isinstance(self.boundary, CircleBoundary):
            raise NotImplementedError

        pos = self.ball.pos  # 当前位置（碰撞点）
        vel = self.ball.vel  # 当前速度（碰撞前）
        norm = self.boundary.get_normal(pos)  # 碰撞点外法向方向

        acc = Vec2(0, -self.g)  # 重力加速度
        r_f = pos + vel * t_f + 0.5 * acc * t_f**2
        A = t_f**2
        B = 2 * t_f * r_f.dot(norm)
        C = r_f.dot(r_f) - (self.boundary.radius - self.ball.radius) ** 2

        roots = np.roots([A, B, C])  # 返回所有复数根
        real_roots = roots[np.isreal(roots)].real  # 保持为np数组，只取实根

        # 理论公式：k = -(1+e)*vel.dot(norm)
        k = real_roots / (-vel.dot(norm)) - 1
        k = k[k > 0]  # 只保留正值

        return k if len(k) > 0 else None

    def step(self, dt: float) -> bool:
        """
        步进仿真，不处理碰撞

        Args:
            dt (float): 时间步长

        Returns:
            bool: 是否发生碰撞
        """
        self.ball.update(dt)
        self.time += dt
        if self.boundary.is_colliding(self.ball):
            return not self.bounce_flag
        else:
            self.bounce_flag = False
            return False

    def resolve_collision(self, override_e: float | None = None) -> None:
        """解析碰撞，修改小球速度"""
        if self.boundary.is_colliding(self.ball):
            if not self.bounce_flag:  # 避免单次步进未离开反弹区域导致异常的多次反弹
                self.ball.vel = self.boundary.reflect(self.ball, override_e=override_e)
                self.bounce_flag = True


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
