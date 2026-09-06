import time
from pathlib import Path
from typing import Optional, Callable, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config import TEMP_EXTENSIONS, get_current_target_folder
from organizer import organize_file, cleanup_empty_category_folders


def is_file_stable(file_path: Path, checks: int = 3, delay: float = 0.8) -> bool:
    """
    Verify if a file has finished downloading and is stable.
    Checks if size is non-zero, constant across intervals, and readable.
    """
    if not file_path.exists() or not file_path.is_file():
        return False

    if file_path.suffix.lower() in TEMP_EXTENSIONS:
        return False

    previous_size = -1

    for _ in range(checks):
        if not file_path.exists():
            return False

        try:
            current_size = file_path.stat().st_size
            with open(file_path, "a+"):
                pass

            if current_size == previous_size and current_size > 0:
                return True

            previous_size = current_size
        except (PermissionError, OSError):
            pass

        time.sleep(delay)

    try:
        if file_path.exists() and file_path.stat().st_size > 0:
            with open(file_path, "a+"):
                return True
    except (PermissionError, OSError):
        pass

    return False


class DynamicFolderHandler(FileSystemEventHandler):
    """Event handler for monitoring files in the active target folder."""

    def __init__(self, watcher_manager: "DownloadWatcher"):
        super().__init__()
        self.watcher = watcher_manager

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle_file(Path(event.src_path))

    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle_file(Path(event.src_path))

    def on_deleted(self, event):
        """When files or folders are deleted, auto-prune empty category folders."""
        if self.watcher.target_folder and self.watcher.target_folder.exists():
            cleaned = cleanup_empty_category_folders(self.watcher.target_folder)
            if cleaned > 0 and self.watcher.callback:
                self.watcher.callback("folder_cleaned", cleaned)

    def _handle_file(self, file_path: Path):
        try:
            file_path = file_path.resolve()
            target_folder = self.watcher.target_folder.resolve()

            # Non-recursive: only organize files in the root of target_folder
            if file_path.parent != target_folder:
                return

            if file_path.suffix.lower() in TEMP_EXTENSIONS:
                return

            if is_file_stable(file_path):
                record = organize_file(file_path, target_folder)
                if record and self.watcher.callback:
                    self.watcher.callback("file_organized", record)
        except Exception as e:
            print(f"Error handling watcher event for {file_path}: {e}")


class DownloadWatcher:
    """Manager for the watchdog observer with dynamic target folder."""

    def __init__(
        self,
        target_folder: Optional[Path] = None,
        callback: Optional[Callable[[str, Any], None]] = None
    ):
        self.target_folder = (target_folder or get_current_target_folder()).resolve()
        self.callback = callback
        self.observer: Optional[Observer] = None
        self.handler = DynamicFolderHandler(self)
        self.running = False

    def set_target_folder(self, new_folder: Path) -> None:
        """Switch the monitored folder dynamically."""
        new_folder = Path(new_folder).resolve()
        if new_folder == self.target_folder:
            return

        was_running = self.running
        if was_running:
            self.stop()

        self.target_folder = new_folder

        if was_running:
            self.start()

    def start(self) -> bool:
        """Start monitoring target_folder."""
        if self.running:
            return True

        self.target_folder.mkdir(parents=True, exist_ok=True)
        self.observer = Observer()
        # Watch recursively so that deleted events inside subfolders also trigger cleanup
        self.observer.schedule(
            self.handler,
            str(self.target_folder),
            recursive=True
        )
        self.observer.start()
        self.running = True
        print(f"Watcher started on: {self.target_folder}")
        return True

    def stop(self) -> bool:
        """Stop the observer."""
        if not self.running or not self.observer:
            return False

        self.observer.stop()
        self.observer.join()
        self.running = False
        self.observer = None
        print("Watcher stopped.")
        return True

    def is_running(self) -> bool:
        return self.running
