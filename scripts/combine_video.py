# pyright: standard
# ruff: noqa: RUF005
"""Combine rendered tracks with sample-aligned MIDI audio.

> **Behavior**

Read one or two track videos and their matching simulation Pickles from `rendered-videos/`, synthesize the selected
MIDI tracks with a SoundFont, align video and audio from the first collision, and write the result to `final-videos/`.

> **Common commands**

Combine two tracks with an explicit SoundFont:

```bash
python scripts/combine_video.py --music "example" --tracks 0 1 --soundfont assets/sf2/FluidR3_GM.sf2
```

The MIDI path is resolved as `assets/midi/<music>.mid`. Each selected track must have a common render profile.

> **Options**

- `--tracks` accepts one or two track indices and defaults to track 0.
- `--soundfont` defaults to the first `.sf2` file under `assets/sf2/`.
- The highest common `<size>p<fps>` profile is selected automatically and affects the output filename and timing.
"""

import argparse
import pickle
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import soundfile as sf
from rich import print

from _project_paths import ASSETS_PATH, FINAL_VIDEOS_PATH, RENDERED_VIDEOS_PATH
from bounce_music.midi import midi_tracks_to_wav
from bounce_music.models.simulation import SimulationRecord
from bounce_music.utils.cli import ArgsValidationError, RichArgumentParser, ScriptArgs

_PROFILE_PATTERN = re.compile(r"^(?P<size>\d+)p(?P<fps>\d+)$")


@dataclass(frozen=True, order=True, slots=True)
class RenderProfile:
    size: int
    fps: int

    @property
    def name(self) -> str:
        return f"{self.size}p{self.fps}"


@dataclass(frozen=True, slots=True)
class Args(ScriptArgs):
    midi_file: Path
    soundfont_path: Path
    tracks: tuple[int, ...]

    DESCRIPTION = "Combine rendered tracks with sample-aligned MIDI audio."

    @classmethod
    def add_arguments(cls, parser: RichArgumentParser) -> None:
        parser.add_argument(
            "-m",
            "--music",
            required=True,
            help="MIDI filename without its .mid suffix",
        )
        parser.add_argument(
            "-s",
            "--soundfont",
            type=Path,
            default=None,
            help="SoundFont path (default: first assets/sf2/*.sf2)",
        )
        parser.add_argument(
            "-t",
            "--tracks",
            type=int,
            nargs="+",
            default=[0],
            help="MIDI track indices (default: %(default)s)",
        )

    @classmethod
    def from_ns(cls, ns: argparse.Namespace) -> "Args":
        soundfont = cast("Path | None", ns.soundfont)
        return cls(
            midi_file=(ASSETS_PATH / "midi" / f"{cast('str', ns.music)}.mid").resolve(),
            soundfont_path=cls._find_default_soundfont() if soundfont is None else soundfont.expanduser().resolve(),
            tracks=tuple(cast("list[int]", ns.tracks)),
        )

    def __post_init__(self) -> None:
        if not self.midi_file.is_file():
            raise ArgsValidationError(f"MIDI file does not exist: {self.midi_file}")
        if not self.soundfont_path.is_file():
            raise ArgsValidationError(f"SoundFont does not exist: {self.soundfont_path}")
        if not 1 <= len(self.tracks) <= 2:
            raise ArgsValidationError("--tracks must contain one or two track indices")
        if any(track < 0 for track in self.tracks):
            raise ArgsValidationError("--tracks cannot contain negative indices")
        if len(set(self.tracks)) != len(self.tracks):
            raise ArgsValidationError("--tracks cannot contain duplicate indices")

    @classmethod
    def _find_default_soundfont(cls) -> Path:
        soundfont_files = sorted((ASSETS_PATH / "sf2").glob("*.sf2"))
        if not soundfont_files:
            raise ArgsValidationError(f"No .sf2 files found in {ASSETS_PATH / 'sf2'}")
        return soundfont_files[0].resolve()


