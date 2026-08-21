"""
test_article.py
Test terhadap artikel/blog standar: <article> jelas, heading,
paragraf, sedikit noise (nav/footer/iklan di sekitar konten utama).

Modul ini menggunakan pytest dan asyncio untuk menguji pipeline ekstraksi
pada skenario halaman artikel berita atau blog post yang umum.
"""

import pytest
import asyncio
from bs4 import BeautifulSoup

# Import komponen yang akan diuji
from webfetch.model import Document, HeadingBlock, ParagraphBlock
from webfetch.cleaner import DOMCleaner
from webfetch.scoring import ContentScorer
from webfetch.content import MainContentDetector
from webfetch.semantic import SemanticExtractor
from webfetch.metadata import MetadataExtractor

# Sample HTML Artikel Standar dengan Noise
SAMPLE_ARTICLE_HTML = """
<html>
<head>
    <title>Cara Membuat Kopi Enak - Blog Kopi</title>
    <meta name="author" content="Barista Pro">
    <meta name="description" content="Panduan lengkap membuat kopi enak di rumah.">
</head>
<body>
    <!-- Noise: Navigasi -->
    <nav class="main-nav">
        <a href="/">Home</a> | <a href="/about">About</a>
        <div class="ad-banner">IKLAN NAVIGASI</div>
    </nav>

    <!-- Konten Utama -->
    <article id="post-123">
        <header>
            <h1>Cara Membuat Kopi Enak</h1>
            <p class="meta">Diposting oleh Barista Pro</p>
        </header>
        
        <section class="content">
            <p>Kopi adalah minuman yang dinikmati jutaan orang setiap pagi. Namun, membuat kopi yang benar-benar enak memerlukan teknik khusus.</p>
            
            <h2>Pilih Biji Kopi Segar</h2>
            <p>Pastikan Anda membeli biji kopi yang baru disangrai (roasted) dalam 2-3 minggu terakhir. Hindari kopi bubuk instan jika ingin rasa otentik.</p>
            
            <h2>Giling Sebelum Seduh</h2>
            <p>Menggiling biji kopi sesaat sebelum penyeduhan mempertahankan aroma dan minyak alami yang sering hilang pada kopi bubuk kemasan.</p>
            
            <blockquote>"Kopi yang baik dimulai dari biji yang baik." - Ahli Kopi</blockquote>
            
            <p>Ikuti langkah-langkah ini untuk hasil maksimal.</p>
        </section>
    </article>

    <!-- Noise: Sidebar & Footer -->
    <aside class="sidebar">
        <div class="widget">Artikel Populer</div>
        <div class="ad-unit">IKLAN SIDEBAR BESAR</div>
    </aside>
    
    <footer>
        <p>&copy; 2023 Blog Kopi. All rights reserved.</p>
        <div class="social-share">Share on Facebook</div>
    </footer>
    
    <script>console.log("Tracking script");</script>
</body>
</html>
"""

