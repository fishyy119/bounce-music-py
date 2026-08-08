"""Deterministic simulation playback and closing-effect state."""

from bisect import bisect_right
from dataclasses import dataclass
from math import cos, hypot, isfinite, pi, sin, sqrt, tanh
from random import Random

from ..models.simulation import CollisionEvent, SimulationRecord

type Point = tuple[float, float]


@dataclass(frozen=True, slots=True)
class _Segment:
    start_time: float
    position: Point
    velocity: Point


class TrajectorySampler:
    """Sample a piecewise ballistic trajectory at exact frame timestamps."""

    def __init__(self, record: SimulationRecord) -> None:
        metadata = record.metadata
        ball = metadata.ball
        self._acceleration = ball.acc
        self._collision_times = [event.time for event in record.collisions]
        self._validate_collisions(record.collisions)
        self._segments = [
            _Segment(
                start_time=0.0,
                position=ball.initial_pos,
                velocity=ball.initial_vel,
            ),
            *[
                _Segment(
                    start_time=event.time,
                    position=event.position,
                    velocity=event.velocity_after,
                )
                for event in record.collisions
            ],
        ]

    @staticmethod
    def _validate_collisions(collisions: list[CollisionEvent]) -> None:
        previous_time = -1.0
        for collision in collisions:
            if not isfinite(collision.time) or collision.time < 0:
                raise ValueError("Collision times must be finite and non-negative.")
            if collision.time <= previous_time:
                raise ValueError("Collision times must be strictly increasing.")
            previous_time = collision.time

    def position_at(self, time: float) -> Point:
        segment_index = bisect_right(self._collision_times, time)
        segment = self._segments[segment_index]
        elapsed = max(0.0, time - segment.start_time)
        return (
            segment.position[0] + segment.velocity[0] * elapsed + 0.5 * self._acceleration[0] * elapsed**2,
            segment.position[1] + segment.velocity[1] * elapsed + 0.5 * self._acceleration[1] * elapsed**2,
        )


@dataclass(frozen=True, slots=True)
class ExplosionPiece:
    offset: Point
    displacement: Point


def build_explosion(
    record: SimulationRecord,
    *,
    seed: int,
    viewport_size: Point,
    piece_count: int = 8,
) -> tuple[ExplosionPiece, ...]:
    """Precompute deterministic closing-effect particles."""

    if piece_count <= 0:
        raise ValueError("Piece count must be greater than zero.")

    rng = Random(seed)
    radius = record.metadata.ball.radius
    piece_radius = radius / sqrt(piece_count)
    offset_radius = max(0.0, radius - piece_radius)
    velocity_x, velocity_y = record.metadata.ball.final_vel
    velocity_length = hypot(velocity_x, velocity_y)
    velocity_cap = min(viewport_size) / 3
    if velocity_length > 1e-9 and velocity_cap > 0:
        capped_length = velocity_cap * tanh(velocity_length / velocity_cap)
        velocity_x *= capped_length / velocity_length
        velocity_y *= capped_length / velocity_length

    pieces: list[ExplosionPiece] = []
    for _ in range(piece_count):
        offset_distance = offset_radius * sqrt(rng.random())
        offset_angle = 2 * pi * rng.random()
        direction = 2 * pi * rng.random()
        speed = rng.uniform(0.5, 1.5)
        pieces.append(
            ExplosionPiece(
                offset=(offset_distance * cos(offset_angle), offset_distance * sin(offset_angle)),
                displacement=(velocity_x + cos(direction) * speed, velocity_y + sin(direction) * speed),
            )
        )
    return tuple(pieces)


def smooth_progress(progress: float) -> float:
    """Cubic smoothstep matching the ease-in/ease-out closing animation."""

    progress = min(1.0, max(0.0, progress))
    return progress * progress * (3.0 - 2.0 * progress)
