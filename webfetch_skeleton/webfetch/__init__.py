"""
Paket webfetch.
Entry point publik: fungsi async fetch() untuk konversi satu URL
ke Markdown/format lain, dengan Document Model sebagai representasi antara.
"""

__version__ = "0.1.0"


async def fetch(url: str, output: str = None, javascript: bool = True,
                 extract_images: bool = True, extract_links: bool = True,
                 extract_metadata: bool = True):
    """
    Fungsi utama: jalankan seluruh pipeline (robots -> fetcher -> content_type
    -> metadata -> cleaner -> boilerplate -> scoring -> content -> pagination
    -> semantic -> links/images/tables/embeds -> model -> renderer).
    Detail orkestrasi ada di cli.py.
    """
    # TODO: panggil seluruh modul sesuai urutan di README, kembalikan objek
    # hasil (mis. namedtuple/dataclass Result dengan .markdown/.title/.metadata)
    pass
