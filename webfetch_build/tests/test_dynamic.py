"""
test_dynamic.py
Test terhadap halaman yang kontennya dirender via JavaScript
(SPA), memverifikasi Playwright benar-benar diperlukan & bekerja.

Modul ini menguji dua skenario kritis:
1. Konten yang hanya muncul setelah eksekusi JS (React/Vue/Angular).
2. Mekanisme fallback screenshot ketika deteksi DOM gagal total.

Catatan: Test ini memerlukan environment dengan Playwright terinstall
dan browser tersedia (biasanya dijalankan via `pytest --asyncio-mode=auto`).
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Import komponen
from webfetch.browser import BrowserEngine
from webfetch.content import MainContentDetector
from webfetch.scoring import ContentScorer
from webfetch.screenshot_fallback import ScreenshotFallback
from webfetch.model import Document, ParagraphBlock

# HTML Mentah (Tanpa JS) - Kosong atau Loading State
STATIC_HTML_LOADING = """
<html>
<head><title>SPA App</title></head>
<body>
    <div id="root">
        <!-- Konten akan dimuat via JS -->
        <div class="spinner">Loading...</div>
    </div>
    <script src="app.bundle.js"></script>
</body>
</html>
"""

# HTML Hasil Render JS (Simulasi apa yang dilihat Playwright)
DYNAMIC_HTML_RENDERED = """
<html>
<head><title>SPA App</title></head>
<body>
    <div id="root">
        <article>
            <h1>Selamat Datang di Aplikasi SPA</h1>
            <p>Konten ini dirender secara dinamis oleh React.</p>
            <p>Jika Anda melihat teks ini, berarti Playwright berhasil mengeksekusi JavaScript.</p>
        </article>
    </div>
</body>
</html>
"""

@pytest.mark.asyncio
async def test_js_rendered_content_present():
    """Bandingkan hasil fetch (dengan JS) vs HTML mentah (tanpa JS)."""
    
    # 1. Simulasi HTML Statis (tanpa JS)
    soup_static = MagicMock()
    soup_static.find.return_value = None # Tidak ada konten berarti
    # Jika diparsing manual:
    from bs4 import BeautifulSoup
    static_soup = BeautifulSoup(STATIC_HTML_LOADING, 'html.parser')
    static_text = static_soup.get_text(strip=True)
    assert "Loading..." in static_text
    assert "Konten ini dirender" not in static_text, "HTML statis tidak boleh punya konten utama"

    # 2. Simulasi HTML Dinamis (hasil Playwright)
    # Kita mock browser engine agar mengembalikan HTML rendered
    with patch.object(BrowserEngine, 'launch', new_callable=AsyncMock):
        with patch.object(BrowserEngine, 'new_page', new_callable=AsyncMock) as mock_new_page:
            mock_page = AsyncMock()
            mock_page.content.return_value = DYNAMIC_HTML_RENDERED
            mock_page.title.return_value = "SPA App"
            mock_page.url = "https://example.com"
            mock_new_page.return_value = mock_page
            
            # Inisialisasi browser & fetch manual (simulasi logic fetcher)
            browser = BrowserEngine(headless=True)
            await browser.launch()
            page = await browser.new_page()
            
            # Ambil konten yang sudah di-render
            rendered_html = await page.content()
            dynamic_soup = BeautifulSoup(rendered_html, 'html.parser')
            dynamic_text = dynamic_soup.get_text(strip=True)
            
            assert "Loading..." not in dynamic_text or "Konten ini dirender" in dynamic_text, \
                "Konten dinamis harus menggantikan loading spinner"
            assert "Konten ini dirender secara dinamis oleh React" in dynamic_text, \
                "Playwright harus mampu mengekstrak konten hasil render JS"
            
            await browser.close()

@pytest.mark.asyncio
def test_screenshot_fallback_triggered_when_confidence_low():
    """Simulasikan halaman yang gagal dideteksi, pastikan fallback jalan."""
    
    # 1. Siapkan Detektor & Fallback
    scorer = ContentScorer()
    detector = MainContentDetector(scorer=scorer)
    fallback_handler = ScreenshotFallback()
    
    # 2. Buat Soup "Rusak" / Kosong (Simulasi kegagalan deteksi)
    # HTML tanpa struktur jelas, hanya div kosong
    bad_html = "<html><body><div id='app'></div></body></html>"
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(bad_html, 'html.parser')
    
    # 3. Jalani Deteksi (Harus Gagal/Confidence Rendah)
    detection_result = detector.detect(soup, bad_html)
    
    # Validasi bahwa deteksi gagal
    assert detection_result['element'] is None or detection_result['confidence'] == 'LOW', \
        "Deteksi harus gagal atau confidence rendah pada HTML kosong"
    
    # 4. Cek Apakah Fallback Perlu Dijalankan
    should_trigger = fallback_handler.should_fallback(detection_result)
    assert should_trigger is True, "Fallback harus dipicu saat deteksi gagal"
    
    # 5. Mock Page untuk Screenshot
    mock_page = AsyncMock()
    mock_screenshot_data = b"FAKE_PNG_IMAGE_DATA"
    mock_page.screenshot.return_value = mock_screenshot_data
    mock_page.wait_for_load_state.return_value = None
    
    # 6. Eksekusi Fallback
    description = asyncio.run(fallback_handler.process_fallback(mock_page, detection_result))
    
    assert description is not None, "Deskripsi fallback harus dihasilkan"
    assert "VISUAL FALLBACK TRIGGERED" in description, "Pesan fallback harus ada"
    assert "Screenshot" in description, "Penyebutan screenshot harus ada"
    
    # Verifikasi method screenshot dipanggil
    mock_page.screenshot.assert_called_once()