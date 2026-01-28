import pickle
from pathlib import Path
from typing import List, cast

import _pre_init
import hydra
import numpy as np
from hydra.core.hydra_config import HydraConfig
from jaxtyping import Float
from rich import print

from src.body import Ball
from src.boundary import CircleBoundary, EllipseBoundary
from src.midi import NoteRecord
from src.models import CollisionEvent, Config, MetaData, SimulationRecord
from src.models.hydra import CircleConfig, EllipseConfig
from src.simulator import Simulator
from src.utils.usable_class import OnlineStats, PeekableIterator, Vec2

stats_vel = OnlineStats()
stats_err = OnlineStats()


@hydra.main(version_base=None, config_path=(_pre_init.ASSETS_PATH / "conf").as_posix(), config_name="config")
def main(cfg: Config):
    ball = Ball(
        pos=Vec2.from_hydra(cfg.ball.pos),
        vel=Vec2.from_hydra(cfg.ball.vel),
        acc=Vec2.from_hydra(cfg.ball.acc),
        radius=cfg.ball.radius,
    )
    match cfg.boundary.type:
        case "circle":
            cfg.boundary = cast(CircleConfig, cfg.boundary)
            boundary = CircleBoundary(
                center=Vec2(0, 0),
                radius=cfg.boundary.radius,
                restitution=cfg.boundary.restitution,
            )
        case "ellipse":
            print(
                "[bold yellow][WARN][/bold yellow]",
                "[yellow]The results of elliptical boundary may not be optimal.[/yellow]",
            )
            cfg.boundary = cast(EllipseConfig, cfg.boundary)
            boundary = EllipseBoundary.from_ab(
                center=Vec2(0, 0),
                a=cfg.boundary.a,
                b=cfg.boundary.b,
                restitution=cfg.boundary.restitution,
            )
        case _:
            raise ValueError(f"Unknown boundary type: {cfg.boundary.type}")

    simulator = Simulator(ball, boundary)
    dt = cfg.simulation.dt

    midi = NoteRecord(_pre_init.ASSETS_PATH / "midi" / cfg.music.midi)
    iter_notes = PeekableIterator(midi.notes[cfg.music.inst_idx])
    res = SimulationRecord(
        meta=MetaData(
            ball=ball.to_manim_meta(),
            boundary=boundary.to_manim_meta(),
            dt=dt,
            midi_file=midi.path.as_posix(),
            inst_idx=cfg.music.inst_idx,
        )
    )

    try:
        generate_bounce_record(simulator, dt, iter_notes, res)
    except StopIteration:
        print("Simulation completed.")
    finally:
        res.meta.ball.final_vel = simulator.ball_vel_before_collision.as_tuple
        res.meta.music_total_time = midi.duration
        res.meta.prefix_free_time = res.collisions[0].time if res.collisions else 0.0
        print("Ball velocity statistics (m/s):", end=" ")
        stats_vel.print_stats()
        print("Collision error statistics (s):", end=" ")
        stats_err.print_stats()
        print(f"Non-note collision: {len([c for c in res.collisions if not c.is_note_event])}/{len(res.collisions)}")
        output_path = Path(HydraConfig.get().runtime.output_dir) / "bounce_history.pkl"
        with open(output_path, "wb") as f:
            pickle.dump(res, f)
            print(f"Bounce history saved to {output_path}")


def generate_bounce_record(
    simulator: Simulator,
    dt: float,
    iter_notes: PeekableIterator[float],
    res: SimulationRecord,
):
    e_history: List[Float[np.ndarray, "n"]] = []
    is_init = False
    running = True
    free_time = 0
    has_note = False
    last_note_time = 0.0
    while running:
        if simulator.step(dt):
            if not is_init:  # 将自由下落后第一次碰撞视作时间起点
                free_time = simulator.time
                simulator.reset_time()
                is_init = True

            desired_duration = iter_notes.peek() - simulator.time

            last_has_note = has_note
            if last_has_note:
                stats_err.update(simulator.time - last_note_time)

            has_note = True
            while True:
                desired_e = simulator.boundary.calc_desired_restitution(
                    desired_duration,
                    simulator.ball.pos,
                    simulator.ball.vel,
                    simulator.ball.acc,
                )
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

            simulator.resolve_collision(override_e=desired_e[0].item())
            res.collisions.append(
                CollisionEvent(
                    time=simulator.time + free_time,
                    position=simulator.ball.pos.as_tuple,
                    velocity_after=simulator.ball.vel.as_tuple,
                    is_note_event=last_has_note,
                )
            )

            if has_note:
                last_note_time = iter_notes.peek()
                iter_notes.consume()

        stats_vel.update(simulator.ball.vel.vec_len())


if __name__ == "__main__":
    main()
