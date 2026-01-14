# pyright: standard
# 不太行

import cma
import numpy as np
from jaxtyping import Float

from .body import Ball
from .boundary import CircleBoundary
from .simulator import Simulator
from .utils import Vec2


def eval_solution(
    simulator: Simulator, theta: Float[np.ndarray, "a"], t_target: Float[np.ndarray, "b"], dt=0.001
) -> float:
    ind = 0
    t_now = 0
    e_now = np.exp(theta[ind])
    t_eval = []

    while t_now < t_target[-1] + 1.0:
        if simulator.step(dt=dt, override_e=e_now):
            ind += 1
            t_eval.append(t_now)

            if ind >= theta.shape[0]:
                break
            e_now = np.exp(theta[ind])

        t_now += dt

    # --- 计算 Loss ---

    if len(t_eval) < len(t_target):
        t_eval += [t_now] * (len(t_target) - len(t_eval))

    t_eval = np.array(t_eval)

    # A. 时间误差项 (Timing Loss)
    loss_time = 0.0

    used_indices = set()
    for target in t_target:
        diffs = np.abs(t_eval - target)

        # 寻找全局最接近且未被占用的索引
        sorted_indices = np.argsort(diffs)
        for idx in sorted_indices:
            if idx not in used_indices:
                loss_time += (t_eval[idx] - target) ** 2
                used_indices.add(idx)
                break

    # B. 正则化项 (Regularization)
    lambda_reg = 0.01
    loss_reg = lambda_reg * np.sum(theta**2)

    total_loss = loss_time + loss_reg
    return float(total_loss)


def run_optimization(simulator: Simulator, t_target: np.ndarray):
    x0 = np.zeros(t_target.shape[0] + 1)
    sigma0 = 0.1
    es = cma.CMAEvolutionStrategy(x0, sigma0, options={"popsize": 10})

    best_x = x0
    best_loss = 1000.0

    while not es.stop():
        solutions = es.ask()
        losses = []
        for theta in solutions:
            loss = eval_solution(simulator, theta, t_target)
            losses.append(loss)
            if loss < best_loss:
                best_loss = loss
                best_x = theta

        es.tell(solutions, losses)
        es.disp()

    print(f"{best_loss=}, {best_x=}")

    es2 = cma.CMAEvolutionStrategy(best_x, 1e-7)
    while not es2.stop():
        solutions = es2.ask()
        losses = []
        for theta in solutions:
            loss = eval_solution(simulator, theta, t_target)
            losses.append(loss)
            if loss < best_loss:
                best_loss = loss
                best_x = theta

        es2.tell(solutions, losses)
        es2.disp()

    print(f"{best_loss=}, {best_x=}")
    theta_opt = best_x
    e_opt = np.exp(theta_opt)

    return theta_opt, e_opt


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    ball = Ball(pos=Vec2(0, 0), vel=Vec2(0, 0), acc=Vec2(0, -9.81))
    boundary = CircleBoundary(center=Vec2(0, 0), radius=50)
    simulator = Simulator(ball, boundary)

    run_optimization(simulator, t_target=np.array([1.0]))
