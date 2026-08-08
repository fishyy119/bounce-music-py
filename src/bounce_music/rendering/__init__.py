"""Backend-neutral public API for video rendering."""

from ._renderer import Color, RenderConfig, RenderError, RenderResult, parse_color, render_record

__all__ = [
    "Color",
    "RenderConfig",
    "RenderError",
    "RenderResult",
    "parse_color",
    "render_record",
]
