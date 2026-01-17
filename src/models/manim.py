from dataclasses import dataclass, field
from typing import List, Tuple

Vec2 = Tuple[float, float]


@dataclass
class MetaData:
    ball_radius: float
    ball_initial_pos: Vec2
    ball_initial_vel: Vec2
    ball_acc: Vec2
    boundary_radius: float
    dt: float
    midi_file: str
    inst_idx: int
    ball_final_vel: Vec2 = (0.0, 0.0)
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
