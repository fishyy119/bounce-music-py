"""Simple pygame-based renderer for the bouncing ball scene.

This renderer is intentionally minimal and uses pygame.Surface to draw an ellipse
boundary and a filled ball. It returns numpy RGB images suitable for imageio.

Notes:
- For headless environments set SDL_VIDEODRIVER=dummy in the environment before importing
  (the module will set a default if not present).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

# allow headless use by defaulting to dummy if not provided
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame


@dataclass
class Piece:
    x: float
    y: float
    color: Tuple[int, int, int]
    alpha: float = 1.0


class Renderer:
    def __init__(self, width: int, height: int, world_w: float, world_h: float):
        self.width = int(width)
        self.height = int(height)
        self.world_w = float(world_w)
        self.world_h = float(world_h)

        pygame.init()
        # no display window; use Surface
        self.surface = pygame.Surface((self.width, self.height))

        # precompute scale: pixels per world unit
        self.px_per_x = self.width / self.world_w
        self.px_per_y = self.height / self.world_h

    def world_to_px(self, x: float, y: float) -> Tuple[int, int]:
        # world coords centered at (0,0). map to pixel coords
        px = int((x / self.world_w + 0.5) * self.width)
        py = int((-y / self.world_h + 0.5) * self.height)  # invert y
        return px, py

    def render_frame(self, ball_pos: Tuple[float, float], ball_radius: float, pieces: List[Piece] = None):
        pieces = pieces or []
        # clear
        self.surface.fill((0, 0, 0))

        # draw boundary as ellipse centered
        # compute ellipse pixel rect using world_w/world_h
        a_pix = int(self.px_per_x * (self.world_w / 2.0))
        b_pix = int(self.px_per_y * (self.world_h / 2.0))
        rect = pygame.Rect((self.width // 2 - a_pix, self.height // 2 - b_pix, a_pix * 2, b_pix * 2))
        pygame.draw.ellipse(
            self.surface, (160, 160, 160), rect, width=max(1, int(min(self.width, self.height) * 0.005))
        )

        # draw ball
        bx, by = ball_pos
        px, py = self.world_to_px(bx, by)
        # radius in pixels: approximate using x-scale
        r_px = max(1, int(ball_radius * self.px_per_x))
        pygame.draw.circle(self.surface, (50, 150, 245), (px, py), r_px)

        # draw pieces (simple circles)
        for p in pieces:
            pxp, pyp = self.world_to_px(p.x, p.y)
            color = tuple(int(max(0, min(255, c))) for c in p.color)
            r = max(1, int(r_px * 0.45))
            # draw with alpha by using a temporary surface
            if p.alpha < 1.0:
                tmp = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(tmp, (*color, int(p.alpha * 255)), (r + 1, r + 1), r)
                self.surface.blit(tmp, (pxp - r - 1, pyp - r - 1))
            else:
                pygame.draw.circle(self.surface, color, (pxp, pyp), r)

        # get array (pygame.surfarray.array3d returns shape (w,h,3))
        arr = pygame.surfarray.array3d(self.surface)
        img = np.transpose(arr, (1, 0, 2))  # to (h,w,3)
        return img
