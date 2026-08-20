"""
errors.py
Taksonomi error untuk pipeline webfetch, supaya kegagalan fetch/
render/parse bisa ditangani secara spesifik oleh fetcher.py & cli.py.
"""

class FetchError(Exception):
    """
    Base exception untuk semua error terkait proses fetch dan ekstraksi konten web.
    
    Exception ini menjadi parent class bagi seluruh hierarki exception di modul errors.py,
    memastikan konsistensi handling error di seluruh pipeline webfetch.
    
    Attributes:
        url (str): URL yang sedang diproses saat error terjadi. Digunakan untuk logging,
                   debugging, dan memberikan konteks kepada pengguna CLI.
        message (str): Pesan deskriptif yang menjelaskan penyebab error secara spesifik.
        original_exception (Exception, optional): Exception asli dari library bawah (Playwright,
                                                  httpx, dll) yang memicu error ini. Disimpan
                                                  untuk keperluan debugging mendalam atau
                                                  re-raising jika diperlukan.
    
    Contoh penggunaan:
        try:
            # ... operasi fetch ...
        except SomeLibraryError as e:
            raise FetchError(url=url, message="Gagal mengambil konten", original_exception=e)
    """
    
    def __init__(self, url: str, message: str, original_exception: Exception = None):
        self.url = url
        self.message = message
        self.original_exception = original_exception
        super().__init__(f"[{url}] {message}")


class FetchTimeoutError(FetchError):
    """
    Exception yang diangkat ketika operasi fetch halaman web melebihi batas waktu (timeout) yang ditentukan.
    
    Terjadi ketika server tidak merespons dalam jangka waktu yang diharapkan, atau proses loading
    halaman (termasuk eksekusi JavaScript) memakan waktu terlalu lama. Ini membantu pengguna
    membedakan antara error jaringan biasa dengan masalah performa/latency.
    
    Attributes:
        url (str): URL yang gagal dimuat karena timeout.
        timeout (float): Nilai timeout dalam detik yang telah dilampaui.
        message (str): Pesan error yang menjelaskan konteks timeout.
    
    Contoh penggunaan:
        try:
            await fetcher.get(url, timeout=30.0)
        except TimeoutError as e:
            raise FetchTimeoutError(url=url, timeout=30.0)
    """
    
    def __init__(self, url: str, timeout: float):
        self.timeout = timeout
        message = f"Fetch timed out after {timeout}s"
        super().__init__(url=url, message=message)


class BlockedError(FetchError):
    """
    Exception yang diangkat ketika request ke URL diblokir oleh server target.
    
    Situasi ini umumnya terjadi karena:
    - Server mengembalikan status 403 Forbidden
    - Deteksi bot/crawler oleh mekanisme keamanan server (WAF, Cloudflare, dll)
    - Rate limiting yang memblokir IP atau user-agent tertentu
    - Kebijakan akses berbasis geolokasi atau header request
    
    Exception ini membantu pengguna membedakan antara halaman yang tidak ada (404)
    dengan halaman yang sengaja diblokir untuk crawler/automation.
    
    Attributes:
        url (str): URL yang diblokir aksesnya.
        status_code (int): Kode status HTTP yang diterima (biasanya 403, tapi bisa juga 429).
        message (str): Pesan error yang menyertakan konteks pemblokiran.
    
    Contoh penggunaan:
        if response.status_code == 403:
            raise BlockedError(url=url, status_code=403)
    """
    
    def __init__(self, url: str, status_code: int):
        self.status_code = status_code
        message = f"Request blocked with status {status_code} (possible bot detection or rate limit)"
        super().__init__(url=url, message=message)


class NotFoundError(FetchError):
    """
    Exception yang diangkat ketika server mengembalikan status 404 Not Found.
    
    Menandakan bahwa resource yang diminta tidak ditemukan di server target.
    Ini berbeda dengan error koneksi atau timeout; server merespons dengan benar
    tetapi menyatakan bahwa halaman tersebut tidak ada (mungkin telah dihapus,
    dipindahkan, atau URL salah ketik).
    
    Dalam konteks pipeline webfetch, error ini dapat digunakan untuk:
    - Mencatat URL yang broken dalam log audit.
    - Menghentikan proses ekstraksi lebih awal tanpa mencoba parsing konten kosong.
    - Memberikan feedback jelas kepada pengguna CLI bahwa URL tidak valid.
    
    Attributes:
        url (str): URL yang mengembalikan respons 404.
        message (str): Pesan error standar yang menjelaskan kondisi not found.
    
    Contoh penggunaan:
        if response.status_code == 404:
            raise NotFoundError(url=url)
    """
    
    def __init__(self, url: str):
        message = "Resource not found (HTTP 404)"
        super().__init__(url=url, message=message)


class RedirectLoopError(FetchError):
    """
    Exception yang diangkat ketika terdeteksi loop redirect (pengalihan) berulang tanpa akhir.
    
    Situasi ini terjadi ketika server mengarahkan request ke URL lain, yang kemudian
    mengarahkan kembali ke URL sebelumnya (atau membentuk siklus), sehingga proses
    fetch tidak pernah mencapai halaman tujuan final. Browser atau HTTP client biasanya
    memiliki batas maksimal redirect (misal: 10-20 hop) sebelum menghentikan proses
    dan melempar error.
    
    Dalam pipeline webfetch, deteksi dini loop redirect penting untuk:
    - Mencegah hang-nya proses fetch karena mencoba mengikuti redirect tak terbatas.
    - Mengidentifikasi konfigurasi server yang salah atau skema redirect yang bermasalah.
    - Memberikan laporan error yang jelas kepada pengguna alih-alih timeout umum.
    
    Attributes:
        url (str): URL awal atau URL di mana loop terdeteksi.
        message (str): Pesan error yang menjelaskan terjadinya redirect loop.
    
    Contoh penggunaan:
        if redirect_count > max_redirects:
            raise RedirectLoopError(url=start_url)
    """
    
    def __init__(self, url: str):
        message = "Redirect loop detected (too many redirects without reaching final destination)"
        super().__init__(url=url, message=message)


