"""
fetcher.py
Orkestrator level rendah: gabungkan robots.py + browser.py +
consent.py + cache.py + retry logic menjadi satu langkah "fetch"
yang menghasilkan HTML mentah + metadata dasar (bukan konten final).
"""

from .errors import handle_fetch_error


class Fetcher:
    """Orkestrator fetch satu URL, dipanggil oleh cli.py/__init__.py."""

    def __init__(self, browser, robots_checker, rate_limiter, cache=None):
        self.browser = browser
        self.robots_checker = robots_checker
        self.rate_limiter = rate_limiter
        self.cache = cache

    def normalize_url(self, url: str) -> str:
        """Normalisasi URL: lowercase host, buang fragment, urutkan query param, dll."""
        # TODO
        pass

    async def fetch(self, url: str, javascript: bool = True, retries: int = 3) -> dict:
        """
        Alur: normalize -> cek robots.txt -> cek cache -> rate limit ->
        launch page -> load -> dismiss consent banner -> ambil rendered HTML.
        Return dict mentah: {url, final_url, html, title, status}.
        """
        # TODO: implementasi orkestrasi lengkap + retry dengan backoff
        pass

    async def handle_redirects(self, page) -> str:
        """Deteksi & tangani redirect chain, cegah redirect loop."""
        # TODO: bandingkan final_url dengan riwayat url yang sudah dikunjungi
        pass
