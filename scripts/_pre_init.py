import sys
from pathlib import Path

sys.path.append(Path(__file__).parents[1].as_posix())

PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_PATH = PROJECT_ROOT / "assets"
