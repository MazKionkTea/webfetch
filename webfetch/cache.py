"""
cache.py
Caching & conditional fetch: hindari fetch ulang URL yang sama
memakai ETag/Last-Modified, plus penyimpanan hasil sementara.
"""


import time
from typing import Optional, Dict, Any

class FetchCache:
    """
    Cache hasil fetch per URL dengan dukungan conditional request (ETag/Last-Modified).
    
    Kelas ini berfungsi sebagai lapisan optimasi untuk menghindari fetch berulang
    ke URL yang sama dalam jangka waktu tertentu. Mendukung dua strategi:
    1. Freshness Check: Menggunakan timestamp untuk menentukan apakah data masih valid.
    2. Conditional Request: Menyimpan ETag dan Last-Modified untuk dikirim kembali
       ke server (via header If-None-Match/If-Modified-Since), memungkinkan server
       merespons dengan 304 Not Modified jika konten belum berubah.
    
    Attributes:
        backend (dict): Penyimpanan data cache. Defaultnya adalah dictionary in-memory.
                        Dapat diganti dengan database (SQLite/Redis) untuk persistensi.
    
    Struktur Data Entry Cache:
        {
            "html": str,              # Konten HTML hasil fetch
            "etag": str | None,       // Value header ETag dari server
            "last_modified": str | None, // Value header Last-Modified dari server
            "timestamp": float        // Waktu fetch dilakukan (unix time)
        }
    """

    def __init__(self, backend: Optional[Dict[str, Any]] = None):
        """
        Inisialisasi cache dengan backend penyimpanan.
        
        Args:
            backend: Objek penyimpanan custom. Jika None, menggunakan dictionary kosong
                     yang berjalan di RAM (volatile, hilang saat proses berhenti).
        """
        self.backend = backend if backend is not None else {}

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Mengambil entri cache lengkap untuk URL tertentu.
        
        Args:
            url: URL kunci lookup cache.
            
        Returns:
            dict | None: Dictionary berisi html, etag, last_modified, timestamp jika ada.
                         None jika URL tidak ditemukan di cache.
        """
        return self.backend.get(url)

    def set(self, url: str, html: str, etag: Optional[str] = None, 
            last_modified: Optional[str] = None) -> None:
        """
        Menyimpan hasil fetch ke dalam cache.
        
        Args:
            url: URL sebagai kunci unik.
            html: Konten HTML mentah yang berhasil di-fetch.
            etag: Nilai header 'ETag' dari respons server (opsional).
            last_modified: Nilai header 'Last-Modified' dari respons server (opsional).
        """
        self.backend[url] = {
            "html": html,
            "etag": etag,
            "last_modified": last_modified,
            "timestamp": time.time()
        }

    def is_fresh(self, url: str, max_age_seconds: int = 3600) -> bool:
        """
        Memeriksa apakah entri cache untuk URL masih dianggap segar (belum kadaluarsa).
        
        Args:
            url: URL yang diperiksa.
            max_age_seconds: Batas usia maksimal cache dalam detik. Default 1 jam (3600s).
            
        Returns:
            bool: True jika data ada dan usianya < max_age_seconds, False sebaliknya.
        """
        entry = self.get(url)
        if not entry:
            return False
        
        age = time.time() - entry["timestamp"]
        return age < max_age_seconds

    def build_conditional_headers(self, url: str) -> Dict[str, str]:
        """
        Membangun header HTTP kondisional berdasarkan data cache yang tersimpan.
        
        Header ini digunakan dalam request berikutnya ke URL yang sama untuk memanfaatkan
        mekanisme caching server (HTTP 304 Not Modified).
        
        Args:
            url: URL target request.
            
        Returns:
            dict: Dictionary header HTTP yang siap digabung ke request headers.
                  Berisi 'If-None-Match' (dari ETag) dan/atau 'If-Modified-Since'
                  (dari Last-Modified) jika tersedia di cache. Kosong jika tidak ada data.
        """
        entry = self.get(url)
        if not entry:
            return {}
        
        headers = {}
        
        if entry.get("etag"):
            headers["If-None-Match"] = entry["etag"]
            
        if entry.get("last_modified"):
            headers["If-Modified-Since"] = entry["last_modified"]
            
        return headers