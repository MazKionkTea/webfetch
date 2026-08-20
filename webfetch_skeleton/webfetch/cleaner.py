"""
cleaner.py
DOM cleaning tahap pertama: buang elemen yang hampir pasti bukan
konten (script/style/tracking) di satu halaman. Tidak seagresif
boilerplate.py — elemen yang ambigu (mis. <aside>) sengaja TIDAK
dibuang di sini, diserahkan ke scoring.py/content.py.
"""


class DOMCleaner:
    """Bersihkan elemen non-konten yang jelas dari DOM."""

    def remove_non_content_tags(self, soup):
        """Buang <script>, <style>, <noscript>."""
        # TODO
        pass

    def remove_tracking_elements(self, soup):
        """Buang elemen tracking/analytics (pixel, iframe tracking, dll)."""
        # TODO
        pass

    def remove_obvious_popups(self, soup):
        """Buang newsletter popup/modal yang jelas bukan konten (bukan cookie banner)."""
        # TODO: cookie banner ditangani terpisah oleh consent.py sebelum tahap ini
        pass

    def clean(self, soup):
        """Jalankan semua langkah di atas secara berurutan, kembalikan soup yang bersih."""
        # TODO
        pass
