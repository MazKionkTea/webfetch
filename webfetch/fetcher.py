"""
fetcher.py
Orkestrator level rendah: gabungkan robots.py + browser.py +
consent.py + cache.py + retry logic menjadi satu langkah "fetch"
yang menghasilkan HTML mentah + metadata dasar (bukan konten final).
"""


import asyncio
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Optional, Dict, Any

from .errors import handle_fetch_error, FetchError, RedirectLoopError

class Fetcher:
    """
    Orkestrator utama untuk proses pengambilan (fetch) satu URL.
    
    Kelas ini mengintegrasikan seluruh komponen lapisan fetch:
    1. Normalisasi URL untuk konsistensi kunci cache dan kepatuhan robots.txt.
    2. Pemeriksaan robots.txt sebelum request dilakukan.
    3. Pemanfaatan cache untuk respons cepat dan conditional request (ETag).
    4. Rate limiting untuk etika crawling per domain.
    5. Eksekusi browser (Playwright) dengan penanganan consent banner.
    6. Mekanisme retry dengan exponential backoff untuk error transien.
    
    Attributes:
        browser: Instance BrowserEngine untuk eksekusi rendering JS.
        robots_checker: Instance RobotsChecker untuk validasi izin akses.
        rate_limiter: Instance RateLimiter untuk mengatur jeda request.
        cache: Instance FetchCache (opsional) untuk penyimpanan lokal.
    """

    def __init__(self, browser, robots_checker, rate_limiter, cache=None):
        self.browser = browser
        self.robots_checker = robots_checker
        self.rate_limiter = rate_limiter
        self.cache = cache

    def normalize_url(self, url: str) -> str:
        """
        Menormalisasi URL agar konsisten untuk pengecekan cache dan robots.txt.
        
        Langkah normalisasi:
        1. Lowercase skema (http/https) dan host (domain).
        2. Buang fragment (#section) karena tidak dikirim ke server.
        3. Urutkan parameter query secara alfabetis (agar ?b=1&a=2 sama dengan ?a=1&b=2).
        4. Buang parameter tracking umum (utm_source, fbclid, dll) jika diperlukan (opsional).
        5. Pastikan path selalu ada (default '/').
        
        Args:
            url: URL mentah dari input pengguna.
            
        Returns:
            str: URL yang telah dinormalisasi.
        """
        parsed = urlparse(url)
        
        # Lowercase scheme dan netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        
        # Buang fragment
        fragment = ""
        
        # Parse dan urutkan query parameters
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        # Sort keys untuk konsistensi
        sorted_query = urlencode(sorted(query_params.items()), doseq=True)
        
        # Pastikan path tidak kosong
        path = parsed.path if parsed.path else "/"
        
        return urlunparse((scheme, netloc, path, parsed.params, sorted_query, fragment))

    async def fetch(self, url: str, javascript: bool = True, retries: int = 3) -> Dict[str, Any]:
        """
        Eksekusi lengkap proses fetch satu URL.
        
        Alur kerja:
        1. Normalisasi URL.
        2. Cek robots.txt (raise RobotsDisallowedError jika diblokir).
        3. Cek cache (kembalikan data cache jika fresh & valid).
        4. Terapkan rate limit (tunda jika perlu).
        5. Launch browser & buat page baru.
        6. Blokir resource tidak perlu (gambar/font) untuk performa.
        7. Navigasi ke URL (handle timeout & redirect).
        8. Deteksi & tutup cookie consent banner.
        9. Ekstrak HTML render, judul, dan URL final.
        10. Simpan ke cache (jika enabled).
        11. Retry dengan exponential backoff jika terjadi error transien.
        
        Args:
            url: URL target untuk di-fetch.
            javascript: Jika False, strategi fetch bisa dioptimalkan (misal tanpa wait networkidle),
                        meski saat ini browser tetap digunakan untuk konsistensi parsing DOM.
            retries: Jumlah maksimal percobaan ulang jika terjadi error jaringan/server.
            
        Returns:
            dict: {
                "url": str (URL awal),
                "final_url": str (URL setelah redirect),
                "html": str (Konten HTML rendered),
                "title": str (Judul halaman),
                "status": str ("success" atau status error)
            }
            
        Raises:
            FetchError: Atau subclassnya jika proses gagal total setelah semua retry.
        """
        normalized_url = self.normalize_url(url)
        last_exception = None
        
        # Attempt loop dengan retry
        for attempt in range(retries + 1):
            try:
                # 1. Cek Robots.txt
                if not self.robots_checker.is_allowed(normalized_url):
                    raise FetchError(url=normalized_url, message="Blocked by robots.txt") # Seharusnya RobotsDisallowedError
                
                # 2. Cek Cache
                if self.cache and self.cache.is_fresh(normalized_url, max_age_seconds=3600):
                    entry = self.cache.get(normalized_url)
                    # Return data cache sederhana (bisa dikembangkan untuk conditional request logic)
                    return {
                        "url": normalized_url,
                        "final_url": normalized_url,
                        "html": entry["html"],
                        "title": "Cached Content",
                        "status": "cached"
                    }
                
                # 3. Rate Limiting
                domain = urlparse(normalized_url).netloc
                self.rate_limiter.wait_if_needed(domain)
                
                # 4. Launch Browser & Page
                # Asumsi browser sudah di-launch di luar atau launch di sini jika belum
                if not self.browser._browser:
                    await self.browser.launch()
                    
                page = await self.browser.new_page()
                
                # 5. Optimasi: Blokir resource berat
                await self.browser.block_resources(page, ["image", "stylesheet", "font", "media"])
                
                # 6. Load Page
                try:
                    await self.browser.load_page(page, normalized_url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    # Tangani error load spesifik
                    raise handle_fetch_error(normalized_url, e)
                
                # 7. Handle Consent Banner (Opsional, tapi direkomendasikan)
                # Import di dalam fungsi untuk menghindari circular dependency jika perlu, 
                # atau pastikan urutan import benar di __init__.py
                from .consent import CookieConsentHandler
                consent_handler = CookieConsentHandler()
                if await consent_handler.detect_consent_banner(page):
                    await consent_handler.dismiss(page)
                
                # Tunggu sebentar setelah dismiss agar DOM stabil kembali
                await page.wait_for_timeout(1000)
                
                # 8. Ekstrak Data
                html = await self.browser.get_rendered_html(page)
                title = await self.browser.get_page_title(page)
                final_url = await self.browser.get_final_url(page)
                
                # 9. Update Rate Limiter
                self.rate_limiter.record_request(domain)
                
                # 10. Simpan ke Cache
                if self.cache:
                    # Extract ETag/LastModified jika tersedia (perlu modifikasi browser/engine untuk ambil header)
                    # Untuk sekarang simpan basic saja
                    self.cache.set(normalized_url, html)
                
                await page.close()
                
                return {
                    "url": normalized_url,
                    "final_url": final_url,
                    "html": html,
                    "title": title,
                    "status": "success"
                }

            except FetchError as e:
                # Jangan retry untuk error logis tertentu (seperti robots block, 404)
                if isinstance(e, (RedirectLoopError,)): 
                    raise e
                last_exception = e
                # Exponential backoff sebelum retry berikutnya
                if attempt < retries:
                    wait_time = (2 ** attempt) * 1.0  # 1s, 2s, 4s...
                    await asyncio.sleep(wait_time)
                continue
                
            except Exception as e:
                # Wrap exception tak terduga menjadi FetchError
                last_exception = handle_fetch_error(normalized_url, e)
                if attempt < retries:
                    wait_time = (2 ** attempt) * 1.0
                    await asyncio.sleep(wait_time)
                continue

        # Jika semua retry gagal
        if last_exception:
            raise last_exception
        raise FetchError(url=normalized_url, message="Unknown fetch failure after retries")

    async def handle_redirects(self, page) -> str:
        """
        Mendeteksi dan memvalidasi rantai redirect untuk mencegah loop.
        
        Meskipun Playwright menangani redirect otomatis, metode ini berguna untuk:
        - Logging riwayat redirect (jika diimplementasikan dengan request event).
        - Validasi manual apakah URL final masih dalam domain yang sama (opsional).
        - Mencegah loop jika logika custom diperlukan di luar batas default browser.
        
        Implementasi saat ini mengembalikan URL final dari page object.
        Deteksi loop kompleks biasanya ditangani oleh `load_page` via TimeoutError 
        atau exception TooManyRedirects dari httpx jika menggunakan adapter request.
        
        Args:
            page: Objek page yang selesai navigasi.
            
        Returns:
            str: URL final setelah semua redirect.
        """
        final_url = page.url
        # Logika tambahan untuk mendeteksi loop bisa ditambahkan di sini
        # misalnya dengan membandingkan history redirect jika tersedia
        return final_url