"""
cache.py
Caching & conditional fetch: hindari fetch ulang URL yang sama
memakai ETag/Last-Modified, plus penyimpanan hasil sementara.
"""


class FetchCache:
    """Cache hasil fetch per URL, dengan dukungan conditional request."""

    def __init__(self, backend=None):
        # TODO: backend default bisa in-memory dict, atau sqlite/disk untuk persist
        self.backend = backend or {}

    def get(self, url: str):
        """Ambil entri cache untuk URL (html, etag, last_modified, timestamp)."""
        # TODO
        pass

    def set(self, url: str, html: str, etag: str = None, last_modified: str = None) -> None:
        """Simpan hasil fetch ke cache."""
        # TODO
        pass

    def is_fresh(self, url: str, max_age_seconds: int = 3600) -> bool:
        """Cek apakah entri cache masih dianggap segar."""
        # TODO
        pass

    def build_conditional_headers(self, url: str) -> dict:
        """Bangun header If-None-Match / If-Modified-Since dari entri cache yang ada."""
        # TODO
        pass
