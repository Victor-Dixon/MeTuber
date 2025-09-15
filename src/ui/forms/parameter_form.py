# File: src/ui/forms/parameter_form.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Callable
from PyQt5.QtWidgets import QFileDialog, QMessageBox

def _pick_file(start: str) -> str:
    p = Path(start) if start else Path.cwd()
    fname, _ = QFileDialog.getOpenFileName(None, "Select file", str(p), "Images (*.png *.jpg *.jpeg);;All Files (*)")
    return fname or start

def coerce_file_param(style, key: str, set_param: Callable[[str, Any], None]) -> None:
    """Hook for file params with existence check + inline warning."""
    current = style.params.get(key, "")
    chosen = _pick_file(current)
    if not chosen:
        return
    if not Path(chosen).exists():
        QMessageBox.warning(None, "Invalid Path", f"File for '{key}' not found:\n{chosen}\nKeeping previous value.")
        return
    set_param(key, chosen)
