# pyright: standard
import copy
from pathlib import Path
from typing import List

import numpy as np
import pretty_midi
import soundfile as sf
from rich import print

from .utils.usable_class import ASSETS_PATH, get_default_sf2_file


class NoteRecord:
    def __init__(self, midi_path: Path) -> None:
        self.pm = pretty_midi.PrettyMIDI(midi_path)
        self.notes = self._parse_notes()
        self.path = midi_path
        self.duration: float = self.pm.get_end_time()

    def _parse_notes(self) -> List[List[float]]:
        res: List[List[float]] = []

        for inst in self.pm.instruments:
            start_times = sorted(float(n.start) for n in inst.notes)
            merged_times = []

            for t in start_times:
                if t < 0.1:
                    continue
                if not merged_times or t - merged_times[-1] >= 0.01:
                    merged_times.append(t)

            res.append(merged_times)

        return res


def midi_tracks_to_wav(
    midi_path: Path,
    track_indices: List[int],
    wav_output_path: Path,
    sr: int = 44100,
    soundfont_path: Path | None = None,
) -> Path:
    """
    从 MIDI 文件提取指定轨道，生成 WAV 文件。

    Args:
        midi_path (Path): 输入 MIDI 文件路径
        track_indices (List[int]): 希望保留的轨道索引列表
        wav_output_path (Path): 输出 WAV 文件路径
        fs (int): 采样率，默认 44100
        soundfont_path (Path | None): 可选 SoundFont 文件路径，如果 None 使用默认
    """
    soundfont_path = get_default_sf2_file() if soundfont_path is None else soundfont_path
    wav_output_path = wav_output_path / (midi_path.stem + "-" + "-".join(str(i) for i in track_indices) + ".wav")
    wav_output_path.parent.mkdir(parents=True, exist_ok=True)
    if wav_output_path.exists():
        return wav_output_path

    # 读取 MIDI
    midi_data = pretty_midi.PrettyMIDI(midi_path)

    # 创建新的 MIDI 对象，只保留指定轨道
    new_midi = pretty_midi.PrettyMIDI()
    for idx in track_indices:
        if 0 <= idx < len(midi_data.instruments):
            # 深拷贝避免原对象被修改
            new_midi.instruments.append(copy.deepcopy(midi_data.instruments[idx]))
        else:
            raise IndexError(f"轨道索引 {idx} 超出范围，共 {len(midi_data.instruments)} 条轨道")

    audio = new_midi.fluidsynth(sf2_path=soundfont_path.as_posix(), fs=sr)

    # 确保音频是 float32
    audio = np.float32(audio)

    # 保存为 WAV
    sf.write(wav_output_path, audio, sr)

    print(f"WAV 文件已生成: {wav_output_path}")
    return wav_output_path


if __name__ == "__main__":
    note_record = NoteRecord(ASSETS_PATH / "midi/春日影-My GO_爱给网_aigei_com.mid")
    print(note_record.notes[1])
