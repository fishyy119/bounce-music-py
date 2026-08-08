"""Backend-neutral, serializable simulation records."""

from dataclasses import dataclass, field

type Vec2Tuple = tuple[float, float]


@dataclass(slots=True)
class BallMetadata:
    """Ball properties required to replay a simulation."""

    radius: float
    initial_pos: Vec2Tuple
    initial_vel: Vec2Tuple
    acc: Vec2Tuple
    final_vel: Vec2Tuple = (0.0, 0.0)


@dataclass(slots=True)
class EllipseMetadata:
    """Quadratic-form representation of an elliptical centre boundary."""

    q11: float
    q12: float
    q21: float
    q22: float
    center: Vec2Tuple = (0.0, 0.0)


@dataclass(slots=True)
class SimulationMetadata:
    """Metadata shared by simulation, rendering, and video composition."""

    ball: BallMetadata
    boundary: EllipseMetadata
    dt: float
    midi_file: str
    inst_idx: int
    prefix_free_time: float = 0.0
    music_total_time: float = 0.0


@dataclass(slots=True)
class CollisionEvent:
    """A collision state transition in simulation time."""

    time: float
    position: Vec2Tuple
    velocity_after: Vec2Tuple
    is_note_event: bool = False


@dataclass(slots=True)
class SimulationRecord:
    """Complete data needed to replay one simulated track."""

    metadata: SimulationMetadata
    collisions: list[CollisionEvent] = field(default_factory=lambda: [])
