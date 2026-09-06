import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

from config import (
    FILE_TYPES,
    DEFAULT_CATEGORY,
    ALL_CATEGORIES,
    TEMP_EXTENSIONS,
    get_current_target_folder,
)
from history import add_history


def get_category(extension: str) -> str:
    """Classify file extension into a category defined in config.py."""
    ext_lower = extension.lower()
    for category, extensions in FILE_TYPES.items():
        if ext_lower in extensions:
            return category
    return DEFAULT_CATEGORY


def get_safe_destination(dest_folder: Path, filename: str) -> Path:
    """
    Generate a safe destination path that avoids overwriting existing files.
    If 'report.pdf' exists, generates 'report (1).pdf', 'report (2).pdf', etc.
    Does NOT create the destination folder here - creation happens upon move.
    """
    target_path = dest_folder / filename
    if not target_path.exists():
        return target_path

    stem = target_path.stem
    suffix = target_path.suffix
    counter = 1

    while True:
        candidate_name = f"{stem} ({counter}){suffix}"
        candidate_path = dest_folder / candidate_name
        if not candidate_path.exists():
            return candidate_path
        counter += 1


def cleanup_empty_category_folders(target_folder: Path) -> int:
    """
    Check all recognized category folders inside target_folder.
    If any category folder is completely empty, delete it automatically.
    Returns the count of removed empty folders.
    """
    target_folder = Path(target_folder).resolve()
    if not target_folder.exists() or not target_folder.is_dir():
        return 0

    removed_count = 0
    # Inspect known category directories or any empty directory
    for item in list(target_folder.iterdir()):
        if item.is_dir() and item.name in ALL_CATEGORIES:
            try:
                # Check if folder is completely empty
                if not any(item.iterdir()):
                    item.rmdir()
                    removed_count += 1
                    print(f"Removed empty category folder: {item.name}")
            except OSError as e:
                print(f"Could not remove folder {item.name}: {e}")

    return removed_count


def organize_file(file_path: Path, target_folder: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Organize a single file into its categorized subfolder inside target_folder.
    
    Rules:
    - Never pre-creates category folders; folder is only created when a file is placed into it.
    - Path must exist and be a regular file.
    - File must reside directly in target_folder (non-recursive).
    - Temporary download files are skipped.
    - Files are never overwritten; naming collisions are safely incremented.
    - Successfully moved files are recorded in history.
    """
    try:
        file_path = Path(file_path).resolve()
        if target_folder is None:
            target_folder = get_current_target_folder()
        target_folder = Path(target_folder).resolve()

        # 1. Must exist and be a file
        if not file_path.exists() or not file_path.is_file():
            return None

        # 2. Must be directly inside target root (non-recursive)
        if file_path.parent != target_folder:
            return None

        # 3. Ignore temporary download files
        if file_path.suffix.lower() in TEMP_EXTENSIONS:
            return None

        # 4. Classify category and determine safe destination
        category = get_category(file_path.suffix)
        dest_folder = target_folder / category
        safe_destination = get_safe_destination(dest_folder, file_path.name)

        # 5. Create category folder ONLY now (because this file is available and moving)
        dest_folder.mkdir(parents=True, exist_ok=True)

        # 6. Move file safely
        shutil.move(str(file_path), str(safe_destination))

        # 7. Record operation in history
        history_record = add_history(
            original_path=file_path,
            destination_path=safe_destination,
            category=category
        )

        print(f"Moved: {file_path.name} -> {category}/{safe_destination.name}")
        return history_record

    except PermissionError:
        print(f"Permission denied for file: {file_path.name}")
        return None
    except FileNotFoundError:
        print(f"File not found: {file_path.name}")
        return None
    except OSError as e:
        print(f"OS error organizing {file_path.name}: {e}")
        return None


def organize_existing_files(target_folder: Optional[Path] = None) -> Dict[str, int]:
    """
    Scan target_folder and organize all existing top-level files.
    Cleans up any empty category folders afterward.
    Returns dict with count of organized files and removed empty folders.
    """
    if target_folder is None:
        target_folder = get_current_target_folder()
    target_folder = Path(target_folder).resolve()

    if not target_folder.exists():
        target_folder.mkdir(parents=True, exist_ok=True)
        return {"organized": 0, "cleaned_folders": 0}

    organized_count = 0
    # Iterate top-level files only
    for item in list(target_folder.iterdir()):
        if item.is_file() and item.suffix.lower() not in TEMP_EXTENSIONS:
            record = organize_file(item, target_folder)
            if record is not None:
                organized_count += 1

    # Prune any empty category folders that might have been left or emptied
    cleaned = cleanup_empty_category_folders(target_folder)

    return {"organized": organized_count, "cleaned_folders": cleaned}


if __name__ == "__main__":
    folder = get_current_target_folder()
    print(f"Organizing active folder: {folder}")
    result = organize_existing_files(folder)
    print(f"Result: {result['organized']} organized, {result['cleaned_folders']} empty folders removed.")