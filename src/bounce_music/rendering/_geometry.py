"""Geometry preparation for the raster renderer."""

from dataclasses import dataclass
from math import cos, hypot, isfinite, pi, sin

import numpy as np
from numpy.typing import NDArray

from ..models.simulation import EllipseMetadata

type Point = tuple[float, float]
type FloatArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class Viewport:
    """Uniform world-to-pixel transform for a square output surface."""

    world_center: Point
    scale: float
    world_width: float
    world_height: float
    size: int

    def to_pixel(self, point: Point) -> Point:
        x = self.size / 2 + (point[0] - self.world_center[0]) * self.scale
        y = self.size / 2 - (point[1] - self.world_center[1]) * self.scale
        return (x, y)


@dataclass(frozen=True, slots=True)
class SceneGeometry:
    boundary_points: tuple[Point, ...]
    viewport: Viewport


@dataclass(frozen=True, slots=True)
class _EllipseParameters:
    rotation: FloatArray
    axes: Point
    center: FloatArray
    offset: float

    def point_at(self, theta: float) -> FloatArray:
        cos_theta = cos(theta)
        sin_theta = sin(theta)
        local_point = np.array(
            [self.axes[0] * cos_theta, self.axes[1] * sin_theta],
            dtype=np.float64,
        )
        local_normal = np.array(
            [cos_theta / self.axes[0], sin_theta / self.axes[1]],
            dtype=np.float64,
        )
        world_normal = self.rotation @ local_normal
        normal_length = hypot(float(world_normal[0]), float(world_normal[1]))
        if normal_length == 0:
            raise ValueError("Ellipse produced a zero-length normal.")
        return self.center + self.rotation @ local_point + self.offset * world_normal / normal_length


def _ellipse_parameters(metadata: EllipseMetadata, offset: float) -> _EllipseParameters:
    if not isfinite(offset) or offset < 0:
        raise ValueError("Ball radius must be a finite, non-negative number.")

    matrix = np.array(
        [[metadata.q11, metadata.q12], [metadata.q21, metadata.q22]],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(matrix)):
        raise ValueError("Ellipse matrix must contain only finite values.")
    if not np.allclose(matrix, matrix.T, rtol=1e-9, atol=1e-12):
        raise ValueError("Ellipse matrix must be symmetric.")

    eigenvalues, rotation = np.linalg.eigh(matrix)
    if np.any(eigenvalues <= 0):
        raise ValueError("Ellipse matrix must be positive definite.")

    axes_array = 1.0 / np.sqrt(eigenvalues)
    axes = (float(axes_array[0]), float(axes_array[1]))
    center = np.array(metadata.center, dtype=np.float64)
    if not np.all(np.isfinite(center)):
        raise ValueError("Ellipse centre must contain only finite values.")

    return _EllipseParameters(
        rotation=np.asarray(rotation, dtype=np.float64),
        axes=axes,
        center=center,
        offset=offset,
    )


def _point_to_segment_distance(point: FloatArray, start: FloatArray, end: FloatArray) -> float:
    segment = end - start
    length_squared = float(np.dot(segment, segment))
    if length_squared == 0:
        return hypot(float(point[0] - start[0]), float(point[1] - start[1]))

    ratio = float(np.dot(point - start, segment)) / length_squared
    ratio = min(1.0, max(0.0, ratio))
    projection = start + ratio * segment
    difference = point - projection
    return hypot(float(difference[0]), float(difference[1]))


def _sample_adaptive(
    ellipse: _EllipseParameters,
    pixel_scale: float,
    pixel_tolerance: float,
    *,
    base_segments: int = 16,
    max_depth: int = 12,
) -> tuple[Point, ...]:
    points: list[Point] = []

    def append_segment(
        theta_start: float,
        point_start: FloatArray,
        theta_end: float,
        point_end: FloatArray,
        depth: int,
    ) -> None:
        theta_middle = (theta_start + theta_end) / 2
        point_middle = ellipse.point_at(theta_middle)
        error_pixels = _point_to_segment_distance(point_middle, point_start, point_end) * pixel_scale
        if error_pixels > pixel_tolerance and depth < max_depth:
            append_segment(theta_start, point_start, theta_middle, point_middle, depth + 1)
            append_segment(theta_middle, point_middle, theta_end, point_end, depth + 1)
            return
        points.append((float(point_end[0]), float(point_end[1])))

    first = ellipse.point_at(0.0)
    points.append((float(first[0]), float(first[1])))
    for index in range(base_segments):
        theta_start = 2 * pi * index / base_segments
        theta_end = 2 * pi * (index + 1) / base_segments
        append_segment(
            theta_start,
            ellipse.point_at(theta_start),
            theta_end,
            ellipse.point_at(theta_end),
            0,
        )
    return tuple(points)


def build_scene_geometry(
    metadata: EllipseMetadata,
    ball_radius: float,
    size: int,
    margin_ratio: float,
    pixel_tolerance: float,
) -> SceneGeometry:
    """Build an offset ellipse and a viewport without raster morphology."""

    if size <= 0:
        raise ValueError("Render size must be greater than zero.")
    if not 0 <= margin_ratio < 0.5:
        raise ValueError("Margin ratio must be in the range [0, 0.5).")
    if pixel_tolerance <= 0:
        raise ValueError("Pixel tolerance must be greater than zero.")

    ellipse = _ellipse_parameters(metadata, ball_radius)
    estimate = np.stack([ellipse.point_at(2 * pi * index / 720) for index in range(720)])
    minimum = np.min(estimate, axis=0)
    maximum = np.max(estimate, axis=0)
    span = maximum - minimum
    world_width = float(span[0])
    world_height = float(span[1])
    if world_width <= 0 or world_height <= 0:
        raise ValueError("Ellipse must have a positive width and height.")

    usable_fraction = 1.0 - 2.0 * margin_ratio
    scale = min(size * usable_fraction / world_width, size * usable_fraction / world_height)
    world_center_array = (minimum + maximum) / 2
    viewport = Viewport(
        world_center=(float(world_center_array[0]), float(world_center_array[1])),
        scale=scale,
        world_width=world_width,
        world_height=world_height,
        size=size,
    )
    return SceneGeometry(
        boundary_points=_sample_adaptive(ellipse, scale, pixel_tolerance),
        viewport=viewport,
    )
