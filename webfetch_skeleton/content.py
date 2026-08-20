"""
content.py
Deteksi main content halaman, dengan prioritas heuristik:
<article> -> <main> -> [role="main"] -> hasil scoring.py ->
fallback Readability-style extraction.
"""


class MainContentDetector:
    """Temukan elemen yang paling mungkin berisi konten utama halaman."""

    def __init__(self, scorer=None):
        self.scorer = scorer  # TODO: instance ContentScorer

    def detect_via_semantic_tags(self, soup):
        """Cek keberadaan <article>, <main>, atau [role="main"]."""
        # TODO
        pass

    def detect_via_scoring(self, soup):
        """Gunakan ContentScorer untuk memilih kandidat terbaik."""
        # TODO
        pass

    def detect_via_readability(self, html: str):
        """Fallback terakhir: pakai library ala Readability (mis. readability-lxml)."""
        # TODO
        pass

    def detect(self, soup, html: str) -> dict:
        """
        Jalankan prioritas: semantic tag -> scoring -> readability.
        Kembalikan dict {element, confidence, method_used}.
        """
        # TODO
        pass
