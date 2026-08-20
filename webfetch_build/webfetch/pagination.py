"""
pagination.py
Deteksi & agregasi artikel yang terpecah jadi beberapa halaman
(?page=1,2,3) maupun infinite scroll/"load more". Analog
merge_cross_page_tables di pdf2markdown, tapi untuk artikel web.
"""


import asyncio
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag

# Asumsi model Block dan Document sudah ada
from .model import Block, HeadingBlock, ParagraphBlock

class PaginationHandler:
    """
    Handler untuk mendeteksi, menavigasi, dan menggabungkan konten dari halaman yang terpaginasi.
    
    Kelas ini menangani dua skenario umum:
    1. Paginasi Tradisional: Link "Next", nomor halaman, atau rel="next".
    2. Infinite Scroll / Load More: Konten dimuat dinamis via JavaScript saat scroll atau klik tombol.
    
    Tujuannya adalah menyajikan konten multi-halaman sebagai satu dokumen utuh (agregasi)
    kepada pengguna, menghindari pemotongan artikel panjang menjadi bagian-bagian terpisah.
    
    Attributes:
        visited_urls: Set URL yang sudah diproses untuk mencegah loop infinite.
        max_pages: Batas maksimal halaman yang akan digabung (safety break).
    """

    def __init__(self, max_pages: int = 5):
        self.visited_urls: set = set()
        self.max_pages = max_pages

    def detect_pagination_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Mencari link menuju halaman berikutnya berdasarkan pola umum paginasi.
        
        Strategi deteksi (berurutan):
        1. Tag `<link rel="next">` (standar SEO).
        2. Link dengan teks anchor "Next", ">", "Halaman Berikutnya", ">>".
        3. Link dengan class/id mengandung "next", "page-next".
        
        Args:
            soup: Objek BeautifulSoup halaman saat ini.
            base_url: URL halaman saat ini untuk resolve URL relatif.
            
        Returns:
            list: Daftar URL halaman berikutnya (biasanya 1 URL, bisa lebih jika ambigu).
        """
        next_urls = []
        
        # 1. Cek <link rel="next">
        link_next = soup.find('link', rel='next')
        if link_next and link_next.get('href'):
            next_urls.append(urljoin(base_url, link_next['href']))
            return next_urls # Prioritas tertinggi
            
        # 2. Cek Link berdasarkan Teks Anchor
        # Pola teks umum untuk tombol next
        next_patterns = ['next', '>', '>>', 'halaman berikutnya', 'weiter', 'suivant']
        
        candidates = soup.find_all('a', href=True)
        for a in candidates:
            text = a.get_text(strip=True).lower()
            href = a.get('href')
            
            if any(p in text for p in next_patterns):
                full_url = urljoin(base_url, href)
                # Validasi sederhana: pastikan masih dalam domain yang sama
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    next_urls.append(full_url)
                    
        # 3. Cek berdasarkan Class/ID
        for a in candidates:
            class_str = " ".join(a.get('class', []))
            id_str = a.get('id', '')
            combined = f"{class_str} {id_str}".lower()
            
            if 'next' in combined and 'prev' not in combined: # Hindari 'previous'
                full_url = urljoin(base_url, href)
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    if full_url not in next_urls:
                        next_urls.append(full_url)
                        
        return next_urls[:1] # Biasanya hanya butuh 1 link next terdekat

    async def detect_infinite_scroll(self, page) -> bool:
        """
        Mendeteksi apakah halaman menggunakan infinite scroll (lazy-load) dengan simulasi scroll.
        
        Metode:
        1. Catat tinggi dokumen (`scrollHeight`) sebelum scroll.
        2. Lakukan scroll ke bawah secara programatis.
        3. Tunggu sebentar (network idle atau timeout).
        4. Catat tinggi dokumen lagi.
        5. Jika tinggi bertambah signifikan, berarti ada konten baru yang dimuat.
        
        Args:
            page: Objek page Playwright.
            
        Returns:
            bool: True jika terdeteksi konten baru dimuat setelah scroll.
        """
        try:
            # Ambil tinggi awal
            initial_height = await page.evaluate("document.documentElement.scrollHeight")
            
            # Scroll ke bawah
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Tunggu potensi loading (bisa diperbaiki dengan wait_for_load_state('networkidle'))
            await page.wait_for_timeout(2000) 
            
            # Ambil tinggi akhir
            final_height = await page.evaluate("document.documentElement.scrollHeight")
            
            # Threshold kenaikan minimal 100px agar dianggap konten baru
            return final_height > initial_height + 100
            
        except Exception:
            return False

    async def trigger_load_more(self, page) -> bool:
        """
        Mencari dan mengklik tombol "Load More" atau "Show More" jika ada.
        
        Args:
            page: Objek page Playwright.
            
        Returns:
            bool: True jika tombol ditemukan dan diklik, False jika tidak ada.
        """
        selectors = [
            "button:has-text('Load More')",
            "button:has-text('Show More')",
            "a:has-text('Load More')",
            ".load-more-button",
            "#load-more",
            "[class*='load-more']"
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    await element.click()
                    # Tunggu konten baru muncul (networkidle atau timeout)
                    await page.wait_for_timeout(1500) 
                    return True
            except Exception:
                continue
                
        return False

    def aggregate_multi_page_content(self, contents: List[Dict]) -> List[Block]:
        """
        Menggabungkan list blok konten dari beberapa halaman menjadi satu urutan koheren.
        
        Logika penggabungan:
        1. Iterasi blok dari setiap halaman secara berurutan.
        2. Deteksi duplikasi heading/judul yang sering muncul di header/footer tiap halaman.
        3. Hanya tambahkan blok jika unik atau merupakan kelanjutan logis konten.
        
        Args:
            contents: List of dict, dimana setiap dict berisi {'blocks': List[Block], 'url': str}.
            
        Returns:
            list: Daftar tunggal objek Block yang sudah digabung.
        """
        final_blocks: List[Block] = []
        seen_headings: set = set() # Untuk mencegah duplikasi judul bab yang sama
        
        for i, page_data in enumerate(contents):
            blocks = page_data.get('blocks', [])
            
            for block in blocks:
                # Heuristik anti-duplikasi untuk Heading
                if isinstance(block, HeadingBlock):
                    # Normalisasi teks heading (lowercase, strip)
                    sig = block.text.strip().lower()
                    if sig in seen_headings:
                        # Lewati heading yang sama persis (kemungkinan header/footer berulang)
                        # Kecuali ini halaman pertama (i=0), kita ambil semua
                        if i > 0:
                            continue
                    seen_headings.add(sig)
                
                # Heuristik sederhana: abaikan blok paragraf sangat pendek (< 10 char) 
                # di halaman > 1 yang mungkin artefak navigasi
                if i > 0 and isinstance(block, ParagraphBlock):
                    if len(block.text.strip()) < 10:
                        continue
                        
                final_blocks.append(block)
                
        return final_blocks

    async def fetch_all_pages(self, fetcher_func, start_url: str, start_soup: BeautifulSoup) -> List[Dict]:
        """
        Helper method untuk melakukan crawling otomatis seluruh halaman paginasi.
        
        Args:
            fetcher_func: Fungsi async untuk mengambil konten halaman (return dict with 'html', 'soup').
            start_url: URL halaman pertama.
            start_soup: Soup halaman pertama (sudah di-fetch sebelumnya).
            
        Returns:
            list: List data konten per halaman.
        """
        results = []
        current_url = start_url
        current_soup = start_soup
        count = 0
        
        while count < self.max_pages:
            if current_url in self.visited_urls:
                break # Loop detection
                
            self.visited_urls.add(current_url)
            
            # Simpan hasil halaman ini (asumsi fetcher_func mengembalikan struktur yg dibutuhkan)
            # Dalam implementasi nyata, Anda mungkin perlu memproses HTML -> Blocks dulu di sini
            # atau menyimpan raw html/soup untuk diproses nanti oleh pipeline utama
            results.append({
                "url": current_url,
                "soup": current_soup,
                # "blocks": ... # Bisa diisi jika ekstraksi blok dilakukan di sini
            })
            
            # Cari link next
            next_urls = self.detect_pagination_links(current_soup, current_url)
            
            if not next_urls:
                break # Tidak ada halaman berikutnya
                
            current_url = next_urls[0]
            
            # Fetch halaman berikutnya
            try:
                next_data = await fetcher_func(current_url)
                current_soup = next_data.get('soup')
                # Update soup untuk iterasi berikutnya
            except Exception:
                break # Gagal fetch halaman berikutnya, stop
                
            count += 1
            
        return results