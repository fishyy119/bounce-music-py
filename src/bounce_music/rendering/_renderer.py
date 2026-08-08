"""Pycairo frame renderer with a streaming FFmpeg encoder."""
# ruff: noqa: RUF005

from __future__ import annotations  # Cairo 类型运行时会出错

import subprocess
import sys
from collections import deque
from contextlib import suppress
from dataclasses import dataclass
from math import ceil, isfinite, pi
from threading import Thread
from typing import IO, TYPE_CHECKING

import cairo

from ..utils.progress import track
from ._geometry import Point, SceneGeometry, Viewport, build_scene_geometry
from ._timeline import ExplosionPiece, TrajectorySampler, build_explosion, smooth_progress

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ..models.simulation import SimulationRecord

type RGB = tuple[float, float, float]
type RGBA = tuple[float, float, float, float]
type Color = str | RGB | RGBA

_NAMED_COLORS: dict[str, RGBA] = {
    "BLACK": (0.0, 0.0, 0.0, 1.0),
    "WHITE": (1.0, 1.0, 1.0, 1.0),
    "BLUE": (0.345, 0.769, 0.867, 1.0),
    "GREY": (0.533, 0.533, 0.533, 1.0),
    "GRAY": (0.533, 0.533, 0.533, 1.0),
    "RED": (0.988, 0.384, 0.333, 1.0),
    "GREEN": (0.514, 0.780, 0.518, 1.0),
    "YELLOW": (1.0, 0.922, 0.231, 1.0),
}


class RenderError(RuntimeError):
    """Raised when frame rendering or video encoding cannot complete."""


@dataclass(frozen=True, slots=True)
class RenderConfig:
    size: int = 960
    fps: int = 30
    ball_color: Color = "BLUE"
    border_color: Color = "GREY"
    background_color: Color = "BLACK"
    border_width: float = 4.0
    margin_ratio: float = 0.1
    pixel_tolerance: float = 0.25
    explosion_duration: float = 2.0
    random_seed: int = 0
    ffmpeg_path: str = "ffmpeg"
    codec: str = "libx264"
    crf: int = 18
    preset: str = "medium"
    show_progress: bool = True


@dataclass(frozen=True, slots=True)
class RenderResult:
    output_path: Path
    frame_count: int
    duration_seconds: float


def parse_color(color: Color) -> RGBA:
    """Convert a named, hexadecimal, or numeric color to normalized RGBA."""

    if isinstance(color, str):
        normalized = color.strip().upper()
        if normalized in _NAMED_COLORS:
            return _NAMED_COLORS[normalized]
        hexadecimal = normalized.removeprefix("#")
        if len(hexadecimal) not in (6, 8):
            raise ValueError(f"Unsupported color {color!r}. Use a known name or #RRGGBB[AA].")
        try:
            channels = tuple(int(hexadecimal[index : index + 2], 16) / 255 for index in range(0, len(hexadecimal), 2))
        except ValueError as error:
            raise ValueError(f"Invalid hexadecimal color {color!r}.") from error
        if len(channels) == 3:
            return (channels[0], channels[1], channels[2], 1.0)
        return (channels[0], channels[1], channels[2], channels[3])

    channels = tuple(float(channel) for channel in color)
    if len(channels) == 3:
        channels = (*channels, 1.0)
    if len(channels) != 4 or not all(isfinite(channel) and 0 <= channel <= 1 for channel in channels):
        raise ValueError("Numeric colors must contain three or four values in the range [0, 1].")
    return (channels[0], channels[1], channels[2], channels[3])


def _validate_config(config: RenderConfig) -> None:
    if config.size <= 0:
        raise ValueError("Render size must be greater than zero.")
    if config.size % 2 != 0:
        raise ValueError("Render size must be even for yuv420p output.")
    if config.fps <= 0:
        raise ValueError("Frame rate must be greater than zero.")
    if not isfinite(config.border_width) or config.border_width <= 0:
        raise ValueError("Border width must be a finite positive number.")
    if not isfinite(config.explosion_duration) or config.explosion_duration < 0:
        raise ValueError("Explosion duration must be finite and non-negative.")
    if not 0 <= config.crf <= 51:
        raise ValueError("CRF must be in the range [0, 51].")


