"""
json.py
Serialisasi Document Model langsung menjadi JSON — representasi
internal untuk pipeline RAG (lihat diskusi arsitektur: Markdown
untuk manusia/LLM, JSON untuk metadata/RAG).
"""

import json as json_lib
from .base import BaseRenderer


class JSONRenderer(BaseRenderer):
    """Render Document Model menjadi string JSON."""

    def render(self, document) -> str:
        # TODO: document.to_dict() lalu json_lib.dumps(..., ensure_ascii=False, indent=2)
        pass
