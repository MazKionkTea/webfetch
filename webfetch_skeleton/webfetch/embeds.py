"""
embeds.py
Deteksi & ekstraksi elemen embed (iframe YouTube, tweet, embedded
PDF, dll) menjadi EmbedBlock, supaya tidak hilang begitu saja
saat DOM dibersihkan.
"""


class EmbedExtractor:
    """Deteksi & ekstraksi konten embed dalam main-content."""

    def detect_embed_type(self, iframe_element) -> str:
        """Tentukan jenis embed dari src (youtube.com, twitter.com/x.com, dll)."""
        # TODO: pattern matching pada domain src iframe
        pass

    def extract_embed(self, iframe_element) -> "EmbedBlock":
        """Bangun EmbedBlock dari satu elemen iframe/embed."""
        # TODO
        pass
