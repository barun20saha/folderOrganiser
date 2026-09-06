import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

def get_app_dir() -> Path:
    """Return the application directory, respecting PyInstaller bundle location."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent.resolve()
    return Path(__file__).parent.resolve()


HISTORY_FILE = get_app_dir() / "organizer_history.json"


def load_history() -> List[Dict[str, Any]]:
    """Load history records from JSON file. Returns empty list if missing or invalid."""
    if not HISTORY_FILE.exists():
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_history(history: List[Dict[str, Any]]) -> None:
    """Save history records to JSON file."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
    except OSError as e:
        print(f"Error saving history file: {e}")


def add_history(original_path: Path, destination_path: Path, category: str) -> Dict[str, Any]:
    """Record a file organization operation."""
    history = load_history()

    record = {
        "id": uuid.uuid4().hex[:8],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "filename": original_path.name,
        "category": category,
        "source_folder": str(original_path.parent.resolve()),
        "original_path": str(original_path.resolve()),
        "destination_path": str(destination_path.resolve()),
        "status": "Moved",
        "undone": False
    }

    history.append(record)
    save_history(history)
    return record


def get_history() -> List[Dict[str, Any]]:
    """Return all history records."""
    return load_history()


def get_record_by_id(record_id: str) -> Optional[Dict[str, Any]]:
    """Find a record by its unique ID."""
    history = load_history()
    for record in history:
        if record.get("id") == record_id:
            return record
    return None


def get_last_active_record(folder_filter: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return the most recent record that has not been undone, optionally filtered by folder."""
    history = load_history()
    for record in reversed(history):
        if not record.get("undone", False):
            if folder_filter:
                rec_folder = Path(record.get("source_folder", "")).resolve()
                if rec_folder != Path(folder_filter).resolve():
                    continue
            return record
    return None


def mark_as_undone(record_id: str) -> bool:
    """Mark a history record as undone."""
    history = load_history()
    updated = False
    for record in history:
        if record.get("id") == record_id:
            record["undone"] = True
            record["status"] = "Undone"
            updated = True
            break

    if updated:
        save_history(history)
    return updated


def clear_history() -> None:
    """Clear all records from history."""
    save_history([])