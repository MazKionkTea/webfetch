"""
metadata.py
Ekstraksi metadata dokumen dari berbagai sumber di HTML: title tag,
meta tag standar, Open Graph tag, JSON-LD, dan canonical URL.
Prioritas: JSON-LD > Open Graph > meta tag > title tag.
"""


class MetadataExtractor:
    """Ekstraksi & penggabungan metadata dari satu halaman."""

    def extract_title(self, soup) -> str:
        # TODO: <title>
        pass

    def extract_from_meta_tags(self, soup) -> dict:
        """Ambil <meta name="author">, <meta name="description">, dll."""
        # TODO
        pass

    def extract_from_og_tags(self, soup) -> dict:
        """Ambil <meta property="og:title">, og:description, og:image, dll."""
        # TODO
        pass

    def extract_from_json_ld(self, soup) -> dict:
        """Parse <script type="application/ld+json"> untuk field Article/NewsArticle."""
        # TODO: json.loads tiap script ld+json, cari @type Article/NewsArticle/BlogPosting
        pass

    def extract_canonical_url(self, soup) -> str:
        # TODO: <link rel="canonical">
        pass

    def merge_metadata_sources(self, sources: list) -> "Metadata":
        """
        Gabungkan hasil semua extract_* di atas jadi satu objek Metadata,
        dengan prioritas JSON-LD > OG > meta tag > title tag per field.
        """
        # TODO
        pass
