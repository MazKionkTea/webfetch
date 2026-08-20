"""
robots.py
Crawl politeness: parsing robots.txt dan rate limiting per domain,
dijalankan sebelum browser.py membuka halaman.
"""

import urllib.robotparser
import httpx
from typing import Optional
from urllib.parse import urlparse

class RobotsChecker:
    """
    Checker untuk memverifikasi izin akses URL berdasarkan aturan robots.txt domain target.
    
    Kelas ini mengimplementasikan Robots Exclusion Protocol (REP) standar dengan fitur:
    - Cache per-domain untuk menghindari request berulang ke /robots.txt
    - Parsing otomatis menggunakan urllib.robotparser
    - Support untuk Crawl-Delay directive (umum di Bingbot, Yandex, dll)
    - Fallback aman jika robots.txt tidak ditemukan (asumsi: allowed)
    
    Attributes:
        user_agent (str): User-agent string yang digunakan untuk mencocokkan aturan.
                          Contoh: 'webfetch/1.0' atau 'Mozilla/5.0 ...'
    
    Contoh penggunaan:
        checker = RobotsChecker(user_agent="webfetch/1.0")
        if not checker.is_allowed("https://example.com/private"):
            raise RobotsDisallowedError(url="https://example.com/private")
    """

    def __init__(self, user_agent: str):
        """
        Inisialisasi checker dengan user-agent spesifik.
        
        Args:
            user_agent: String user-agent yang akan dicocokkan dengan aturan 'User-agent' 
                        di file robots.txt. Gunakan nama spesifik tool Anda untuk etika crawling.
        """
        self.user_agent = user_agent
        self._cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    def _get_domain(self, url: str) -> str:
        """Ekstrak base domain (scheme + host) dari URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _get_parser(self, domain: str) -> urllib.robotparser.RobotFileParser:
        """Ambil parser dari cache atau buat baru dengan fetch robots.txt."""
        if domain not in self._cache:
            parser = urllib.robotparser.RobotFileParser()
            robots_url = f"{domain}/robots.txt"
            try:
                # Menggunakan httpx sync client sederhana untuk fetch awal
                # Dalam implementasi async penuh, ini bisa diganti dengan httpx.AsyncClient
                with httpx.Client(timeout=5.0) as client:
                    response = client.get(robots_url)
                    if response.status_code == 200:
                        parser.parse(response.text.splitlines())
                    else:
                        # Jika 404 atau error, anggap kosong (semua diizinkan)
                        parser.parse([""])
            except Exception:
                # Jika network error saat fetch robots.txt, anggap kosong (fail-safe)
                parser.parse([""])
            
            self._cache[domain] = parser
        
        return self._cache[domain]

    def is_allowed(self, url: str) -> bool:
        """
        Periksa apakah URL tertentu diizinkan untuk diakses oleh user-agent ini.
        
        Metode ini akan:
        1. Mengambil atau membuat parser robots.txt untuk domain URL tersebut.
        2. Memeriksa aturan 'Disallow' dan 'Allow' terhadap path URL.
        3. Mengembalikan True jika diizinkan, False jika diblokir.
        
        Catatan: Jika robots.txt tidak ada atau error saat fetch, metode ini mengembalikan
        True (prinsip fail-safe: jika tidak ada larangan eksplisit, maka diizinkan).
        
        Args:
            url: URL lengkap yang akan diperiksa izin aksesnya.
        
        Returns:
            bool: True jika akses diizinkan, False jika diblokir oleh robots.txt.
        """
        domain = self._get_domain(url)
        parser = self._get_parser(domain)
        return parser.can_fetch(self.user_agent, url)

    def get_crawl_delay(self, url: str) -> Optional[float]:
        """
        Ambil nilai Crawl-Delay yang ditentukan dalam robots.txt untuk domain ini.
        
        Crawl-Delay adalah direktif non-standar (de facto) yang meminta crawler
        untuk menunggu sejumlah detik antar request ke domain yang sama.
        Umum digunakan oleh mesin pencari seperti Bing dan Yandex.
        
        Catatan: urllib.robotparser tidak mendukung Crawl-Delay secara native di semua versi Python.
        Implementasi ini mencoba mengekstraknya manual jika tersedia, atau None jika tidak ada.
        
        Args:
            url: URL salah satu halaman di domain tersebut (untuk identifikasi domain).
        
        Returns:
            float | None: Nilai delay dalam detik, atau None jika tidak didefinisikan.
        """
        domain = self._get_domain(url)
        parser = self._get_parser(domain)
        
        # urllib.robotparser tidak punya method publik untuk crawl-delay
        # Kita akses atribut internal jika ada (tergantung implementasi Python)
        if hasattr(parser, '_crawl_delay'):
            return parser._crawl_delay
        
        # Fallback: parsing manual dari teks asli jika diperlukan (opsional, kompleks)
        # Untuk sekarang, kembalikan None jika tidak tersedia via library standar
        return None


import time
from typing import Dict

class RateLimiter:
    """
    Rate limiter untuk membatasi kecepatan request HTTP per domain.
    
    Kelas ini mencegah flooding server target dengan memastikan adanya jeda waktu
    (delay) minimum antara dua request berturut-turut ke domain yang sama.
    Delay ini bisa bersifat default (global) atau spesifik per domain jika diambil
    dari directive `Crawl-Delay` di robots.txt.
    
    Mekanisme kerja:
    1. Menyimpan timestamp request terakhir untuk setiap domain.
    2. Sebelum request baru, menghitung selisih waktu dengan request terakhir.
    3. Jika selisih < delay yang ditentukan, lakukan sleep selama sisa waktu.
    
    Attributes:
        default_delay (float): Waktu tunggu default dalam detik antar request 
                               jika tidak ada aturan spesifik dari robots.txt.
    
    Contoh penggunaan:
        limiter = RateLimiter(default_delay=1.0)
        
        # Sebelum fetch
        limiter.wait_if_needed("example.com")
        
        # Lakukan request...
        
        # Setelah request berhasil dikirim
        limiter.record_request("example.com")
    """

    def __init__(self, default_delay: float = 1.0):
        """
        Inisialisasi rate limiter dengan delay default.
        
        Args:
            default_delay: Jumlah detik minimal tunggu antar request ke domain yang sama.
                           Nilai aman umum adalah 1.0 detik.
        """
        self.default_delay = default_delay
        self._last_request_time: Dict[str, float] = {}

    def wait_if_needed(self, domain: str, specific_delay: float = None) -> None:
        """
        Tunda eksekusi jika waktu sejak request terakhir ke domain ini belum mencapai batas delay.
        
        Metode ini harus dipanggil *sebelum* melakukan request HTTP. Jika waktu yang berlalu
        sejak request terakhir kurang dari `delay`, metode ini akan memblokir thread saat ini
        (blocking sleep) sampai batas waktu terpenuhi.
        
        Args:
            domain: Nama domain target (misal: 'example.com').
            specific_delay: Override untuk delay default. Bisa digunakan jika nilai Crawl-Delay
                            spesifik ditemukan di robots.txt domain tersebut. Jika None, gunakan default_delay.
        """
        delay = specific_delay if specific_delay is not None else self.default_delay
        
        if domain in self._last_request_time:
            last_time = self._last_request_time[domain]
            now = time.time()
            elapsed = now - last_time
            
            if elapsed < delay:
                sleep_time = delay - elapsed
                time.sleep(sleep_time)

    def record_request(self, domain: str) -> None:
        """
        Catat timestamp saat request dikirim ke domain tertentu.
        
        Metode ini harus dipanggil segera *setelah* request HTTP berhasil dikirim
        (bukan setelah respons diterima, agar waktu tunggu mencakup durasi network latency).
        
        Args:
            domain: Nama domain target yang baru saja di-request.
        """
        self._last_request_time[domain] = time.time()