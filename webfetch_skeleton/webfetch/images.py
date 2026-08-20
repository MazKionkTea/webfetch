"""
images.py
Ekstraksi <img> dari konten, normalisasi src relatif->absolute,
dan pencarian caption terdekat (mis. <figcaption>).
"""


class ImageExtractor:
    """Ekstraksi & normalisasi gambar dalam main-content."""

    def extract_images(self, element, base_url: str) -> list:
        """Ambil semua <img> di dalam elemen."""
        # TODO
        pass

    def resolve_relative_src(self, src: str, base_url: str) -> str:
        # TODO: urljoin, sama seperti links.py
        pass

    def extract_caption(self, img_element) -> str:
        """Cari <figcaption> di dalam <figure> yang sama, atau alt text sebagai fallback."""
        # TODO
        pass
