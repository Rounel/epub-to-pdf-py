"""
EPUB → PDF Converter — Interface graphique
Lancement : python gui.py
"""

import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from main import convert_epub_to_pdf

# ── Thème global ──────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Palette ───────────────────────────────────────────────────────────────────
CLR_BG        = "#1e1e2e"
CLR_SURFACE   = "#2a2a3d"
CLR_BORDER    = "#3a3a55"
CLR_ACCENT    = "#7c6af7"
CLR_ACCENT_HV = "#6355d4"
CLR_SUCCESS   = "#23c45e"
CLR_ERROR     = "#f05b5b"
CLR_TEXT      = "#e0e0f0"
CLR_MUTED     = "#888aaa"
CLR_LOG_BG    = "#13131f"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("EPUB → PDF Converter")
        self.geometry("680x620")
        self.minsize(580, 560)
        self.configure(fg_color=CLR_BG)
        self.resizable(True, True)

        # État interne
        self._output_path: str = ""
        self._converting   = False

        self._build_ui()

    # ── Construction de l'interface ───────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)   # zone de log extensible

        # ── En-tête ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=CLR_SURFACE, corner_radius=12)
        header.grid(row=0, column=0, padx=20, pady=(20, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="EPUB → PDF",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=CLR_ACCENT,
        ).grid(row=0, column=0, padx=20, pady=(16, 2))

        ctk.CTkLabel(
            header,
            text="Convertissez vos livres numériques en PDF imprimables",
            font=ctk.CTkFont(size=12),
            text_color=CLR_MUTED,
        ).grid(row=1, column=0, padx=20, pady=(0, 14))

        # ── Fichier EPUB ─────────────────────────────────────────────────────
        self._epub_frame = self._file_section(
            row=1,
            label="Fichier EPUB",
            placeholder="Sélectionnez un fichier .epub…",
            browse_cmd=self._browse_epub,
        )
        self._epub_entry = self._epub_frame._entry  # référence directe

        # ── Fichier PDF de sortie ─────────────────────────────────────────────
        self._pdf_frame = self._file_section(
            row=2,
            label="Fichier PDF de sortie",
            placeholder="Chemin du fichier .pdf généré…",
            browse_cmd=self._browse_pdf,
        )
        self._pdf_entry = self._pdf_frame._entry

        # ── Bouton Convertir ─────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=3, column=0, padx=20, pady=(4, 0), sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=0)

        self._convert_btn = ctk.CTkButton(
            btn_row,
            text="  Convertir",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=CLR_ACCENT,
            hover_color=CLR_ACCENT_HV,
            height=42,
            corner_radius=10,
            command=self._start_conversion,
        )
        self._convert_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._open_btn = ctk.CTkButton(
            btn_row,
            text="Ouvrir le PDF",
            font=ctk.CTkFont(size=13),
            fg_color=CLR_SUCCESS,
            hover_color="#1aab52",
            height=42,
            corner_radius=10,
            width=130,
            command=self._open_pdf,
            state="disabled",
        )
        self._open_btn.grid(row=0, column=1, sticky="e")

        # ── Barre de progression ──────────────────────────────────────────────
        self._progress = ctk.CTkProgressBar(
            self,
            height=6,
            corner_radius=4,
            fg_color=CLR_BORDER,
            progress_color=CLR_ACCENT,
        )
        self._progress.set(0)
        self._progress.grid(row=4, column=0, padx=20, pady=(10, 4), sticky="ew")

        self._status_lbl = ctk.CTkLabel(
            self,
            text="Prêt",
            font=ctk.CTkFont(size=11),
            text_color=CLR_MUTED,
            anchor="w",
        )
        self._status_lbl.grid(row=4, column=0, padx=22, pady=(0, 0), sticky="sw")

        # ── Zone de logs ──────────────────────────────────────────────────────
        log_container = ctk.CTkFrame(self, fg_color=CLR_SURFACE, corner_radius=10)
        log_container.grid(row=5, column=0, padx=20, pady=(6, 20), sticky="nsew")
        log_container.grid_rowconfigure(1, weight=1)
        log_container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            log_container,
            text="Journal",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=CLR_MUTED,
            anchor="w",
        ).grid(row=0, column=0, padx=12, pady=(8, 0), sticky="w")

        self._log_box = ctk.CTkTextbox(
            log_container,
            fg_color=CLR_LOG_BG,
            text_color=CLR_TEXT,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8,
            border_width=0,
            wrap="word",
            state="disabled",
        )
        self._log_box.grid(row=1, column=0, padx=8, pady=(4, 8), sticky="nsew")

        # Tag coloré pour les messages d'erreur et de succès
        self._log_box._textbox.tag_configure("error",   foreground=CLR_ERROR)
        self._log_box._textbox.tag_configure("success", foreground=CLR_SUCCESS)
        self._log_box._textbox.tag_configure("muted",   foreground=CLR_MUTED)

    # ── Widget utilitaire : section fichier ───────────────────────────────────

    def _file_section(self, row: int, label: str, placeholder: str, browse_cmd):
        frame = ctk.CTkFrame(self, fg_color=CLR_SURFACE, corner_radius=10)
        frame.grid(row=row, column=0, padx=20, pady=4, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=CLR_TEXT,
            width=170,
            anchor="w",
        ).grid(row=0, column=0, padx=(14, 8), pady=12, sticky="w")

        entry = ctk.CTkEntry(
            frame,
            placeholder_text=placeholder,
            fg_color=CLR_LOG_BG,
            border_color=CLR_BORDER,
            text_color=CLR_TEXT,
            font=ctk.CTkFont(size=11),
            height=34,
        )
        entry.grid(row=0, column=1, padx=(0, 8), pady=12, sticky="ew")

        ctk.CTkButton(
            frame,
            text="Parcourir",
            width=90,
            height=34,
            fg_color=CLR_BORDER,
            hover_color="#505075",
            text_color=CLR_TEXT,
            font=ctk.CTkFont(size=12),
            corner_radius=8,
            command=browse_cmd,
        ).grid(row=0, column=2, padx=(0, 12), pady=12)

        # Attacher l'entry au frame pour y accéder depuis l'extérieur
        frame._entry = entry
        return frame

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _browse_epub(self):
        path = filedialog.askopenfilename(
            title="Choisir un fichier EPUB",
            filetypes=[("Fichiers EPUB", "*.epub"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return
        self._epub_entry.delete(0, "end")
        self._epub_entry.insert(0, path)

        # Auto-remplir le chemin de sortie
        auto_pdf = str(Path(path).with_suffix(".pdf"))
        self._pdf_entry.delete(0, "end")
        self._pdf_entry.insert(0, auto_pdf)

        self._open_btn.configure(state="disabled")
        self._log("Fichier EPUB sélectionné : " + path, tag="muted")

    def _browse_pdf(self):
        initial = self._pdf_entry.get() or str(Path.home())
        path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF sous…",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")],
            initialfile=Path(initial).name if initial else "output.pdf",
            initialdir=str(Path(initial).parent) if initial else str(Path.home()),
        )
        if path:
            self._pdf_entry.delete(0, "end")
            self._pdf_entry.insert(0, path)

    def _start_conversion(self):
        if self._converting:
            return

        epub_path = self._epub_entry.get().strip()
        pdf_path  = self._pdf_entry.get().strip()

        if not epub_path:
            self._set_status("Veuillez sélectionner un fichier EPUB.", error=True)
            return
        if not os.path.isfile(epub_path):
            self._set_status(f"Fichier introuvable : {epub_path}", error=True)
            return
        if not pdf_path:
            self._set_status("Veuillez spécifier un chemin de sortie PDF.", error=True)
            return

        self._converting = True
        self._open_btn.configure(state="disabled")
        self._convert_btn.configure(state="disabled", text="  Conversion…")
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
        self._progress.set(0)
        self._progress.configure(mode="indeterminate")
        self._progress.start()
        self._set_status("Conversion en cours…")

        thread = threading.Thread(
            target=self._run_conversion,
            args=(epub_path, pdf_path),
            daemon=True,
        )
        thread.start()

    def _run_conversion(self, epub_path: str, pdf_path: str):
        try:
            convert_epub_to_pdf(epub_path, pdf_path, log=self._log_thread_safe)
            self.after(0, self._on_success, pdf_path)
        except Exception as exc:
            self.after(0, self._on_error, str(exc))

    def _on_success(self, pdf_path: str):
        self._converting = False
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress.set(1)
        self._set_status("Conversion terminée avec succès !", error=False, success=True)
        self._log("Conversion terminée.", tag="success")
        self._convert_btn.configure(state="normal", text="  Convertir")
        self._open_btn.configure(state="normal")
        self._output_path = pdf_path

    def _on_error(self, message: str):
        self._converting = False
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress.set(0)
        self._set_status("Erreur lors de la conversion.", error=True)
        self._log(f"Erreur : {message}", tag="error")
        self._convert_btn.configure(state="normal", text="  Convertir")

    def _open_pdf(self):
        if not self._output_path or not os.path.isfile(self._output_path):
            self._set_status("Fichier PDF introuvable.", error=True)
            return
        if sys.platform == "win32":
            os.startfile(self._output_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", self._output_path])
        else:
            subprocess.Popen(["xdg-open", self._output_path])

    # ── Helpers UI ────────────────────────────────────────────────────────────

    def _set_status(self, text: str, error: bool = False, success: bool = False):
        color = CLR_ERROR if error else (CLR_SUCCESS if success else CLR_MUTED)
        self._status_lbl.configure(text=text, text_color=color)

    def _log(self, message: str, tag: str = ""):
        self._log_box.configure(state="normal")
        prefix = "  "
        if tag == "error":
            prefix = "✗ "
        elif tag == "success":
            prefix = "✓ "
        elif tag == "muted":
            prefix = "· "
        else:
            prefix = "› "
        full_msg = prefix + message + "\n"
        if tag:
            self._log_box._textbox.insert("end", full_msg, tag)
        else:
            self._log_box.insert("end", full_msg)
        self._log_box._textbox.see("end")
        self._log_box.configure(state="disabled")

    def _log_thread_safe(self, message: str):
        """Called from the worker thread — schedule on the main thread."""
        self.after(0, self._log, message)


# ── Point d'entrée ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
