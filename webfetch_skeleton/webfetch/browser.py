"""
browser.py
Wrapper di atas Playwright: bertanggung jawab murni untuk
URL -> Browser -> Page -> Rendered HTML. Tidak menangani robots.txt,
konsen cookie, atau parsing konten (itu tugas modul lain).
"""


class BrowserEngine:
    """Wrapper Playwright untuk satu sesi browser."""

    def __init__(self, headless: bool = True, user_agent: str = None,
                 viewport: dict = None, locale: str = None):
        self.headless = headless
        self.user_agent = user_agent
        self.viewport = viewport
        self.locale = locale
        self._browser = None  # TODO: instance playwright browser setelah launch()

    async def launch(self):
        """Buka instance browser (chromium)."""
        # TODO: async_playwright().start() -> chromium.launch(headless=self.headless)
        pass

    async def close(self):
        """Tutup browser."""
        # TODO
        pass

    async def new_page(self):
        """Buat page baru dengan viewport/locale/user_agent yang dikonfigurasi."""
        # TODO
        pass

    async def load_page(self, page, url: str, wait_until: str = "domcontentloaded",
                         timeout: int = 30000):
        """Navigasi ke URL, tangani redirect & timeout."""
        # TODO: page.goto(url, wait_until=wait_until, timeout=timeout)
        pass

    async def block_resources(self, page, resource_types: list):
        """Blokir tipe resource tertentu (image/font/media) untuk mempercepat load."""
        # TODO: page.route() untuk intercept & abort request sesuai resource_types
        pass

    async def get_rendered_html(self, page) -> str:
        """Ambil HTML hasil render (setelah JS jalan)."""
        # TODO: page.content()
        pass

    async def get_page_title(self, page) -> str:
        # TODO: page.title()
        pass

    async def get_final_url(self, page) -> str:
        """URL akhir setelah redirect (bisa beda dari URL awal)."""
        # TODO: page.url
        pass
