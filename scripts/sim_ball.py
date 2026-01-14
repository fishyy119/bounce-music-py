import pickle
from pathlib import Path
from typing import Dict, Iterator, List

import _pre_init
import hydra
import numpy as np
from hydra.core.hydra_config import HydraConfig
from jaxtyping import Float
from rich import print

from src.body import Ball
from src.boundary import CircleBoundary
from src.midi import NoteRecord
from src.models import Config
from src.simulator import Simulator
from src.utils import Vec2


@hydra.main(version_base=None, config_path=(_pre_init.ASSETS_PATH / "conf").as_posix(), config_name="config")
def main(cfg: Config):
    ball = Ball(
        pos=Vec2.from_hydra(cfg.ball.pos),
        vel=Vec2.from_hydra(cfg.ball.vel),
        acc=Vec2.from_hydra(cfg.ball.acc),
        radius=cfg.ball.radius,
    )
    boundary = CircleBoundary(
        center=Vec2.from_hydra(cfg.boundary.center),
        radius=cfg.boundary.radius,
        restitution=cfg.boundary.restitution,
    )
    simulator = Simulator(ball, boundary)
    dt = cfg.simulation.dt

    midi = NoteRecord.from_midi_file(_pre_init.ASSETS_PATH / "midi" / cfg.music.midi)
    iter_notes = iter(midi.notes[cfg.music.inst_idx])
    res = {}

    try:
        generate_bounce_record(simulator, dt, iter_notes, res)
    except StopIteration:
        print("Simulation completed.")
    finally:
        output_path = Path(HydraConfig.get().runtime.output_dir) / "bounce_history.pkl"
        with open(output_path, "wb") as f:
            pickle.dump(res, f)
            print(f"Bounce history saved to {output_path}")


def generate_bounce_record(simulator: Simulator, dt: float, iter_notes: Iterator[float], res: Dict):
    e_history: List[Float[np.ndarray, "n"]] = []
    is_init = False
    running = True
    while running:
        if simulator.step(dt):
            if not is_init:  # 将自由下落后第一次碰撞视作时间起点
                simulator.reset_time()
                is_init = True

            desired_duration = next(iter_notes) - simulator.time

            while True:
                desired_e = simulator.calc_desired_restitution(desired_duration)
                if desired_e is not None:
                    break
                elif desired_duration > 0.1:
                    desired_duration /= 2
                else:
                    assert False, "Cannot find suitable restitution coefficient"

            desired_e_another = np.abs(np.log(desired_e))
            desired_e = desired_e[desired_e_another.argsort()]
            e_history.append(desired_e)

            simulator.resolve_collision(override_e=desired_e[0])


if __name__ == "__main__":
    main()
