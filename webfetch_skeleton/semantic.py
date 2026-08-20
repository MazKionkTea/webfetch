"""
semantic.py
Ekstraksi struktur semantik dari elemen main-content yang sudah
ditemukan content.py: heading, paragraf, list, code, blockquote.
(Tabel, gambar, link, embed masing-masing punya modul sendiri.)
"""


class SemanticExtractor:
    """Ubah elemen HTML main-content menjadi list Block di Document Model."""

    def extract_heading(self, element) -> "HeadingBlock":
        # TODO: level dari nama tag h1-h6
        pass

    def extract_paragraph(self, element) -> "ParagraphBlock":
        # TODO
        pass

    def extract_list(self, element) -> "ListBlock":
        """Dukung <ul>/<ol>, termasuk nested list di dalam <li>."""
        # TODO
        pass

    def extract_code_block(self, element) -> "CodeBlock":
        """Ekstraksi <pre><code class="language-X">, ambil X sebagai bahasa."""
        # TODO
        pass

    def extract_blockquote(self, element) -> "BlockquoteBlock":
        # TODO
        pass

    def extract_all(self, main_content_element) -> list:
        """Iterasi children elemen main-content, dispatch ke extract_* sesuai tag."""
        # TODO: mapping tag -> method (h1-h6, p, ul/ol, pre, blockquote, table, img, iframe)
        pass
