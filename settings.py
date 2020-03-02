import os
from pathlib import Path

ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

LOGGER_NAME = "chihiro"
LOG_DIR = ROOT_DIR / "logs"
MAX_WORKERS = 6  # Set this high and your PC dies

DATA_PATH = ROOT_DIR / "data"
DB_PATH = DATA_PATH / "db"
IMAGE_PATH = DATA_PATH / "img"
IMAGE_PATH32 = DATA_PATH / "img32"
IMAGE_PATH64 = DATA_PATH / "img64"
ZIP_PATH = ROOT_DIR / "img.zip"
MUSICSCORES_PATH = DATA_PATH / "musicscores"
CACHEDB_PATH = DB_PATH / "chihiro.db"
MANIFEST_PATH = DB_PATH / "manifest.db"
MASTERDB_PATH = DB_PATH / "master.db"

PROFILE_PATH = DATA_PATH / "profiles"

STATIC_PATH = ROOT_DIR / "src" / "static"
TOOL_EXE = STATIC_PATH / "tool.exe"
TEMP_PATH = STATIC_PATH / "temppp"

DIFFICULTY_NAMES_PATH = STATIC_PATH / "difficulty_names.json"

INDEX_PATH = DATA_PATH / "index"
