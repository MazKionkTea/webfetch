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


class PaywallDetectedError(FetchError):
    """
    Exception yang diangkat ketika konten halaman terdeteksi berada di balik paywall atau require login.
    
    Deteksi ini dilakukan menggunakan heuristik di modul `content.py` yang menganalisis:
    - Keberadaan overlay/popup yang menutupi konten utama.
    - Rasio teks yang terlihat vs total teks dalam DOM.
    - Kata kunci umum pada tombol/teks (misal: "Subscribe", "Login to read", "Premium content").
    - Struktur HTML yang tidak biasa untuk artikel gratis (misal: konten dipotong tiba-tiba).
    
    Ketika exception ini dilempar, pipeline akan menghentikan proses ekstraksi lebih lanjut
    karena konten lengkap tidak dapat diakses tanpa interaksi pengguna atau langganan.
    
    Attributes:
        url (str): URL halaman yang terdeteksi memiliki paywall.
        message (str): Pesan error yang menjelaskan deteksi paywall.
    
    Catatan Implementasi:
        Logika deteksi spesifik terdapat di `content.py`. Modul ini hanya bertugas melempar
        exception setelah heuristik mengembalikan hasil positif.
    
    Contoh penggunaan:
        if is_paywall_detected(html_content):
            raise PaywallDetectedError(url=url)
    """
    
    def __init__(self, url: str):
        message = "Paywall or login requirement detected; full content inaccessible"
        super().__init__(url=url, message=message)


class RobotsDisallowedError(FetchError):
    """
    Exception yang diangkat ketika robots.txt dari domain target secara eksplisit melarang (Disallow)
    akses ke URL yang diminta oleh user-agent kita.
    
    Sebelum melakukan fetch konten, modul `robots.py` akan memeriksa aturan robots.txt.
    Jika URL target cocok dengan pola 'Disallow' untuk user-agent yang digunakan,
    exception ini akan dilempar untuk membatalkan proses fetch secara proaktif.
    
    Ini adalah implementasi kepatuhan terhadap standar Robots Exclusion Protocol (REP),
    memastikan crawler webfetch bertindak etis dan menghormati kebijakan pemilik situs.
    
    Attributes:
        url (str): URL yang dilarang diakses berdasarkan aturan robots.txt.
        message (str): Pesan error yang menjelaskan bahwa akses diblokir oleh robots.txt.
    
    Contoh penggunaan:
        if not robots_parser.can_fetch(user_agent, url):
            raise RobotsDisallowedError(url=url)
    """
    
    def __init__(self, url: str):
        message = "Access denied by robots.txt (URL is Disallowed for this user-agent)"
        super().__init__(url=url, message=message)


class UnsupportedContentTypeError(FetchError):
    """
    Exception yang diangkat ketika header Content-Type dari respons server tidak didukung
    oleh pipeline ekstraksi webfetch.
    
    Pipeline ini dirancang khusus untuk memproses konten teks terstruktur seperti:
    - `text/html` (halaman web standar)
    - `application/pdf` (dokumen PDF, jika fitur PDF diaktifkan)
    - `application/xhtml+xml` (XHTML)
    
    Jika server mengembalikan tipe konten lain (misal: `image/jpeg`, `video/mp4`,
    `application/octet-stream`, atau `application/json` untuk API), maka proses fetch
    akan dihentikan segera karena tidak ada parser yang sesuai untuk menangani format tersebut.
    
    Attributes:
        url (str): URL yang mengembalikan Content-Type tidak didukung.
        content_type (str): Nilai header Content-Type yang diterima dari server.
        message (str): Pesan error yang menyertakan detail tipe konten yang bermasalah.
    
    Contoh penggunaan:
        if content_type not in SUPPORTED_TYPES:
            raise UnsupportedContentTypeError(url=url, content_type=content_type)
    """
    
    def __init__(self, url: str, content_type: str):
        self.content_type = content_type
        message = f"Unsupported content type '{content_type}' (expected HTML or PDF)"
        super().__init__(url=url, message=message)


def handle_fetch_error(url: str, original_exception: Exception) -> FetchError:
    """
    Menerjemahkan exception mentah dari library eksternal (Playwright, httpx, requests)
    menjadi instance exception khusus yang didefinisikan dalam hierarki `errors.py`.
    
    Fungsi ini bertindak sebagai adapter error handling di lapisan paling atas proses fetch,
    memastikan bahwa seluruh pipeline hanya berurusan dengan exception lokal yang konsisten,
    tanpa perlu mengimpor atau bergantung langsung pada library jaringan tertentu.
    
    Logika Mapping:
    - TimeoutError / httpx.TimeoutException -> FetchTimeoutError
    - HTTPStatusError (404) -> NotFoundError
    - HTTPStatusError (403, 429) -> BlockedError
    - TooManyRedirects -> RedirectLoopError
    - Exception lain dengan pesan spesifik -> Dicek manual atau dibungkus FetchError umum
    
    Args:
        url (str): URL yang sedang diproses saat error terjadi.
        original_exception (Exception): Exception asli yang ditangkap dari blok try/except
                                        saat melakukan request HTTP atau interaksi browser.
    
    Returns:
        FetchError: Instance dari subclass FetchError yang paling representatif untuk
                    kondisi error tersebut, siap untuk dilempar (raise) kembali ke caller.
    
    Contoh penggunaan:
        try:
            response = await page.goto(url)
        except Exception as e:
            raise handle_fetch_error(url, e) from e
    """
    import httpx
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import Error as PlaywrightError

    # Handle Timeout
    if isinstance(original_exception, (PlaywrightTimeoutError, httpx.TimeoutException)):
        timeout_val = getattr(original_exception, 'timeout', 30.0)
        return FetchTimeoutError(url=url, timeout=timeout_val)

    # Handle HTTP Status Errors (httpx)
    if isinstance(original_exception, httpx.HTTPStatusError):
        status_code = original_exception.response.status_code
        if status_code == 404:
            return NotFoundError(url=url)
        elif status_code in (403, 429):
            return BlockedError(url=url, status_code=status_code)
        else:
            # Fallback untuk status code error lain
            return FetchError(url=url, message=f"HTTP Error {status_code}", original_exception=original_exception)

    # Handle Redirect Loop (Playwright/httpx)
    if isinstance(original_exception, httpx.TooManyRedirects) or \
       (isinstance(original_exception, PlaywrightError) and "redirect" in str(original_exception).lower()):
        return RedirectLoopError(url=url)

    # Handle Network/Connection Errors (Fallback ke BlockedError atau FetchError umum)
    if isinstance(original_exception, (httpx.NetworkError, httpx.ConnectError)):
        return FetchError(url=url, message="Network connection failed", original_exception=original_exception)

    # Default: Bungkus sebagai FetchError umum dengan pesan asli
    return FetchError(
        url=url,
        message=str(original_exception),
        original_exception=original_exception
    )