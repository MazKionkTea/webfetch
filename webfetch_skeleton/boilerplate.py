"""
boilerplate.py
Deteksi elemen berulang lintas HALAMAN (bukan cuma satu halaman),
analog headers.py di pdf2markdown. Berguna saat webfetch dipakai untuk
crawl banyak halaman dari domain yang sama — nav/sidebar/footer yang
identik di semua halaman bisa dikenali lebih akurat lewat pengulangan,
bukan cuma heuristic per-halaman.
"""


class BoilerplateLearner:
    """Pelajari pola elemen berulang dari beberapa sample halaman satu domain."""

    def __init__(self):
        self._domain_samples = {}  # TODO: dict domain -> list of cleaned soup/html

    def collect_page_samples(self, domain: str, cleaned_html: str) -> None:
        """Simpan hasil cleaner.py dari satu halaman untuk domain ini."""
        # TODO
        pass

    def find_repeated_blocks(self, domain: str) -> list:
        """
        Bandingkan sample halaman yang terkumpul untuk domain ini,
        cari fragmen HTML/teks yang muncul identik di banyak halaman.
        """
        # TODO: mirip find_repeated_text di pdf2markdown/headers.py,
        # tapi berbasis structural/text similarity antar sample
        pass

    def strip_boilerplate(self, soup, repeated_blocks: list):
        """Hapus elemen yang cocok dengan pola boilerplate hasil find_repeated_blocks()."""
        # TODO
        pass
