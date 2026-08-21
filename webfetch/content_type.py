"""
content_type.py
Deteksi Content-Type hasil fetch dan pencabangan alur: HTML lanjut
ke pipeline normal, PDF didelegasikan ke pipeline pdf2markdown,
tipe lain (gambar/video) ditangani sebagai block tunggal atau ditolak.
"""


from typing import Any, Optional, Tuple
from urllib.parse import urlparse
from .errors import UnsupportedContentTypeError


def detect_content_type(headers: dict, url: str) -> str:
    """
    Menentukan tipe konten utama dari respons HTTP.
    
    Prioritas deteksi:
    1. Header 'Content-Type' dari server (paling akurat).
    2. Ekstensi file pada URL jika header ambigu atau tidak ada (fallback).
    
    Args:
        headers: Dictionary header HTTP respons (kunci case-insensitive).
        url: URL sumber untuk analisis ekstensi file fallback.
        
    Returns:
        str: Tipe konten sederhana dalam format 'category/subcategory' atau 'unknown'.
             Contoh: 'text/html', 'application/pdf', 'image/jpeg', 'unknown'.
    """
    # Normalisasi kunci header agar case-insensitive
    headers_lower = {k.lower(): v for k, v in headers.items()}
    content_type_header = headers_lower.get('content-type', '')
    
    if content_type_header:
        # Ambil bagian utama sebelum parameter (misal: 'text/html; charset=utf-8' -> 'text/html')
        main_type = content_type_header.split(';')[0].strip().lower()
        return main_type
    
    # Fallback: Analisis ekstensi URL
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    if path.endswith('.html') or path.endswith('.htm'):
        return 'text/html'
    elif path.endswith('.pdf'):
        return 'application/pdf'
    elif path.endswith('.json'):
        return 'application/json'
    elif path.endswith('.xml'):
        return 'application/xml'
    elif any(path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']):
        return 'image'
    elif any(path.endswith(ext) for ext in ['.mp4', '.webm', '.ogg']):
        return 'video'
    elif any(path.endswith(ext) for ext in ['.mp3', '.wav', '.flac']):
        return 'audio'
    
    return 'unknown'


class ContentDispatcher:
    """
    Dispatcher yang mengarahkan konten mentah hasil fetch ke pipeline pemrosesan yang sesuai.
    
    Kelas ini bertindak sebagai switchboard berdasarkan tipe konten yang terdeteksi:
    - HTML: Diteruskan ke pipeline pembersihan dan ekstraksi standar.
    - PDF: Didelegasikan ke engine konversi PDF (misal: pdf2markdown).
    - Gambar/Audio/Video: Dibungkus menjadi block media tunggal.
    - Tipe lain: Melempar exception jika tidak didukung.
    
    Metode `dispatch` mengembalikan tuple (strategy, payload) dimana strategy menentukan
    langkah selanjutnya bagi caller (cli.py atau orchestrator utama).
    """

    def dispatch(self, content_type: str, raw_content: Any, url: str) -> Tuple[str, Any]:
        """
        Mengarahkan konten berdasarkan tipe yang terdeteksi.
        
        Args:
            content_type: String tipe MIME (hasil dari `detect_content_type`).
            raw_content: Data mentah konten (biasanya string bytes atau str).
            url: URL sumber konten.
            
        Returns:
            tuple: (strategy_name, payload_data)
                   - strategy_name: 'html_pipeline', 'pdf_convert', 'media_block', atau 'error'.
                   - payload_data: Data yang siap diproses langkah berikutnya, atau exception.
                   
        Raises:
            UnsupportedContentTypeError: Jika tipe konten tidak dikenali atau tidak didukung.
        """
        ct = content_type.split(';')[0].strip().lower()
        
        # 1. HTML Pipeline (Standar)
        if ct in ['text/html', 'application/xhtml+xml']:
            # Pastikan konten adalah string unicode
            if isinstance(raw_content, bytes):
                raw_content = raw_content.decode('utf-8', errors='ignore')
            return ('html_pipeline', {'html': raw_content, 'url': url})
        
        # 2. PDF Converter
        elif ct == 'application/pdf':
            # Kembalikan binary data untuk diproses engine PDF eksternal
            return ('pdf_convert', {'pdf_data': raw_content, 'url': url})
        
        # 3. Media Langsung (Image/Audio/Video) -> Bungkus jadi Block
        elif ct.startswith('image/'):
            return ('media_block', {
                'type': 'image',
                'mime': ct,
                'url': url,
                'data': raw_content # Bisa base64 atau binary
            })
        
        elif ct.startswith('video/') or ct.startswith('audio/'):
             return ('media_block', {
                'type': 'video' if ct.startswith('video/') else 'audio',
                'mime': ct,
                'url': url,
                'data': raw_content
            })

        # 4. JSON/XML (Opsional: bisa langsung di-parse atau dilempar ke parser khusus)
        elif ct in ['application/json', 'application/xml', 'text/xml']:
             if isinstance(raw_content, bytes):
                raw_content = raw_content.decode('utf-8', errors='ignore')
             return ('raw_text', {'content': raw_content, 'mime': ct, 'url': url})

        # 5. Tidak Didukung
        else:
            raise UnsupportedContentTypeError(url=url, content_type=content_type)