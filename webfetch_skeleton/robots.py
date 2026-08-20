"""
robots.py
Crawl politeness: parsing robots.txt dan rate limiting per domain,
dijalankan sebelum browser.py membuka halaman.
"""


class RobotsChecker:
    """Cek izin akses berdasarkan robots.txt tiap domain."""

    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self._cache = {}  # TODO: cache robots.txt per domain supaya tidak fetch berulang

    def fetch_robots_txt(self, domain: str) -> str:
        """Ambil isi robots.txt untuk sebuah domain."""
        # TODO: request ke {domain}/robots.txt
        pass

    def is_allowed(self, url: str) -> bool:
        """Cek apakah URL boleh diakses menurut robots.txt."""
        # TODO: parse robots.txt (mis. pakai urllib.robotparser) lalu cek path
        pass

    def get_crawl_delay(self, domain: str) -> float:
        """Ambil crawl-delay yang diminta robots.txt (jika ada)."""
        # TODO
        pass


class RateLimiter:
    """Batasi kecepatan request per domain supaya tidak membebani server target."""

    def __init__(self, default_delay: float = 1.0):
        self.default_delay = default_delay
        self._last_request_time = {}  # TODO: dict domain -> timestamp terakhir

    def wait_if_needed(self, domain: str) -> None:
        """Tunda request berikutnya jika belum cukup jeda sejak request terakhir ke domain ini."""
        # TODO
        pass

    def record_request(self, domain: str) -> None:
        """Catat waktu request untuk domain ini."""
        # TODO
        pass
