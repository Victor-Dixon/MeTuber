#!/usr/bin/env python3
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.styles.loader import StyleRegistry

def main() -> int:
    modules = [
        # Test with a style that has the expected STYLE instance
        "styles.effects.test_style",
        "src.styles.effects.stippling",  # Test our new stippling style
    ]
    sr = StyleRegistry()
    sr.load_from_module_names(modules)
    ok = True
    for s in sr.all():
        cv = getattr(s, "current_variant", None)
        tex = (s.params or {}).get("texture_path")
        print(f"{s.name:24} | variant={cv!r:>8} | texture={tex}")
        if not hasattr(s, "current_variant"):
            ok = False
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
