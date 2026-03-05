import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from PIL import Image

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

# ── Palette ────────────────────────────────────────────────────────────────
BG      = "#F7F7F8"
WHITE   = "#FFFFFF"
BORDER  = "#E2E2E6"
TEXT    = "#111111"
MUTED   = "#9A9AAF"
ACCENT  = "#5B5BD6"
SUCCESS = "#30A46C"
DANGER  = "#E5484D"
RADIUS  = 10


class WebpToPngConverter:
    def __init__(self):
        self.root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
        self.root.title("WebP → PNG")
        self.root.geometry("540x560")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.files = []
        self.output_folder = tk.StringVar()
        self._dragging = False

        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Bar.Horizontal.TProgressbar",
                        background=ACCENT, troughcolor=BORDER,
                        borderwidth=0, thickness=4)

        outer = tk.Frame(root, bg=BG)
        outer.pack(fill="both", expand=True, padx=24, pady=24)

        # ── Header ────────────────────────────────────────────────────────
        hdr = tk.Frame(outer, bg=BG)
        hdr.pack(fill="x", pady=(0, 16))
        tk.Label(hdr, text="WebP → PNG", font=("Helvetica", 17, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        self.status_label = tk.Label(hdr, text="", font=("Helvetica", 10),
                                     bg=BG, fg=MUTED)
        self.status_label.pack(side="right", pady=(4, 0))

        # ── Drop zone ─────────────────────────────────────────────────────
        self.drop_canvas = tk.Canvas(outer, width=492, height=140,
                                     bg=WHITE, bd=0, highlightthickness=0,
                                     cursor="hand2")
        self.drop_canvas.pack(fill="x")
        self._draw_drop_zone(active=False)

        self.drop_canvas.bind("<Button-1>", self._browse_files)
        self.drop_canvas.bind("<Enter>", lambda e: self._draw_drop_zone(active=True))
        self.drop_canvas.bind("<Leave>", lambda e: self._draw_drop_zone(active=False))

        if HAS_DND:
            self.drop_canvas.drop_target_register(DND_FILES)
            self.drop_canvas.dnd_bind("<<Drop>>", self._on_drop)
            self.drop_canvas.dnd_bind("<<DragEnter>>",
                                      lambda e: self._draw_drop_zone(active=True))
            self.drop_canvas.dnd_bind("<<DragLeave>>",
                                      lambda e: self._draw_drop_zone(active=False))

        # ── File list ─────────────────────────────────────────────────────
        list_hdr = tk.Frame(outer, bg=BG)
        list_hdr.pack(fill="x", pady=(14, 4))

        self.count_label = tk.Label(list_hdr, text="No files added",
                                    font=("Helvetica", 10, "bold"),
                                    bg=BG, fg=MUTED)
        self.count_label.pack(side="left")

        self.clear_btn = tk.Label(list_hdr, text="Clear all",
                                  font=("Helvetica", 10), bg=BG, fg=ACCENT,
                                  cursor="hand2")
        self.clear_btn.pack(side="right")
        self.clear_btn.bind("<Button-1>", lambda e: self._clear_files())

        list_card = tk.Frame(outer, bg=WHITE, bd=1, relief="flat",
                             highlightbackground=BORDER, highlightthickness=1)
        list_card.pack(fill="x")

        sb = tk.Scrollbar(list_card, width=10)
        sb.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            list_card, yscrollcommand=sb.set,
            bg=WHITE, fg=TEXT, selectbackground="#EDEDFF",
            selectforeground=ACCENT, font=("Helvetica", 10),
            height=6, relief="flat", bd=0, highlightthickness=0,
            activestyle="none"
        )
        self.listbox.pack(fill="x", padx=2, pady=2)
        sb.config(command=self.listbox.yview)

        # ── Progress bar ─────────────────────────────────────────────────
        self.progress = ttk.Progressbar(outer, style="Bar.Horizontal.TProgressbar",
                                        orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(10, 0))

        # ── Output folder ─────────────────────────────────────────────────
        folder_card = tk.Frame(outer, bg=WHITE, bd=1, relief="flat",
                               highlightbackground=BORDER, highlightthickness=1)
        folder_card.pack(fill="x", pady=(12, 0))

        tk.Label(folder_card, text="Save to", font=("Helvetica", 10),
                 bg=WHITE, fg=MUTED, width=7, anchor="w").pack(side="left", padx=(10, 0))

        self.out_entry = tk.Entry(folder_card, textvariable=self.output_folder,
                                  font=("Helvetica", 10), bg=WHITE, fg=TEXT,
                                  insertbackground=TEXT, relief="flat", bd=0)
        self.out_entry.pack(side="left", fill="x", expand=True, ipady=8)

        sep = tk.Frame(folder_card, bg=BORDER, width=1)
        sep.pack(side="left", fill="y", pady=6)

        tk.Button(folder_card, text="Browse", font=("Helvetica", 10),
                  bg=WHITE, fg=ACCENT, relief="flat", cursor="hand2",
                  command=self._pick_output_folder, bd=0,
                  padx=12, pady=8, activebackground=BG,
                  activeforeground=ACCENT).pack(side="right")

        # ── Convert button ────────────────────────────────────────────────
        self.convert_btn = tk.Button(
            outer, text="Convert to PNG",
            font=("Helvetica", 12, "bold"),
            bg=ACCENT, fg="white", relief="flat", cursor="hand2",
            command=self._start_conversion, bd=0,
            pady=12, activebackground="#4A4ABF", activeforeground="white"
        )
        self.convert_btn.pack(fill="x", pady=(12, 0))

    def _draw_drop_zone(self, active=False):
        c = self.drop_canvas
        c.delete("all")
        w, h = 492, 140
        color = ACCENT if active else BORDER

        # Rounded-rect dashed border via short line segments
        r = RADIUS
        dash = (6, 4)
        opts = dict(fill="", dash=dash, outline=color, width=2)
        c.create_arc(0, 0, r*2, r*2, start=90, extent=90, **opts)
        c.create_arc(w-r*2, 0, w, r*2, start=0, extent=90, **opts)
        c.create_arc(w-r*2, h-r*2, w, h, start=270, extent=90, **opts)
        c.create_arc(0, h-r*2, r*2, h, start=180, extent=90, **opts)
        c.create_line(r, 0, w-r, 0, dash=dash, fill=color, width=2)
        c.create_line(r, h, w-r, h, dash=dash, fill=color, width=2)
        c.create_line(0, r, 0, h-r, dash=dash, fill=color, width=2)
        c.create_line(w, r, w, h-r, dash=dash, fill=color, width=2)

        icon_color = ACCENT if active else MUTED
        # Up-arrow icon
        cx = w // 2
        c.create_line(cx, 50, cx, 82, fill=icon_color, width=2)
        c.create_line(cx-12, 62, cx, 50, fill=icon_color, width=2)
        c.create_line(cx+12, 62, cx, 50, fill=icon_color, width=2)

        label = "Drop .webp files here" if not active else "Release to add files"
        c.create_text(cx, 96, text=label,
                      font=("Helvetica", 12), fill=icon_color)
        c.create_text(cx, 114, text="or click to browse",
                      font=("Helvetica", 10), fill=MUTED)

    # ── File handling ──────────────────────────────────────────────────────

    def _browse_files(self, event=None):
        paths = filedialog.askopenfilenames(
            title="Select WebP files",
            filetypes=[("WebP files", "*.webp"), ("All files", "*.*")]
        )
        if paths:
            self._add_files(list(paths))

    def _on_drop(self, event):
        paths = self._parse_drop_data(event.data)
        webp = [p for p in paths if p.lower().endswith(".webp")]
        self._draw_drop_zone(active=False)
        if webp:
            self._add_files(webp)
        elif paths:
            self._flash_status("Only .webp files are supported", error=True)

    def _parse_drop_data(self, raw):
        paths, current, inside = [], "", False
        for ch in raw:
            if ch == "{":
                inside = True
            elif ch == "}":
                inside = False
                if current:
                    paths.append(current.strip())
                    current = ""
            elif ch == " " and not inside:
                if current:
                    paths.append(current.strip())
                    current = ""
            else:
                current += ch
        if current:
            paths.append(current.strip())
        return paths

    def _add_files(self, paths):
        added = 0
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.listbox.insert(tk.END, f"  {os.path.basename(p)}")
                added += 1
        self._update_count()
        if added:
            self._flash_status(f"+{added} file{'s' if added != 1 else ''} added")

    def _clear_files(self):
        self.files.clear()
        self.listbox.delete(0, tk.END)
        self.progress["value"] = 0
        self._update_count()
        self.status_label.config(text="", fg=MUTED)

    def _update_count(self):
        n = len(self.files)
        if n:
            self.count_label.config(
                text=f"{n} file{'s' if n != 1 else ''}", fg=TEXT)
        else:
            self.count_label.config(text="No files added", fg=MUTED)

    def _pick_output_folder(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_folder.set(folder)

    # ── Conversion ────────────────────────────────────────────────────────

    def _start_conversion(self):
        if not self.files:
            self._flash_status("Add some files first", error=True)
            return
        if not self.output_folder.get():
            self._flash_status("Choose an output folder first", error=True)
            return

        self.convert_btn.config(state="disabled", bg="#9898D8")
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.files)
        self._flash_status("Converting…")

        threading.Thread(target=self._convert_all, daemon=True).start()

    def _convert_all(self):
        out_dir = self.output_folder.get()
        success, errors = 0, []

        for i, path in enumerate(self.files):
            try:
                img = Image.open(path).convert("RGBA")
                base = os.path.splitext(os.path.basename(path))[0]
                img.save(os.path.join(out_dir, base + ".png"), "PNG")
                success += 1
            except Exception as e:
                errors.append(f"{os.path.basename(path)}: {e}")
            self.root.after(0, self._tick, i + 1)

        self.root.after(0, self._done, success, errors)

    def _tick(self, value):
        self.progress["value"] = value
        self.status_label.config(
            text=f"{value} / {len(self.files)}", fg=MUTED)

    def _done(self, success, errors):
        self.convert_btn.config(state="normal", bg=ACCENT)
        if errors:
            self._flash_status(
                f"{success}/{len(self.files)} done · {len(errors)} failed",
                error=True)
        else:
            self._flash_status(
                f"All {success} file{'s' if success != 1 else ''} converted",
                success=True)

    def _flash_status(self, msg, error=False, success=False):
        color = DANGER if error else (SUCCESS if success else MUTED)
        self.status_label.config(text=msg, fg=color)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    WebpToPngConverter().run()
