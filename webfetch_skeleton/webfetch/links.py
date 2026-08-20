"""
links.py
Ekstraksi hyperlink dari konten & normalisasi URL relatif
menjadi absolute berdasarkan base URL halaman.
"""


class LinkExtractor:
    """Ekstraksi & normalisasi link dalam main-content."""

    def extract_links(self, element, base_url: str) -> list:
        """Ambil semua <a href> di dalam elemen, kembalikan list (text, url)."""
        # TODO
        pass

    def resolve_relative_url(self, href: str, base_url: str) -> str:
        """Ubah URL relatif ('/docs') jadi absolute ('https://example.com/docs')."""
        # TODO: urllib.parse.urljoin(base_url, href)
        pass
