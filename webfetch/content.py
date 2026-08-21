"""
content.py
Deteksi main content halaman, dengan prioritas heuristik:
<article> -> <main> -> [role="main"] -> hasil scoring.py ->
fallback Readability-style extraction.
"""


from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup, Tag

# Import lokal untuk scorer yang sudah dibuat
from .scoring import ContentScorer

class MainContentDetector:
    """
    Detektor konten utama (Main Content) yang menggunakan strategi berlapis (cascading).
    
    Alur deteksi prioritas:
    1. **Semantic Tags**: Mencari tag HTML5 eksplisit (`<article>`, `<main>`, `[role="main"]`).
       Ini adalah sinyal terkuat dan paling cepat.
    2. **Heuristic Scoring**: Jika tidak ada tag semantik jelas, gunakan `ContentScorer`
       untuk menilai semua kandidat container berdasarkan kepadatan teks, link, dan kelas CSS.
    3. **Readability Fallback**: Jika scoring gagal memberikan hasil yakin, gunakan library
       eksternal (seperti `readability-lxml`) sebagai last resort untuk ekstraksi robust.
    
    Attributes:
        scorer: Instance `ContentScorer` untuk evaluasi heuristik.
    
    Returns (detect):
        dict: {
            "element": Tag | None,      # Elemen DOM yang terdeteksi sebagai konten utama
            "confidence": str,          # 'HIGH', 'MEDIUM', 'LOW' (dari enum ConfidenceLevel)
            "method_used": str          # 'semantic', 'scoring', atau 'readability'
        }
    """

    def __init__(self, scorer: ContentScorer = None):
        """
        Inisialisasi detector dengan instance scorer opsional.
        Jika tidak diberikan, instance baru `ContentScorer` akan dibuat.
        """
        self.scorer = scorer if scorer is not None else ContentScorer()

    def detect_via_semantic_tags(self, soup: BeautifulSoup) -> Optional[Tag]:
        """
        Mencari elemen konten utama berdasarkan tag semantik HTML5 standar.
        
        Prioritas pencarian:
        1. Tag `<article>` (paling spesifik untuk konten mandiri).
        2. Atribut `role="main"` (standar aksesibilitas WAI-ARIA).
        3. Tag `<main>` (wrapper konten utama dokumen).
        
        Args:
            soup: Objek BeautifulSoup dokumen.
            
        Returns:
            Tag | None: Elemen semantik pertama yang ditemukan, atau None.
        """
        # 1. Cari <article>
        article = soup.find('article')
        if article:
            return article
            
        # 2. Cari [role="main"]
        main_role = soup.find(attrs={"role": "main"})
        if main_role:
            return main_role
            
        # 3. Cari <main>
        main_tag = soup.find('main')
        if main_tag:
            return main_tag
            
        return None

    def detect_via_scoring(self, soup: BeautifulSoup) -> Optional[Tag]:
        """
        Menggunakan algoritma scoring heuristik untuk menemukan kandidat terbaik.
        
        Memanggil `ContentScorer.score_all_candidates()` dan memilih elemen dengan skor tertinggi.
        Hanya mengembalikan elemen jika skornya positif (di atas ambang noise).
        
        Args:
            soup: Objek BeautifulSoup dokumen.
            
        Returns:
            Tag | None: Elemen dengan skor tertinggi, atau None jika tidak ada kandidat layak.
        """
        scores = self.scorer.score_all_candidates(soup)
        best_candidate = self.scorer.pick_best_candidate(scores)
        return best_candidate

    def detect_via_readability(self, html: str) -> Optional[str]:
        """
        Fallback menggunakan library `readability-lxml` untuk ekstraksi konten robust.
        
        Metode ini memproses string HTML mentah (bukan Soup) karena library readability
        bekerja lebih efisien pada parser lxml asli. Mengembalikan HTML片段 dari konten utama
        yang sudah dibersihkan oleh library tersebut.
        
        Catatan:
            Memerlukan instalasi library eksternal: `pip install readability-lxml`.
            Jika library tidak terinstal, metode ini mengembalikan None.
        
        Args:
            html: String HTML mentah halaman.
            
        Returns:
            str | None: String HTML konten utama hasil ekstraksi, atau None jika gagal/impor error.
        """
        try:
            from readability import Document as ReadabilityDocument
            doc = ReadabilityDocument(html)
            # .summary() mengembalikan HTML konten utama yang sudah dibersihkan
            return doc.summary()
        except ImportError:
            # Library tidak terinstal, skip fallback ini
            return None
        except Exception:
            # Error saat parsing (misal HTML rusak parah), skip
            return None

    def detect(self, soup: BeautifulSoup, html: str) -> Dict[str, Any]:
        """
        Menjalankan pipeline deteksi berlapis dengan prioritas: Semantic -> Scoring -> Readability.
        
        Alur eksekusi:
        1. Coba deteksi via tag semantik. Jika berhasil -> Return dengan confidence HIGH.
        2. Jika gagal, coba via scoring heuristik. Jika skor cukup tinggi -> Return MEDIUM.
        3. Jika gagal lagi, coba via library readability. Jika berhasil -> Return LOW.
        4. Jika semua gagal -> Return None dengan confidence LOW.
        
        Args:
            soup: Objek BeautifulSoup dokumen (untuk metode 1 & 2).
            html: String HTML mentah dokumen (untuk metode 3).
            
        Returns:
            dict: Hasil deteksi terstruktur:
                  {
                      "element": Tag | None,       # Elemen BeautifulSoup (jika metode 1/2)
                      "html_content": str | None,  # String HTML (jika metode 3/readability)
                      "confidence": str,           # 'HIGH', 'MEDIUM', 'LOW'
                      "method_used": str           # 'semantic', 'scoring', 'readability', 'none'
                  }
        """
        result = {
            "element": None,
            "html_content": None,
            "confidence": "LOW",
            "method_used": "none"
        }

        # --- Langkah 1: Semantic Tags (Prioritas Tertinggi) ---
        semantic_elem = self.detect_via_semantic_tags(soup)
        if semantic_elem:
            result["element"] = semantic_elem
            result["confidence"] = "HIGH"
            result["method_used"] = "semantic"
            return result

        # --- Langkah 2: Heuristic Scoring ---
        scored_elem = self.detect_via_scoring(soup)
        if scored_elem:
            # Cek skor elemen ini untuk memastikan kualitas (opsional, bisa langsung accept)
            score_val = self.scorer.score_element(scored_elem)
            if score_val > 0:
                result["element"] = scored_elem
                result["confidence"] = "MEDIUM"
                result["method_used"] = "scoring"
                return result

        # --- Langkah 3: Readability Fallback ---
        readability_html = self.detect_via_readability(html)
        if readability_html:
            result["html_content"] = readability_html
            result["confidence"] = "LOW" # Readability kadang terlalu agresif membersihkan
            result["method_used"] = "readability"
            return result

        # --- Gagal Total ---
        return result