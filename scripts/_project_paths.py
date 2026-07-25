"""Repository paths used by the scripts.

This module deliberately does not alter interpreter import paths. The installed
``bounce_music`` package remains independent of the checkout location.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_PATH = PROJECT_ROOT / "assets"
OUTPUTS_PATH = PROJECT_ROOT / "outputs"
MANIM_VIDEOS_PATH = PROJECT_ROOT / "manim-videos"
FINAL_VIDEOS_PATH = PROJECT_ROOT / "final-videos"
MEDIA_PATH = PROJECT_ROOT / "media"
