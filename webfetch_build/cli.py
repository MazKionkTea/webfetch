"""
cli.py
Entry point command-line + orchestrator utama pipeline webfetch.
Menjahit semua modul jadi satu alur fetch().

Contoh pemakaian:
    webfetch https://example.com
    webfetch https://example.com -o article.md
    webfetch https://example.com --format json
    webfetch urls.txt -o ./output/
"""

import argparse
import asyncio
import sys
import os
from pathlib import Path
from typing import List, Optional

# Import komponen pipeline
from .robots import RobotsChecker, RateLimiter
from .browser import BrowserEngine
from .consent import CookieConsentHandler
from .cache import FetchCache
from .fetcher import Fetcher
from .content_type import detect_content_type, ContentDispatcher
from .metadata import MetadataExtractor
from .cleaner import DOMCleaner
from .boilerplate import BoilerplateLearner
from .scoring import ContentScorer
from .content import MainContentDetector
from .pagination import PaginationHandler
from .semantic import SemanticExtractor
from .links import LinkExtractor
from .images import ImageExtractor
from .tables import TableExtractor
from .embeds import EmbedExtractor
from .screenshot_fallback import ScreenshotFallback
from .model import Document, Metadata
from .renderers.markdown import MarkdownRenderer
from .renderers.json import JSONRenderer
from .renderers.txt import TXTRenderer
from .errors import FetchError, RobotsDisallowedError, UnsupportedContentTypeError


async def fetch_single_url(url: str, args) -> Optional[Document]:
    """
    Orkestrasi penuh untuk satu URL.
    Mengembalikan objek Document jika sukses, atau None jika gagal.
    """
    # Konfigurasi awal
    user_agent = "webfetch/0.1.0 (compatible; +https://github.com/webfetch)"
    
    # 1. Inisialisasi Komponen Dasar
    robots_checker = RobotsChecker(user_agent=user_agent)
    rate_limiter = RateLimiter(default_delay=1.0)
    cache = FetchCache()
    browser = BrowserEngine(headless=True, user_agent=user_agent)
    
    fetcher = Fetcher(browser, robots_checker, rate_limiter, cache)
    
    try:
        # 2. Eksekusi Fetch (Robots -> Cache -> Browser)
        fetch_data = await fetcher.fetch(url, javascript=args.javascript, retries=2)
        html = fetch_data.get("html")
        final_url = fetch_data.get("final_url", url)
        
        if not html:
            print(f"[ERROR] Konten kosong untuk {url}", file=sys.stderr)
            return None

        # 3. Deteksi Tipe Konten
        # Asumsi header ada di fetch_data atau kita deteksi dari ekstensi/url
        headers = {"content-type": "text/html"} 
        content_type = detect_content_type(headers, final_url)
        
        dispatcher = ContentDispatcher()
        try:
            dispatch_result = dispatcher.dispatch(content_type, html, final_url)
        except UnsupportedContentTypeError as e:
            print(f"[SKIP] {e}", file=sys.stderr)
            return None
            
        # Handle PDF delegation (simulasi)
        if dispatch_result[0] == 'pdf_convert':
            print(f"[INFO] Mendeteksi PDF, delegasikan ke pdf2markdown (belum diimplementasi di demo ini)")
            # Di sini bisa dipanggil: from pdf2markdown import convert; return convert(...)
            return None

        if dispatch_result[0] != 'html_pipeline':
            # Handle gambar/media langsung jika perlu
            return None

        # 4. Parsing & Ekstraksi Metadata
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        metadata_obj = Metadata(url=final_url)
        if args.extract_metadata:
            meta_extractor = MetadataExtractor()
            metadata_obj = meta_extractor.extract_all(soup, url=final_url)
            
        # 5. Pembersihan DOM
        cleaner = DOMCleaner()
        cleaner.clean(soup)
        
        # 6. Boilerplate Learning (Opsional untuk single URL, skip agar cepat)
        # boilerplate_learner = BoilerplateLearner()
        # ... logic boilerplate ...
        
        # 7. Deteksi Main Content
        scorer = ContentScorer()
        detector = MainContentDetector(scorer=scorer)
        detection = detector.detect(soup, html)
        
        main_element = detection.get("element")
        
        # 8. Fallback Screenshot jika Confidence Rendah
        if not main_element or detection.get("confidence") == "LOW":
            if args.screenshot_fallback:
                print(f"[WARN] Confidence rendah pada {url}, mencoba fallback screenshot...")
                fallback_handler = ScreenshotFallback()
                # Perlu akses ke page object, tapi fetcher sudah menutupnya.
                # Solusi: Modifikasi fetcher untuk mengembalikan page object jika gagal, 
                # atau jalankan ulang browser khusus fallback (mahal).
                # Untuk demo ini, kita cetak pesan saja.
                print(f"[INFO] Fallback screenshot diperlukan tapi memerlukan modifikasi fetcher untuk mengakses page object.")
            else:
                print(f"[WARN] Deteksi konten lemah pada {url}. Lanjut dengan body penuh.")
                
        if not main_element:
            main_element = soup.find('body') or soup
            
        # 9. Ekstraksi Semantik ke Blocks
        semantic_extractor = SemanticExtractor()
        blocks = semantic_extractor.extract_all(main_element)
        
        # 10. Ekstraksi Aset Tambahan
        if args.extract_images:
            img_extractor = ImageExtractor()
            images = img_extractor.extract_images(main_element, base_url=final_url)
            from .model import ImageBlock, ConfidenceLevel
            for img_data in images:
                # Cek duplikasi sederhana
                if not any(hasattr(b, 'src') and b.src == img_data['src'] for b in blocks):
                    blocks.append(ImageBlock(
                        type="image", confidence=ConfidenceLevel.MEDIUM,
                        src=img_data['src'], alt=img_data['alt'], caption=img_data['caption']
                    ))
                    
        # Embeds
        embed_extractor = EmbedExtractor()
        embeds = embed_extractor.extract_all(main_element)
        blocks.extend(embeds)
        
        # Tables (Sudah dihandle semantic, tapi bisa diperkaya)
        # Links (Ekstraksi info saja)
        if args.extract_links:
            link_extractor = LinkExtractor()
            links = link_extractor.extract_links(main_element, final_url)
            # Bisa disimpan di metadata.extra jika perlu
            
        # 11. Bangun Document Model
        document = Document(
            url=final_url,
            metadata=metadata_obj,
            blocks=blocks
        )
        
        return document

    except RobotsDisallowedError as e:
        print(f"[BLOCKED] {e.url} dilarang oleh robots.txt", file=sys.stderr)
        return None
    except FetchError as e:
        print(f"[FETCH ERROR] {e.url}: {e.message}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[CRASH] Error tak terduga pada {url}: {str(e)}", file=sys.stderr)
        return None
    finally:
        # Pastikan browser ditutup
        try:
            await browser.close()
        except:
            pass


