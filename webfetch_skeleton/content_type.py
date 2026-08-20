"""
content_type.py
Deteksi Content-Type hasil fetch dan pencabangan alur: HTML lanjut
ke pipeline normal, PDF didelegasikan ke pipeline pdf2markdown,
tipe lain (gambar/video) ditangani sebagai block tunggal atau ditolak.
"""


def detect_content_type(headers: dict, url: str) -> str:
    """Tentukan tipe konten dari header HTTP (fallback ke ekstensi URL jika perlu)."""
    # TODO: cek header 'content-type', fallback ke suffix .pdf/.jpg/dll pada url
    pass


class ContentDispatcher:
    """Arahkan hasil fetch ke pipeline yang sesuai berdasarkan content type."""

    def dispatch(self, content_type: str, raw_content, url: str):
        """
        Kembalikan salah satu:
        - lanjut ke pipeline HTML normal (cleaner.py dst)
        - delegasi ke pdf2markdown.convert() untuk PDF
        - bentuk ImageBlock tunggal untuk gambar langsung
        - lempar UnsupportedContentTypeError untuk tipe lain
        """
        # TODO: percabangan berdasarkan content_type
        pass
