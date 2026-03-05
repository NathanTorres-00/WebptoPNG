import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False


class WebpToPngConverter:
    def __init__(self):
        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        self.root.title("WebP to PNG Converter")
        self.root.geometry("620x520")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.files = []
        self.output_folder = tk.StringVar(value="")

        self._build_ui()

    def _build_ui(self):
        root = self.root
        PAD = 14
        BG = "#1e1e2e"
        SURFACE = "#2a2a3e"
        ACCENT = "#7c6af7"
        TEXT = "#e0e0f0"
        MUTED = "#888aaa"

        title = tk.Label(root, text="WebP  PNG", font=("Helvetica", 22, "bold"),
                         bg=BG, fg=TEXT)
        title.pack(pady=(PAD + 4, 2))

        subtitle = tk.Label(root, text="Drop files below or click to browse",
                            font=("Helvetica", 11), bg=BG, fg=MUTED)
        subtitle.pack()

        # Drop zone
        self.drop_frame = tk.Frame(root, bg=SURFACE, bd=0, relief="flat",
                                   width=560, height=160, cursor="hand2")
        self.drop_frame.pack(padx=PAD, pady=(PAD, 8))
        self.drop_frame.pack_propagate(False)

        self.drop_label = tk.Label(
            self.drop_frame,
            text="Drag & drop .webp files here\nor click to browse",
            font=("Helvetica", 13), bg=SURFACE, fg=MUTED,
            justify="center", cursor="hand2"
        )
        self.drop_label.place(relx=0.5, rely=0.5, anchor="center")

        for widget in (self.drop_frame, self.drop_label):
            widget.bind("<Button-1>", self._browse_files)

        if HAS_DND:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)

        # File list
        list_frame = tk.Frame(root, bg=BG)
        list_frame.pack(padx=PAD, fill="x")

        self.file_count_label = tk.Label(list_frame, text="No files selected",
                                         font=("Helvetica", 10), bg=BG, fg=MUTED)
        self.file_count_label.pack(side="left")

        clear_btn = tk.Button(list_frame, text="Clear", font=("Helvetica", 9),
                              bg=SURFACE, fg=MUTED, relief="flat", cursor="hand2",
                              command=self._clear_files, bd=0, padx=8, pady=2)
        clear_btn.pack(side="right")

        list_container = tk.Frame(root, bg=SURFACE, bd=0)
        list_container.pack(padx=PAD, pady=(4, PAD), fill="x")

        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            list_container, yscrollcommand=scrollbar.set,
            bg=SURFACE, fg=TEXT, selectbackground=ACCENT,
            font=("Helvetica", 10), height=6, relief="flat",
            bd=0, highlightthickness=0
        )
        self.listbox.pack(fill="x")
        scrollbar.config(command=self.listbox.yview)

        # Output folder
        out_frame = tk.Frame(root, bg=BG)
        out_frame.pack(padx=PAD, fill="x", pady=(0, PAD))

        tk.Label(out_frame, text="Output folder:", font=("Helvetica", 10, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")

        self.out_entry = tk.Entry(out_frame, textvariable=self.output_folder,
                                  font=("Helvetica", 10), bg=SURFACE, fg=TEXT,
                                  insertbackground=TEXT, relief="flat", bd=4)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))

        pick_btn = tk.Button(out_frame, text="Browse", font=("Helvetica", 9),
                             bg=ACCENT, fg="white", relief="flat", cursor="hand2",
                             command=self._pick_output_folder, bd=0, padx=10, pady=4)
        pick_btn.pack(side="right")

        # Progress bar
        self.progress = ttk.Progressbar(root, orient="horizontal",
                                        length=560, mode="determinate")
        self.progress.pack(padx=PAD, pady=(0, 6))

        self.status_label = tk.Label(root, text="", font=("Helvetica", 10),
                                     bg=BG, fg=MUTED)
        self.status_label.pack()

        # Convert button
        self.convert_btn = tk.Button(
            root, text="Convert All to PNG",
            font=("Helvetica", 13, "bold"),
            bg=ACCENT, fg="white", relief="flat", cursor="hand2",
            command=self._start_conversion, bd=0, padx=20, pady=10
        )
        self.convert_btn.pack(pady=(10, 0))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Horizontal.TProgressbar", background=ACCENT,
                        troughcolor=SURFACE, borderwidth=0, thickness=8)

    def _browse_files(self, event=None):
        paths = filedialog.askopenfilenames(
            title="Select WebP files",
            filetypes=[("WebP files", "*.webp"), ("All files", "*.*")]
        )
        if paths:
            self._add_files(list(paths))

    def _on_drop(self, event):
        raw = event.data
        # tkinterdnd2 returns space-separated paths; handle braces for paths with spaces
        paths = []
        current = ""
        inside_brace = False
        for ch in raw:
            if ch == "{":
                inside_brace = True
            elif ch == "}":
                inside_brace = False
                if current:
                    paths.append(current.strip())
                    current = ""
            elif ch == " " and not inside_brace:
                if current:
                    paths.append(current.strip())
                    current = ""
            else:
                current += ch
        if current:
            paths.append(current.strip())

        webp_paths = [p for p in paths if p.lower().endswith(".webp")]
        if webp_paths:
            self._add_files(webp_paths)
        else:
            messagebox.showwarning("No WebP files", "Please drop .webp files only.")

    def _add_files(self, paths):
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.listbox.insert(tk.END, os.path.basename(p))
        self._update_count()

    def _clear_files(self):
        self.files.clear()
        self.listbox.delete(0, tk.END)
        self._update_count()
        self.progress["value"] = 0
        self.status_label.config(text="")

    def _update_count(self):
        n = len(self.files)
        self.file_count_label.config(
            text=f"{n} file{'s' if n != 1 else ''} selected" if n else "No files selected"
        )

    def _pick_output_folder(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_folder.set(folder)

    def _start_conversion(self):
        if not self.files:
            messagebox.showwarning("No files", "Please add some WebP files first.")
            return
        if not self.output_folder.get():
            messagebox.showwarning("No output folder", "Please select an output folder.")
            return

        self.convert_btn.config(state="disabled")
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.files)
        self.status_label.config(text="Converting...")

        thread = threading.Thread(target=self._convert_all, daemon=True)
        thread.start()

    def _convert_all(self):
        out_dir = self.output_folder.get()
        success = 0
        errors = []

        for i, path in enumerate(self.files):
            try:
                img = Image.open(path).convert("RGBA")
                base = os.path.splitext(os.path.basename(path))[0]
                out_path = os.path.join(out_dir, base + ".png")
                img.save(out_path, "PNG")
                success += 1
            except Exception as e:
                errors.append(f"{os.path.basename(path)}: {e}")

            self.root.after(0, self._update_progress, i + 1)

        self.root.after(0, self._conversion_done, success, errors)

    def _update_progress(self, value):
        self.progress["value"] = value
        total = len(self.files)
        self.status_label.config(text=f"Converting... {value}/{total}")

    def _conversion_done(self, success, errors):
        self.convert_btn.config(state="normal")
        total = len(self.files)

        if errors:
            err_text = "\n".join(errors)
            messagebox.showerror(
                "Some files failed",
                f"{success}/{total} converted successfully.\n\nErrors:\n{err_text}"
            )
        else:
            messagebox.showinfo(
                "Done!",
                f"All {success} file{'s' if success != 1 else ''} converted successfully!\n\nSaved to:\n{self.output_folder.get()}"
            )

        self.status_label.config(text=f"Done — {success}/{total} converted")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = WebpToPngConverter()
    app.run()
