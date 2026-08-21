"""
test_metadata.py
Test ekstraksi & prioritas sumber metadata: JSON-LD > OG > meta > title.

Modul ini memverifikasi logika `MetadataExtractor` dalam menggabungkan
data dari berbagai sumber HTML dengan hierarki prioritas yang benar.
Ini krusial untuk memastikan akurasi data dokumen (judul, penulis, tanggal)
yang akan digunakan sebagai konteks LLM atau metadata RAG.
"""

import pytest
from bs4 import BeautifulSoup
from webfetch.metadata import MetadataExtractor

# Skenario 1: Konflik Data (JSON-LD vs OG vs Meta)
# JSON-LD mengatakan judul "Judul Asli Artikel", OG mengatakan "Judul Clickbait"
SAMPLE_CONFLICT_HTML = """
<html>
<head>
    <title>Judul Default Browser</title>
    <meta name="author" content="Meta Author">
    <meta property="og:title" content="Judul Clickbait Media Sosial">
    <meta property="og:description" content="Deskripsi OG">
    
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": "Judul Asli Artikel (JSON-LD)",
        "author": {
            "@type": "Person",
            "name": "JSON-LD Author"
        },
        "datePublished": "2023-10-01T08:00:00Z",
        "description": "Deskripsi Lengkap JSON-LD"
    }
    </script>
</head>
<body>
    <h1>Konten Halaman</h1>
</body>
</html>
"""

# Skenario 2: Minim Metadata (Hanya Title Tag)
SAMPLE_MINIMAL_HTML = """
<html>
<head>
    <title>Hanya Judul di Title Tag</title>
</head>
<body>
    <p>Tanpa meta tag, tanpa OG, tanpa JSON-LD.</p>
</body>
</html>
"""

def test_json_ld_takes_priority_over_og_tags():
    """Kalau JSON-LD & OG tag beda, JSON-LD yang dipakai."""
    
    soup = BeautifulSoup(SAMPLE_CONFLICT_HTML, 'html.parser')
    extractor = MetadataExtractor()
    metadata = extractor.extract_all(soup, url="https://example.com/artikel")
    
    # 1. Validasi Judul (Headline)
    # Prioritas: JSON-LD ("Judul Asli Artikel (JSON-LD)") > OG ("Judul Clickbait...")
    assert metadata.title == "Judul Asli Artikel (JSON-LD)", \
        f"Judul harus dari JSON-LD, didapat: {metadata.title}"
    
    # 2. Validasi Penulis
    # Prioritas: JSON-LD ("JSON-LD Author") > Meta ("Meta Author")
    assert metadata.author == "JSON-LD Author", \
        f"Penulis harus dari JSON-LD, didapat: {metadata.author}"
        
    # 3. Validasi Tanggal Publikasi
    # Hanya ada di JSON-LD
    assert metadata.published == "2023-10-01T08:00:00Z", \
        f"Tanggal harus dari JSON-LD, didapat: {metadata.published}"

    # 4. Validasi Sumber Dominan
    assert metadata.source == "json-ld", \
        "Field source harus mengindikasikan json-ld sebagai sumber utama"


def test_falls_back_to_title_tag_when_no_other_source():
    """Kalau tidak ada meta/OG/JSON-LD sama sekali, pakai <title>."""
    
    soup = BeautifulSoup(SAMPLE_MINIMAL_HTML, 'html.parser')
    extractor = MetadataExtractor()
    metadata = extractor.extract_all(soup, url="https://example.com/minimal")
    
    # 1. Validasi Judul
    # Fallback terakhir ke <title>
    assert metadata.title == "Hanya Judul di Title Tag", \
        f"Judul harus fallback ke title tag, didapat: {metadata.title}"
        
    # 2. Validasi Field Lain Kosong
    assert metadata.author is None, "Penulis harus None karena tidak ada data"
    assert metadata.published is None, "Tanggal harus None karena tidak ada data"
    assert metadata.description is None, "Deskripsi harus None karena tidak ada data"
    
    # 3. Validasi Sumber Dominan
    assert metadata.source == "title-tag", \
        f"Field source harus 'title-tag', didapat: {metadata.source}"


def test_og_fills_gap_when_json_ld_partial():
    """Jika JSON-LD ada tapi tidak lengkap, OG mengisi kekosongan."""
    
    # JSON-LD hanya punya judul, OG punya deskripsi
    html_partial = """
    <html>
    <head>
        <title>Fallback Title</title>
        <meta property="og:description" content="Deskripsi dari Open Graph">
        <meta property="og:image" content="image.jpg">
        <script type="application/ld+json">
        {
            "@type": "Article",
            "headline": "Judul Dari JSON-LD"
            // Tidak ada author/description di sini
        }
        </script>
    </head>
    </html>
    """
    
    soup = BeautifulSoup(html_partial, 'html.parser')
    extractor = MetadataExtractor()
    metadata = extractor.extract_all(soup, url="https://example.com/partial")
    
    # Judul dari JSON-LD
    assert metadata.title == "Judul Dari JSON-LD"
    
    # Deskripsi HARUS diisi oleh OG karena JSON-LD kosong di field ini
    # Catatan: Implementasi merge_metadata_sources harus mendukung logika "fill gaps"
    # Jika implementasi saat ini hanya mengambil prioritas tertinggi dan mengabaikan sisanya,
    # maka test ini mungkin gagal tergantung strategi merge. 
    # Asumsi implementasi kita melakukan merge per-field (field-level merging).
    assert metadata.description == "Deskripsi dari Open Graph", \
        "Deskripsi harus diambil dari OG karena JSON-LD tidak menyediakannya"