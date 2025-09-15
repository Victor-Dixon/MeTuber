# File: tests/test_style_loader_validation.py
import types
from src.styles.loader import StyleRegistry

class DummyStyleNoVariant:
    name = "NoVariant"
    category = "Effects"
    params = {"texture_path": "textures/texture.png"}
    def apply(self, frame): return frame

def test_loader_injects_current_variant_and_resolves_missing_assets(monkeypatch, tmp_path):
    # Fake module
    m = types.SimpleNamespace(STYLE=DummyStyleNoVariant())
    monkeypatch.setitem(globals(), "dummy_mod", m)  # no real import
