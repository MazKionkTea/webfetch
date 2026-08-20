"""
Paket webfetch.
Entry point publik: fungsi async fetch() untuk konversi satu URL
ke Markdown/format lain, dengan Document Model sebagai representasi antara.

Modul ini mengorkestrasi seluruh pipeline pemrosesan dari awal (URL mentah)
hingga akhir (Document Model terstruktur), menyediakan antarmuka sederhana
bagi pengguna atau modul CLI.
"""

__version__ = "0.1.0"

from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Import komponen pipeline (pastikan urutan import sesuai dependensi)
from .model import Document, Metadata
from .browser import BrowserEngine
from .robots import RobotsChecker, RateLimiter
from .cache import FetchCache
from .fetcher import Fetcher
from .content_type import detect_content_type, ContentDispatcher
from .metadata import MetadataExtractor
from .cleaner import DOMCleaner
from .boilerplate import BoilerplateLearner
from .scoring import ContentScorer
from .content import MainContentDetector
from .semantic import SemanticExtractor
from .links import LinkExtractor
from .images import ImageExtractor
from .tables import TableExtractor
from .embeds import EmbedExtractor
from .renderers.markdown import MarkdownRenderer
from .renderers.json import JSONRenderer
from .renderers.txt import TXTRenderer
from .errors import FetchError, RobotsDisallowedError, UnsupportedContentTypeError

@dataclass
class FetchResult:
    """
    Container hasil proses fetch lengkap.
    
    Attributes:
        document: Objek Document Model utama (jika sukses).
        markdown: String hasil render Markdown (jika diminta).
        json_str: String hasil render JSON (jika diminta).
        text_str: String hasil render TXT (jika diminta).
        raw_html: HTML mentah sebelum diproses (opsional, untuk debug).
        error: Pesan error jika proses gagal (None jika sukses).
    """
    document: Optional[Document] = None
    markdown: Optional[str] = None
    json_str: Optional[str] = None
    text_str: Optional[str] = None
    raw_html: Optional[str] = None
    error: Optional[str] = None