def test_extracts_title_and_paragraphs():
    """Pastikan title & paragraf utama terambil, boilerplate terbuang."""
    
    # 1. Persiapan
    soup = BeautifulSoup(SAMPLE_ARTICLE_HTML, 'html.parser')
    
    # 2. Ekstraksi Metadata
    meta_extractor = MetadataExtractor()
    metadata = meta_extractor.extract_all(soup, url="https://example.com/kopi")
    
    assert metadata.title == "Cara Membuat Kopi Enak - Blog Kopi", "Judul harus terekstrak dari tag <title>"
    assert metadata.author == "Barista Pro", "Penulis harus terekstrak dari meta tag"
    
    # 3. Pembersihan Awal (Opsional, karena scoring cukup kuat)
    cleaner = DOMCleaner()
    cleaner.clean(soup)
    
    # Pastikan script dan nav hilang
    assert soup.find('script') is None, "Tag script harus dibuang"
    assert soup.find('nav') is None, "Tag nav harus dibuang"
    
    # 4. Deteksi Konten Utama
    scorer = ContentScorer()
    detector = MainContentDetector(scorer=scorer)
    
    # Re-parse html setelah cleaning jika diperlukan, atau pakai soup yang sudah dibersihkan
    detection = detector.detect(soup, str(soup))
    
    assert detection['element'] is not None, "Konten utama harus ditemukan"
    assert detection['confidence'] in ['HIGH', 'MEDIUM'], "Kepercayaan deteksi harus tinggi untuk artikel jelas"
    
    # Pastikan elemen yang terpilih adalah <article> atau pembungkus konten, bukan footer/sidebar
    main_elem = detection['element']
    assert main_elem.name == 'article' or 'content' in main_elem.get('class', []), "Elemen utama haruslah artikel"
    
    # 5. Ekstraksi Semantik
    extractor = SemanticExtractor()
    blocks = extractor.extract_all(main_elem)
    
    # Validasi Blok
    headings = [b for b in blocks if hasattr(b, 'type') and str(b.type) in ['heading', 'BlockType.HEADING']]
    paragraphs = [b for b in blocks if hasattr(b, 'type') and str(b.type) in ['paragraph', 'BlockType.PARAGRAPH']]
    
    assert len(headings) >= 2, "Harus ada minimal 2 heading (H1 dan H2)"
    assert len(paragraphs) >= 3, "Harus ada minimal 3 paragraf konten"
    
    # Cek konten spesifik tidak mengandung noise iklan
    all_text = " ".join([getattr(b, 'text', '') for b in blocks])
    assert "IKLAN SIDEBAR" not in all_text, "Teks iklan sidebar tidak boleh masuk ke konten utama"
    assert "Tracking script" not in all_text, "Konten script tidak boleh masuk"


def test_reading_order_preserved():
    """Pastikan urutan heading/paragraf sesuai urutan visual artikel."""
    
    soup = BeautifulSoup(SAMPLE_ARTICLE_HTML, 'html.parser')
    
    # Langsung ke deteksi dan ekstraksi (asumsikan cleaner sudah jalan di background logic)
    scorer = ContentScorer()
    detector = MainContentDetector(scorer=scorer)
    detection = detector.detect(soup, str(soup))
    
    main_elem = detection['element']
    extractor = SemanticExtractor()
    blocks = extractor.extract_all(main_elem)
    
    # Filter hanya heading dan paragraf untuk cek urutan
    content_blocks = [
        b for b in blocks 
        if hasattr(b, 'type') and str(b.type) in ['heading', 'paragraph', 'BlockType.HEADING', 'BlockType.PARAGRAPH']
    ]
    
    assert len(content_blocks) > 0, "Harus ada blok konten"
    
    # Urutan teks harus sesuai alur baca:
    # 1. Judul Utama (Cara Membuat...)
    # 2. Intro (Kopi adalah...)
    # 3. Subjudul 1 (Pilih Biji...)
    # 4. Paragraf 1 (Pastikan Anda...)
    # dst.
    
    # Ambil teks dari blok
    texts = [getattr(b, 'text', '').strip() for b in content_blocks]
    
    # Validasi urutan logis
    assert "Cara Membuat Kopi Enak" in texts[0], "Heading pertama harus judul utama"
    assert "Kopi adalah minuman" in texts[1], "Paragraf pertama harus intro"
    assert "Pilih Biji Kopi Segar" in texts[2], "Heading kedua harus subjudul pertama"
    
    # Pastikan 'Giling Sebelum Seduh' muncul SETELAH 'Pilih Biji Kopi Segar'
    idx_pilih = next(i for i, t in enumerate(texts) if "Pilih Biji" in t)
    idx_giling = next(i for i, t in enumerate(texts) if "Giling Sebelum" in t)
    
    assert idx_giling > idx_pilih, "Urutan bab harus terjaga (Giling setelah Pilih)"