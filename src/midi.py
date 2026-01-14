# pyright: standard
from pathlib import Path
from typing import List

import pretty_midi


class NoteRecord:
    def __init__(self, notes: List[List[float]]) -> None:
        self.notes = notes

    @classmethod
    def from_midi_file(cls, midi_path: Path) -> "NoteRecord":
        pm = pretty_midi.PrettyMIDI(midi_path)
        res: List[List[float]] = []

        for inst in pm.instruments:
            start_times = sorted(float(n.start) for n in inst.notes)
            merged_times = []

            for t in start_times:
                if t < 0.1:
                    continue
                if not merged_times or t - merged_times[-1] >= 0.01:
                    merged_times.append(t)

            res.append(merged_times)

        return cls(notes=res)
