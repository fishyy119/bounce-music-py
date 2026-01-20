from .body import Ball
from .boundary import Boundary, CircleBoundary
from .utils.usable_class import Vec2


class Simulator:
    def __init__(self, ball: Ball, boundary: Boundary) -> None:
        self.time = 0
        self.ball = ball
        self.ball_vel_before_collision = ball.vel
        self.boundary = boundary
        self.bounce_flag = False

    def reset_time(self) -> None:
        """第一段下落是不可控的，所以需要将第一次反弹视作时间起点"""
        self.time = 0

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
        self.ball_vel_before_collision = self.ball.vel
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
