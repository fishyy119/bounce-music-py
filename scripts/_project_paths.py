"""Repository paths used by the scripts."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_PATH = PROJECT_ROOT / "assets"
OUTPUTS_PATH = PROJECT_ROOT / "outputs"
RENDERED_VIDEOS_PATH = PROJECT_ROOT / "rendered-videos"
FINAL_VIDEOS_PATH = PROJECT_ROOT / "final-videos"
MEDIA_PATH = PROJECT_ROOT / "media"
