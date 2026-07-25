from pathlib import Path


def get_default_sf2_file(sf2_directory: Path) -> Path:
    sf2_files = list(sf2_directory.glob("*.sf2"))
    if not sf2_files:
        raise FileNotFoundError(f"No .sf2 files found in {sf2_directory}")
    return sf2_files[0]
