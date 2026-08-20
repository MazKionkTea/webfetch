"""
tables.py
Ekstraksi <table> HTML menjadi TableBlock terstruktur
(headers + rows), siap dirender jadi tabel Markdown.
"""


class TableExtractor:
    """Parse elemen <table> HTML menjadi struktur headers/rows."""

    def extract_table(self, table_element) -> dict:
        """Parse <tr>/<th>/<td> jadi {headers: [...], rows: [[...], ...]}."""
        # TODO: tangani <thead>/<tbody> jika ada, atau <tr> pertama sebagai header
        pass

    def normalize_table(self, headers: list, rows: list) -> dict:
        """Pastikan jumlah kolom tiap baris konsisten (padding jika perlu)."""
        # TODO
        pass
