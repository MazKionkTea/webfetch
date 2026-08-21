"""
screenshot_fallback.py
Fallback visual untuk halaman yang gagal diekstrak lewat DOM
(SPA dengan canvas rendering, shadow DOM berat, dll). Analog
ocr.py di pdf2markdown — dijalankan hanya saat deteksi konten
via DOM menghasilkan confidence rendah.
"""

import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import Page

class ScreenshotFallback:
    """
    Fallback berbasis screenshot ketika ekstraksi berbasis DOM gagal atau tidak meyakinkan.
    
    Modul ini dirancang untuk menangani kasus-kasus ekstrem:
    1. **SPA Kompleks**: Aplikasi React/Vue/Angular yang merender konten utama via Canvas atau WebGL.
    2. **Shadow DOM Tertutup**: Konten tersembunyi di dalam Shadow Root yang tidak bisa diakses parser HTML biasa.
    3. **Proteksi Anti-Scraping**: Halaman yang sengaja mengacaukan struktur DOM namun tetap menampilkan visual normal.
    
    Alur Kerja:
    1. Cek hasil deteksi konten utama (`MainContentDetector`).
    2. Jika confidence 'LOW' atau elemen None, aktifkan fallback.
    3. Ambil screenshot full-page.
    4. (Opsional) Kirim ke model Vision AI untuk deskripsi, atau simpan sebagai artefak untuk review manual.
    
    Catatan:
        Pada versi awal (MVP), modul ini hanya menyimpan screenshot dan memberikan placeholder teks.
        Integrasi OCR/Vision AI memerlukan dependency eksternal (seperti pytesseract atau API cloud) 
        yang dapat ditambahkan nanti.
    """

    def __init__(self, output_dir: str = "./screenshots"):
        """
        Inisialisasi fallback handler.
        
        Args:
            output_dir: Direktori untuk menyimpan artefak screenshot jika diperlukan.
        """
        self.output_dir = output_dir
        # Threshold confidence untuk memicu fallback (bisa dikonfigurasi)
        self.confidence_threshold = "LOW" 

    def should_fallback(self, detection_result: Dict[str, Any]) -> bool:
        """
        Menentukan apakah perlu melakukan fallback berdasarkan hasil deteksi konten.
        
        Kriteria pemicu:
        1. `confidence` adalah 'LOW'.
        2. `element` adalah None (tidak ada konten yang terdeteksi sama sekali).
        3. `method_used` adalah 'none'.
        
        Args:
            detection_result: Dictionary hasil dari `MainContentDetector.detect()`.
                              Format: {'element': Tag|None, 'confidence': str, 'method_used': str}
            
        Returns:
            bool: True jika fallback diperlukan, False jika ekstraksi DOM dianggap sukses.
        """
        if not detection_result:
            return True
            
        confidence = detection_result.get("confidence", "HIGH")
        element = detection_result.get("element")
        method = detection_result.get("method_used", "none")
        
        # Trigger jika confidence rendah ATAU tidak ada elemen sama sekali
        if confidence == self.confidence_threshold or element is None:
            return True
            
        # Trigger jika metode yang dipakai 'none' (gagal total)
        if method == "none":
            return True
            
        return False

    async def capture_screenshot(self, page: Page) -> bytes:
        """
        Mengambil screenshot penuh (full-page) dari halaman saat ini.
        
        Menggunakan fitur native Playwright `full_page=True` untuk menangkap konten
        di luar viewport (perlu scroll otomatis oleh browser).
        
        Args:
            page: Objek page Playwright yang sedang aktif.
            
        Returns:
            bytes: Data biner gambar PNG dari screenshot.
            
        Raises:
            Exception: Jika proses screenshot gagal (misal: halaman belum dimuat sepenuhnya).
        """
        try:
            # Pastikan halaman sudah stabil sebelum screenshot
            await page.wait_for_load_state('networkidle')
            
            screenshot_bytes = await page.screenshot(
                full_page=True, 
                type='png',
                timeout=10000 # Timeout 10 detik untuk screenshot
            )
            return screenshot_bytes
        except Exception as e:
            # Log error atau raise kembali sesuai kebutuhan
            raise RuntimeError(f"Gagal mengambil screenshot fallback: {str(e)}") from e

    def describe_visual_content(self, screenshot: bytes) -> str:
        """
        Menghasilkan deskripsi teks atau placeholder dari screenshot.
        
        Implementasi saat ini (MVP):
        - Mengembalikan string placeholder yang menandakan kegagalan ekstraksi teks.
        - Menyertakan informasi ukuran file screenshot sebagai referensi.
        
        Rencana Pengembangan (Future):
        - Integrasi dengan model Vision-Language (seperti GPT-4V, LLaVA) untuk mendeskripsikan isi gambar.
        - Integrasi OCR (Tesseract) jika konten didominasi teks statis dalam gambar/canvas.
        
        Args:
            screenshot: Data biner gambar dari `capture_screenshot`.
            
        Returns:
            str: Deskripsi teks atau pesan placeholder.
        """
        size_kb = len(screenshot) / 1024
        
        # Placeholder untuk versi non-AI
        description = (
            "[VISUAL FALLBACK TRIGGERED]\n"
            "Ekstraksi konten berbasis DOM gagal atau memiliki keyakinan rendah.\n"
            "Konten halaman ini mungkin dirender via Canvas, WebGL, atau Shadow DOM.\n"
            f"Screenshot visual telah diambil (Ukuran: {size_kb:.2f} KB).\n"
            "Silakan periksa artefak gambar secara manual atau gunakan model Vision AI untuk analisis lebih lanjut."
        )
        
        # TODO: Di masa depan, tambahkan logika berikut:
        # if VISION_MODEL_AVAILABLE:
        #     response = vision_model.analyze(image=screenshot, prompt="Describe the main content...")
        #     return response.text
        
        return description

    async def process_fallback(self, page: Page, detection_result: Dict[str, Any]) -> Optional[str]:
        """
        Metode convenience untuk menjalankan seluruh alur fallback.
        
        Args:
            page: Objek page Playwright.
            detection_result: Hasil deteksi konten dari tahap sebelumnya.
            
        Returns:
            str | None: Deskripsi hasil fallback, atau None jika fallback tidak diperlukan.
        """
        if not self.should_fallback(detection_result):
            return None
            
        screenshot_data = await self.capture_screenshot(page)
        description = self.describe_visual_content(screenshot_data)
        
        # Opsional: Simpan file ke disk
        # import os
        # from datetime import datetime
        # filename = f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        # filepath = os.path.join(self.output_dir, filename)
        # with open(filepath, 'wb') as f: f.write(screenshot_data)
        
        return description