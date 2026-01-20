from dataclasses import dataclass

from hydra.core.config_store import ConfigStore
from omegaconf import MISSING

from ..utils.usable_class import Vec2


@dataclass
class BallConfig:
    pos: Vec2
    vel: Vec2
    acc: Vec2
    radius: float


@dataclass
class BoundaryConfig:
    type: str = MISSING
    restitution: float = 1


@dataclass
class CircleConfig(BoundaryConfig):
    type: str = "circle"
    radius: float = MISSING


@dataclass
class EllipseConfig(BoundaryConfig):
    type: str = "ellipse"
    a: float = MISSING
    b: float = MISSING


@dataclass
class MusicConfig:
    midi: str
    inst_idx: int


@dataclass
class SimulationConfig:
    dt: float


@dataclass
class Config:
    ball: BallConfig
    boundary: BoundaryConfig
    music: MusicConfig
    simulation: SimulationConfig


cs = ConfigStore.instance()
cs.store(name="base_config", node=Config)
cs.store(group="ball", name="ball_schema", node=BallConfig)
cs.store(group="boundary", name="circle_schema", node=CircleConfig)
cs.store(group="boundary", name="ellipse_schema", node=EllipseConfig)
cs.store(group="music", name="music_schema", node=MusicConfig)
