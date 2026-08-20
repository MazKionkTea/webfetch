"""
boilerplate.py
Deteksi elemen berulang lintas HALAMAN (bukan cuma satu halaman),
analog headers.py di pdf2markdown. Berguna saat webfetch dipakai untuk
crawl banyak halaman dari domain yang sama — nav/sidebar/footer yang
identik di semua halaman bisa dikenali lebih akurat lewat pengulangan,
bukan cuma heuristic per-halaman.
"""


import hashlib
from collections import defaultdict, Counter
from typing import List, Dict, Set, Any, Optional
from bs4 import BeautifulSoup, Tag

class BoilerplateLearner:
    """
    Modul pembelajaran pola boilerplate (konten berulang) lintas halaman dalam satu domain.
    
    Strategi:
    1. Mengumpulkan sample HTML yang sudah dibersihkan (dari `cleaner.py`) dari berbagai halaman.
    2. Menganalisis kemiripan struktural dan tekstual untuk menemukan elemen yang muncul 
       secara identik di sebagian besar halaman (misal: header navigasi, sidebar, footer, disclaimer).
    3. Membuat "signature" atau hash dari blok-blok ini.
    4. Pada proses ekstraksi halaman baru, menghapus elemen yang cocok dengan signature boilerplate.
    
    Ini adalah pendekatan heuristik tanpa machine learning berat, mirip dengan algoritma 
    'Content Extraction' klasik namun disesuaikan untuk struktur DOM modern.
    
    Attributes:
        _domain_samples: Penyimpanan sementara list of BeautifulSoup per domain.
        _boilerplate_signatures: Cache hash blok boilerplate yang sudah dipelajari per domain.
    """

    def __init__(self):
        # Struktur: { "example.com": [soup1, soup2, ...] }
        self._domain_samples: Dict[str, List[BeautifulSoup]] = {}
        # Struktur: { "example.com": set_of_hashes }
        self._boilerplate_signatures: Dict[str, Set[str]] = defaultdict(set)
        
        # Threshold minimal kemunculan blok untuk dianggap boilerplate (misal: muncul di > 60% sample)
        self.frequency_threshold = 0.6
        # Minimal panjang teks dalam blok untuk dipertimbangkan (menghindari noise ikon kecil)
        self.min_text_length = 20

    def collect_page_samples(self, domain: str, cleaned_html: str) -> None:
        """
        Menyimpan hasil HTML yang sudah dibersihkan ke dalam koleksi sample domain.
        
        Args:
            domain: Nama domain (contoh: 'example.com').
            cleaned_html: String HTML yang sudah melalui proses `DOMCleaner`.
        """
        if domain not in self._domain_samples:
            self._domain_samples[domain] = []
            
        # Parse ulang menjadi soup untuk manipulasi
        soup = BeautifulSoup(cleaned_html, 'html.parser')
        self._domain_samples[domain].append(soup)
        
        # Opsional: Batasi jumlah sample agar memori tidak meledak (misal max 20 halaman)
        if len(self._domain_samples[domain]) > 20:
            self._domain_samples[domain].pop(0)

    def _get_block_signature(self, tag: Tag) -> Optional[str]:
        """
        Membuat signature unik untuk sebuah blok DOM berdasarkan struktur dan konten teksnya.
        
        Signature dibuat dari:
        1. Hash dari struktur tag (nama tag + jumlah anak + urutan tag anak).
        2. Hash dari teks normalisasi (spasi dirapikan, lowercase).
        
        Returns:
            str | None: Hash signature, atau None jika blok terlalu kecil/tidak valid.
        """
        if not isinstance(tag, Tag):
            return None
            
        text = tag.get_text(separator=' ', strip=True)
        if len(text) < self.min_text_length:
            return None
            
        # Normalisasi teks untuk hashing
        normalized_text = " ".join(text.split()).lower()
        text_hash = hashlib.md5(normalized_text.encode('utf-8')).hexdigest()
        
        # Signature struktural sederhana: tag_name + jumlah_children
        # Bisa dikembangkan menjadi hash dari tree structure penuh jika perlu akurasi lebih tinggi
        struct_sig = f"{tag.name}:{len(tag.find_all(recursive=False))}"
        struct_hash = hashlib.md5(struct_sig.encode('utf-8')).hexdigest()
        
        # Gabungkan text hash dan struct hash
        return f"{text_hash}:{struct_hash}"

    def find_repeated_blocks(self, domain: str) -> List[str]:
        """
        Menganalisis sample yang terkumpul untuk menemukan blok boilerplate dominan.
        
        Algoritma:
        1. Iterasi semua sample halaman untuk domain tersebut.
        2. Untuk setiap halaman, ekstrak semua blok kandidat (div, section, nav, footer, header).
        3. Hitung frekuensi kemunculan signature blok di seluruh sample.
        4. Tanda tangan blok yang muncul di >= threshold (misal 60%) halaman dianggap boilerplate.
        
        Args:
            domain: Domain target analisis.
            
        Returns:
            list: Daftar signature hash string yang teridentifikasi sebagai boilerplate.
        """
        samples = self._domain_samples.get(domain, [])
        if len(samples) < 2:
            # Butuh minimal 2 sample untuk membandingkan repetisi
            return []
            
        signature_counts: Counter = Counter()
        total_pages = len(samples)
        
        for soup in samples:
            page_signatures: Set[str] = set()
            
            # Cari kandidat container besar
            # Fokus pada tag semantik yang sering jadi wadah boilerplate
            candidates = soup.find_all(['div', 'section', 'nav', 'footer', 'header', 'aside'])
            
            for tag in candidates:
                sig = self._get_block_signature(tag)
                if sig:
                    page_signatures.add(sig)
            
            # Tambahkan ke counter global (hitung 1 per halaman meski muncul 2x di halaman sama)
            for sig in page_signatures:
                signature_counts[sig] += 1
        
        # Filter berdasarkan threshold
        boilerplate_sigs = [
            sig for sig, count in signature_counts.items()
            if (count / total_pages) >= self.frequency_threshold
        ]
        
        # Simpan ke cache internal
        self._boilerplate_signatures[domain] = set(boilerplate_sigs)
        
        return boilerplate_sigs

    def strip_boilerplate(self, soup: BeautifulSoup, domain: str) -> BeautifulSoup:
        """
        Menghapus elemen dari soup saat ini yang cocok dengan pola boilerplate yang sudah dipelajari.
        
        Metode ini harus dipanggil setelah `find_repeated_blocks` dijalankan untuk domain tersebut,
        atau setidaknya setelah cukup sample dikumpulkan. Jika belum ada pola yang dipelajari,
        metode ini akan mencoba menghitungnya secara instan (on-the-fly).
        
        Args:
            soup: Objek BeautifulSoup halaman saat ini yang ingin dibersihkan.
            domain: Domain halaman tersebut untuk lookup pola.
            
        Returns:
            BeautifulSoup: Soup yang sama namun dengan elemen boilerplate telah dihapus (decompose).
        """
        # Pastikan kita punya pola boilerplate untuk domain ini
        if domain not in self._boilerplate_signatures or not self._boilerplate_signatures[domain]:
            # Jika belum ada cache, coba hitung dulu dari sample yang ada
            if domain in self._domain_samples:
                self.find_repeated_blocks(domain)
        
        known_boilerplate = self._boilerplate_signatures.get(domain, set())
        if not known_boilerplate:
            return soup # Tidak ada pola boilerplate yang dikenali, kembalikan apa adanya
            
        # Cari semua kandidat lagi di halaman ini
        candidates = soup.find_all(['div', 'section', 'nav', 'footer', 'header', 'aside'])
        
        removed_count = 0
        for tag in candidates:
            sig = self._get_block_signature(tag)
            if sig and sig in known_boilerplate:
                # Cek juga apakah blok ini terlalu dominan (misal > 80% isi halaman adalah boilerplate ini)
                # untuk menghindari penghapusan konten utama yang kebetulan punya template sama
                # (Heuristik sederhana: jangan hapus jika tag ini adalah <body> atau root konten utama)
                if tag.name == 'body':
                    continue
                    
                tag.decompose()
                removed_count += 1
                
        return soup