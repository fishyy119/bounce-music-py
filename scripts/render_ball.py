# pyright: standard
"""Render a simulation record with the in-process Pycairo backend.

> **Behavior**

Read a `bounce_history.pkl` simulation record, replay its trajectory with Pycairo, stream the frames to FFmpeg, and
write an MP4 plus a matching Pickle sidecar under `rendered-videos/`.

> **Common commands**

Render an explicit record at 960 x 960 and 30 fps:

```bash
python scripts/render_ball.py --input outputs/2026-01-01/00-00-00/bounce_history.pkl --size 960 --fps 30
```

Omit `--input` to render the most recently modified `outputs/**/bounce_history.pkl` file.

> **Options**

- `--size` controls the square output resolution and defaults to 960 pixels. It must be even for yuv420p encoding.
- `--fps`/`--frame-rate` controls frame timing and defaults to 30 fps.
- `--ball-color` and `--border-color` accept named colors or `#RRGGBB[AA]` values.
"""

import argparse
import pickle
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from rich import print

from _project_paths import OUTPUTS_PATH, RENDERED_VIDEOS_PATH
from bounce_music.rendering import Color, RenderConfig, parse_color, render_record
from bounce_music.utils.cli import ArgsValidationError, RichArgumentParser, ScriptArgs

if TYPE_CHECKING:
    from bounce_music.models.simulation import SimulationRecord


@dataclass(frozen=True, slots=True)
class Args(ScriptArgs):
    input_path: Path
    ball_color: Color
    border_color: Color
    size: int
    fps: int

    DESCRIPTION = "Render a simulation record to an MP4 with Pycairo and FFmpeg."

    @classmethod
    def add_arguments(cls, parser: RichArgumentParser) -> None:
        parser.add_argument(
            "-i",
            "--input",
            type=Path,
            default=None,
            help="Input Pickle path (default: latest outputs/**/bounce_history.pkl)",
        )
        parser.add_argument(
            "--ball-color",
            "--ball_color",
            default="BLUE",
            help="Ball color name or #RRGGBB[AA] (default: %(default)s)",
        )
        parser.add_argument(
            "--border-color",
            "--border_color",
            default="GREY",
            help="Boundary color name or #RRGGBB[AA] (default: %(default)s)",
        )
        parser.add_argument(
            "--size",
            type=int,
            default=960,
            help="Square video size in pixels (default: %(default)s)",
        )
        parser.add_argument(
            "--fps",
            "--frame-rate",
            "--frame_rate",
            type=int,
            default=30,
            help="Video frame rate (default: %(default)s)",
        )

    @classmethod
    def from_ns(cls, ns: argparse.Namespace) -> "Args":
        input_path = cls._find_latest_record() if ns.input is None else cast("Path", ns.input).expanduser().resolve()
        return cls(
            input_path=input_path,
            ball_color=cls._parse_color(cast("str", ns.ball_color), "--ball-color"),
            border_color=cls._parse_color(cast("str", ns.border_color), "--border-color"),
            size=cast("int", ns.size),
            fps=cast("int", ns.fps),
        )

    def __post_init__(self) -> None:
        if not self.input_path.is_file():
            raise ArgsValidationError(f"Simulation record does not exist: {self.input_path}")
        if self.size <= 0 or self.size % 2 != 0:
            raise ArgsValidationError("--size must be a positive even integer for yuv420p output")
        if self.fps <= 0:
            raise ArgsValidationError("--fps must be greater than zero")

    @classmethod
    def _find_latest_record(cls) -> Path:
        record_files = list(OUTPUTS_PATH.rglob("bounce_history.pkl"))
        if not record_files:
            raise ArgsValidationError(f"No bounce_history.pkl files found in {OUTPUTS_PATH}")
        return max(record_files, key=lambda path: path.stat().st_mtime).resolve()

    @classmethod
    def _parse_color(cls, value: str, option: str) -> Color:
        try:
            return parse_color(value)
        except ValueError as exc:
            raise ArgsValidationError(f"{option}: {exc}") from exc


def main() -> None:
    args = Args.parse()
    with args.input_path.open("rb") as file:
        record = cast("SimulationRecord", pickle.load(file))

    output_file = (
        RENDERED_VIDEOS_PATH
        / f"{Path(record.metadata.midi_file).stem}-{record.metadata.inst_idx}"
        / f"{args.size}p{args.fps}.mp4"
    )
    sidecar_file = output_file.with_suffix(".pkl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    result = render_record(
        record,
        output_file,
        RenderConfig(
            size=args.size,
            fps=args.fps,
            ball_color=args.ball_color,
            border_color=args.border_color,
            show_progress=True,
        ),
    )
    if args.input_path != sidecar_file.resolve():
        shutil.copy2(args.input_path, sidecar_file)

    print(
        f"[green]Rendered {result.frame_count} frames ({result.duration_seconds:.3f} s) to {result.output_path}[/green]"
    )


if __name__ == "__main__":
    main()