def _validate_record(record: SimulationRecord, explosion_duration: float) -> tuple[float, float]:
    if not record.collisions:
        raise ValueError("A simulation record must contain at least one collision.")
    metadata = record.metadata
    motion_end = record.collisions[-1].time
    content_end = metadata.music_total_time + metadata.prefix_free_time
    if not isfinite(content_end) or content_end < motion_end:
        raise ValueError("Music duration plus prefix time must not end before the last collision.")
    return (motion_end, content_end + explosion_duration)


def _set_source(context: cairo.Context[cairo.ImageSurface], color: RGBA, *, alpha_scale: float = 1.0) -> None:
    context.set_source_rgba(color[0], color[1], color[2], color[3] * alpha_scale)


def _draw_boundary(
    context: cairo.Context[cairo.ImageSurface],
    geometry: SceneGeometry,
    color: RGBA,
    width: float,
) -> None:
    points = geometry.boundary_points
    first = geometry.viewport.to_pixel(points[0])
    context.new_path()
    context.move_to(*first)
    for point in points[1:]:
        context.line_to(*geometry.viewport.to_pixel(point))
    context.close_path()
    context.set_line_width(width)
    context.set_line_join(cairo.LineJoin.ROUND)
    _set_source(context, color)
    context.stroke()


def _draw_ball(
    context: cairo.Context[cairo.ImageSurface],
    viewport: Viewport,
    position: Point,
    radius: float,
    color: RGBA,
    *,
    opacity: float = 1.0,
) -> None:
    center = viewport.to_pixel(position)
    context.new_path()
    context.arc(center[0], center[1], radius * viewport.scale, 0.0, 2 * pi)
    _set_source(context, color, alpha_scale=opacity)
    context.fill()


def _draw_explosion(
    context: cairo.Context[cairo.ImageSurface],
    geometry: SceneGeometry,
    pieces: Sequence[ExplosionPiece],
    origin: Point,
    ball_radius: float,
    ball_color: RGBA,
    progress: float,
) -> None:
    eased = smooth_progress(progress)
    piece_radius = ball_radius / len(pieces) ** 0.5
    for piece in pieces:
        position = (
            origin[0] + piece.offset[0] + piece.displacement[0] * eased,
            origin[1] + piece.offset[1] + piece.displacement[1] * eased,
        )
        _draw_ball(
            context,
            geometry.viewport,
            position,
            piece_radius,
            ball_color,
            opacity=1.0 - eased,
        )


def _draw_frame(
    context: cairo.Context[cairo.ImageSurface],
    geometry: SceneGeometry,
    record: SimulationRecord,
    trajectory: TrajectorySampler,
    pieces: Sequence[ExplosionPiece],
    config: RenderConfig,
    time: float,
    motion_end: float,
    colors: tuple[RGBA, RGBA, RGBA],
) -> None:
    ball_color, border_color, background_color = colors
    context.save()
    context.set_operator(cairo.Operator.SOURCE)
    _set_source(context, background_color)
    context.paint()
    context.restore()

    _draw_boundary(context, geometry, border_color, config.border_width)
    if time < motion_end:
        _draw_ball(
            context,
            geometry.viewport,
            trajectory.position_at(time),
            record.metadata.ball.radius,
            ball_color,
        )
    elif config.explosion_duration > 0 and time < motion_end + config.explosion_duration:
        _draw_explosion(
            context,
            geometry,
            pieces,
            record.collisions[-1].position,
            record.metadata.ball.radius,
            ball_color,
            (time - motion_end) / config.explosion_duration,
        )


def _consume_stderr(stream: IO[bytes], tail: deque[str]) -> None:
    for raw_line in iter(stream.readline, b""):
        tail.append(raw_line.decode(errors="replace").rstrip())


def _ffmpeg_command(config: RenderConfig, temporary_output: Path) -> list[str]:
    input_pixel_format = "bgra" if sys.byteorder == "little" else "argb"
    return (
        [config.ffmpeg_path, "-hide_banner", "-loglevel", "warning", "-y"]
        + ["-f", "rawvideo"]
        + ["-pixel_format", input_pixel_format]
        + ["-video_size", f"{config.size}x{config.size}"]
        + ["-framerate", str(config.fps)]
        + ["-i", "pipe:0"]
        + ["-an", "-c:v", config.codec]
        + ["-preset", config.preset]
        + ["-crf", str(config.crf)]
        + ["-pix_fmt", "yuv420p"]
        + ["-movflags", "+faststart"]
        + [temporary_output.as_posix()]
    )


