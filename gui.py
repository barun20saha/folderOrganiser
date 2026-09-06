import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional, List, Dict, Any

from config import (
    PRESETS,
    get_current_target_folder,
    set_current_target_folder,
)
from organizer import (
    organize_existing_files,
    cleanup_empty_category_folders,
)
from watcher import DownloadWatcher
from history import get_history, clear_history
from undo import undo_entry, undo_all


class MinimalistOrganizerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("File Organizer")
        self.root.geometry("880x620")
        self.root.minsize(780, 520)

        # Set window background
        self.bg_color = "#f8fafc"
        self.card_bg = "#ffffff"
        self.border_color = "#e2e8f0"
        self.text_primary = "#0f172a"
        self.text_muted = "#64748b"
        self.accent_color = "#2563eb"
        self.accent_hover = "#1d4ed8"
        self.danger_color = "#dc2626"
        self.success_color = "#16a34a"

        self.root.configure(bg=self.bg_color)

        # State
        self.current_folder = get_current_target_folder()
        self.watcher = DownloadWatcher(
            target_folder=self.current_folder,
            callback=self._on_watcher_event
        )
        self.search_var = tk.StringVar()
        self.path_var = tk.StringVar(value=str(self.current_folder))
        self.status_var = tk.StringVar(value="Ready")

        self._configure_styles()
        self._build_ui()
        self.refresh_history()

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        # Base Frame
        style.configure("App.TFrame", background=self.bg_color)
        style.configure("Card.TFrame", background=self.card_bg, relief="flat")

        # Labels
        style.configure("Title.TLabel", background=self.bg_color, foreground=self.text_primary, font=("Segoe UI", 15, "bold"))
        style.configure("Subtitle.TLabel", background=self.bg_color, foreground=self.text_muted, font=("Segoe UI", 9))
        style.configure("Section.TLabel", background=self.card_bg, foreground=self.text_primary, font=("Segoe UI", 10, "bold"))
        style.configure("Muted.TLabel", background=self.card_bg, foreground=self.text_muted, font=("Segoe UI", 9))
        style.configure("Card.TLabel", background=self.card_bg, foreground=self.text_primary, font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=self.bg_color, foreground=self.text_muted, font=("Segoe UI", 9))

        # Buttons
        style.configure(
            "Primary.TButton",
            background=self.accent_color,
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
            padding=(12, 6),
            focuscolor=self.accent_color
        )
        style.map("Primary.TButton", background=[("active", self.accent_hover), ("pressed", "#1e40af")])

        style.configure(
            "Secondary.TButton",
            background="#f1f5f9",
            foreground=self.text_primary,
            font=("Segoe UI", 9),
            borderwidth=1,
            relief="solid",
            padding=(10, 5)
        )
        style.map("Secondary.TButton", background=[("active", "#e2e8f0"), ("pressed", "#cbd5e1")])

        style.configure(
            "Chip.TButton",
            background="#ffffff",
            foreground=self.text_primary,
            font=("Segoe UI", 8),
            borderwidth=1,
            relief="solid",
            padding=(8, 3)
        )
        style.map("Chip.TButton", background=[("active", "#f1f5f9"), ("pressed", "#e2e8f0")])

        style.configure(
            "Danger.TButton",
            background="#fee2e2",
            foreground=self.danger_color,
            font=("Segoe UI", 9),
            borderwidth=1,
            relief="solid",
            padding=(10, 5)
        )
        style.map("Danger.TButton", background=[("active", "#fecaca"), ("pressed", "#fca5a5")])

        # Entry
        style.configure("Card.TEntry", fieldbackground="#ffffff", foreground=self.text_primary)

        # Treeview styling
        style.configure(
            "History.Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground=self.text_primary,
            font=("Segoe UI", 9),
            rowheight=26,
            borderwidth=0
        )
        style.configure(
            "History.Treeview.Heading",
            background="#f8fafc",
            foreground=self.text_muted,
            font=("Segoe UI", 8, "bold"),
            borderwidth=0,
            relief="flat",
            padding=5
        )
        style.map("History.Treeview", background=[("selected", "#e0e7ff")], foreground=[("selected", "#1e1b4b")])

    def _build_ui(self):
        container = ttk.Frame(self.root, style="App.TFrame", padding="16 12 16 12")
        container.pack(fill=tk.BOTH, expand=True)

        # ---------------------------------------------------------------------
        # TOP HEADER
        # ---------------------------------------------------------------------
        header = ttk.Frame(container, style="App.TFrame")
        header.pack(fill=tk.X, pady=(0, 10))

        title_col = ttk.Frame(header, style="App.TFrame")
        title_col.pack(side=tk.LEFT)

        ttk.Label(title_col, text="File Organizer", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            title_col,
            text="Organize any folder with smart empty folder deletion and reversible history",
            style="Subtitle.TLabel"
        ).pack(anchor=tk.W)

        # Watcher Badge
        self.watch_badge = tk.Label(
            header,
            text="● Watcher Off",
            font=("Segoe UI", 8, "bold"),
            bg="#f1f5f9",
            fg="#64748b",
            padx=10,
            pady=4,
            relief="flat",
            bd=0
        )
        self.watch_badge.pack(side=tk.RIGHT, pady=4)

        # ---------------------------------------------------------------------
        # FOLDER SELECTOR CARD
        # ---------------------------------------------------------------------
        folder_card = tk.Frame(container, bg=self.card_bg, bd=1, relief="solid", highlightbackground=self.border_color)
        folder_card.pack(fill=tk.X, pady=(0, 10), ipady=4, ipadx=4)

        folder_inner = ttk.Frame(folder_card, style="Card.TFrame", padding="10")
        folder_inner.pack(fill=tk.X)

        # Row 1: Label and Presets
        top_row = ttk.Frame(folder_inner, style="Card.TFrame")
        top_row.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(top_row, text="Target Folder:", style="Section.TLabel").pack(side=tk.LEFT)

        preset_box = ttk.Frame(top_row, style="Card.TFrame")
        preset_box.pack(side=tk.RIGHT)

        ttk.Label(preset_box, text="Presets:", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        for name, path in PRESETS.items():
            btn = ttk.Button(
                preset_box,
                text=name,
                style="Chip.TButton",
                command=lambda p=path: self.set_folder(p)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Row 2: Entry and Browse Button
        path_row = ttk.Frame(folder_inner, style="Card.TFrame")
        path_row.pack(fill=tk.X)

        path_entry = ttk.Entry(path_row, textvariable=self.path_var, font=("Segoe UI", 9))
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=3)
        path_entry.bind("<Return>", lambda e: self.on_path_entered())

        ttk.Button(
            path_row,
            text="Set",
            style="Secondary.TButton",
            command=self.on_path_entered
        ).pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(
            path_row,
            text="Browse...",
            style="Secondary.TButton",
            command=self.browse_folder
        ).pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(
            path_row,
            text="Open Folder",
            style="Secondary.TButton",
            command=self.open_current_folder
        ).pack(side=tk.LEFT)

        # ---------------------------------------------------------------------
        # CONTROLS / ACTION BAR
        # ---------------------------------------------------------------------
        action_bar = ttk.Frame(container, style="App.TFrame")
        action_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(
            action_bar,
            text="⚡ Organize Now",
            style="Primary.TButton",
            command=self.organize_now
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.watch_toggle_btn = ttk.Button(
            action_bar,
            text="Start Auto-Watch",
            style="Secondary.TButton",
            command=self.toggle_watch
        )
        self.watch_toggle_btn.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(
            action_bar,
            text="🧹 Clean Empty Folders",
            style="Secondary.TButton",
            command=self.clean_empty_folders
        ).pack(side=tk.LEFT, padx=(0, 6))

        # Right-side stats
        self.stats_label = ttk.Label(
            action_bar,
            text="0 operations recorded",
            style="Status.TLabel"
        )
        self.stats_label.pack(side=tk.RIGHT, pady=4)

        # ---------------------------------------------------------------------
        # HISTORY CARD (MAIN VIEW)
        # ---------------------------------------------------------------------
        history_card = tk.Frame(container, bg=self.card_bg, bd=1, relief="solid", highlightbackground=self.border_color)
        history_card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        h_inner = ttk.Frame(history_card, style="Card.TFrame", padding="10")
        h_inner.pack(fill=tk.BOTH, expand=True)

        # History Header Row
        h_header = ttk.Frame(h_inner, style="Card.TFrame")
        h_header.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(h_header, text="Organization History", style="Section.TLabel").pack(side=tk.LEFT)

        # Search box
        search_box = ttk.Frame(h_header, style="Card.TFrame")
        search_box.pack(side=tk.RIGHT)

        ttk.Label(search_box, text="Filter:", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        search_entry = ttk.Entry(search_box, textvariable=self.search_var, width=22, font=("Segoe UI", 9))
        search_entry.pack(side=tk.LEFT)
        self.search_var.trace_add("write", lambda *args: self.filter_history())

        # Table frame
        table_frame = ttk.Frame(h_inner, style="Card.TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "time", "filename", "category", "destination", "status")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="History.Treeview",
            selectmode="browse"
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("time", text="Timestamp")
        self.tree.heading("filename", text="File Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("destination", text="Moved To")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=70, anchor=tk.CENTER)
        self.tree.column("time", width=135, anchor=tk.W)
        self.tree.column("filename", width=220, anchor=tk.W)
        self.tree.column("category", width=100, anchor=tk.CENTER)
        self.tree.column("destination", width=240, anchor=tk.W)
        self.tree.column("status", width=90, anchor=tk.CENTER)

        # Scrollbars
        y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=y_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind events
        self.tree.bind("<Double-1>", lambda e: self.undo_selected_file())
        self.tree.bind("<Button-3>", self._show_context_menu)

        # Context Menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="↩ Undo This File", command=self.undo_selected_file)
        self.context_menu.add_command(label="📂 Open Destination Folder", command=self.open_selected_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Copy File Name", command=self.copy_selected_filename)

        # History Action Bottom Row
        h_actions = ttk.Frame(h_inner, style="Card.TFrame")
        h_actions.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(
            h_actions,
            text="↩ Undo Selected File",
            style="Secondary.TButton",
            command=self.undo_selected_file
        ).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(
            h_actions,
            text="↩ Undo All",
            style="Secondary.TButton",
            command=self.undo_all_files
        ).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(
            h_actions,
            text="Clear History",
            style="Secondary.TButton",
            command=self.clear_history_records
        ).pack(side=tk.LEFT)

        ttk.Button(
            h_actions,
            text="Refresh",
            style="Secondary.TButton",
            command=self.refresh_history
        ).pack(side=tk.RIGHT)

        # ---------------------------------------------------------------------
        # BOTTOM STATUS BAR
        # ---------------------------------------------------------------------
        status_bar = ttk.Frame(container, style="App.TFrame")
        status_bar.pack(fill=tk.X)

        self.status_label = ttk.Label(
            status_bar,
            textvariable=self.status_var,
            style="Status.TLabel"
        )
        self.status_label.pack(side=tk.LEFT)

    # -------------------------------------------------------------------------
    # FOLDER MANAGEMENT
    # -------------------------------------------------------------------------
    def set_folder(self, folder_path: Path):
        folder_path = Path(folder_path).resolve()
        if not folder_path.exists():
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                messagebox.showerror("Invalid Folder", f"Could not create or access folder:\n{e}")
                return

        self.current_folder = folder_path
        self.path_var.set(str(folder_path))
        set_current_target_folder(folder_path)

        # Switch watcher if running
        self.watcher.set_target_folder(folder_path)
        self.status_var.set(f"Active target updated to: {folder_path.name}")

    def on_path_entered(self):
        new_path_str = self.path_var.get().strip()
        if not new_path_str:
            return
        p = Path(new_path_str).resolve()
        if not p.exists() or not p.is_dir():
            messagebox.showerror("Error", f"Path does not exist or is not a directory:\n{p}")
            return
        self.set_folder(p)

    def browse_folder(self):
        selected = filedialog.askdirectory(
            initialdir=str(self.current_folder),
            title="Select Target Folder to Organize"
        )
        if selected:
            self.set_folder(Path(selected))

    def open_current_folder(self):
        try:
            if self.current_folder.exists():
                os.startfile(str(self.current_folder))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder:\n{e}")

    # -------------------------------------------------------------------------
    # ORGANIZER ACTIONS
    # -------------------------------------------------------------------------
    def organize_now(self):
        self.status_var.set(f"Organizing files in {self.current_folder.name}...")
        self.root.update_idletasks()

        result = organize_existing_files(self.current_folder)
        org_count = result["organized"]
        clean_count = result["cleaned_folders"]

        self.refresh_history()
        msg = f"Organized {org_count} file(s)."
        if clean_count > 0:
            msg += f" Removed {clean_count} empty category folder(s)."
        self.status_var.set(msg)
        messagebox.showinfo("Organization Complete", msg)

    def clean_empty_folders(self):
        cleaned = cleanup_empty_category_folders(self.current_folder)
        msg = f"Removed {cleaned} empty category folder(s)." if cleaned > 0 else "No empty category folders found."
        self.status_var.set(msg)
        messagebox.showinfo("Clean Complete", msg)

    # -------------------------------------------------------------------------
    # WATCHER / AUTO-ORGANIZE
    # -------------------------------------------------------------------------
    def toggle_watch(self):
        if self.watcher.is_running():
            self.watcher.stop()
            self.watch_toggle_btn.config(text="Start Auto-Watch")
            self.watch_badge.config(
                text="● Watcher Off",
                bg="#f1f5f9",
                fg="#64748b"
            )
            self.status_var.set("Auto-watch stopped.")
        else:
            self.watcher.start()
            self.watch_toggle_btn.config(text="Stop Auto-Watch")
            self.watch_badge.config(
                text="● Auto-Watching",
                bg="#dcfce7",
                fg="#16a34a"
            )
            self.status_var.set(f"Auto-watching active folder: {self.current_folder.name}")

    def _on_watcher_event(self, event_type: str, data: Any):
        # Thread-safe UI update
        self.root.after(0, lambda: self._handle_watcher_event(event_type, data))

    def _handle_watcher_event(self, event_type: str, data: Any):
        self.refresh_history()
        if event_type == "file_organized":
            filename = data.get("filename", "file")
            category = data.get("category", "")
            self.status_var.set(f"Auto-organized '{filename}' into {category}")
        elif event_type == "folder_cleaned":
            self.status_var.set(f"Pruned {data} empty folder(s)")

    # -------------------------------------------------------------------------
    # HISTORY & UNDO
    # -------------------------------------------------------------------------
    def refresh_history(self):
        records = get_history()
        self.all_records = records
        self._populate_tree(records)
        active_count = sum(1 for r in records if not r.get("undone", False))
        self.stats_label.config(text=f"{len(records)} total | {active_count} active")

    def _populate_tree(self, records: List[Dict[str, Any]]):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for record in reversed(records):
            item_id = record.get("id", "")
            time_str = record.get("timestamp", "")
            filename = record.get("filename", "")
            category = record.get("category", "")
            dest_path = record.get("destination_path", "")
            # Shorten destination path to relative category/filename for cleaner display
            try:
                dest_display = f"{category}/{Path(dest_path).name}"
            except Exception:
                dest_display = dest_path
            status = record.get("status", "Moved")

            item_tag = "undone" if record.get("undone", False) else "active"
            self.tree.insert(
                "",
                tk.END,
                values=(item_id, time_str, filename, category, dest_display, status),
                tags=(item_tag,)
            )

        self.tree.tag_configure("undone", foreground="#94a3b8")
        self.tree.tag_configure("active", foreground=self.text_primary)

    def filter_history(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self._populate_tree(self.all_records)
            return

        filtered = [
            r for r in self.all_records
            if query in r.get("filename", "").lower()
            or query in r.get("category", "").lower()
            or query in r.get("status", "").lower()
            or query in r.get("id", "").lower()
        ]
        self._populate_tree(filtered)

    def _get_selected_record_id(self) -> Optional[str]:
        selected = self.tree.selection()
        if not selected:
            return None
        values = self.tree.item(selected[0], "values")
        return values[0] if values else None

    def undo_selected_file(self):
        record_id = self._get_selected_record_id()
        if not record_id:
            messagebox.showwarning("No Selection", "Please select a file from the history table to undo.")
            return

        result = undo_entry(record_id)
        self.refresh_history()

        if result.get("success"):
            self.status_var.set(result["message"])
            messagebox.showinfo("Undo Successful", result["message"])
        else:
            self.status_var.set(f"Undo failed: {result['message']}")
            messagebox.showwarning("Cannot Undo", result["message"])

    def undo_all_files(self):
        active_count = sum(1 for r in self.all_records if not r.get("undone", False))
        if active_count == 0:
            messagebox.showinfo("Undo All", "There are no active file moves to undo.")
            return

        if not messagebox.askyesno("Undo All", f"Are you sure you want to restore {active_count} file(s) back to their original locations?"):
            return

        res = undo_all()
        self.refresh_history()
        self.status_var.set(res["message"])
        messagebox.showinfo("Undo All Complete", res["message"])

    def clear_history_records(self):
        if not self.all_records:
            return
        if messagebox.askyesno("Clear History", "Clear all history records? This does not delete any files, but removes the record list."):
            clear_history()
            self.refresh_history()
            self.status_var.set("History cleared.")

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def open_selected_folder(self):
        record_id = self._get_selected_record_id()
        if not record_id:
            return
        from history import get_record_by_id
        rec = get_record_by_id(record_id)
        if rec and "destination_path" in rec:
            dest_dir = Path(rec["destination_path"]).parent
            if dest_dir.exists():
                os.startfile(str(dest_dir))

    def copy_selected_filename(self):
        record_id = self._get_selected_record_id()
        if not record_id:
            return
        from history import get_record_by_id
        rec = get_record_by_id(record_id)
        if rec:
            self.root.clipboard_clear()
            self.root.clipboard_append(rec["filename"])
            self.status_var.set(f"Copied '{rec['filename']}' to clipboard")

    def on_closing(self):
        if self.watcher.is_running():
            self.watcher.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MinimalistOrganizerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
