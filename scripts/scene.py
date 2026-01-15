# pyright: standard
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import List

import _pre_init
import pretty_midi
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

config.pixel_width = 1080
config.pixel_height = 1080
config.frame_width = meta.boundary_radius * 2 * 1.15
config.frame_height = meta.boundary_radius * 2 * 1.15


def vec2_to_point(v):
    if hasattr(v, "x") and hasattr(v, "y"):
        return np.array([v.x, v.y, 0.0])
    return np.array([v[0], v[1], 0.0])


class BouncingBallScene(Scene):
    def construct(self):
        system = BallSystem(meta, record_config, collisions, self)
        system.play()
        self.wait(3)


class BallSystem:
    def __init__(self, meta: MetaData, record_config: Config, collisions: List[CollisionEvent], scene: Scene):
        self.meta = meta
        self.config = record_config
        self.collisions = collisions
        self.scene = scene

        self._build_boundary()
        self._build_ball()

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
        """
        播放整个小球运动过程（按 collision 分段）
        """
        p0 = Vec2.from_tuple(self.meta.ball_initial_pos)
        v0 = Vec2.from_tuple(self.meta.ball_initial_vel)
        t_prev = 0.0

        i = 0
        current_session = []
        final_session = []
        duration = 0
        ball_anime = None

        while i < len(collisions):
            collision = collisions[i]
            if collision.is_note_event:
                if not current_session:  # 第一段
                    duration = 0
                    ball_anime = None
                else:  # 分到下一段
                    ball_anime = Succession(*current_session)
                    current_session.clear()

            if ball_anime is None:  # 还在组织这段动画
                dt = collision.time - t_prev
                duration += dt
                current_session.append(
                    BallSegmentAnimation(
                        ball=self.ball,
                        p0=p0,
                        v0=v0,
                        a=self.acc,
                        run_time=dt,
                    )
                )

                p0 = Vec2.from_tuple(collision.position)
                v0 = Vec2.from_tuple(collision.velocity_after)
                t_prev = collision.time
            else:
                ripple_anime = self._make_ripple_animation(duration)
                # self.scene.play(
                #     AnimationGroup(
                #         ball_anime,
                #         # ripple_anime,
                #         lag_ratio=0.0,
                #     )
                # )
                final_session.append(AnimationGroup(ball_anime, ripple_anime))

                i -= 1
            i += 1
        else:
            if ball_anime is not None:
                # ripple_anime = self._make_ripple_animation(duration)
                # self.scene.play(
                #     AnimationGroup(
                #         ball_anime,
                #         ripple_anime,
                #         lag_ratio=0.0,
                #     )
                # )
                final_session.append(ball_anime)

            self.scene.play(Succession(*final_session))

    def _make_ripple_animation(self, duration: float):
        ripple = Circle(
            radius=self.meta.boundary_radius,
            color=RED,
            stroke_width=3,
        )
        ripple.move_to(ORIGIN)
        ripple_anim = AnimationGroup(
            ripple.animate.scale(1.15).set_opacity(0),  # pyright: ignore[reportArgumentType]
            run_time=duration,
            lag_ratio=0.0,
            rate_func=linear,
        )

        return ripple_anim


class BallSegmentAnimation(Animation):
    def __init__(
        self,
        ball: Mobject,
        p0: Vec2,
        v0: Vec2,
        a: Vec2,
        run_time: float,
        **kwargs,
    ):
        super().__init__(ball, run_time=run_time, rate_func=linear, **kwargs)
        self.p0 = p0
        self.v0 = v0
        self.a = a

    def interpolate_mobject(self, alpha: float) -> None:
        t = alpha * self.run_time
        pos = self.p0 + self.v0 * t + 0.5 * self.a * t * t
        self.mobject.move_to(vec2_to_point(pos))
