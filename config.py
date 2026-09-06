import json
import os
from pathlib import Path
from typing import Dict, List, Optional

# --------------------------------------------------
# COMMON SYSTEM PRESETS
# --------------------------------------------------
PRESETS: Dict[str, Path] = {
    "Downloads": Path.home() / "Downloads",
    "Documents": Path.home() / "Documents",
    "Desktop": Path.home() / "Desktop",
}

SETTINGS_FILE = Path(__file__).parent / "settings.json"


def load_settings() -> Dict[str, str]:
    """Load persistent settings or return sensible defaults."""
    default_target = str(PRESETS["Downloads"])
    if not SETTINGS_FILE.exists():
        return {"target_folder": default_target}

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"target_folder": default_target}


def save_settings(settings: Dict[str, str]) -> None:
    """Save persistent settings."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except OSError as e:
        print(f"Error saving settings: {e}")


def get_current_target_folder() -> Path:
    """Return the currently configured target folder, defaulting to Downloads."""
    settings = load_settings()
    path_str = settings.get("target_folder")
    if path_str:
        folder = Path(path_str).resolve()
        if folder.exists() and folder.is_dir():
            return folder
    return PRESETS["Downloads"].resolve()


def set_current_target_folder(folder_path: Path) -> None:
    """Update and persist the active target folder."""
    settings = load_settings()
    settings["target_folder"] = str(Path(folder_path).resolve())
    save_settings(settings)


# --------------------------------------------------
# FILE CATEGORIES & EXTENSIONS
# --------------------------------------------------
FILE_TYPES: Dict[str, List[str]] = {
    "Documents": [
        ".pdf", ".doc", ".docx", ".txt", ".ppt",
        ".pptx", ".xls", ".xlsx", ".csv", ".rtf", ".odt"
    ],
    "Images": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp",
        ".webp", ".svg", ".ico", ".tiff", ".psd"
    ],
    "Videos": [
        ".mp4", ".mkv", ".avi", ".mov", ".wmv",
        ".flv", ".webm"
    ],
    "Audio": [
        ".mp3", ".wav", ".flac", ".aac", ".ogg",
        ".m4a", ".wma"
    ],
    "Archives": [
        ".zip", ".rar", ".7z", ".tar", ".gz",
        ".bz2", ".xz", ".iso"
    ],
    "Installers": [
        ".exe", ".msi", ".bat", ".cmd"
    ],
    "Code": [
        ".py", ".java", ".c", ".cpp", ".h", ".cs",
        ".html", ".css", ".js", ".ts", ".json", ".sql",
        ".xml", ".yaml", ".yml", ".sh"
    ],
    "E-Books": [
        ".epub", ".mobi", ".azw3"
    ]
}

DEFAULT_CATEGORY = "Others"

# Set of all known category folder names
ALL_CATEGORIES = set(FILE_TYPES.keys()) | {DEFAULT_CATEGORY}

# Temporary download extensions to ignore while file is in-flight
TEMP_EXTENSIONS = {
    ".crdownload",  # Chrome / Edge
    ".part",        # Firefox / Thunderbird
    ".tmp",         # General temporary files
    ".download",    # Safari / general
    ".partial"      # Download managers
}
