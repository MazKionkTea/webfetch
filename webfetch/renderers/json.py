"""
json.py
Serialisasi Document Model langsung menjadi JSON — representasi
internal untuk pipeline RAG (lihat diskusi arsitektur: Markdown
untuk manusia/LLM, JSON untuk metadata/RAG).

Renderer ini memanfaatkan metode `to_dict()` yang sudah didefinisikan
dalam kelas `Document` (model.py) untuk melakukan konversi rekursif
struktur dataclass menjadi dictionary Python, lalu mengubahnya menjadi
string JSON yang terformat rapi.
"""

import json as json_lib
from typing import Any
from .base import BaseRenderer


class JSONRenderer(BaseRenderer):
    """
    Renderer untuk mengonversi objek Document menjadi string JSON.
    
    Output JSON dirancang agar:
    1. Mudah diparsing oleh mesin (RAG pipeline, database dokumen).
    2. Membawa seluruh metadata dan struktur block secara eksplisit.
    3. Menggunakan indentasi 2 spasi dan `ensure_ascii=False` agar karakter
       non-ASCII (seperti UTF-8: emoji, aksara non-Latin) tetap terbaca jelas.
    """

    def render(self, document: Any) -> str:
        """
        Serialisasi dokumen menjadi string JSON.
        
        Args:
            document: Objek instance dari `model.Document`.
                      Harus memiliki metode `to_dict()` yang mengembalikan dictionary.
        
        Returns:
            str: Representasi JSON dari dokumen.
            
        Raises:
            AttributeError: Jika objek document tidak memiliki metode `to_dict`.
            TypeError: Jika struktur dokumen tidak dapat diserialisasi ke JSON.
        """
        if not hasattr(document, 'to_dict'):
            raise AttributeError("Objek document harus memiliki metode 'to_dict()'")
            
        data_dict = document.to_dict()
        
        return json_lib.dumps(
            data_dict,
            ensure_ascii=False,
            indent=2,
            default=str  # Fallback untuk tipe data non-standar (misal: datetime/date)
        )