"""
base.py
Interface dasar untuk semua renderer webfetch, sama polanya
dengan renderers/base.py di pdf2markdown.

Modul ini mendefinisikan kontrak abstrak yang wajib dipenuhi oleh
setiap implementasi renderer spesifik (Markdown, JSON, TXT).
Hal ini memastikan konsistensi input (Document Model) dan output (String),
serta memudahkan penambahan format renderer baru di masa depan tanpa
mengubah logik inti pipeline.
"""

from abc import ABC, abstractmethod
from typing import Any

# Forward reference untuk menghindari circular import jika model belum dimuat
# Tipe dokumen yang diharapkan adalah instance dari model.Document
class BaseRenderer(ABC):
    """
    Kelas dasar abstrak untuk semua renderer output webfetch.
    
    Setiap renderer bertanggung jawab untuk:
    1. Menerima objek `Document` yang sudah terisi penuh dengan metadata dan blocks.
    2. Melakukan iterasi pada blocks tersebut.
    3. Mengonversi setiap block menjadi representasi teks sesuai format target.
    4. Menggabungkan hasilnya menjadi satu string utuh yang siap ditampilkan atau disimpan.
    
    Contoh Implementasi:
    - MarkdownRenderer: Mengonversi HeadingBlock jadi '# Judul', TableBlock jadi tabel MD, dll.
    - JSONRenderer: Menserialisasi seluruh objek Document jadi string JSON.
    - TextRenderer: Mengekstrak hanya teks bersih tanpa formatting.
    """

    @abstractmethod
    def render(self, document: Any) -> str:
        """
        Mengonversi objek Document Model menjadi string output final.
        
        Metode ini adalah titik masuk utama bagi CLI atau API untuk mendapatkan
        hasil ekstraksi dalam format yang diinginkan.
        
        Args:
            document (model.Document): Objek dokumen hasil ekstraksi yang berisi
                                       metadata dan daftar blocks konten.
        
        Returns:
            str: Representasi string lengkap dari dokumen dalam format spesifik
                 renderer (misal: string Markdown, string JSON, atau plain text).
        
        Raises:
            NotImplementedError: Jika metode ini tidak diimplementasikan oleh subclass.
        """
        pass