async def fetch(url: str, output: str = None, format: str = "markdown", 
                javascript: bool = True, extract_images: bool = True, 
                extract_links: bool = True, extract_metadata: bool = True,
                screenshot_fallback: bool = False):
    """
    Wrapper async untuk fetch_single_url dengan argumen namespace sederhana.
    Menangani rendering dan penulisan file.
    """
    # Buat objek args dummy
    class Args:
        def __init__(self):
            self.javascript = javascript
            self.extract_images = extract_images
            self.extract_links = extract_links
            self.extract_metadata = extract_metadata
            self.screenshot_fallback = screenshot_fallback
            
    args = Args()
    
    document = await fetch_single_url(url, args)
    
    if not document:
        return None
        
    # Rendering
    output_text = ""
    if format == "markdown":
        renderer = MarkdownRenderer()
        output_text = renderer.render(document)
    elif format == "json":
        renderer = JSONRenderer()
        output_text = renderer.render(document)
    elif format == "txt":
        renderer = TXTRenderer()
        output_text = renderer.render(document)
    else:
        raise ValueError(f"Format tidak didukung: {format}")
        
    # Output handling
    if output:
        # Jika output adalah direktori, buat filename otomatis
        out_path = Path(output)
        if out_path.is_dir():
            filename = f"{Path(url).stem}.{format}"
            out_path = out_path / filename
        elif output.endswith('/'):
            os.makedirs(output, exist_ok=True)
            filename = f"{Path(url).stem}.{format}"
            out_path = Path(output) / filename
            
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(output_text)
        print(f"[OK] Disimpan ke {out_path}")
    else:
        # Print to stdout
        print(output_text)
        
    return document


