# 测试pygame和pymunk的使用流程
# 结论：弃用pymunk，手动实现定制化物理引擎

import pygame
import pymunk
import math
import pymunk.pygame_util

# 初始化
pygame.init()
screen = pygame.display.set_mode((600, 600))
pygame.display.set_caption("Pymunk + Pygame Demo")
clock = pygame.time.Clock()

# 物理空间
space = pymunk.Space()
space.gravity = (0, 900)

# 地板（圆形容器可改造为多边形边界或圆形检测）
# static_lines = [pymunk.Segment(space.static_body, (50, 550), (550, 550), 5)]
# for line in static_lines:
#     line.elasticity = 1  # * 根据源码：两个物体的系数相乘为速度衰减系数
# space.add(*static_lines)


# 圆形容器参数
width, height = 600, 600
container_radius = 250
container_center = (width // 2, height // 2)
segments = 120  # 越多越圆

# 创建圆形容器边界（用许多小segment构成）
for i in range(segments):
    angle1 = 2 * math.pi * i / segments
    angle2 = 2 * math.pi * (i + 1) / segments
    p1 = (
        container_center[0] + container_radius * math.cos(angle1),
        container_center[1] + container_radius * math.sin(angle1),
    )
    p2 = (
        container_center[0] + container_radius * math.cos(angle2),
        container_center[1] + container_radius * math.sin(angle2),
    )
    segment = pymunk.Segment(space.static_body, p1, p2, 2)
    segment.elasticity = 1.0  # 恢复系数
    # segment.friction = 0.5
    space.add(segment)


# 小球
mass = 1
radius = 20
moment = pymunk.moment_for_circle(mass, 0, radius)
body = pymunk.Body(mass, moment)
body.position = (350, 200)
shape = pymunk.Circle(body, radius)
shape.elasticity = 1
space.add(body, shape)

# 可视化
draw_options = pymunk.pygame_util.DrawOptions(screen)

running = True
while running:
    screen.fill((255, 255, 255))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    space.step(1 / 60.0)
    space.debug_draw(draw_options)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
