import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_PATH = PROJECT_ROOT / "assets"

sys.path.append(PROJECT_ROOT.as_posix())
