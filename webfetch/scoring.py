"""
scoring.py
Content scoring: beri skor tiap elemen kandidat main-content
berdasarkan kepadatan teks, jumlah paragraf, heading, gambar
(positif) vs jumlah link, navigasi, tanda iklan/footer (negatif).
"""


from bs4 import BeautifulSoup, Tag
from typing import Dict, List, Optional, Tuple

class ContentScorer:
    """
    Algoritma scoring heuristik untuk menentukan elemen DOM mana yang paling mungkin
    merupakan konten utama (main content) dari sebuah halaman web.
    
    Prinsip kerja:
    1. Menetapkan bobot positif untuk fitur yang mengindikasikan konten berkualitas 
       (misal: kepadatan teks, tag semantik artikel, keberadaan heading).
    2. Menetapkan bobot negatif (penalti) untuk fitur yang mengindikasikan noise 
       (misal: kepadatan link tinggi, kelas iklan, navigasi, footer).
    3. Menghitung skor total untuk setiap kandidat elemen container (div, section, article).
    4. Memilih elemen dengan skor tertinggi sebagai akar konten utama.
    
    Pendekatan ini terinspirasi oleh algoritma klasik seperti Readability dan Drummond.
    
    Konstanta Bobot (Weight):
        - Positif: Mendorong elemen dipilih sebagai konten.
        - Negatif: Mengurangi peluang elemen dipilih (penalti).
    """

    # --- Bobot Positif (Indikator Konten) ---
    WEIGHT_TEXT_LENGTH = 0.5       # Skor per karakter teks (skala linear)
    WEIGHT_PARAGRAPH = 15.0        # Keberadaan tag <p>
    WEIGHT_HEADING = 20.0          # Keberadaan <h1>-<h6>
    WEIGHT_IMAGE_WITH_ALT = 5.0    # Gambar dengan alt text (indikasi kontekstual)
    WEIGHT_IMAGE_NO_ALT = -2.0     # Gambar tanpa alt (cenderung dekoratif/iklan)
    WEIGHT_LIST_ITEM = 2.0         # Item list (<li>)
    WEIGHT_DATA_TABLE = 10.0       # Tabel data (bukan layout)
    WEIGHT_SEMANTIC_ARTICLE = 30.0 # Tag <article>
    WEIGHT_SEMANTIC_SECTION = 15.0 # Tag <section>
    WEIGHT_SEMANTIC_MAIN = 40.0    # Tag <main>

    # --- Bobot Negatif (Penalti Noise) ---
    PENALTY_LINK_DENSITY = -20.0   # Jika rasio teks-link > threshold
    PENALTY_NAV_TAG = -30.0        # Tag <nav>
    PENALTY_FOOTER_TAG = -25.0     # Tag <footer>
    PENALTY_ASIDE_TAG = -15.0      # Tag <aside> (sidebar)
    PENALTY_AD_PATTERN = -50.0     # Class/ID mengandung 'ad', 'banner', 'sponsor'
    PENALTY_SHARE_PATTERN = -15.0  # Class/ID mengandung 'share', 'social'
    PENALTY_SHORT_CONTENT = -10.0  # Konten terlalu pendek (< 50 char)

    # --- Threshold ---
    MIN_TEXT_LENGTH = 50           # Panjang minimal teks untuk dianggap konten serius
    LINK_DENSITY_THRESHOLD = 0.5   # Batas rasio panjang teks link terhadap total teks

    def _get_text_stats(self, element: Tag) -> Tuple[int, int]:
        """
        Menghitung statistik teks dasar: total panjang teks dan panjang teks dalam link.
        
        Returns:
            tuple: (total_text_length, link_text_length)
        """
        all_text = element.get_text(separator=' ', strip=True)
        total_len = len(all_text)
        
        link_text_len = 0
        for a in element.find_all('a'):
            link_text_len += len(a.get_text(strip=True))
            
        return total_len, link_text_len

    def _check_class_patterns(self, element: Tag, patterns: List[str]) -> bool:
        """Cek apakah class atau ID elemen mengandung pola tertentu."""
        class_str = " ".join(element.get('class', []))
        id_str = element.get('id', '')
        combined = f"{class_str} {id_str}".lower()
        
        return any(p in combined for p in patterns)

    def score_element(self, element: Tag) -> float:
        """
        Hitung skor kelayakan satu elemen sebagai konten utama.
        
        Logika scoring:
        1. Base score dari panjang teks.
        2. Bonus dari tag semantik dan struktur (p, h, article).
        3. Penalti dari kepadatan link dan pola iklan/navigasi.
        
        Args:
            element: Objek Tag BeautifulSoup.
            
        Returns:
            float: Skor akhir elemen.
        """
        if not isinstance(element, Tag):
            return 0.0
            
        score = 0.0
        text_len, link_text_len = self._get_text_stats(element)
        
        # 1. Skor dasar dari panjang teks
        score += text_len * self.WEIGHT_TEXT_LENGTH
        
        # Penalti jika terlalu pendek
        if text_len < self.MIN_TEXT_LENGTH:
            score += self.PENALTY_SHORT_CONTENT

        # 2. Bonus Struktur & Semantik
        # Paragraphs
        score += len(element.find_all('p')) * self.WEIGHT_PARAGRAPH
        
        # Headings
        for h in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            score += len(element.find_all(h)) * self.WEIGHT_HEADING
            
        # Images
        imgs = element.find_all('img')
        for img in imgs:
            if img.get('alt'):
                score += self.WEIGHT_IMAGE_WITH_ALT
            else:
                score += self.WEIGHT_IMAGE_NO_ALT
                
        # Lists
        score += len(element.find_all('li')) * self.WEIGHT_LIST_ITEM
        
        # Semantic Tags
        if element.name == 'article':
            score += self.WEIGHT_SEMANTIC_ARTICLE
        elif element.name == 'section':
            score += self.WEIGHT_SEMANTIC_SECTION
        elif element.name == 'main':
            score += self.WEIGHT_SEMANTIC_MAIN
            
        # Cek parent semantic tags (bonus jika berada di dalam article/main)
        parent = element.parent
        while parent:
            if parent.name == 'article':
                score += 10.0
                break
            if parent.name == 'main':
                score += 15.0
                break
            parent = parent.parent

        # 3. Penalti (Negatif)
        # Link Density
        if text_len > 0:
            density = link_text_len / text_len
            if density > self.LINK_DENSITY_THRESHOLD:
                score += self.PENALTY_LINK_DENSITY
                
        # Tag Navigasi/Footer
        if element.name == 'nav':
            score += self.PENALTY_NAV_TAG
        elif element.name == 'footer':
            score += self.PENALTY_FOOTER_TAG
        elif element.name == 'aside':
            score += self.PENALTY_ASIDE_TAG
            
        # Pola Kelas/ID (Iklan, Share, Sponsor)
        ad_patterns = ['ad-', 'ads_', 'banner', 'sponsor', 'promo', 'advertisement']
        if self._check_class_patterns(element, ad_patterns):
            score += self.PENALTY_AD_PATTERN
            
        share_patterns = ['share', 'social', 'like-button', 'tweet']
        if self._check_class_patterns(element, share_patterns):
            score += self.PENALTY_SHARE_PATTERN

        return score

    def score_all_candidates(self, soup: BeautifulSoup) -> Dict[Tag, float]:
        """
        Melakukan scoring terhadap semua elemen kandidat potensial di seluruh dokumen.
        
        Kandidat adalah elemen container yang biasanya membungkus konten:
        div, section, article, main, td (untuk layout tabel lama).
        
        Args:
            soup: Objek BeautifulSoup dokumen lengkap.
            
        Returns:
            dict: Mapping {element_tag: score}.
        """
        candidates = soup.find_all(['div', 'section', 'article', 'main', 'td'])
        scores = {}
        
        for elem in candidates:
            # Abaikan elemen yang terlalu kecil (heuristik cepat)
            text_len, _ = self._get_text_stats(elem)
            if text_len < 20:
                continue
                
            scores[elem] = self.score_element(elem)
            
        return scores

    def pick_best_candidate(self, scores: Dict[Tag, float]) -> Optional[Tag]:
        """
        Memilih elemen tunggal dengan skor tertinggi sebagai representasi konten utama.
        
        Strategi tambahan:
        - Jika skor tertinggi negatif, mungkin halaman tidak memiliki konten jelas (return None).
        - Mengembalikan objek Tag langsung agar bisa langsung diekstrak atau diproses lanjut.
        
        Args:
            scores: Dictionary hasil dari `score_all_candidates`.
            
        Returns:
            Tag | None: Elemen terbaik, atau None jika tidak ada kandidat layak.
        """
        if not scores:
            return None
            
        best_elem = max(scores, key=scores.get)
        best_score = scores[best_elem]
        
        # Ambang batas mutlak: jika skor terbaik masih sangat rendah, abaikan
        if best_score < 0:
            return None
            
        return best_elem