def _write_all(stream: IO[bytes], data: memoryview) -> None:
    remaining = data.cast("B")
    while remaining:
        written = stream.write(remaining)
        if written <= 0:
            raise BrokenPipeError("FFmpeg stopped accepting frame data.")
        remaining = remaining[written:]


def _encoder_error(message: str, stderr_tail: deque[str]) -> RenderError:
    details = "\n".join(stderr_tail)
    suffix = f":\n{details}" if details else ""
    return RenderError(f"{message}{suffix}")


def render_record(
    record: SimulationRecord,
    output_path: Path,
    config: RenderConfig | None = None,
) -> RenderResult:
    """Render one record to H.264 while keeping only one frame in memory."""

    render_config = RenderConfig() if config is None else config
    _validate_config(render_config)
    motion_end, requested_duration = _validate_record(record, render_config.explosion_duration)
    frame_count = max(1, ceil(requested_duration * render_config.fps))
    colors = (
        parse_color(render_config.ball_color),
        parse_color(render_config.border_color),
        parse_color(render_config.background_color),
    )
    geometry = build_scene_geometry(
        record.metadata.boundary,
        record.metadata.ball.radius,
        render_config.size,
        render_config.margin_ratio,
        render_config.pixel_tolerance,
    )
    trajectory = TrajectorySampler(record)
    pieces = build_explosion(
        record,
        seed=render_config.random_seed,
        viewport_size=(geometry.viewport.world_width, geometry.viewport.world_height),
    )

    output_path = output_path.resolve()
    if output_path.suffix.lower() != ".mp4":
        raise ValueError("Output path must use the .mp4 extension.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output_path.with_name(f".{output_path.stem}.part{output_path.suffix}")
    temporary_output.unlink(missing_ok=True)
    stderr_tail: deque[str] = deque(maxlen=60)
    surface = cairo.ImageSurface(cairo.Format.ARGB32, render_config.size, render_config.size)
    expected_stride = render_config.size * 4
    actual_stride = surface.get_stride()
    if actual_stride != expected_stride:
        surface.finish()
        raise RenderError(f"Unsupported Cairo image stride {actual_stride}; expected {expected_stride}.")
    context = cairo.Context(surface)
    context.set_antialias(cairo.Antialias.BEST)

    try:
        process = subprocess.Popen(
            _ffmpeg_command(render_config, temporary_output),
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        surface.finish()
        raise RenderError(f"Unable to start FFmpeg executable {render_config.ffmpeg_path!r}.") from error

    if process.stdin is None or process.stderr is None:
        process.kill()
        process.wait()
        surface.finish()
        raise RenderError("FFmpeg pipes could not be created.")

    stderr_thread = Thread(target=_consume_stderr, args=(process.stderr, stderr_tail), daemon=True)
    stderr_thread.start()

    try:
        frame_indices = (
            track(range(frame_count), description="Rendering frames", unit="frame")
            if render_config.show_progress
            else range(frame_count)
        )
        for frame_index in frame_indices:
            _draw_frame(
                context,
                geometry,
                record,
                trajectory,
                pieces,
                render_config,
                frame_index / render_config.fps,
                motion_end,
                colors,
            )
            surface.flush()
            try:
                _write_all(process.stdin, surface.get_data())
            except OSError as error:
                if not process.stdin.closed:
                    with suppress(OSError):
                        process.stdin.close()
                process.wait()
                stderr_thread.join()
                raise _encoder_error("FFmpeg stopped accepting frame data", stderr_tail) from error

        try:
            process.stdin.close()
        except OSError as error:
            process.wait()
            stderr_thread.join()
            raise _encoder_error("FFmpeg stopped while finalizing frame data", stderr_tail) from error
        return_code = process.wait()
        stderr_thread.join()
        if return_code != 0:
            raise _encoder_error(f"FFmpeg exited with status {return_code}", stderr_tail)
        temporary_output.replace(output_path)
    except BaseException:
        if not process.stdin.closed:
            with suppress(OSError):
                process.stdin.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        stderr_thread.join()
        temporary_output.unlink(missing_ok=True)
        raise
    finally:
        surface.finish()

    return RenderResult(
        output_path=output_path,
        frame_count=frame_count,
        duration_seconds=frame_count / render_config.fps,
    )
