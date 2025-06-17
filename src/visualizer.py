import pygame
from body import Ball
from boundary import CircleBoundary
from simulator import Simulator
from utils import Vec2, CoordinateTransformer, Metronome
from typing import Tuple, TypeAlias

Color: TypeAlias = Tuple[int, int, int]  # RGB颜色类型

import mido
import pygame.midi
import time


class MidiNotePlayer:
    def __init__(self, midi_path: str):
        self.midi = mido.MidiFile(midi_path)
        self.events = self._collect_events()
        self.current_index = 0

        pygame.midi.init()
        self.midi_out = pygame.midi.Output(0)  # 默认设备

        self.tempo = 500000  # 默认 120 BPM
        for msg in self.midi:  # 查找 tempo
            if msg.type == "set_tempo":
                self.tempo = msg.tempo
                break

    def _collect_events(self):
        events = []
        abs_time = 0.0
        ticks_per_beat = self.midi.ticks_per_beat

        for msg in self.midi:
            abs_time += mido.tick2second(msg.time, ticks_per_beat, self.tempo)
            if msg.type in ["note_on", "note_off"]:
                events.append((abs_time, msg))
        return events

    def step(self) -> float | None:
        """播放当前时间点所有音符，并返回到下一音符的时间间隔"""
        if self.current_index >= len(self.events):
            return None  # 播放结束

        # 当前时间点
        current_time = self.events[self.current_index][0]

        # 收集所有与当前时间相同的 note_on/note_off
        batch = []
        while self.current_index < len(self.events):
            event_time, msg = self.events[self.current_index]
            if abs(event_time - current_time) < 1e-6:
                batch.append(msg)
                self.current_index += 1
            else:
                break

        # 播放所有音符
        for msg in batch:
            if msg.type == "note_on":
                self.midi_out.note_on(msg.note, msg.velocity, msg.channel)
            elif msg.type == "note_off":
                self.midi_out.note_off(msg.note, msg.velocity, msg.channel)

        # 计算下一事件的时间差
        if self.current_index < len(self.events):
            next_time = self.events[self.current_index][0]
            return next_time - current_time
        else:
            return None

    def close(self):
        self.midi_out.close()
        pygame.midi.quit()


class Visualizer:
    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        bg_color: Color = (255, 255, 255),
        ppm: float = 3.0,
    ):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("可视化")
        self.clock = pygame.time.Clock()
        self.bg_color = bg_color
        self.transformer = CoordinateTransformer(
            screen_size=(width, height),
            ppm=ppm,
        )

        # 圆形容器参数，居中显示
        self.container_center = Vec2(width // 2, height // 2)
        self.container_radius = 200
        self.container_color = (0, 0, 0)  # 黑色

    def draw_container(self, container: CircleBoundary):
        t = self.transformer.to_screen
        pygame.draw.circle(
            self.screen,
            self.container_color,
            t(container.center).as_tuple,
            t(container.radius),
            width=2,
        )

    def draw_ball(self, ball: Ball, color: Color = (255, 0, 0)):
        t = self.transformer.to_screen
        pygame.draw.circle(
            self.screen,
            color,
            t(ball.pos).as_tuple,
            t(ball.radius),
        )

    def clear(self):
        self.screen.fill(self.bg_color)

    def tick(self, fps: float = 60):
        pygame.display.flip()
        self.clock.tick(fps)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True


if __name__ == "__main__":
    vis = Visualizer(ppm=8)
    ball = Ball(pos=Vec2(-5, 0), vel=Vec2(0, 0), acc=Vec2(0, -9.81), radius=0.5)
    boundary = CircleBoundary(center=Vec2(0, 0), radius=15, restitution=1.0)
    simulator = Simulator(ball, boundary)
    metronome = Metronome()

    running = True
    while running:
        dt = vis.clock.get_time() / 1000  # 秒
        if simulator.step(dt):
            metronome(pygame.time.get_ticks())
        running = vis.handle_events()
        vis.clear()
        vis.draw_container(boundary)
        vis.draw_ball(ball)  # 居中小球
        vis.tick(120)
