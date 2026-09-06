import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from history import get_record_by_id, get_last_active_record, mark_as_undone, get_history
from organizer import get_safe_destination, cleanup_empty_category_folders


def undo_entry(record_id: str) -> Dict[str, Any]:
    """
    Undo a specific file move operation by its unique record ID.
    
    Safety & Cleanliness rules:
    - Verifies entry exists and hasn't already been undone.
    - Verifies moved file exists at destination_path.
    - Restores file safely back to original source folder without overwriting existing files.
    - If the category folder becomes empty after moving this file out, automatically deletes the category folder.
    - Marks the entry as undone in history.
    """
    record = get_record_by_id(record_id)
    if not record:
        return {"success": False, "message": f"Operation ID '{record_id}' not found in history."}

    if record.get("undone", False):
        return {"success": False, "message": f"'{record['filename']}' has already been undone."}

    dest_file = Path(record["destination_path"]).resolve()
    if not dest_file.exists() or not dest_file.is_file():
        return {
            "success": False,
            "message": f"File no longer exists at '{dest_file}'."
        }

    # Determine original source folder
    source_folder = Path(record.get("source_folder", Path(record["original_path"]).parent)).resolve()
    source_folder.mkdir(parents=True, exist_ok=True)

    # Safe restore path back to source folder
    safe_restore_path = get_safe_destination(source_folder, record["filename"])
    category_folder = dest_file.parent

    try:
        shutil.move(str(dest_file), str(safe_restore_path))
        mark_as_undone(record_id)

        # Automatic cleanup: if category folder is now empty, delete it
        folder_deleted = False
        if category_folder.exists() and category_folder.is_dir():
            try:
                if not any(category_folder.iterdir()):
                    category_folder.rmdir()
                    folder_deleted = True
                    print(f"Automatically deleted empty category folder: {category_folder.name}")
            except OSError as e:
                print(f"Could not delete folder {category_folder.name}: {e}")

        # Also run cleanup on the source_folder in case of subfolders
        cleanup_empty_category_folders(source_folder)

        cleanup_msg = f" (Category folder '{category_folder.name}' was empty and removed)" if folder_deleted else ""
        return {
            "success": True,
            "message": f"Restored '{record['filename']}' back to {source_folder.name}.{cleanup_msg}",
            "restored_path": str(safe_restore_path)
        }

    except PermissionError:
        return {"success": False, "message": f"Permission denied restoring '{record['filename']}'."}
    except OSError as e:
        return {"success": False, "message": f"OS error restoring '{record['filename']}': {e}"}


def undo_last(folder_filter: Optional[str] = None) -> Dict[str, Any]:
    """Undo the most recent active file move operation."""
    last_record = get_last_active_record(folder_filter)
    if not last_record:
        return {"success": False, "message": "No active operations to undo."}
    return undo_entry(last_record["id"])


def undo_all(folder_filter: Optional[str] = None) -> Dict[str, Any]:
    """Undo all active file move operations."""
    history = get_history()
    restored_count = 0
    failed_count = 0

    for record in reversed(history):
        if not record.get("undone", False):
            if folder_filter:
                rec_folder = Path(record.get("source_folder", "")).resolve()
                if rec_folder != Path(folder_filter).resolve():
                    continue
            res = undo_entry(record["id"])
            if res.get("success"):
                restored_count += 1
            else:
                failed_count += 1

    return {
        "success": restored_count > 0,
        "message": f"Undone {restored_count} file(s). Failed: {failed_count}.",
        "restored_count": restored_count,
        "failed_count": failed_count
    }


if __name__ == "__main__":
    res = undo_last()
    print(res["message"])
