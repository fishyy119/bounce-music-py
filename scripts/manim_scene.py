# pyright: standard
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import List, cast

import _pre_init
from manim import *  # pyright: ignore[reportWildcardImportFromLibrary]

from src.boundary import EllipseBoundary
from src.models.manim import CollisionEvent, MetaData, MetaEllipse, SimulationRecord
from src.utils.usable_class import Vec2


@dataclass
class Config:
    pkl_file: str
    ball_color: str
    border_color: str

    @classmethod
    def from_json(cls, path: Path) -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        filtered = {k: v for k, v in raw.items() if not k.startswith("_")}

        return cls(**filtered)


record_config = Config.from_json(_pre_init.PROJECT_ROOT / "scripts/config.tmp.json")
with open(record_config.pkl_file, "rb") as f:
    record: SimulationRecord = pickle.load(f)

meta = record.meta
collisions = record.collisions

match meta.boundary.type:
    case "ellipse":
        meta.boundary = cast(MetaEllipse, meta.boundary)
        boundary = EllipseBoundary.from_manim_meta(meta.boundary)
        w, h = boundary.calc_manim_wh()
        config.frame_height = h
        config.frame_width = w
    case _:
        raise ValueError(f"Unknown boundary type: {meta.boundary.type}")


def vec2_to_point(v):
    if hasattr(v, "x") and hasattr(v, "y"):
        return np.array([v.x, v.y, 0.0])
    return np.array([v[0], v[1], 0.0])


class BouncingBallScene(Scene):
    def construct(self):
        system = BallSystem(meta, record_config, collisions, self)
        system.play()
        system.close()
        self.wait(meta.music_total_time + meta.prefix_free_time - collisions[-1].time)


@dataclass
class BallSegment:
    t0: float
    t1: float
    p0: Vec2
    v0: Vec2


class PiecewiseTrajectory:
    def __init__(
        self,
        p0: Vec2,
        v0: Vec2,
        a: Vec2,
        collisions: List[CollisionEvent],
    ):
        self.p0 = p0
        self.v0 = v0
        self.a = a
        self.collisions = collisions

        # 预计算每一段的初始状态
        self.segments: List[BallSegment] = []
        self._build_segments()

    def _build_segments(self):
        self.segments.append(BallSegment(t0=0.0, t1=self.collisions[0].time, p0=self.p0, v0=self.v0))
        for c in self.collisions:
            self.segments[-1].t1 = c.time  # 外面固定先放进去一个，所以不用担心索引不存在
            self.segments.append(
                BallSegment(
                    t0=c.time,
                    t1=-1,
                    p0=Vec2.from_tuple(c.position),
                    v0=Vec2.from_tuple(c.velocity_after),
                )
            )

    def position_at(self, t: float) -> np.ndarray:
        for segment in self.segments:
            if segment.t0 <= t <= segment.t1:
                dt = t - segment.t0
                return vec2_to_point(segment.p0 + segment.v0 * dt + 0.5 * self.a * dt * dt)

        # 超出末尾
        segment = self.segments[-1]
        dt = segment.t1 - segment.t0
        return vec2_to_point(segment.p0 + segment.v0 * dt + 0.5 * self.a * dt * dt)


class BallMotionAnimation(Animation):
    def __init__(self, ball: Mobject, trajectory: PiecewiseTrajectory, **kwargs):
        self.trajectory = trajectory
        self.total_time = trajectory.collisions[-1].time
        super().__init__(ball, run_time=self.total_time, **kwargs)

    def interpolate(self, alpha: float):
        t = alpha * self.total_time
        pos = self.trajectory.position_at(t)
        self.mobject.move_to(pos)


class BallSystem:
    def __init__(self, meta: MetaData, record_config: Config, collisions: List[CollisionEvent], scene: Scene):
        self.meta = meta
        self.config = record_config
        self.collisions = collisions
        self.scene = scene

        self._build_boundary()
        self._build_ball()
        self.trajectory = PiecewiseTrajectory(
            Vec2.from_tuple(self.meta.ball.initial_pos),
            Vec2.from_tuple(self.meta.ball.initial_vel),
            Vec2.from_tuple(self.meta.ball.acc),
            collisions,
        )

    def _build_boundary(self):
        self.boundary = boundary.to_manim_object(self.meta.ball.radius, color=self.config.border_color)
        self.scene.add(self.boundary)

    def _build_ball(self):
        self.acc = Vec2.from_tuple(self.meta.ball.acc)

        self.ball = Circle(
            radius=self.meta.ball.radius,
            color=self.config.ball_color,
            fill_opacity=1.0,
        )
        self.ball.move_to(vec2_to_point(self.meta.ball.initial_pos))
        self.scene.add(self.ball)

    def play(self):
        self.scene.play(BallMotionAnimation(self.ball, self.trajectory))

    def close(self, run_time: float = 2):
        """让主球分裂成多个小球并逐渐消失"""

        def sample_in_disc(radius: float) -> np.ndarray:
            u = np.random.rand()
            v = np.random.rand()
            r = radius * np.sqrt(u)
            theta = 2 * np.pi * v
            return np.array([r * np.cos(theta), r * np.sin(theta), 0.0])

        def tanh_cap(v, vmax):
            s = np.linalg.norm(v)
            if s < 1e-6:
                return v
            return v / s * vmax * np.tanh(s / vmax)

        # 生成分裂小球
        pieces: List[Mobject] = []
        n_pieces = 8
        R = self.ball.radius
        piece_radius = R / (n_pieces**0.5)

        for _ in range(n_pieces):
            offset = sample_in_disc(R - piece_radius)
            piece = Circle(radius=piece_radius, color=self.ball.get_color(), fill_opacity=1.0)
            piece.move_to(self.ball.get_center() + offset)
            self.scene.add(piece)
            pieces.append(piece)

        # 隐藏原球
        self.ball.set_opacity(0.0)

        # 随机方向和速度
        vel_ball = vec2_to_point(self.meta.ball.final_vel)
        vel_ball = tanh_cap(vel_ball, min(config.frame_height, config.frame_width) / 3)
        angles = np.random.uniform(0, 2 * np.pi, n_pieces)
        speeds = np.random.uniform(0.5, 1.5, n_pieces)
        velocities = [vel_ball + np.array([np.cos(a), np.sin(a), 0]) * s for a, s in zip(angles, speeds)]

        # 播放动画
        self.scene.play(
            *[
                piece.animate.move_to(piece.get_center() + vel).set_opacity(0.0)
                for piece, vel in zip(pieces, velocities)
            ],
            run_time=run_time,
        )
