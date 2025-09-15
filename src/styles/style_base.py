# File: src/styles/style_base.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Protocol


class StyleProtocol(Protocol):
    """Runtime contract for style plugins."""
    name: str
    category: str
    params: Dict[str, Any]

    # Optional members (provide safe defaults in BaseStyle)
    current_variant: Optional[str]

    def apply(self, frame) -> Any:  # typically a numpy array
        ...


@dataclass
class BaseStyle:
    """Safe base for all styles; guarantees optional attributes exist."""
    name: str = "Unnamed"
    category: str = "Misc"
    params: Dict[str, Any] = field(default_factory=dict)
    current_variant: Optional[str] = None  # ✅ prevents 'has no attribute' crash

    def update_params(self, **updates: Any) -> None:
        self.params.update(updates)

    def validate_params(self) -> Dict[str, str]:
        """Return field->message map for warnings (non-fatal)."""
        return {}
