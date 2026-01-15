import pickle
from pathlib import Path
from typing import Iterator, List

import _pre_init
import hydra
import numpy as np
from hydra.core.hydra_config import HydraConfig
from jaxtyping import Float
from rich import print

from src.body import Ball
from src.boundary import CircleBoundary
from src.midi import NoteRecord
from src.models import CollisionEvent, Config, MetaData, SimulationRecord
from src.simulator import Simulator
from src.utils import OnlineStats, Vec2


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
    res = SimulationRecord(
        meta=MetaData(
            ball_radius=ball.radius,
            ball_initial_pos=ball.pos.as_tuple,
            ball_initial_vel=ball.vel.as_tuple,
            ball_acc=ball.acc.as_tuple,
            boundary_radius=boundary.radius,
            dt=dt,
            midi_file=midi.path.as_posix(),
            inst_idx=cfg.music.inst_idx,
        )
    )
    stats = OnlineStats()

    try:
        generate_bounce_record(simulator, dt, iter_notes, res, stats)
    except StopIteration:
        print("Simulation completed.")
    finally:
        print("Ball velocity statistics (m/s):", end=" ")
        stats.print_stats()
        print(f"Non-note collision: {len([c for c in res.collisions if not c.is_note_event])}/{len(res.collisions)}")
        output_path = Path(HydraConfig.get().runtime.output_dir) / "bounce_history.pkl"
        with open(output_path, "wb") as f:
            pickle.dump(res, f)
            print(f"Bounce history saved to {output_path}")


def generate_bounce_record(
    simulator: Simulator,
    dt: float,
    iter_notes: Iterator[float],
    res: SimulationRecord,
    stats: OnlineStats | None = None,
):
    e_history: List[Float[np.ndarray, "n"]] = []
    is_init = False
    running = True
    free_time = 0
    while running:
        if simulator.step(dt):
            if not is_init:  # 将自由下落后第一次碰撞视作时间起点
                free_time = simulator.time
                simulator.reset_time()
                is_init = True

            desired_duration = next(iter_notes) - simulator.time

            has_note = True
            while True:
                desired_e = simulator.calc_desired_restitution(desired_duration)
                if desired_e is not None:
                    break
                elif desired_duration > 0.1:
                    has_note = False
                    desired_duration /= 2
                else:
                    assert False, "Cannot find suitable restitution coefficient"

            desired_e_another = np.abs(np.log(desired_e))
            desired_e = desired_e[desired_e_another.argsort()]
            e_history.append(desired_e)

            simulator.resolve_collision(override_e=desired_e[0])
            res.collisions.append(
                CollisionEvent(
                    time=simulator.time + free_time,
                    position=simulator.ball.pos.as_tuple,
                    velocity_after=simulator.ball.vel.as_tuple,
                    is_note_event=has_note,
                )
            )

        stats.update(simulator.ball.vel.vec_len()) if stats else None


if __name__ == "__main__":
    main()
