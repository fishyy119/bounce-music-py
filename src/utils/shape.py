# pyright: standard
import numpy as np
from manim import VMobject
from scipy.ndimage import binary_dilation
from skimage import measure

from .usable_class import Vec2


def ellipse_boundary_to_manim(Q: np.ndarray, center: Vec2, ball_r: float, grid_res: int = 400, **kwargs) -> VMobject:
    """
    将二次型椭圆均匀膨胀 ball_r，返回 Manim VMobject

    参数:
        Q: 2x2 二次型矩阵，定义椭圆 x^T Q x = 1
        center: Vec2, 椭圆中心
        ball_r: float, 膨胀半径（球半径）
        grid_res: int, 网格分辨率，越大越平滑

    返回:
        VMobject: 可直接渲染的 Manim 曲线
    """
    eigvals = np.linalg.eigvalsh(Q)
    a = 1.0 / np.sqrt(eigvals[0])
    b = 1.0 / np.sqrt(eigvals[1])

    if np.isclose(a, b, rtol=1e-6):
        from manim import Circle

        return Circle(radius=a + ball_r, **kwargs).move_to(np.array([center.x, center.y, 0.0]))

    margin = ball_r * 1.5
    xmin, xmax = -a - margin, a + margin
    ymin, ymax = -b - margin, b + margin

    xs = np.linspace(xmin, xmax, grid_res)
    ys = np.linspace(ymin, ymax, grid_res)
    X, Y = np.meshgrid(xs, ys)

    P = np.stack([X - center.x, Y - center.y], axis=-1)
    f = P[..., 0] * (Q[0, 0] * P[..., 0] + Q[0, 1] * P[..., 1]) + P[..., 1] * (
        Q[1, 0] * P[..., 0] + Q[1, 1] * P[..., 1]
    )
    mask = f <= 1.0

    # 半径对应的像素数
    dx = xs[1] - xs[0]
    r_px = max(1, int(np.ceil(ball_r / dx)))

    # 使用圆形结构元素膨胀
    y, x = np.ogrid[-r_px : r_px + 1, -r_px : r_px + 1]
    selem = x**2 + y**2 <= r_px**2
    dilated_mask = binary_dilation(mask, structure=selem)

    contours = measure.find_contours(dilated_mask.astype(float), 0.5)
    if not contours:
        raise RuntimeError("未找到膨胀轮廓")
    # 取最长的轮廓
    contour = max(contours, key=len)

    pts = []
    for row, col in contour:
        x_world = xs[int(col)]
        y_world = ys[int(row)]
        pts.append([x_world, y_world, 0.0])
    pts.append(pts[0])  # 封闭曲线

    vm = VMobject(**kwargs)
    vm.set_points_smoothly(np.array(pts))
    return vm
