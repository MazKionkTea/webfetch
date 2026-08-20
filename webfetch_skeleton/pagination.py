"""
pagination.py
Deteksi & agregasi artikel yang terpecah jadi beberapa halaman
(?page=1,2,3) maupun infinite scroll/"load more". Analog
merge_cross_page_tables di pdf2markdown, tapi untuk artikel web.
"""


class PaginationHandler:
    """Deteksi & gabungkan konten multi-halaman jadi satu Document."""

    def detect_pagination_links(self, soup, base_url: str) -> list:
        """Cari link 'next page'/nomor halaman berikutnya."""
        # TODO: pola umum rel="next", teks "Next"/"Halaman Berikutnya", dll
        pass

    async def detect_infinite_scroll(self, page) -> bool:
        """Deteksi apakah halaman memuat konten baru saat discroll (lazy-load)."""
        # TODO: bandingkan tinggi DOM sebelum & sesudah scroll simulasi
        pass

    async def trigger_load_more(self, page) -> bool:
        """Klik tombol 'load more' jika ada, return True jika konten baru dimuat."""
        # TODO
        pass

    def aggregate_multi_page_content(self, contents: list) -> list:
        """Gabungkan block dari beberapa halaman jadi satu urutan block yang koheren."""
        # TODO: hati-hati jangan duplikasi heading/judul yang berulang tiap halaman
        pass