async def fetch(url: str, output: str = "markdown", javascript: bool = True,
                extract_images: bool = True, extract_links: bool = True,
                extract_metadata: bool = True, timeout: int = 30) -> FetchResult:
    """
    Fungsi utama: jalankan seluruh pipeline webfetch untuk satu URL.
    
    Alur eksekusi:
    1. Inisialisasi komponen (Browser, Robots, Cache, RateLimiter).
    2. Cek robots.txt & cache.
    3. Fetch HTML via Playwright (Fetcher).
    4. Deteksi tipe konten (ContentDispatcher).
    5. Ekstrak Metadata (MetadataExtractor).
    6. Bersihkan DOM (DOMCleaner, BoilerplateLearner).
    7. Deteksi konten utama (MainContentDetector).
    8. Ekstrak blok semantik (SemanticExtractor).
    9. Ekstrak aset tambahan (Links, Images, Tables, Embeds) -> injeksi ke blocks.
    10. Bangun objek Document Model.
    11. Render ke format output yang diminta (Markdown/JSON/TXT).
    
    Args:
        url: URL target untuk di-fetch.
        output: Format output yang diinginkan ('markdown', 'json', 'txt', 'all').
        javascript: Jika True, gunakan browser untuk render JS. Jika False, coba fetch statis (belum didukung penuh).
        extract_images: Jika True, sertakan ImageBlock dalam hasil.
        extract_links: Jika True, sertakan ekstraksi link (saat ini hanya internal logic, bisa dikembangkan).
        extract_metadata: Jika True, isi field metadata dokumen.
        timeout: Batas waktu operasi dalam detik.
        
    Returns:
        FetchResult: Objek dataclass berisi dokumen hasil konversi atau error.
        
    Contoh penggunaan:
        result = await fetch("https://example.com/artikel", output="markdown")
        if result.error:
            print(f"Gagal: {result.error}")
        else:
            print(result.markdown)
    """
    try:
        # 1. Inisialisasi Komponen Dasar
        user_agent = "webfetch/0.1.0 (compatible; +https://github.com/user/webfetch)"
        robots_checker = RobotsChecker(user_agent=user_agent)
        rate_limiter = RateLimiter(default_delay=1.0)
        cache = FetchCache()
        browser = BrowserEngine(headless=True, user_agent=user_agent)
        
        fetcher = Fetcher(browser, robots_checker, rate_limiter, cache)
        
        # 2. Eksekusi Fetch
        # Normalisasi URL awal
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        # Ambil data mentah
        fetch_data = await fetcher.fetch(url, javascript=javascript, retries=2)
        html = fetch_data.get("html")
        final_url = fetch_data.get("final_url", url)
        title_raw = fetch_data.get("title", "")
        
        if not html:
            return FetchResult(error="Konten HTML kosong diterima.")

        # 3. Deteksi Tipe Konten
        # Asumsi fetcher mengembalikan headers juga jika diperlukan, disini kita simulasi
        headers = {"content-type": "text/html"} 
        content_type = detect_content_type(headers, final_url)
        
        dispatcher = ContentDispatcher()
        try:
            dispatch_result = dispatcher.dispatch(content_type, html, final_url)
        except UnsupportedContentTypeError as e:
            return FetchResult(error=str(e))
            
        if dispatch_result[0] != 'html_pipeline':
            # Handle non-HTML (PDF/Image) secara khusus jika diperlukan
            # Saat ini kita fokus ke HTML pipeline
            pass
            
        # 4. Parsing & Ekstraksi Metadata
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        metadata_obj = Metadata(url=final_url)
        if extract_metadata:
            meta_extractor = MetadataExtractor()
            metadata_obj = meta_extractor.extract_all(soup, url=final_url)
            
        # 5. Pembersihan DOM
        cleaner = DOMCleaner()
        cleaner.clean(soup)
        
        # 6. Boilerplate Learning (Opsional, butuh sample sebelumnya)
        # Untuk single fetch, kita skip atau inisialisasi baru
        boilerplate_learner = BoilerplateLearner()
        # boilerplate_learner.collect_page_samples(domain, str(soup)) 
        # soup = boilerplate_learner.strip_boilerplate(soup, domain)
        
        # 7. Deteksi Main Content
        scorer = ContentScorer()
        detector = MainContentDetector(scorer=scorer)
        detection = detector.detect(soup, html)
        
        main_element = detection.get("element")
        if not main_element:
            # Fallback: gunakan body jika deteksi gagal total
            main_element = soup.find('body') or soup
            
        # 8. Ekstraksi Semantik ke Blocks
        semantic_extractor = SemanticExtractor()
        blocks = semantic_extractor.extract_all(main_element)
        
        # 9. Ekstraksi Aset Tambahan & Injeksi ke Blocks
        # Images
        if extract_images:
            img_extractor = ImageExtractor()
            images = img_extractor.extract_images(main_element, base_url=final_url)
            # Konversi dict image ke ImageBlock dan tambahkan ke blocks
            for img_data in images:
                # Hindari duplikasi jika sudah diekstrak semantic extractor
                # (Logic sederhana: cek src apakah sudah ada di blocks existing)
                exists = any(
                    hasattr(b, 'src') and b.src == img_data['src'] 
                    for b in blocks if hasattr(b, 'src')
                )
                if not exists:
                    from .model import ImageBlock, ConfidenceLevel
                    blocks.append(ImageBlock(
                        type="image",
                        confidence=ConfidenceLevel.MEDIUM,
                        src=img_data['src'],
                        alt=img_data['alt'],
                        caption=img_data['caption']
                    ))
                    
        # Embeds
        embed_extractor = EmbedExtractor()
        embeds = embed_extractor.extract_all(main_element)
        blocks.extend(embeds)
        
        # Tables (Sudah ditangani semantic_extractor, tapi bisa diperkaya lagi jika perlu)
        
        # Links (Saat ini hanya ekstraksi info, tidak mengubah struktur blocks kecuali mau membuat LinkBlock khusus)
        if extract_links:
            link_extractor = LinkExtractor()
            links = link_extractor.extract_links(main_element, final_url)
            # Bisa disimpan di metadata atau diabaikan untuk output markdown biasa
            
        # 10. Bangun Document Model
        document = Document(
            url=final_url,
            metadata=metadata_obj,
            blocks=blocks
        )
        
        # 11. Render Output
        result = FetchResult(document=document, raw_html=html)
        
        if output == "markdown" or output == "all":
            renderer_md = MarkdownRenderer()
            result.markdown = renderer_md.render(document)
            
        if output == "json" or output == "all":
            renderer_json = JSONRenderer()
            result.json_str = renderer_json.render(document)
            
        if output == "txt" or output == "all":
            renderer_txt = TXTRenderer()
            result.text_str = renderer_txt.render(document)
            
        return result

    except RobotsDisallowedError as e:
        return FetchResult(error=f"Blocked by robots.txt: {e.url}")
    except FetchError as e:
        return FetchResult(error=f"Fetch failed: {e.message}")
    except Exception as e:
        return FetchResult(error=f"Unexpected error: {str(e)}")
    finally:
        # Cleanup browser jika masih terbuka (seharusnya di-handle fetcher, tapi jaga-jaga)
        # Dalam implementasi nyata, pastikan loop event asyncio menangani ini dengan baik
        pass