async def batch_fetch(urls_file: str, output_dir: str, **kwargs) -> None:
    """Jalankan fetch() untuk semua URL dalam file daftar."""
    if not os.path.exists(urls_file):
        print(f"[ERROR] File daftar URL tidak ditemukan: {urls_file}", file=sys.stderr)
        return
        
    with open(urls_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
    if not urls:
        print("[WARN] Tidak ada URL valid dalam file.")
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    # Inisialisasi RateLimiter global untuk batch
    rate_limiter = RateLimiter(default_delay=1.0)
    
    print(f"[INFO] Memproses {len(urls)} URL...")
    
    for url in urls:
        # Hormati rate limit antar domain
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        rate_limiter.wait_if_needed(domain)
        
        # Tentukan output file per URL
        safe_filename = f"{Path(url).stem}.md" # Default md
        fmt = kwargs.get('format', 'markdown')
        if fmt == 'json': safe_filename = f"{Path(url).stem}.json"
        if fmt == 'txt': safe_filename = f"{Path(url).stem}.txt"
        
        out_path = os.path.join(output_dir, safe_filename)
        
        await fetch(url, output=out_path, **kwargs)
        
        rate_limiter.record_request(domain)


def build_arg_parser() -> argparse.ArgumentParser:
    """Definisikan argumen CLI."""
    parser = argparse.ArgumentParser(
        prog="webfetch",
        description="Ambil konten web dan konversi ke Markdown/JSON/TXT dengan struktur rapi."
    )
    
    parser.add_argument("source", help="URL tunggal atau file teks berisi daftar URL (batch mode).")
    parser.add_argument("-o", "--output", help="File output (-) untuk stdout, atau path file/direktori untuk batch.", default="-")
    parser.add_argument("--format", choices=["markdown", "json", "txt"], default="markdown", help="Format output.")
    parser.add_argument("--no-javascript", action="store_false", dest="javascript", help="Matikan eksekusi JavaScript (lebih cepat, tapi mungkin kehilangan konten dinamis).")
    parser.add_argument("--no-images", action="store_false", dest="extract_images", help="Jangan ekstrak gambar.")
    parser.add_argument("--no-links", action="store_false", dest="extract_links", help="Jangan ekstrak daftar link.")
    parser.add_argument("--no-meta", action="store_false", dest="extract_metadata", help="Jangan ekstrak metadata (judul, penulis, dll).")
    parser.add_argument("--screenshot-fallback", action="store_true", help="Aktifkan fallback screenshot jika deteksi konten gagal (memerlukan konfigurasi tambahan).")
    
    return parser


def main():
    """Entry point `python -m webfetch`."""
    parser = build_arg_parser()
    args = parser.parse_args()
    
    # Deteksi mode batch vs tunggal
    source = args.source
    
    is_batch = False
    if os.path.isfile(source):
        with open(source, 'r') as f:
            first_line = f.readline().strip()
            # Heuristik sederhana: jika isi file terlihat seperti URL atau ada banyak baris
            if first_line.startswith('http') or len(open(source).readlines()) > 1:
                is_batch = True
                
    kwargs = {
        "format": args.format,
        "javascript": args.javascript,
        "extract_images": args.extract_images,
        "extract_links": args.extract_links,
        "extract_metadata": args.extract_metadata,
        "screenshot_fallback": args.screenshot_fallback
    }
    
    try:
        if is_batch:
            if args.output == "-":
                print("[ERROR] Output harus berupa direktori untuk mode batch.", file=sys.stderr)
                sys.exit(1)
            asyncio.run(batch_fetch(source, args.output, **kwargs))
        else:
            # Single URL
            if not source.startswith('http'):
                print("[ERROR] Input harus URL valid (http/https) atau file daftar URL.", file=sys.stderr)
                sys.exit(1)
                
            asyncio.run(fetch(source, **{"output": args.output, **kwargs}))
            
    except KeyboardInterrupt:
        print("\n[INFO] Dibatalkan oleh pengguna.")
        sys.exit(130)
    except Exception as e:
        print(f"[FATAL] {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()