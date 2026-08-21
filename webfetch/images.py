"""
images.py
Ekstraksi <img> dari konten, normalisasi src relatif->absolute,
dan pencarian caption terdekat (mis. <figcaption>).
"""

from typing import List, Dict, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag

class ImageExtractor:
    """
    Ekstraktor gambar yang mengambil informasi visual dari konten utama.
    
    Tugas utama:
    1. Menemukan semua tag <img> dalam elemen konten.
    2. Menormalisasi atribut `src` dari URL relatif ke absolut.
    3. Mencari teks alternatif (`alt`) dan keterangan (`caption`) yang relevan.
    4. Mengembalikan struktur data yang kaya untuk setiap gambar ditemukan.
    
    Strategi Caption:
    - Prioritas 1: Tag <figcaption> jika gambar dibungkus <figure>.
    - Prioritas 2: Atribut `title` pada tag img.
    - Fallback: Atribut `alt` (jika tidak digunakan sebagai caption langsung).
    """

    def resolve_relative_src(self, src: str, base_url: str) -> str:
        """
        Mengonversi URL sumber gambar relatif menjadi absolut.
        
        Args:
            src: Nilai atribut src (bisa relatif seperti '/img/logo.png' atau '//cdn...').
            base_url: URL halaman dasar untuk resolusi.
            
        Returns:
            str: URL absolut gambar.
        """
        if not src:
            return ""
        return urljoin(base_url, src)

    def extract_caption(self, img_element: Tag) -> Optional[str]:
        """
        Mencari keterangan (caption) terbaik untuk elemen gambar.
        
        Alur pencarian:
        1. Cek parent <figure>, lalu cari <figcaption> di dalamnya.
        2. Jika tidak ada, cek atribut `title` pada img.
        3. Jika masih tidak ada, kembalikan None (biarkan caller memutuskan pakai alt atau tidak).
        
        Args:
            img_element: Objek Tag <img>.
            
        Returns:
            str | None: Teks caption, atau None jika tidak ditemukan.
        """
        # 1. Cek Figcaption
        figure_parent = img_element.find_parent('figure')
        if figure_parent:
            figcap = figure_parent.find('figcaption')
            if figcap:
                return figcap.get_text(strip=True)
        
        # 2. Cek Title Attribute
        title = img_element.get('title')
        if title:
            return title.strip()
            
        return None

    def extract_images(self, element: Tag, base_url: str) -> List[Dict]:
        """
        Ekstrak semua gambar dalam elemen konten menjadi list dictionary terstruktur.
        
        Args:
            element: Tag root konten utama (misal: hasil deteksi main content).
            base_url: URL halaman untuk resolusi URL relatif.
            
        Returns:
            list: Daftar dict dengan kunci:
                  {
                    'src': str (URL absolut),
                    'alt': str (Teks alternatif),
                    'caption': str (Keterangan dari figcaption/title),
                    'width': str (Opsional, dari atribut),
                    'height': str (Opsional, dari atribut)
                  }
        """
        images = []
        img_tags = element.find_all('img')
        
        for img in img_tags:
            src_raw = img.get('src')
            if not src_raw:
                continue # Skip img tanpa src
                
            src_abs = self.resolve_relative_src(src_raw, base_url)
            alt_text = img.get('alt', '')
            caption_text = self.extract_caption(img)
            
            # Jika tidak ada caption eksplisit, beberapa strategi mungkin menggunakan alt sebagai caption.
            # Di sini kita pisahkan agar caller bisa memilih: tampilkan alt italic atau caption bold.
            # Jika caption tetap None, kita bisa fallback ke alt jika diinginkan, tapi disini kita biarkan None.
            
            image_data = {
                'src': src_abs,
                'alt': alt_text.strip(),
                'caption': caption_text,
                'width': img.get('width'),
                'height': img.get('height')
            }
            
            images.append(image_data)
            
        return images