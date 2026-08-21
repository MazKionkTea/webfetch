"""
links.py
Ekstraksi hyperlink dari konten & normalisasi URL relatif
menjadi absolute berdasarkan base URL halaman.
"""

from typing import List, Tuple, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag

class LinkExtractor:
    """
    Ekstraktor hyperlink yang mendeteksi semua tag <a> dalam elemen konten utama,
    membersihkan teks anchor, dan menormalisasi URL relatif menjadi absolut.
    
    Fitur:
    - Mengabaikan link navigasi boilerplate (karena sudah diproses di tahap cleaner/scoring).
    - Menangani berbagai format URL relatif (path-relative, protocol-relative, root-relative).
    - Memfilter link yang tidak valid atau skema non-http (mailto:, javascript:, #).
    
    Contoh penggunaan:
        extractor = LinkExtractor()
        links = extractor.extract_links(main_content_div, "https://example.com/blog/post-1")
        # Output: [("Baca selengkapnya", "https://example.com/blog/lanjutan"), ...]
    """

    def resolve_relative_url(self, href: str, base_url: str) -> str:
        """
        Mengubah URL relatif menjadi URL absolut menggunakan base_url sebagai referensi.
        
        Menangani kasus:
        - URL relatif path: "/about" -> "https://example.com/about"
        - URL relatif direktori: "page2.html" -> "https://example.com/blog/page2.html"
        - Protocol-relative: "//cdn.example.com/img.png" -> "https://cdn.example.com/img.png"
        - URL absolut: Dikembalikan apa adanya.
        
        Args:
            href: URL mentah dari atribut href.
            base_url: URL halaman sumber sebagai basis resolusi.
            
        Returns:
            str: URL absolut yang sudah dinormalisasi.
        """
        if not href:
            return ""
            
        # urllib.parse.urljoin menangani sebagian besar kasus relatif vs absolut secara otomatis
        return urljoin(base_url, href)

    def extract_links(self, element: Tag, base_url: str) -> List[Tuple[str, str]]:
        """
        Mengekstrak semua hyperlink valid (<a href>) di dalam elemen konten.
        
        Proses ekstraksi:
        1. Cari semua tag <a> dengan atribut href.
        2. Ekstrak teks anchor (dikumpulkan dari text nodes di dalam tag <a>).
        3. Bersihkan teks dari whitespace berlebih.
        4. Resolves URL relatif ke absolut.
        5. Filter link yang tidak berguna (fragment-only '#', javascript:, mailto:, tel:).
        
        Args:
            element: Tag BeautifulSoup (biasanya root konten utama) untuk discan.
            base_url: URL halaman saat ini untuk resolusi URL relatif.
            
        Returns:
            list: Daftar tuple `(text, url)` dimana text adalah label link dan url adalah URL absolut.
                  Contoh: [("Hubungi Kami", "mailto:info@example.com"), ("Next", "https://...")]
                  *Catatan: Implementasi ini memfilter mailto/js untuk fokus pada link navigasi konten.*
        """
        links = []
        
        if not isinstance(element, Tag):
            return links
            
        anchors = element.find_all('a', href=True)
        
        for a in anchors:
            href = a.get('href', '').strip()
            
            # Skip link kosong
            if not href:
                continue
                
            # Skip fragment-only (href="#") atau anchor internal halaman yang sama
            if href.startswith('#'):
                continue
                
            # Skip skema non-http/https (javascript, mailto, tel, data)
            parsed = urlparse(href)
            if parsed.scheme and parsed.scheme.lower() not in ['http', 'https']:
                continue
                
            # Ekstrak teks anchor
            # Mengambil semua teks, termasuk dari nested tags (seperti <a><img></a> atau <a><span>Text</span></a>)
            text = a.get_text(separator=' ', strip=True)
            
            # Fallback: Jika tidak ada teks tapi ada img alt, gunakan alt text
            if not text:
                img = a.find('img')
                if img:
                    text = img.get('alt', '')
            
            # Skip jika setelah dibersihkan tetap tidak ada teks (link gambar tanpa alt)
            # Opsional: Bisa disimpan jika ingin mengekstrak semua link meski tanpa konteks teks
            if not text:
                text = "[Link]" # Placeholder agar struktur tetap ada
            
            # Resolve URL
            absolute_url = self.resolve_relative_url(href, base_url)
            
            links.append((text, absolute_url))
            
        return links