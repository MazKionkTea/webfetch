"""
tables.py
Ekstraksi <table> HTML menjadi TableBlock terstruktur
(headers + rows), siap dirender jadi tabel Markdown.
"""

from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup, Tag

class TableExtractor:
    """
    Parser elemen <table> HTML menjadi struktur data ternormalisasi.
    
    Kelas ini menangani kompleksitas struktur tabel HTML seperti:
    - Pemisahan <thead> dan <tbody>.
    - Sel yang menggabungkan baris/kolom (rowspan/colspan) - *ditangani secara dasar*.
    - Tabel tanpa header eksplisit (fallback ke baris pertama).
    - Normalisasi jumlah kolom agar konsisten untuk rendering Markdown.
    
    Output berupa dictionary dengan kunci 'headers' (list of str) dan 
    'rows' (list of list of str).
    """

    def _extract_cell_text(self, cell: Tag) -> str:
        """Mengambil teks bersih dari sel tabel, menghapus newline berlebih."""
        return cell.get_text(separator=' ', strip=True)

    def extract_table(self, table_element: Tag) -> Dict[str, Any]:
        """
        Parse elemen <table> menjadi struktur headers dan rows.
        
        Logika ekstraksi:
        1. Cari <thead>. Jika ada, ambil semua <th> di dalamnya sebagai headers.
        2. Jika tidak ada <thead>, cek apakah baris pertama (<tr>) berisi <th>.
           Jika ya, anggap baris pertama sebagai header.
        3. Ambil sisa baris dari <tbody> atau langsung dari <table> (jika tidak ada tbody).
        
        Args:
            table_element: Tag <table> dari BeautifulSoup.
            
        Returns:
            dict: {
                "headers": List[str],
                "rows": List[List[str]]
            }
        """
        headers = []
        rows = []
        
        # 1. Ekstrak Header
        thead = table_element.find('thead')
        if thead:
            # Ambil baris pertama di thead
            first_row = thead.find('tr')
            if first_row:
                cells = first_row.find_all(['th', 'td']) # Fallback ke td jika th tidak ada
                headers = [self._extract_cell_text(c) for c in cells]
        else:
            # Tidak ada thead, cek baris pertama tabel
            first_row = table_element.find('tr')
            if first_row:
                cells = first_row.find_all(['th', 'td'])
                # Jika semua sel adalah <th>, atau sebagian besar, anggap sebagai header
                th_count = sum(1 for c in cells if c.name == 'th')
                if th_count > 0: 
                    headers = [self._extract_cell_text(c) for c in cells]
                    # Baris ini sudah diproses sebagai header, nanti kita skip saat ambil body
        
        # 2. Ekstrak Rows (Body)
        tbody = table_element.find('tbody')
        # Jika ada tbody, ambil tr dari sana. Jika tidak, ambil langsung dari table.
        source_tag = tbody if tbody else table_element
        
        all_rows = source_tag.find_all('tr')
        
        for i, tr in enumerate(all_rows):
            # Skip baris header jika kita menemukannya di langkah sebelumnya tanpa <thead>
            # Heuristik: Jika headers tidak kosong (dari fallback) dan ini baris pertama且 sumbernya bukan tbody
            if not tbody and len(headers) > 0 and i == 0:
                # Cek apakah isi baris ini sama persis dengan headers yang sudah diambil?
                # Atau cukup asumsi baris pertama sudah diambil jika logic fallback atas berjalan.
                # Agar aman, kita cek lagi apakah sel-selnya <th>.
                cells = tr.find_all(['th', 'td'])
                if all(c.name == 'th' for c in cells):
                    continue 
            
            cells = tr.find_all(['td', 'th']) # Ambil td dan th (untuk jaga-jaga)
            row_data = [self._extract_cell_text(c) for c in cells]
            
            if row_data: # Hanya tambahkan jika ada isi
                rows.append(row_data)
                
        return {
            "headers": headers,
            "rows": rows
        }

    def normalize_table(self, headers: List[str], rows: List[List[str]]) -> Dict[str, Any]:
        """
        Menormalisasi struktur tabel agar jumlah kolom konsisten.
        
        Masalah umum di HTML:
        - Baris memiliki jumlah sel lebih sedikit dari header (kurang kolom).
        - Baris memiliki jumlah sel lebih banyak dari header (lebih kolom).
        - Header kosong tapi rows punya data.
        
        Strategi normalisasi:
        1. Tentukan `max_cols` berdasarkan panjang headers atau row terpanjang.
        2. Padankan panjang headers ke `max_cols` (isi dengan string kosong jika kurang).
        3. Padankan setiap row ke `max_cols` (truncate jika lebih, padding jika kurang).
        
        Args:
            headers: List header awal.
            rows: List of rows awal.
            
        Returns:
            dict: Struktur tabel yang sudah dinormalisasi.
        """
        if not headers and not rows:
            return {"headers": [], "rows": []}
            
        # Hitung jumlah kolom maksimal yang ditemukan di seluruh struktur
        max_cols = len(headers)
        for row in rows:
            if len(row) > max_cols:
                max_cols = len(row)
        
        # Normalisasi Headers
        normalized_headers = headers[:]
        while len(normalized_headers) < max_cols:
            normalized_headers.append("") # Padding header kosong
            
        # Normalisasi Rows
        normalized_rows = []
        for row in rows:
            new_row = row[:]
            if len(new_row) > max_cols:
                new_row = new_row[:max_cols] # Truncate
            while len(new_row) < max_cols:
                new_row.append("") # Padding
            normalized_rows.append(new_row)
            
        return {
            "headers": normalized_headers,
            "rows": normalized_rows
        }

    def extract_and_normalize(self, table_element: Tag) -> Dict[str, Any]:
        """
        Metode convenience: ekstrak lalu normalisasi dalam satu langkah.
        
        Args:
            table_element: Tag <table>.
            
        Returns:
            dict: Struktur tabel final yang siap diproses renderer.
        """
        raw_data = self.extract_table(table_element)
        return self.normalize_table(raw_data['headers'], raw_data['rows'])