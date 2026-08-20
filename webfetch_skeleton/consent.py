"""
consent.py
Deteksi & dismiss cookie consent banner / popup secara aktif.
Beberapa situs mengunci konten sampai banner ini di-klik "accept",
jadi tidak cukup hanya dihapus dari DOM setelah render (lihat cleaner.py).
"""


class CookieConsentHandler:
    """Deteksi & klik tombol accept pada cookie/consent banner."""

    # TODO: daftar selector umum (OneTrust, Cookiebot, custom banner, dll)
    COMMON_SELECTORS = []

    async def detect_consent_banner(self, page) -> bool:
        """Cek apakah ada consent banner yang terlihat di halaman."""
        # TODO: cek visibility elemen dari COMMON_SELECTORS
        pass

    async def dismiss(self, page) -> bool:
        """Klik tombol accept/dismiss jika banner ditemukan. Return True jika berhasil."""
        # TODO: coba tiap selector, klik yang pertama cocok & visible
        pass
