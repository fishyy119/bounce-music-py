# pyright: standard
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import List

import _pre_init
from manim import *  # pyright: ignore[reportWildcardImportFromLibrary]

from src.models.manim import CollisionEvent, MetaData, SimulationRecord
from src.utils import Vec2


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

config.frame_width = meta.boundary_radius * 2 * 1.2
config.frame_height = meta.boundary_radius * 2 * 1.2


def vec2_to_point(v):
    if hasattr(v, "x") and hasattr(v, "y"):
        return np.array([v.x, v.y, 0.0])
    return np.array([v[0], v[1], 0.0])


class BouncingBallScene(Scene):
    def construct(self):
        system = BallSystem(meta, record_config, collisions, self)
        system.play()
        self.wait(3)


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
            Vec2.from_tuple(self.meta.ball_initial_pos),
            Vec2.from_tuple(self.meta.ball_initial_vel),
            Vec2.from_tuple(self.meta.ball_acc),
            collisions,
        )

    def _build_boundary(self):
        self.boundary = Circle(
            radius=self.meta.boundary_radius,
            color=self.config.border_color,
        )
        self.scene.add(self.boundary)

    def _build_ball(self):
        self.acc = Vec2.from_tuple(self.meta.ball_acc)

        self.ball = Circle(
            radius=self.meta.ball_radius,
            color=self.config.ball_color,
            fill_opacity=1.0,
        )
        self.ball.move_to(vec2_to_point(self.meta.ball_initial_pos))
        self.scene.add(self.ball)

    def play(self):
        self.scene.play(BallMotionAnimation(self.ball, self.trajectory))
