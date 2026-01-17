# pyright: standard
import argparse
import pickle
import subprocess
from pathlib import Path
from typing import List, Set, Tuple

import _pre_init
from rich import print

from src.midi import midi_tracks_to_wav
from src.models.manim import SimulationRecord

MANIM_PATH = _pre_init.PROJECT_ROOT / "manim-videos"
FINAL_PATH = _pre_init.PROJECT_ROOT / "final-videos"


def parse_manim_folder(midi_file: Path, tracks: List[int]) -> str:
    midi_name = midi_file.stem

    common_quality: Set[Tuple[int, int]] | None = None
    for t in tracks:
        video_root = MANIM_PATH / f"{midi_name}-{t}"
        track_quality = set()
        if video_root.exists() and video_root.is_dir():
            for video_file in video_root.glob("*.mp4"):
                parts = video_file.stem.split("p")
                if len(parts) == 2 and parts[1].isdigit():
                    quality = (int(parts[0]), int(parts[1]))  # (size, fps)
                    track_quality.add(quality)

        if common_quality is None:
            common_quality = track_quality
        else:
            common_quality &= track_quality

    if not common_quality:
        raise ValueError("No common video quality found across tracks.")

    highest_quality = max(common_quality)
    print(f"Highest common quality: {highest_quality}")

    return f"{highest_quality[0]}p{highest_quality[1]}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--music", type=str, required=True, help="Midi filename (without suffix)")
    parser.add_argument(
        "-t", "--tracks", type=int, nargs="+", default=[0], help="List of MIDI tracks to use (default: [0])"
    )
    args = parser.parse_args()

    midi_file = _pre_init.ASSETS_PATH / "midi" / (args.music + ".mid")
    video_quality = parse_manim_folder(midi_file, args.tracks)
    records: List[SimulationRecord] = []
    videos: List[Path] = []

    for t in args.tracks:
        pkl_file = MANIM_PATH / f"{midi_file.stem}-{t}/{video_quality}.pkl"
        videos.append(MANIM_PATH / f"{midi_file.stem}-{t}/{video_quality}.mp4")
        with open(pkl_file, "rb") as f:
            record: SimulationRecord = pickle.load(f)
            records.append(record)

    wav_path = midi_tracks_to_wav(midi_file, args.tracks, wav_output_path=_pre_init.ASSETS_PATH / "wav")

    record = records[0]
    print(record.collisions[0].time)
    offset_ms = int(record.collisions[0].time * 1000)

    ffmpeg_cmd = (
        ["ffmpeg"]
        + ["-i", videos[0].as_posix()]
        + ["-i", wav_path.as_posix()]
        + ["-filter_complex", f"[1:a]adelay={offset_ms}[a1]"]
        + ["-map", "0:v", "-map", "[a1]"]
        + ["-c:v", "copy", "-c:a", "aac"]
        + ["-strict", "experimental"]
        + [
            (FINAL_PATH / f"{midi_file.stem}-{'-'.join(str(t) for t in args.tracks)}-{video_quality}.mp4").as_posix(),
            "-y",
        ]
    )

    print(f"Running command: '{" ".join(ffmpeg_cmd)}'")
    subprocess.run(ffmpeg_cmd)
