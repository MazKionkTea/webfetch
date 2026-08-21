"""
cleaner.py
DOM cleaning tahap pertama: buang elemen yang hampir pasti bukan
konten (script/style/tracking) di satu halaman. Tidak seagresif
boilerplate.py — elemen yang ambigu (mis. <aside>) sengaja TIDAK
dibuang di sini, diserahkan ke scoring.py/content.py.
"""


from bs4 import BeautifulSoup, Tag
from typing import List, Set

class DOMCleaner:
    """
    Pembersih DOM tahap awal untuk menghilangkan elemen-elemen yang secara eksplisit
    bukan merupakan konten utama (non-content noise).
    
    Kelas ini beroperasi langsung pada objek `BeautifulSoup` sebelum proses analisis
    semantik atau ekstraksi blok dilakukan. Tujuannya adalah mengurangi ukuran DOM,
    mempercepat parsing selanjutnya, dan menghilangkan gangguan seperti script, style,
    tracker iklan, dan popup modal yang tidak relevan.
    
    Catatan:
        - Cookie banner ditangani secara khusus oleh `consent.py` sebelum tahap ini.
        - Metode ini bersifat destruktif terhadap objek soup yang diberikan (in-place).
    """

    # Daftar tag HTML yang pasti bukan konten teks utama
    NON_CONTENT_TAGS: List[str] = [
        'script', 'style', 'noscript', 'iframe', 'svg', 'canvas', 
        'object', 'embed', 'applet', 'meta', 'link', 'head'
    ]

    # Pola atribut/class/id yang mengindikasikan elemen tracking/iklan
    TRACKING_PATTERNS: List[str] = [
        'google-analytics', 'googletag', 'gtag', 'facebook-pixel', 'pixel',
        'adsbygoogle', 'doubleclick', 'taboola', 'outbrain', 'tracking',
        'analytics', 'beacon', 'statcounter', 'klaviyo', 'hotjar'
    ]

    # Pola class/id untuk popup/modal newsletter yang mengganggu
    POPUP_PATTERNS: List[str] = [
        'newsletter-popup', 'subscribe-modal', 'email-signup', 'popup-overlay',
        'modal-backdrop', 'lightbox', 'mfp-bg', 'fancybox', 'lean-overlay',
        'share-bar', 'social-share-fixed'
    ]

    def remove_non_content_tags(self, soup: BeautifulSoup) -> None:
        """
        Menghapus tag HTML standar yang tidak mengandung konten teks artikel.
        
        Tag seperti <script>, <style>, <noscript>, <svg>, dan <head> dihapus sepenuhnya
        dari DOM karena hanya berisi logika, presentasi, atau metadata mesin.
        
        Args:
            soup: Objek BeautifulSoup yang akan dibersihkan (dimodifikasi in-place).
        """
        for tag_name in self.NON_CONTENT_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

    def remove_tracking_elements(self, soup: BeautifulSoup) -> None:
        """
        Mengidentifikasi dan menghapus elemen yang diduga sebagai pelacak (tracker) atau iklan.
        
        Deteksi dilakukan berdasarkan pencocokan substring pada atribut `id`, `class`,
        `name`, atau `src` elemen tersebut terhadap daftar pola tracking yang dikenal.
        Ini mencakup pixel analitik, iframe iklan, dan script pihak ketiga.
        
        Args:
            soup: Objek BeautifulSoup yang akan dibersihkan (dimodifikasi in-place).
        """
        # Kita cari semua tag yang mungkin punya atribut relevan
        candidates = soup.find_all(True) 
        
        for tag in candidates:
            is_tracking = False
            
            # Gabungkan nilai id, class, name, src untuk dicek
            check_strings = []
            if tag.get('id'):
                check_strings.append(tag['id'].lower())
            if tag.get('class') and isinstance(tag['class'], list):
                check_strings.extend([c.lower() for c in tag['class']])
            elif tag.get('class') and isinstance(tag['class'], str):
                check_strings.append(tag['class'].lower())
            if tag.get('name'):
                check_strings.append(str(tag['name']).lower())
            if tag.get('src') and isinstance(tag['src'], str):
                check_strings.append(tag['src'].lower())
            
            combined = " ".join(check_strings)
            
            # Cek apakah ada pola tracking yang cocok
            for pattern in self.TRACKING_PATTERNS:
                if pattern in combined:
                    is_tracking = True
                    break
            
            if is_tracking:
                tag.decompose()

    def remove_obvious_popups(self, soup: BeautifulSoup) -> None:
        """
        Menghapus elemen overlay, modal, atau popup newsletter yang jelas bukan konten.
        
        Berbeda dengan cookie banner (yang ditangani lebih awal), ini menargetkan
        elemen yang meminta berlangganan email, share sosial media fixed, atau
        overlay gelap (backdrop) yang menutupi konten utama.
        
        Deteksi berbasis pola pada class dan ID elemen container.
        
        Args:
            soup: Objek BeautifulSoup yang akan dibersihkan (dimodifikasi in-place).
        """
        candidates = soup.find_all(True)
        
        for tag in candidates:
            is_popup = False
            
            check_strings = []
            if tag.get('id'):
                check_strings.append(tag['id'].lower())
            if tag.get('class') and isinstance(tag['class'], list):
                check_strings.extend([c.lower() for c in tag['class']])
            elif tag.get('class') and isinstance(tag['class'], str):
                check_strings.append(tag['class'].lower())
                
            combined = " ".join(check_strings)
            
            for pattern in self.POPUP_PATTERNS:
                if pattern in combined:
                    is_popup = True
                    break
            
            # Tambahan: Hapus div yang role-nya dialog/alertdialog dan terlihat sebagai overlay
            if tag.get('role') in ['dialog', 'alertdialog']:
                is_popup = True
                
            if is_popup:
                tag.decompose()

    def clean(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Menjalankan seluruh pipeline pembersihan DOM secara berurutan.
        
        Urutan eksekusi:
        1. Hapus tag non-konten standar (script/style).
        2. Hapus elemen tracking/iklan.
        3. Hapus popup/modal gangguan.
        
        Args:
            soup: Objek BeautifulSoup mentah hasil fetch.
            
        Returns:
            BeautifulSoup: Objek soup yang sama namun sudah dibersihkan (referensi yang sama).
        """
        self.remove_non_content_tags(soup)
        self.remove_tracking_elements(soup)
        self.remove_obvious_popups(soup)
        return soup