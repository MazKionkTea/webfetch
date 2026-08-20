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


