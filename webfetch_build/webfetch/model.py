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


class ConfidenceLevel(Enum):
    """Tingkat keyakinan hasil deteksi/klasifikasi sebuah block."""
    # TODO: HIGH, MEDIUM, LOW
    pass


@dataclass
class Block:
    """Base class untuk semua tipe block di Document Model web."""
    id: str
    type: "BlockType"
    confidence: "ConfidenceLevel" = None
    # TODO: tambahkan field umum lain jika perlu (mis. source_tag, dom_path)


@dataclass
class HeadingBlock(Block):
    level: int = 1
    text: str = ""


@dataclass
class ParagraphBlock(Block):
    text: str = ""


@dataclass
class ListBlock(Block):
    items: list = field(default_factory=list)
    ordered: bool = False
    # TODO: dukung nested list


@dataclass
class TableBlock(Block):
    headers: list = field(default_factory=list)
    rows: list = field(default_factory=list)


@dataclass
class ImageBlock(Block):
    src: str = ""
    alt: Optional[str] = None
    caption: Optional[str] = None


@dataclass
class CodeBlock(Block):
    code: str = ""
    language: Optional[str] = None


@dataclass
class BlockquoteBlock(Block):
    text: str = ""


@dataclass
class EmbedBlock(Block):
    """Untuk iframe/embed (YouTube, tweet, embedded PDF, dll)."""
    url: str = ""
    embed_type: Optional[str] = None  # TODO: 'youtube' | 'twitter' | 'generic' | dll
    title: Optional[str] = None


@dataclass
class Metadata:
    """Metadata dokumen, sumbernya bisa JSON-LD/OG tag/meta tag/title tag."""
    url: str = ""
    title: Optional[str] = None
    author: Optional[str] = None
    published: Optional[str] = None
    language: Optional[str] = None
    canonical_url: Optional[str] = None
    source: Optional[str] = None  # TODO: 'json-ld' | 'og' | 'meta' | 'title-tag'


@dataclass
class Document:
    """Representasi seluruh hasil ekstraksi satu URL (atau agregasi multi-halaman)."""
    url: str
    metadata: "Metadata" = None
    blocks: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialisasi Document Model menjadi dict (dipakai JSONRenderer)."""
        # TODO: implementasi rekursif dataclass -> dict
        pass

    def get_blocks_by_type(self, block_type: "BlockType") -> list:
        """Ambil semua block dengan tipe tertentu."""
        # TODO
        pass
