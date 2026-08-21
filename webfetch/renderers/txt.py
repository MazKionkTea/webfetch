"""
txt.py
Renderer teks polos tanpa markup Markdown.

Modul ini bertujuan menghasilkan output yang bersih dan mudah dibaca
oleh manusia atau diproses oleh alat NLP sederhana yang tidak membutuhkan
formatting struktural (seperti bold, italic, atau syntax highlighting).
Semua elemen struktural (heading, list, table) diratakan menjadi aliran teks linear.
"""

from typing import Any, List
from .base import BaseRenderer


class TXTRenderer(BaseRenderer):
    """Render Document Model menjadi teks polos."""

    def _normalize_whitespace(self, text: str) -> str:
        """Membersihkan spasi berlebih dalam satu baris teks."""
        return " ".join(text.split())

    def render(self, document: Any) -> str:
        """
        Menggabungkan konten dari seluruh block menjadi satu string teks polos.
        
        Strategi rendering per tipe block:
        - Heading/Paragraph/Blockquote: Diambil teksnya, ditambah newline ganda.
        - List: Setiap item dijadikan baris baru dengan bullet point sederhana (-).
        - Table: Ditarik menjadi format CSV sederhana atau baris terpisah dipisahkan pipa (|).
        - Code: Diambil mentah-mentah (preserve whitespace) karena penting untuk kode.
        - Image/Embed: Diambil teks alternatif/caption-nya saja, URL bisa diabaikan atau disertakan dalam kurung.
        
        Args:
            document: Objek `model.Document` yang sudah terisi.
            
        Returns:
            str: Konten dokumen dalam format teks polos.
        """
        if not hasattr(document, 'blocks') or not document.blocks:
            return ""
            
        output_lines = []
        
        # Opsional: Tambahkan metadata sebagai header teks jika diinginkan
        if hasattr(document, 'metadata') and document.metadata:
            if document.metadata.title:
                output_lines.append(f"Judul: {document.metadata.title}")
            if document.metadata.author:
                output_lines.append(f"Penulis: {document.metadata.author}")
            if document.metadata.url:
                output_lines.append(f"Sumber: {document.metadata.url}")
            output_lines.append("") # Spasi pemisah
            
        for block in document.blocks:
            # Ambil nilai enum jika tipe adalah Enum object
            block_type = block.type
            if hasattr(block_type, 'value'):
                block_type = block_type.value
            
            try:
                if block_type == 'heading':
                    output_lines.append(block.text)
                    output_lines.append("") # Double newline effect
                    
                elif block_type == 'paragraph':
                    text = self._normalize_whitespace(block.text)
                    output_lines.append(text)
                    output_lines.append("")
                    
                elif block_type == 'blockquote':
                    text = self._normalize_whitespace(block.text)
                    output_lines.append(f"> {text}")
                    output_lines.append("")
                    
                elif block_type == 'list':
                    prefix = "1." if block.ordered else "-"
                    for i, item in enumerate(block.items):
                        # Handle nested list (jika item adalah object lagi, ambil str-nya)
                        item_text = str(item)
                        if hasattr(item, 'text'): # Jika ternyata object Block lagi
                            item_text = item.text
                            
                        num = i + 1
                        current_prefix = f"{num}." if block.ordered else "-"
                        output_lines.append(f"{current_prefix} {item_text}")
                    output_lines.append("")
                    
                elif block_type == 'table':
                    # Render tabel sederhana: Header | Row1 | Row2
                    if block.headers:
                        output_lines.append(" | ".join(block.headers))
                    for row in block.rows:
                        output_lines.append(" | ".join(str(cell) for cell in row))
                    output_lines.append("")
                    
                elif block_type == 'code':
                    # Untuk kode, pertahankan formatting asli (newline & indent)
                    output_lines.append(block.code)
                    output_lines.append("")
                    
                elif block_type == 'image':
                    # Sertakan alt text dan caption jika ada
                    parts = []
                    if block.alt:
                        parts.append(f"[Gambar: {block.alt}]")
                    if block.caption:
                        parts.append(f"(Keterangan: {block.caption})")
                    if parts:
                        output_lines.append(" ".join(parts))
                        output_lines.append("")
                        
                elif block_type == 'embed':
                    title = block.title or block.embed_type or "Konten Sematan"
                    output_lines.append(f"[{title}: {block.url}]")
                    output_lines.append("")
                    
            except Exception:
                # Fallback aman jika block tidak dikenali atau error
                continue
                
        return "\n".join(output_lines)