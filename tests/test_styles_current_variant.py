from types import SimpleNamespace
import importlib
import builtins
import types
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.styles.loader import StyleRegistry

class DummyStyleNoVariant:
    name = "NoVariant"
    category = "Effects"
    params = {"texture_path": "nonexistent/path.png"}
    def apply(self, frame): return frame

def test_loader_injects_current_variant(monkeypatch):
    fake_mod = types.SimpleNamespace(STYLE=DummyStyleNoVariant())
    def fake_import(name):
        if name == "dummy.no_variant":
            return fake_mod
        return importlib.import_module(name)
    monkeypatch.setattr(importlib, "import_module", fake_import)
    sr = StyleRegistry()
    sr.load_from_module_names(["dummy.no_variant"])
    s = sr.get("NoVariant")
    assert hasattr(s, "current_variant")
