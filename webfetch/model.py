"""
model.py
Skema Document Model untuk hasil ekstraksi web: representasi
terstruktur sebelum dirender ke Markdown/JSON/TXT. Analog dengan
model.py di pdf2markdown, tapi tanpa konsep "halaman fisik" —
satu Document = satu URL (atau hasil agregasi multi-halaman).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import uuid


class BlockType(str, Enum):
    """
    Tipe block yang dikenali dalam Document Model web.
    Diturunkan dari (str, Enum) supaya value bisa langsung dipakai
    sebagai string biasa — memudahkan serialisasi JSON (to_dict())
    dan perbandingan langsung di renderer tanpa konversi manual.
    """
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"
    BLOCKQUOTE = "blockquote"
    EMBED = "embed"


class ConfidenceLevel(str, Enum):
    """
    Tingkat keyakinan sistem terhadap deteksi atau klasifikasi sebuah block.
    Diturunkan dari (str, Enum) untuk kemudahan serialisasi dan perbandingan.
    
    HIGH: Deteksi sangat yakin (misal: tag HTML eksplisit seperti <h1>, <table>)
    MEDIUM: Deteksi cukup yakin (misal: struktur yang umum tapi ambigu)
    LOW: Deteksi kurang yakin (misal: tebakan berdasarkan heuristic atau scoring rendah)
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Block:
    """
    Base class untuk semua block konten dalam Document Model.
    Setiap block memiliki identitas unik, tipe, dan tingkat keyakinan deteksi.
    
    Attributes:
        id: Identifier unik untuk block ini (string)
        type: Tipe block mengacu pada enum BlockType
        confidence: Tingkat keyakinan deteksi block (HIGH, MEDIUM, LOW)
    """
    id: str
    type: 'BlockType'
    confidence: 'ConfidenceLevel' = ConfidenceLevel.MEDIUM


@dataclass
class HeadingBlock(Block):
    """
    Block untuk heading (judul bagian) dengan level hierarki.
    
    Attributes:
        level: Tingkat hierarki heading (1-6), analog dengan <h1> sampai <h6>
        text: Konten teks dari heading tersebut
    """
    level: int = 1
    text: str = ""


@dataclass
class ParagraphBlock(Block):
    """
    Block untuk paragraf teks biasa.
    
    Attributes:
        text: Konten teks dari paragraf tersebut.
              Dapat berisi teks polos atau teks dengan formatting inline
              (seperti *bold*, _italic_, `code`) yang akan diproses oleh renderer.
    """
    text: str = ""


@dataclass
class ListBlock(Block):
    """
    Block untuk daftar (list), baik terurut (ordered) maupun tidak terurut (unordered).
    
    Attributes:
        items: Daftar item dalam list. Setiap item dapat berupa string atau ListBlock lain
               untuk mendukung nested list (daftar bersarang).
        ordered: Jika True, ini adalah ordered list (<ol>); jika False, unordered list (<ul>).
    
    Catatan:
        Implementasi ini sudah mendukung nested list dengan mengizinkan item bertipe ListBlock.
        Renderer harus menangani rekursi saat memproses items yang merupakan ListBlock.
    """
    items: list = field(default_factory=list)
    ordered: bool = False


@dataclass
class TableBlock(Block):
    """
    Block untuk tabel data.
    
    Attributes:
        headers: Daftar string yang merepresentasikan header kolom tabel.
                 Bisa kosong jika tabel tidak memiliki header eksplisit.
        rows: Daftar baris data, dimana setiap baris adalah list of strings
              yang merepresentasikan sel-sel dalam baris tersebut.
    
    Contoh struktur:
        headers = ["Nama", "Usia", "Kota"]
        rows = [
            ["Alice", "25", "Jakarta"],
            ["Bob", "30", "Bandung"]
        ]
    """
    headers: list = field(default_factory=list)
    rows: list = field(default_factory=list)


@dataclass
class ImageBlock(Block):
    """
    Block untuk merepresentasikan gambar.
    
    Attributes:
        src: URL atau path relatif dari sumber gambar (atribut src).
        alt: Teks alternatif untuk aksesibilitas (atribut alt). Bisa None jika tidak ada.
        caption: Keterangan atau judul gambar yang biasanya ditampilkan di bawah gambar.
                 Bisa None jika tidak ada caption eksplisit.
    """
    src: str = ""
    alt: Optional[str] = None
    caption: Optional[str] = None


@dataclass
class CodeBlock(Block):
    """
    Block untuk merepresentasikan blok kode (code snippet).
    
    Attributes:
        code: Konten kode sumber sebagai string. Dapat berisi karakter multiline.
        language: Identifikasi bahasa pemrograman (misal: 'python', 'javascript', 'bash').
                  Jika None, renderer akan menampilkan sebagai plain text tanpa syntax highlighting.
    """
    code: str = ""
    language: Optional[str] = None


