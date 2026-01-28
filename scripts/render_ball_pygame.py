# pyright: standard
from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import _pre_init
import imageio
import numpy as np
import tqdm
from rich import print

from scripts.pygame_renderer import Renderer
from src.models.manim import SimulationRecord
from src.utils.usable_class import Vec2


def find_latest_pkl() -> Path:
    outputs = _pre_init.PROJECT_ROOT / "outputs"
    pkl_files = list(outputs.rglob("bounce_history.pkl"))
    if not pkl_files:
        raise FileNotFoundError("No .pkl files found in outputs")
    return max(pkl_files, key=lambda p: p.stat().st_mtime)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=Path, help="path to pkl file")
    parser.add_argument("--size", type=int, default=960)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    pkl_path = find_latest_pkl() if args.input is None else args.input
    with open(pkl_path, "rb") as f:
        record: SimulationRecord = pickle.load(f)

    meta = record.meta
    # The pickle stores Q = [[Q11,Q12],[Q21,Q22]] describing the region the
    # ball center is allowed to move in. We only support circles here.
    try:
        meta_b = meta.boundary
        Q11 = float(getattr(meta_b, "Q11"))
        Q12 = float(getattr(meta_b, "Q12"))
        Q21 = float(getattr(meta_b, "Q21"))
        Q22 = float(getattr(meta_b, "Q22"))

        # require axis-aligned (Q12/Q21 ~= 0) and equal radii (circle)
        eps = 1e-6
        a = 1.0 / (Q11**0.5)
        b = 1.0 / (Q22**0.5)
        if abs(a - b) > eps or abs(Q12) > eps or abs(Q21) > eps:
            raise NotImplementedError("Only circular boundaries are supported; found an ellipse")

        # pkl stores center-restricted radius a; visual boundary should add the ball radius
        ball_r = float(meta.ball.radius)
        outer_r = a + ball_r
        world_w = world_h = 2.0 * outer_r
    except NotImplementedError:
        raise
    except Exception:
        # fallback conservative size
        world_w, world_h = 6.0, 6.0

    renderer = Renderer(args.size, args.size, world_w, world_h)

    duration = meta.music_total_time + meta.prefix_free_time
    fps = args.fps
    n_frames = max(1, int(duration * fps))

    out_dir = _pre_init.PROJECT_ROOT / "manim-videos" / f"{Path(meta.midi_file).stem}-{meta.inst_idx}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{args.size}p{fps}.mp4"

    writer = imageio.get_writer(out_file.as_posix(), fps=fps, codec="libx264", quality=8)

    collisions = record.collisions

    def ball_pos_at(t: float):
        if not collisions:
            p0 = Vec2.from_tuple(meta.ball.initial_pos)
            v0 = Vec2.from_tuple(meta.ball.initial_vel)
            acc = Vec2.from_tuple(meta.ball.acc)
            pos = p0 + v0 * t + acc * (0.5 * t * t)
            return np.array([pos.x, pos.y])

        segs = []
        segs.append(
            (0.0, collisions[0].time, Vec2.from_tuple(meta.ball.initial_pos), Vec2.from_tuple(meta.ball.initial_vel))
        )
        for c in collisions:
            segs[-1] = (segs[-1][0], c.time, segs[-1][2], segs[-1][3])
            segs.append((c.time, float("inf"), Vec2.from_tuple(c.position), Vec2.from_tuple(c.velocity_after)))

        for t0, t1, p0, v0 in segs:
            if t0 <= t <= t1:
                dt = t - t0
                pos = p0 + v0 * dt + Vec2(0.5 * meta.ball.acc[0] * dt * dt, 0.5 * meta.ball.acc[1] * dt * dt)
                return np.array([pos.x, pos.y])

        last = segs[-1]
        dt = last[1] - last[0]
        p0, v0 = last[2], last[3]
        pos = p0 + v0 * dt + Vec2(0.5 * meta.ball.acc[0] * dt * dt, 0.5 * meta.ball.acc[1] * dt * dt)
        return np.array([pos.x, pos.y])

    try:
        for i in tqdm.tqdm(range(n_frames), desc="Rendering frames"):
            t = i / fps
            pos = ball_pos_at(t)
            img = renderer.render_frame((float(pos[0]), float(pos[1])), meta.ball.radius, pieces=[])
            writer.append_data(img)
    finally:
        writer.close()

    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()
