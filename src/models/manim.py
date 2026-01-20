from dataclasses import dataclass, field
from typing import List, Tuple

Vec2 = Tuple[float, float]


@dataclass
class MetaBall:
    radius: float
    initial_pos: Vec2
    initial_vel: Vec2
    acc: Vec2
    final_vel: Vec2 = (0.0, 0.0)


@dataclass
class MetaEllipse:
    Q11: float
    Q12: float
    Q21: float
    Q22: float

    def __post_init__(self):
        self.type = "ellipse"


@dataclass
class MetaData:
    ball: MetaBall
    boundary: MetaEllipse
    dt: float
    midi_file: str
    inst_idx: int
    prefix_free_time: float = 0.0
    music_total_time: float = 0.0


# --------------------
# 碰撞事件部分
# --------------------
@dataclass
class CollisionEvent:
    time: float  # 碰撞发生时间
    position: Vec2  # 碰撞点坐标
    velocity_after: Vec2  # 碰撞后速度
    is_note_event: bool = False  # 是否对应音符


# --------------------
# 整个仿真记录
# --------------------
@dataclass
class SimulationRecord:
    meta: MetaData
    collisions: List[CollisionEvent] = field(default_factory=lambda: [])