@dataclass
class BlockquoteBlock(Block):
    """
    Block untuk merepresentasikan kutipan (blockquote).
    
    Attributes:
        text: Konten teks dari kutipan tersebut. 
              Dapat berisi teks polos atau formatting inline yang akan diproses renderer.
    """
    text: str = ""


@dataclass
class EmbedBlock(Block):
    """
    Block untuk merepresentasikan konten embed dari pihak ketiga (iframe).
    Mendeteksi dan menyimpan informasi tentang video, tweet, atau konten interaktif lainnya.
    
    Attributes:
        url: URL sumber dari konten embed (misal: link YouTube, Twitter, dll).
        embed_type: Klasifikasi tipe embed untuk membantu renderer memilih strategi render.
                    Nilai umum: 'youtube', 'twitter', 'vimeo', 'pdf', 'generic'.
                    Jika None, renderer akan memperlakukannya sebagai iframe generik.
        title: Judul opsional dari konten embed (biasanya diambil dari metadata oEmbed atau title tag).
    """
    url: str = ""
    embed_type: Optional[str] = None
    title: Optional[str] = None


@dataclass
class Metadata:
    """
    Metadata dokumen web yang dikumpulkan dari berbagai sumber HTML.
    Sumber ekstraksi dapat berasal dari JSON-LD, Open Graph tags, meta tags standar, atau title tag.
    
    Attributes:
        url: URL asli dari dokumen yang di-fetch.
        title: Judul halaman (dari <title> atau og:title).
        author: Nama penulis konten (dari meta author atau JSON-LD).
        published: Tanggal publikasi dalam format ISO 8601 (jika tersedia).
        language: Kode bahasa dokumen (misal: 'en', 'id') dari atribut lang atau meta tag.
        canonical_url: URL kanonik untuk menghindari duplikasi konten (dari rel=canonical).
        source: Indikator sumber utama metadata ini diekstraksi untuk keperluan debugging/audit.
                Nilai valid: 'json-ld', 'og', 'meta', 'title-tag', atau None jika tidak terdeteksi.
    """
    url: str = ""
    title: Optional[str] = None
    author: Optional[str] = None
    published: Optional[str] = None
    language: Optional[str] = None
    canonical_url: Optional[str] = None
    source: Optional[str] = None


@dataclass
class Document:
    """
    Representasi seluruh hasil ekstraksi dari satu URL (atau agregasi multi-halaman).
    Berfungsi sebagai container utama yang menghubungkan metadata dengan daftar block konten.
    
    Attributes:
        url: URL sumber dokumen ini.
        metadata: Objek Metadata yang berisi informasi deskriptif halaman.
        blocks: Daftar berurutan dari semua block konten (Heading, Paragraph, dll) yang diekstraksi.
    """
    url: str
    metadata: "Metadata" = field(default_factory=Metadata)
    blocks: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """
        Serialisasi Document Model menjadi dictionary standar Python.
        Digunakan terutama oleh JSONRenderer untuk menghasilkan output JSON.
        
        Proses ini menangani konversi rekursif untuk:
        - Enum (BlockType, ConfidenceLevel) menjadi string
        - Dataclass Block dan turunannya menjadi dict
        - Metadata menjadi dict
        """
        def serialize_block(block: Block) -> dict:
            result = {
                "id": block.id,
                "type": block.type.value if hasattr(block.type, 'value') else block.type,
                "confidence": block.confidence.value if hasattr(block.confidence, 'value') else block.confidence,
            }
            # Tambahkan field spesifik dari subclass Block
            for field_name in block.__dataclass_fields__:
                if field_name not in ("id", "type", "confidence"):
                    value = getattr(block, field_name)
                    # Handle nested ListBlock (rekursi jika item adalah Block)
                    if field_name == "items" and isinstance(value, list):
                        result[field_name] = [
                            serialize_block(item) if isinstance(item, Block) else item 
                            for item in value
                        ]
                    elif isinstance(value, Block):
                        result[field_name] = serialize_block(value)
                    else:
                        result[field_name] = value
            return result

        return {
            "url": self.url,
            "metadata": {
                k: v for k, v in self.metadata.__dict__.items() if v is not None
            } if self.metadata else {},
            "blocks": [serialize_block(block) for block in self.blocks]
        }

    def get_blocks_by_type(self, block_type: "BlockType") -> list:
        """
        Mengambil semua block dalam dokumen yang sesuai dengan tipe tertentu.
        
        Args:
            block_type: Tipe block yang dicari (misal: BlockType.HEADING).
            
        Returns:
            List of Block: Daftar block yang cocok. Bisa kosong jika tidak ditemukan.
        """
        # Penanganan kompatibilitas jika input adalah string atau Enum
        target_value = block_type.value if hasattr(block_type, 'value') else block_type
        
        return [
            block for block in self.blocks 
            if (hasattr(block.type, 'value') and block.type.value == target_value) or block.type == target_value
        ]