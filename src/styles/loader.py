# File: src/styles/loader.py
from __future__ import annotations
import importlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import importlib.resources as pkgres

from .style_base import BaseStyle, StyleProtocol

logger = logging.getLogger(__name__)

COERCE_PATH_KEYS = {"texture_path"}

def _resolve_default_texture() -> Optional[str]:
    """
    Try several fallbacks to resolve a safe default texture:
      1) Packaged resource: styles/assets/textures/texture.png
      2) Repo-relative:      assets/textures/texture.png
      3) Repo-relative:      textures/texture.png
    """
    # 1) packaged
    try:
        with pkgres.as_file(pkgres.files("styles") / "assets" / "textures" / "texture.png") as p:
            if p.exists():
                return str(p)
    except Exception:
        pass
    # 2) repo: assets/textures/texture.png
    root = Path(__file__).resolve().parents[2]
    for rel in (Path("assets/textures/texture.png"), Path("textures/texture.png")):
        cand = root / rel
        if cand.exists():
            return str(cand)
    return None

class StyleRegistry:
    def __init__(self) -> None:
        self._styles: Dict[str, StyleProtocol] = {}

    def load_from_module_names(self, module_names: List[str]) -> None:
        for mod_name in module_names:
            try:
                mod = importlib.import_module(mod_name)
            except Exception as e:
                logger.exception("Failed to import style module %s: %s", mod_name, e)
                continue

            # Heuristic: module exposes `STYLE` instance or `build()` factory.
            style = getattr(mod, "STYLE", None)
            if style is None and hasattr(mod, "build"):
                try:
                    style = mod.build()
                except Exception as e:
                    logger.exception("Failed to build style in %s: %s", mod_name, e)
                    continue

            if style is None:
                logger.warning("No STYLE or build() in %s; skipping.", mod_name)
                continue

            # Wrap/normalize to BaseStyle if needed
            style = self._normalize_style(style, mod_name)
            name = getattr(style, "name", mod_name.split(".")[-1])
            self._styles[name] = style
            logger.info("Loaded style: %s (Category: %s)", name, getattr(style, "category", "Unknown"))

    def _normalize_style(self, style: Any, mod_name: str) -> StyleProtocol:
        # Ensure optional attrs exist (prevents "'... has no attribute current_variant'")
        if not hasattr(style, "current_variant"):
            style_name = getattr(style, "name", mod_name)
            logger.warning("Invalid parameters for style '%s': missing 'current_variant'. Applying safe default.", style_name)
            try:
                setattr(style, "current_variant", None)
            except Exception:
                safe = BaseStyle(
                    name=getattr(style, "name", mod_name),
                    category=getattr(style, "category", "Misc"),
                    params=getattr(style, "params", {}) or {},
                    current_variant=None,
                )
                if hasattr(style, "apply"):
                    setattr(safe, "apply", getattr(style, "apply"))
                style = safe

        # Parameter defaults & file-path coercion
        params = getattr(style, "params", {}) or {}
        for key in COERCE_PATH_KEYS:
            if key in params:
                src = str(params[key] or "")
                if src:
                    p = Path(src)
                    if not p.exists():
                        fallback = _resolve_default_texture()
                        if fallback:
                            logger.warning(
                                "File for parameter '%s' not found at '%s'. Resetting to default '%s'.",
                                key, src, fallback
                            )
                            params[key] = fallback
                else:
                    # empty path -> fill with default
                    fallback = _resolve_default_texture()
                    if fallback:
                        logger.info("Parameter '%s' missing; applying default '%s'.", key, fallback)
                        params[key] = fallback
        setattr(style, "params", params)
        return style

    def get(self, name: str) -> StyleProtocol:
        return self._styles[name]

    def all(self) -> List[StyleProtocol]:
        return list(self._styles.values())
