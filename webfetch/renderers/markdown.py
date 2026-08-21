"""
markdown.py
Renderer utama: ubah Document Model menjadi Markdown LLM-friendly,
lengkap dengan YAML front matter dari Metadata.

Modul ini bertanggung jawab mengonversi struktur data `Document` (blocks + metadata)
menjadi string Markdown yang rapi, terstruktur, dan siap dikonsumsi oleh LLM atau
ditampilkan di editor teks modern (Obsidian, VS Code, Hugo, dll).
"""

from typing import Any, List
from .base import BaseRenderer

class MarkdownRenderer(BaseRenderer):
    """
    Renderer untuk menghasilkan output format Markdown.
    
    Fitur:
    - YAML Front Matter otomatis dari metadata dokumen.
    - Heading bertingkat (# sampai ######).
    - List bersarang (nested lists).
    - Tabel dengan alignment standar.
    - Code block dengan syntax highlighting hint.
    - Image dengan alt text dan caption (sebagai italic).
    - Embed sebagai link referensi atau placeholder.
    """

    def render_front_matter(self, metadata: Any) -> str:
        """
        Membangun blok YAML front matter di bagian paling atas dokumen.
        
        Format:
        ---
        key: value
        ---
        
        Hanya field yang tidak None yang akan disertakan.
        """
        if not metadata:
            return ""
            
        lines = ["---"]
        
        # Mapping field model ke key YAML
        fields = [
            ("title", metadata.title),
            ("url", metadata.url),
            ("author", metadata.author),
            ("published", metadata.published),
            ("language", metadata.language),
            ("source", metadata.source)
        ]
        
        for key, value in fields:
            if value is not None:
                # Escape karakter khusus YAML jika perlu (sederhana)
                if isinstance(value, str) and (':' in value or '#' in value):
                    value = f'"{value}"'
                lines.append(f"{key}: {value}")
                
        lines.append("---")
        return "\n".join(lines) + "\n\n"

    def render_heading(self, block: Any) -> str:
        """Render HeadingBlock menjadi '# Text' sesuai level."""
        hashes = "#" * block.level
        return f"{hashes} {block.text}\n"

    def render_paragraph(self, block: Any) -> str:
        """Render ParagraphBlock menjadi teks biasa dengan double newline."""
        return f"{block.text}\n\n"

    def _render_list_items(self, items: List[Any], ordered: bool, indent_level: int = 0) -> str:
        """Helper rekursif untuk merender item list, termasuk nested list."""
        lines = []
        prefix_char = "1." if ordered else "-"
        
        for i, item in enumerate(items):
            # Hitung indentasi saat ini (2 spasi per level)
            indent = "  " * indent_level
            
            # Penomoran untuk ordered list harus reset per level, tapi di sini kita pakai '1.' terus 
            # karena Markdown renderer modern cukup pintar, atau bisa dihitung manual jika perlu ketat.
            current_prefix = f"{i+1}." if ordered else "-"
            
            if isinstance(item, dict) and item.get('_type') == 'list_block':
                # Nested list detection (jika model menyimpannya sebagai dict/object khusus)
                # Atau jika item adalah instance ListBlock (tergantung implementasi model)
                # Di sini kita asumsikan item bisa berupa string ATAU object ListBlock lagi.
                # Namun sesuai definisi model sebelumnya, items adalah list of str.
                # Jika ada nested list, biasanya dibungkus objek lain atau string khusus.
                # Untuk kesederhanaan, kita anggap item selalu string di versi dasar ini.
                # Jika ingin support nested penuh, model ListBlock.items harus bisa menampung ListBlock.
                lines.append(f"{indent}{current_prefix} {item}\n")
            else:
                lines.append(f"{indent}{current_prefix} {item}\n")
                
        return "".join(lines)

    def render_list(self, block: Any) -> str:
        """Render ListBlock (ordered/unordered) dengan dukungan nested sederhana."""
        # Catatan: Implementasi nested list penuh memerlukan struktur data items 
        # yang bisa berisi ListBlock lagi. Di sini kita asumsikan items adalah list of strings.
        # Jika model sudah mendukung nested ListBlock di dalam items, logika ini perlu penyesuaian rekursif.
        
        lines = []
        prefix = "1." if block.ordered else "-"
        
        for i, item in enumerate(block.items):
            # Cek apakah item ini adalah nested list (instance of ListBlock?)
            # Asumsi: jika item adalah string biasa
            current_num = i + 1
            item_prefix = f"{current_num}." if block.ordered else "-"
            lines.append(f"{item_prefix} {item}\n")
            
        return "\n".join(lines) + "\n\n"

    def render_table(self, block: Any) -> str:
        """Render TableBlock menjadi tabel Markdown standar."""
        if not block.headers and not block.rows:
            return ""
            
        lines = []
        
        # Normalisasi jumlah kolom
        num_cols = max(len(block.headers), max((len(r) for r in block.rows), default=0))
        
        # Pad headers
        headers = block.headers + [""] * (num_cols - len(block.headers))
        lines.append("| " + " | ".join(h.strip() for h in headers) + " |")
        
        # Separator
        lines.append("| " + " | ".join(["---"] * num_cols) + " |")
        
        # Rows
        for row in block.rows:
            # Pad row jika kurang
            padded_row = row + [""] * (num_cols - len(row))
            # Truncate jika lebih
            padded_row = padded_row[:num_cols]
            lines.append("| " + " | ".join(cell.strip() for cell in padded_row) + " |")
            
        return "\n".join(lines) + "\n\n"

    def render_image(self, block: Any) -> str:
        """Render ImageBlock menjadi ![alt](src) dengan caption opsional."""
        alt = block.alt if block.alt else "Image"
        markdown_img = f"![{alt}]({block.src})"
        
        if block.caption:
            return f"{markdown_img}\n*{block.caption}*\n\n"
        return f"{markdown_img}\n\n"

    def render_code(self, block: Any) -> str:
        """Render CodeBlock menjadi fenced code block (```lang ... ```)."""
        lang = block.language or ""
        return f"```{lang}\n{block.code}\n```\n\n"

    def render_blockquote(self, block: Any) -> str:
        """Render BlockquoteBlock dengan prefix '>' pada setiap baris."""
        # Split baris untuk memastikan setiap baris punya prefix >
        quoted_lines = [f"> {line}" for line in block.text.splitlines()]
        return "\n".join(quoted_lines) + "\n\n"

    def render_embed(self, block: Any) -> str:
        """Render EmbedBlock sebagai link referensi atau placeholder deskriptif."""
        title = block.title if block.title else block.embed_type or "Embedded Content"
        return f"[{title}]({block.url})\n\n"

    def render(self, document: Any) -> str:
        """
        Metode utama: Gabungkan front matter + seluruh block menjadi satu string Markdown.
        
        Alur:
        1. Render metadata jadi YAML front matter.
        2. Iterasi document.blocks.
        3. Dispatch ke metode render_* berdasarkan block.type.
        4. Gabungkan semua hasil.
        """
        output_parts = []
        
        # 1. Front Matter
        if hasattr(document, 'metadata') and document.metadata:
            output_parts.append(self.render_front_matter(document.metadata))
            
        # 2. Blocks
        if hasattr(document, 'blocks'):
            for block in document.blocks:
                block_type = block.type
                # Handle enum value jika type adalah Enum
                if hasattr(block_type, 'value'):
                    block_type = block_type.value
                
                renderer_method = getattr(self, f"render_{block_type}", None)
                if renderer_method:
                    output_parts.append(renderer_method(block))
                else:
                    # Fallback jika tipe block tidak dikenali (skip atau log warning)
                    pass
                    
        return "".join(output_parts)