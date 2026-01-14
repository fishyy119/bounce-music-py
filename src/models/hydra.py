from dataclasses import dataclass

from hydra.core.config_store import ConfigStore

from ..utils import Vec2


@dataclass
class BallConfig:
    pos: Vec2
    vel: Vec2
    acc: Vec2
    radius: float


@dataclass
class BoundaryConfig:
    center: Vec2
    radius: float
    restitution: float


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
cs.store(group="boundary", name="boundary_schema", node=BoundaryConfig)
cs.store(group="music", name="music_schema", node=MusicConfig)
