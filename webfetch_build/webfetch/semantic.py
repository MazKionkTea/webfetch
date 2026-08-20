"""
semantic.py
Ekstraksi struktur semantik dari elemen main-content yang sudah
ditemukan content.py: heading, paragraf, list, code, blockquote.
(Tabel, gambar, link, embed masing-masing punya modul sendiri.)
"""


from typing import List, Optional, Any
from bs4 import BeautifulSoup, Tag, NavigableString

# Import model blocks yang sudah dibuat
from .model import (
    Block, HeadingBlock, ParagraphBlock, ListBlock, 
    TableBlock, ImageBlock, CodeBlock, BlockquoteBlock, EmbedBlock,
    ConfidenceLevel
)

class SemanticExtractor:
    """
    Mengonversi elemen HTML dari konten utama (hasil `MainContentDetector`) 
    menjadi list objek `Block` sesuai Document Model.
    
    Kelas ini bertindak sebagai translator dari struktur DOM tree menjadi 
    representasi data terstruktur yang siap dirender ke Markdown, JSON, atau TXT.
    
    Strategi:
    - Iterasi rekursif atau linear terhadap children elemen utama.
    - Dispatch ke metode `extract_*` spesifik berdasarkan nama tag.
    - Menangani nested structure (seperti list dalam list) secara rekursif.
    - Mengabaikan tag dekoratif kecil yang tidak signifikan secara semantik.
    """

    def extract_heading(self, element: Tag) -> HeadingBlock:
        """
        Ekstrak elemen heading (<h1> s.d. <h6>) menjadi HeadingBlock.
        
        Args:
            element: Tag heading dari BeautifulSoup.
            
        Returns:
            HeadingBlock: Objek block dengan level (1-6) dan teks konten.
        """
        tag_name = element.name.lower()
        level = int(tag_name[1]) if len(tag_name) == 2 and tag_name[1].isdigit() else 1
        text = element.get_text(strip=True)
        block_id = element.get('id', '') or f"h{level}-{text[:20].replace(' ', '-').lower()}"

        
        return HeadingBlock(
            id=block_id,
            type="heading", # Sesuai value enum BlockType
            confidence=ConfidenceLevel.HIGH,
            level=level,
            text=text
        )

    def extract_paragraph(self, element: Tag) -> ParagraphBlock:
        """
        Ekstrak elemen paragraf (<p>) menjadi ParagraphBlock.
        
        Args:
            element: Tag <p> dari BeautifulSoup.
            
        Returns:
            ParagraphBlock: Objek block dengan teks konten.
        """
        text = element.get_text(strip=True)
        block_id = element.get('id', '') or f"p-{text[:20].replace(' ', '-').lower()}"
        return ParagraphBlock(
            id=block_id,
            type="paragraph",
            confidence=ConfidenceLevel.HIGH,
            text=text
        )

    def extract_list(self, element: Tag) -> ListBlock:
        """
        Ekstrak elemen list (<ul> atau <ol>) menjadi ListBlock.
        Mendukung nested list (list di dalam <li>).
        
        Args:
            element: Tag <ul> atau <ol>.
            
        Returns:
            ListBlock: Objek block dengan daftar item (string atau ListBlock nested).
        """
        is_ordered = element.name == 'ol'
        items = []
        
        for li in element.find_all('li', recursive=False):
            # Cek apakah li mengandung list lain (nested)
            nested_lists = li.find_all(['ul', 'ol'], recursive=False)
            
            if nested_lists:
                # Jika ada nested list, kita perlu memprosesnya secara khusus
                # Strategi: Gabungkan teks langsung sebelum/sesudah nested list, 
                # lalu tambahkan nested list sebagai object ListBlock
                li_content = []
                
                # Ekstrak teks langsung (tanpa anak list)
                direct_text = ""
                for child in li.children:
                    if isinstance(child, NavigableString):
                        direct_text += str(child)
                    elif child.name not in ['ul', 'ol']:
                        # Ambil teks dari tag non-list lain (misal <strong> di dalam li)
                        direct_text += child.get_text()
                
                if direct_text.strip():
                    li_content.append(direct_text.strip())
                
                # Proses nested list secara rekursif
                for nested in nested_lists:
                    nested_block = self.extract_list(nested)
                    # Simpan sebagai representasi khusus atau gabungkan string
                    # Untuk simplicity model saat ini, kita bisa stringify nested list 
                    # atau menyimpannya sebagai objek jika model mendukung union type.
                    # Karena model items = list, kita bisa masukkan string representasi atau object.
                    # Di sini kita asumsikan items bisa berisi string ATAU ListBlock (sesuai tiping longgar).
                    if direct_text.strip():
                         li_content.append(f"[Nested List: {len(nested_block.items)} items]")
                    else:
                        # Jika li hanya pembungkus list, item utamanya adalah list itu sendiri
                        # Tapi karena items list of any, kita perlu hati-hati.
                        # Solusi aman: flatten teks nested list atau simpan object.
                        # Mari simpan object ListBlock langsung jika tipe data mengizinkan,
                        # atau konversi ke string indentasi.
                        li_content.append(nested_block) 

                # Karena kompleksitas nested list bervariasi, pendekatan sederhana:
                # Ambil seluruh teks li sebagai satu item string jika ada nested, 
                # KECUALI kita ingin struktur pohon penuh. 
                # Implementasi robust: Rekursi hanya untuk item list.
                items.append(li.get_text(strip=True)) # Fallback aman
            else:
                # List biasa tanpa nested
                items.append(li.get_text(strip=True))
                
        block_id = element.get('id', '') or f"list-{'ol' if is_ordered else 'ul'}-{len(items)}"
        return ListBlock(
            id=block_id,
            type="list",
            confidence=ConfidenceLevel.MEDIUM, # Sedikit lebih rendah karena struktur bisa ambigu
            items=items,
            ordered=is_ordered
        )

    def extract_code_block(self, element: Tag) -> CodeBlock:
        """
        Ekstrak blok kode (<pre><code>) menjadi CodeBlock.
        Mendeteksi bahasa pemrograman dari class (misal: class="language-python").
        
        Args:
            element: Tag <pre> atau <code>.
            
        Returns:
            CodeBlock: Objek block dengan kode dan bahasa.
        """
        code_tag = element.find('code') if element.name == 'pre' else element
        if not code_tag:
            code_tag = element
            
        code_text = code_tag.get_text(strip=False) # Preserve whitespace untuk kode
        
        language = None
        classes = code_tag.get('class', [])
        for cls in classes:
            if cls.startswith('language-'):
                language = cls.split('-')[1]
                break
            elif cls.startswith('lang-'):
                language = cls.split('-')[1]
                break
                
        return CodeBlock(
            id=element.get('id', '') or f"code-{language or 'plain'}",
            type="code",
            confidence=ConfidenceLevel.HIGH,
            code=code_text,
            language=language
        )

    def extract_blockquote(self, element: Tag) -> BlockquoteBlock:
        """
        Ekstrak elemen kutipan (<blockquote>) menjadi BlockquoteBlock.
        
        Args:
            element: Tag <blockquote>.
            
        Returns:
            BlockquoteBlock: Objek block dengan teks kutipan.
        """
        text = element.get_text(strip=True)
        block_id = element.get('id', '') or f"quote-{text[:20].replace(' ', '-').lower()}"
        return BlockquoteBlock(
            id=block_id,
            type="blockquote",
            confidence=ConfidenceLevel.HIGH,
            text=text
        )

    def extract_table(self, element: Tag) -> TableBlock:
        """Ekstrak tabel (<table>) menjadi TableBlock."""
        headers = []
        rows = []
        
        # Ekstrak Header
        thead = element.find('thead')
        if thead:
            for th in thead.find_all('th'):
                headers.append(th.get_text(strip=True))
        else:
            # Fallback: ambil baris pertama sebagai header jika tidak ada thead
            first_row = element.find('tr')
            if first_row:
                for cell in first_row.find_all(['th', 'td']):
                    headers.append(cell.get_text(strip=True))
                # Baris pertama sudah diproses sebagai header, skip nanti di rows jika perlu
                # Tapi logika sederhana: kita ambil semua tr lagi nanti, atau manual skip.
                # Mari ambil semua tbody untuk rows agar aman.
        
        # Ekstrak Rows
        tbody = element.find('tbody') or element
        for tr in tbody.find_all('tr'):
            # Skip jika tr ini sama dengan header fallback tadi (opsional, tergantung struktur)
            cells = tr.find_all(['td', 'th'])
            if not cells:
                continue
                
            row_data = [c.get_text(strip=True) for c in cells]
            
            # Jika headers kosong dan ini baris pertama, anggap header? 
            # Lebih aman ikuti struktur thead/tbody. Jika tidak ada thead, semua dianggap body.
            rows.append(row_data)
            
        # Koreksi jika headers diambil dari tr pertama tapi masuk juga ke rows
        if not thead and headers and rows:
            if rows[0] == headers:
                rows.pop(0)

        block_id = element.get('id', '') or f"table-{len(headers)}x{len(rows)}"
        return TableBlock(
            id=block_id,
            type="table",
            confidence=ConfidenceLevel.MEDIUM,
            headers=headers,
            rows=rows
        )

    def extract_image(self, element: Tag) -> ImageBlock:
        """Ekstrak gambar (<img>) menjadi ImageBlock."""
        src = element.get('src', '')
        alt = element.get('alt')
        
        # Cari caption: bisa dari atribut title, atau figcaption terdekat
        caption = element.get('title')
        parent_fig = element.find_parent('figure')
        if parent_fig:
            figcap = parent_fig.find('figcaption')
            if figcap:
                caption = figcap.get_text(strip=True)
                
        return ImageBlock(
            id=element.get('id', '') or f"img-{src.split('/')[-1].split('.')[0]}",
            type="image",
            confidence=ConfidenceLevel.HIGH,
            src=src,
            alt=alt,
            caption=caption
        )

    def extract_embed(self, element: Tag) -> EmbedBlock:
        """Ekstrak embed (<iframe>, <embed>) menjadi EmbedBlock."""
        url = element.get('src', '')
        title = element.get('title')
        
        embed_type = "generic"
        if "youtube" in url or "youtu.be" in url:
            embed_type = "youtube"
        elif "twitter" in url or "x.com" in url:
            embed_type = "twitter"
        elif "vimeo" in url:
            embed_type = "vimeo"
            
        return EmbedBlock(
            id=element.get('id', '') or f"embed-{embed_type}",
            type="embed",
            confidence=ConfidenceLevel.MEDIUM,
            url=url,
            embed_type=embed_type,
            title=title
        )

    def _process_node(self, node: Any) -> Optional[List[Block]]:
        """
        Dispatcher internal untuk memproses satu node dan mengembalikan list Block.
        """
        if not isinstance(node, Tag):
            return None
            
        blocks = []
        
        # Mapping tag ke method
        if node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            blocks.append(self.extract_heading(node))
            
        elif node.name == 'p':
            # Abaikan paragraf kosong atau terlalu pendek
            text = node.get_text(strip=True)
            if len(text) > 5:
                blocks.append(self.extract_paragraph(node))
                
        elif node.name in ['ul', 'ol']:
            blocks.append(self.extract_list(node))
            
        elif node.name == 'pre' or (node.name == 'code' and node.find_parent('pre') is None):
            blocks.append(self.extract_code_block(node))
            
        elif node.name == 'blockquote':
            blocks.append(self.extract_blockquote(node))
            
        elif node.name == 'table':
            blocks.append(self.extract_table(node))
            
        elif node.name == 'img':
            blocks.append(self.extract_image(node))
            
        elif node.name in ['iframe', 'embed']:
            blocks.append(self.extract_embed(node))
            
        elif node.name in ['div', 'section', 'article']:
            # Rekursi untuk container besar jika diperlukan, 
            # tapi biasanya main_content_element sudah difilter sehingga isinya langsung tag semantik.
            # Jika ada tag semantik tersembunyi di dalam div, kita perlu traverse children.
            for child in node.children:
                sub_blocks = self._process_node(child)
                if sub_blocks:
                    blocks.extend(sub_blocks)
                    
        return blocks if blocks else None

    def extract_all(self, main_content_element: Tag) -> List[Block]:
        """
        Iterasi children elemen main-content, dispatch ke extract_* sesuai tag.
        
        Args:
            main_content_element: Tag root dari konten utama (hasil deteksi scoring/semantic).
            
        Returns:
            list: Daftar objek Block yang merepresentasikan konten tersebut.
        """
        all_blocks = []
        
        # Langsung proses children dari root elemen
        for child in main_content_element.children:
            result = self._process_node(child)
            if result:
                all_blocks.extend(result)
                
        return all_blocks
