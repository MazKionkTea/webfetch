"""
scoring.py
Content scoring: beri skor tiap elemen kandidat main-content
berdasarkan kepadatan teks, jumlah paragraf, heading, gambar
(positif) vs jumlah link, navigasi, tanda iklan/footer (negatif).
"""


class ContentScorer:
    """Hitung skor "kemungkinan main content" untuk elemen DOM."""

    # TODO: definisikan bobot sebagai konstanta, mis.
    # WEIGHT_PARAGRAPH = 10, WEIGHT_TEXT_DENSITY = 8, WEIGHT_HEADING = 5,
    # WEIGHT_ARTICLE_TAG = 5, WEIGHT_IMAGE = 3,
    # PENALTY_LINK_DENSITY = -10, PENALTY_NAV = -10,
    # PENALTY_AD_MARKER = -20, PENALTY_FOOTER = -20

    def score_element(self, element) -> float:
        """Hitung skor satu elemen berdasarkan bobot di atas."""
        # TODO
        pass

    def score_all_candidates(self, soup) -> dict:
        """Skor semua elemen kandidat (div/section/article) di halaman."""
        # TODO: kembalikan {element: score}
        pass

    def pick_best_candidate(self, scores: dict):
        """Pilih elemen dengan skor tertinggi sebagai main content."""
        # TODO
        pass