def find_common_render_profile(midi_file: Path, tracks: list[int]) -> RenderProfile:
    common_profiles: set[RenderProfile] | None = None
    for track in tracks:
        video_root = RENDERED_VIDEOS_PATH / f"{midi_file.stem}-{track}"
        track_profiles: set[RenderProfile] = set()
        if video_root.is_dir():
            for video_file in video_root.glob("*.mp4"):
                match = _PROFILE_PATTERN.fullmatch(video_file.stem)
                if match is not None and video_file.with_suffix(".pkl").is_file():
                    track_profiles.add(
                        RenderProfile(
                            size=int(match.group("size")),
                            fps=int(match.group("fps")),
                        )
                    )
        common_profiles = track_profiles if common_profiles is None else common_profiles & track_profiles

    if not common_profiles:
        raise ValueError("No common video profile found across tracks.")

    profile = max(common_profiles)
    print(f"Highest common profile: {profile.name}")
    return profile


def load_record(path: Path) -> SimulationRecord:
    with path.open("rb") as file:
        return cast("SimulationRecord", pickle.load(file))


def main() -> None:
    args = Args.parse()
    profile = find_common_render_profile(args.midi_file, list(args.tracks))
    records: list[SimulationRecord] = []
    videos: list[Path] = []

    for track in args.tracks:
        video_root = RENDERED_VIDEOS_PATH / f"{args.midi_file.stem}-{track}"
        videos.append(video_root / f"{profile.name}.mp4")
        records.append(load_record(video_root / f"{profile.name}.pkl"))

    if any(not record.collisions for record in records):
        raise ValueError("Every simulation record must contain at least one collision.")

    wav_path = midi_tracks_to_wav(
        args.midi_file,
        list(args.tracks),
        wav_output_path=ASSETS_PATH / "wav",
        soundfont_path=args.soundfont_path,
    )
    final_video_path = (
        FINAL_VIDEOS_PATH / f"{args.midi_file.stem}-{'-'.join(str(track) for track in args.tracks)}-{profile.name}.mp4"
    )
    final_video_path.parent.mkdir(parents=True, exist_ok=True)

    first_collisions = [record.collisions[0].time for record in records]
    synchronization_time = max(first_collisions)
    sample_rate = sf.info(wav_path).samplerate
    video_delay_frames = [round((synchronization_time - collision) * profile.fps) for collision in first_collisions]
    audio_filter = f"adelay={round(synchronization_time * sample_rate)}S:all=1"

    match len(videos):
        case 1:
            ffmpeg_command = (
                ["ffmpeg"]
                + ["-i", videos[0].as_posix()]
                + ["-i", wav_path.as_posix()]
                + ["-filter_complex", f"[1:a]{audio_filter}[aout]"]
                + ["-map", "0:v", "-map", "[aout]"]
                + ["-c:v", "copy", "-c:a", "aac"]
                + [final_video_path.as_posix(), "-y"]
            )
        case 2:
            filter_complex = (  # 没有逗号，隐式拼接
                f"[0:v]tpad=start={video_delay_frames[0]}:start_mode=clone[v0];"
                f"[1:v]tpad=start={video_delay_frames[1]}:start_mode=clone[v1];"
                f"[v0][v1]hstack=inputs=2[vout];"
                f"[2:a]{audio_filter}[aout]"
            )
            ffmpeg_command = (
                ["ffmpeg"]
                + ["-i", videos[0].as_posix()]
                + ["-i", videos[1].as_posix()]
                + ["-i", wav_path.as_posix()]
                + ["-filter_complex", filter_complex]
                + ["-map", "[vout]", "-map", "[aout]"]
                + ["-c:v", "libx264", "-c:a", "aac"]
                + ["-pix_fmt", "yuv420p"]
                + [final_video_path.as_posix(), "-y"]
            )
        case _:
            raise NotImplementedError(f"Combining {len(videos)} tracks is not implemented yet.")

    print(f"Running command: '{' '.join(ffmpeg_command)}'")
    subprocess.run(ffmpeg_command, check=True)


if __name__ == "__main__":
    main()
