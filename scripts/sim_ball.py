from typing import List

import _pre_init  # pyright: ignore[reportUnusedImport]
import numpy as np
from jaxtyping import Float

from src.body import Ball
from src.boundary import CircleBoundary
from src.simulator import Simulator
from src.utils import Vec2

if __name__ == "__main__":
    ball = Ball(pos=Vec2(-5, 0), vel=Vec2(0, 0), acc=Vec2(0, -9.81), radius=0.5)
    boundary = CircleBoundary(center=Vec2(0, 0), radius=15, restitution=1.0)
    simulator = Simulator(ball, boundary)
    # metronome = Metronome()
    e_history: List[Float[np.ndarray, "n"]] = []

    running = True
    while running:
        if simulator.step(dt=0.001):
            desired_e = simulator.calc_desired_restitution(0.5)
            if desired_e is not None:
                desired_e_another = np.abs(np.log(desired_e))
                desired_e = desired_e[desired_e_another.argsort()]
                e_history.append(desired_e)

                simulator.resolve_collision(override_e=desired_e[0])
