"""
browser.py
Wrapper di atas Playwright: bertanggung jawab murni untuk
URL -> Browser -> Page -> Rendered HTML. Tidak menangani robots.txt,
konsen cookie, atau parsing konten (itu tugas modul lain).
"""

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from typing import Optional, List, Dict, Any

class BrowserEngine:
    """
    Wrapper asinkron untuk Playwright yang mengelola siklus hidup browser Chromium.
    
    Kelas ini menyediakan abstraksi tingkat tinggi untuk:
    - Meluncurkan dan menutup instance browser.
    - Mengonfigurasi user-agent, viewport, dan locale secara konsisten.
    - Menavigasi halaman dengan penanganan timeout dan wait strategy.
    - Optimasi performa dengan memblokir resource tidak perlu (gambar, font).
    - Mengekstrak konten HTML akhir setelah eksekusi JavaScript selesai.
    
    Attributes:
        headless (bool): Jika True, browser berjalan tanpa UI grafis (cocok untuk server/CI).
        user_agent (str): String User-Agent kustom untuk meniru browser nyata atau bot spesifik.
        viewport (dict): Dimensi jendela browser {'width': int, 'height': int}.
        locale (str): Kode locale (misal: 'en-US', 'id-ID') untuk simulasi regional.
    
    Contoh penggunaan:
        engine = BrowserEngine(headless=True, user_agent="webfetch/1.0")
        await engine.launch()
        page = await engine.new_page()
        await engine.load_page(page, "https://example.com")
        html = await engine.get_rendered_html(page)
        await engine.close()
    """

    def __init__(self, headless: bool = True, user_agent: str = None,
                 viewport: dict = None, locale: str = None):
        """
        Inisialisasi konfigurasi browser.
        
        Args:
            headless: Mode tanpa UI grafis.
            user_agent: Custom user-agent string. Default jika None adalah bawaan Chromium.
            viewport: Ukuran viewport {'width': 1920, 'height': 1080}. Default jika None adalah standar.
            locale: Setting locale browser.
        """
        self.headless = headless
        self.user_agent = user_agent
        self.viewport = viewport or {"width": 1920, "height": 1080}
        self.locale = locale
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def launch(self):
        """
        Meluncurkan instance browser Chromium.
        
        Metode ini harus dipanggil sebelum membuat page atau melakukan navigasi.
        Menggunakan `async_playwright` untuk memulai driver dan meluncurkan browser
        dengan argumen stabilitas tambahan (`--no-sandbox`, `--disable-dev-shm-usage`)
        yang penting untuk lingkungan Docker atau CI/CD.
        """
        self._playwright = await async_playwright().start()
        
        launch_args = {
            "headless": self.headless,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu"
            ]
        }
        
        self._browser = await self._playwright.chromium.launch(**launch_args)
        
        # Buat context dengan konfigurasi user-agent, viewport, locale
        context_args = {
            "viewport": self.viewport,
            "locale": self.locale,
            "timezone_id": "UTC"
        }
        if self.user_agent:
            context_args["user_agent"] = self.user_agent
            
        self._context = await self._browser.new_context(**context_args)

    async def close(self):
        """
        Menutup browser dan membersihkan resource Playwright.
        
        Penting untuk memanggil metode ini di akhir sesi untuk mencegah kebocoran memori
        dan memastikan proses browser terhenti dengan benar.
        """
        if self._context:
            await self._context.close()
            self._context = None
            
        if self._browser:
            await self._browser.close()
            self._browser = None
            
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def new_page(self) -> Page:
        """
        Membuat instance Page baru dalam browser context yang sudah dikonfigurasi.
        
        Returns:
            Page: Objek page Playwright yang siap untuk navigasi.
        """
        if not self._context:
            raise RuntimeError("Browser belum diluncurkan. Panggil launch() terlebih dahulu.")
        return await self._context.new_page()

    async def load_page(self, page: Page, url: str, 
                        wait_until: str = "domcontentloaded",
                        timeout: int = 30000) -> None:
        """
        Menavigasi page ke URL target dengan strategi tunggu yang ditentukan.
        
        Args:
            page: Objek page tempat navigasi dilakukan.
            url: URL tujuan.
            wait_until: Kapan dianggap 'sukses' load. Opsi:
                        - 'load': Tunggu event load penuh.
                        - 'domcontentloaded': Tunggu DOMContentLoaded (lebih cepat, direkomendasikan).
                        - 'networkidle': Tunggu hingga tidak ada koneksi jaringan selama 500ms.
            timeout: Batas waktu dalam milidetik. Jika terlampaui, akan melempar TimeoutError.
        
        Raises:
            PlaywrightTimeoutError: Jika navigasi melebihi batas waktu.
            Exception: Error navigasi lainnya (DNS failure, connection refused, dll).
        """
        await page.goto(url, wait_until=wait_until, timeout=timeout)

    async def block_resources(self, page: Page, 
                              resource_types: List[str] = ["image", "font", "media"]) -> None:
        """
        Memblokir pemuatan tipe resource tertentu untuk mempercepat loading dan menghemat bandwidth.
        
        Sangat berguna untuk scraping konten teks di mana gambar, font, atau video tidak diperlukan.
        
        Args:
            page: Objek page yang akan diintercept request-nya.
            resource_types: Daftar tipe resource untuk diblokir. 
                            Valid values: 'document', 'stylesheet', 'image', 'media', 
                            'font', 'script', 'texttrack', 'xhr', 'fetch', 'eventsource', 
                            'websocket', 'manifest', 'other'.
        """
        async def intercept(route):
            if route.request.resource_type in resource_types:
                await route.abort()
            else:
                await route.continue_()
        
        await page.route("**/*", intercept)

    async def get_rendered_html(self, page: Page) -> str:
        """
        Mengambil seluruh konten HTML halaman setelah JavaScript dieksekusi.
        
        Berbeda dengan mengambil source code awal, metode ini mengembalikan DOM final
        yang mungkin telah dimodifikasi secara dinamis oleh framework JS (React, Vue, dll).
        
        Args:
            page: Objek page yang sudah dimuat.
            
        Returns:
            str: String HTML lengkap dari state halaman saat ini.
        """
        return await page.content()

    async def get_page_title(self, page: Page) -> str:
        """
        Mengambil judul halaman (<title> tag).
        
        Args:
            page: Objek page yang sudah dimuat.
            
        Returns:
            str: Judul halaman.
        """
        return await page.title()

    async def get_final_url(self, page: Page) -> str:
        """
        Mengambil URL akhir halaman setelah semua redirect terjadi.
        
        Berguna untuk mendeteksi redirect chain atau memastikan URL kanonik.
        
        Args:
            page: Objek page yang sudah selesai navigasi.
            
        Returns:
            str: URL saat ini di address bar browser.
        """
        return page.url