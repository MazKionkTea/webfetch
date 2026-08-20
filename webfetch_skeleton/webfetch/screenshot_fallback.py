"""
screenshot_fallback.py
Fallback visual untuk halaman yang gagal diekstrak lewat DOM
(SPA dengan canvas rendering, shadow DOM berat, dll). Analog
ocr.py di pdf2markdown — dijalankan hanya saat deteksi konten
via DOM menghasilkan confidence rendah.
"""


class ScreenshotFallback:
    """Fallback berbasis screenshot saat ekstraksi DOM gagal/tidak yakin."""

    def should_fallback(self, detection_result: dict) -> bool:
        """Tentukan apakah perlu fallback, berdasarkan confidence dari content.py."""
        # TODO: mis. confidence == LOW atau elemen main-content tidak ditemukan sama sekali
        pass

    async def capture_screenshot(self, page) -> bytes:
        """Ambil screenshot full-page."""
        # TODO: page.screenshot(full_page=True)
        pass

    def describe_visual_content(self, screenshot: bytes) -> str:
        """
        Hasilkan deskripsi/placeholder dari screenshot ketika ekstraksi teks
        gagal total (mis. lewat model vision terpisah, di luar scope modul ini).
        """
        # TODO: untuk versi awal, cukup simpan screenshot + tandai butuh review manual
        pass
