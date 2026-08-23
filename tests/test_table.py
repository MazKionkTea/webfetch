"""
test_table.py
Test ekstraksi tabel HTML ke TableBlock & rendering ke Markdown table.

Modul ini memverifikasi komponen `TableExtractor` dan `MarkdownRenderer`
dalam menangani struktur tabel HTML yang bervariasi (dengan/s tanpa thead,
rowspan/colspan sederhana, dll) dan memastikan output Markdown tetap rapi.
"""

import pytest
from bs4 import BeautifulSoup
from webfetch.tables import TableExtractor
from webfetch.model import TableBlock
from webfetch.renderers.markdown import MarkdownRenderer

# Skenario 1: Tabel Standar dengan <thead> dan <tbody>
SAMPLE_TABLE_WITH_THEAD = """
<table>
    <thead>
        <tr>
            <th>Nama</th>
            <th>Usia</th>
            <th>Kota</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Alice</td>
            <td>25</td>
            <td>Jakarta</td>
        </tr>
        <tr>
            <td>Bob</td>
            <td>30</td>
            <td>Bandung</td>
        </tr>
    </tbody>
</table>
"""

# Skenario 2: Tabel Sederhana Tanpa <thead> (Implisit)
SAMPLE_TABLE_WITHOUT_THEAD = """
<table>
    <tr>
        <th>Produk</th>
        <th>Harga</th>
    </tr>
    <tr>
        <td>Laptop</td>
        <td>10 Juta</td>
    </tr>
    <tr>
        <td>Mouse</td>
        <td>100 Ribu</td>
    </tr>
</table>
"""

# Skenario 3: Tabel Tidak Rata (Jumlah kolom berbeda)
SAMPLE_TABLE_UNEVEN = """
<table>
    <tr>
        <th>Kolom A</th>
        <th>Kolom B</th>
    </tr>
    <tr>
        <td>Data 1</td>
        <!-- Kolom B kosong di baris ini -->
    </tr>
    <tr>
        <td>Data 2</td>
        <td>Data 2B</td>
        <td>Data 2C (Extra)</td>
    </tr>
</table>
"""

def test_table_with_thead_tbody():
    """<thead>/<tbody> terparse jadi headers/rows yang benar."""
    
    soup = BeautifulSoup(SAMPLE_TABLE_WITH_THEAD, 'html.parser')
    table_tag = soup.find('table')
    
    extractor = TableExtractor()
    result = extractor.extract_and_normalize(table_tag)
    
    headers = result['headers']
    rows = result['rows']
    
    # Validasi Header
    assert len(headers) == 3, "Harus ada 3 kolom header"
    assert headers == ["Nama", "Usia", "Kota"], f"Isi header salah: {headers}"
    
    # Validasi Rows
    assert len(rows) == 2, "Harus ada 2 baris data"
    assert rows[0] == ["Alice", "25", "Jakarta"], f"Baris pertama salah: {rows[0]}"
    assert rows[1] == ["Bob", "30", "Bandung"], f"Baris kedua salah: {rows[1]}"


def test_table_without_thead_uses_first_row():
    """Tabel tanpa <thead> memakai baris <tr> pertama sebagai header."""
    
    soup = BeautifulSoup(SAMPLE_TABLE_WITHOUT_THEAD, 'html.parser')
    table_tag = soup.find('table')
    
    extractor = TableExtractor()
    result = extractor.extract_and_normalize(table_tag)
    
    headers = result['headers']
    rows = result['rows']
    
    # Validasi Header (diambil dari tr pertama yang berisi th)
    assert len(headers) == 2, "Harus ada 2 kolom header"
    assert headers == ["Produk", "Harga"], f"Isi header salah: {headers}"
    
    # Validasi Rows (sisa baris)
    assert len(rows) == 2, "Harus ada 2 baris data (setelah header)"
    assert rows[0] == ["Laptop", "10 Juta"], f"Baris pertama salah: {rows[0]}"
    assert rows[1] == ["Mouse", "100 Ribu"], f"Baris kedua salah: {rows[1]}"


def test_table_normalization_handles_uneven_columns():
    """Normalisasi tabel harus menangani baris dengan jumlah kolom tidak sama."""
    
    soup = BeautifulSoup(SAMPLE_TABLE_UNEVEN, 'html.parser')
    table_tag = soup.find('table')
    
    extractor = TableExtractor()
    result = extractor.extract_and_normalize(table_tag)
    
    headers = result['headers']
    rows = result['rows']
    
    # Header punya 2 kolom awal, tapi normalisasi menyesuaikan dengan row terpanjang (3 kolom)
    # Maka header akan di-padding jadi 3: ["Kolom A", "Kolom B", ""]
    assert len(headers) == 3, "Header harus di-padding mengikuti kolom terbanyak"
    
    # Baris 1: Hanya 1 sel ("Data 1"), harus di-padding jadi 3
    assert len(rows[0]) == 3, "Baris pendek harus di-padding"
    assert rows[0] == ["Data 1", "", ""], f"Padding gagal: {rows[0]}"

    # Baris 2: Punya 3 sel, tetap 3 karena max_cols = 3
    assert len(rows[1]) == 3
    assert rows[1] == ["Data 2", "Data 2B", "Data 2C (Extra)"], f"Baris kedua salah: {rows[1]}"


def test_render_table_to_markdown():
    """Integrasi test: Pastikan TableBlock dirender jadi Markdown tabel yang valid."""
    
    # Buat TableBlock manual untuk isolasi test renderer
    block = TableBlock(
        id="test-table",
        type="table",
        confidence="HIGH",
        headers=["Item", "Qty"],
        rows=[
            ["Apel", "5"],
            ["Jeruk", "10"]
        ]
    )
    
    # Bungkus dalam Document dummy agar renderer bisa jalan
    from webfetch.model import Document, Metadata
    doc = Document(
        url="https://example.com",
        metadata=Metadata(),
        blocks=[block]
    )
    
    renderer = MarkdownRenderer()
    md_output = renderer.render(doc)
    
    # Validasi sintaks Markdown tabel
    assert "| Item | Qty |" in md_output, "Header tabel harus ada di output"
    assert "| --- | --- |" in md_output, "Pemisah header harus ada"
    assert "| Apel | 5 |" in md_output, "Baris data harus ada"
    assert "| Jeruk | 10 |" in md_output, "Baris data kedua harus ada"