from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
ASSETS_PATH = PROJECT_ROOT / "assets"


def get_default_sf2_file() -> Path:
    sf2_files = list((ASSETS_PATH / "sf2").glob("*.sf2"))
    if not sf2_files:
        raise FileNotFoundError("No .sf2 files found in the sf2 directory.")
    return sf2_files[0]
