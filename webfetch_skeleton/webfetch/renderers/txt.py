"""
txt.py
Renderer teks polos tanpa markup Markdown.
"""

from .base import BaseRenderer


class TXTRenderer(BaseRenderer):
    """Render Document Model menjadi teks polos."""

    def render(self, document) -> str:
        # TODO: gabungkan text dari tiap block, tabel diratakan jadi baris per baris
        pass
