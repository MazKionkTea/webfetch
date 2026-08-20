"""
base.py
Interface dasar untuk semua renderer webfetch, sama polanya
dengan renderers/base.py di pdf2markdown.
"""

from abc import ABC, abstractmethod


class BaseRenderer(ABC):
    """Kontrak yang harus dipenuhi setiap renderer (Markdown/JSON/TXT)."""

    @abstractmethod
    def render(self, document) -> str:
        """Ubah objek model.Document menjadi string output final."""
        # TODO
        pass
