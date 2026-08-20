"""
errors.py
Taksonomi error untuk pipeline webfetch, supaya kegagalan fetch/
render/parse bisa ditangani secara spesifik oleh fetcher.py & cli.py.
"""


class FetchError(Exception):
    """Base exception untuk semua error terkait proses fetch/ekstraksi."""
    # TODO: simpan url & pesan asli
    pass


class FetchTimeoutError(FetchError):
    """Halaman gagal dimuat dalam batas waktu yang ditentukan."""
    pass


class BlockedError(FetchError):
    """Request diblokir (403, deteksi bot, rate limit server)."""
    pass


class NotFoundError(FetchError):
    """URL mengembalikan 404 / halaman tidak ditemukan."""
    pass


class RedirectLoopError(FetchError):
    """Terjadi redirect berulang tanpa akhir."""
    pass


class PaywallDetectedError(FetchError):
    """Konten terdeteksi berada di balik paywall/login."""
    # TODO: heuristik deteksi ada di content.py, exception ini dilempar dari sana
    pass


class RobotsDisallowedError(FetchError):
    """robots.txt melarang akses ke URL ini."""
    pass


class UnsupportedContentTypeError(FetchError):
    """Content-Type tidak didukung pipeline ini (bukan HTML/PDF yang dikenali)."""
    pass


def handle_fetch_error(url: str, original_exception: Exception):
    """Terjemahkan exception mentah (Playwright/httpx) menjadi exception khusus di atas."""
    # TODO: mapping berdasarkan tipe/status code dari original_exception
    pass
