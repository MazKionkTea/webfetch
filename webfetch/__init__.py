#!/usr/bin/env python3
"""
CLI entry point untuk webfetch.

Penggunaan:
    python webfetch.py <url> [options]

Contoh:
    python webfetch.py https://example.com
    python webfetch.py https://example.com --output json
    python webfetch.py https://example.com --output all --no-js
    python webfetch.py https://example.com --save  # Simpan ke folder output/
"""

import sys
import asyncio
import argparse
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from .fetcher import fetch, FetchResult
    from .metadata_extractor import MetadataExtractor

    __all__ = ['fetch', 'FetchResult', 'MetadataExtractor']
except ImportError:
    # Fallback jika struktur file berbeda, biarkan kosong dulu agar modul bisa dimuat
    __all__ = []

def create_parser() -> argparse.ArgumentParser:
    """Buat parser argumen CLI."""
    parser = argparse.ArgumentParser(
        prog="webfetch",
        description="Konversi URL ke Markdown/JSON/TXT dengan ekstraksi konten cerdas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  python webfetch.py https://example.com
  python webfetch.py https://example.com --output json
  python webfetch.py https://example.com --output all --no-js
  python webfetch.py "https://example.com/page?param=value" --timeout 60
  python webfetch.py https://example.com --save  # Simpan ke folder output/
  python webfetch.py https://example.com --save --output json  # Simpan JSON ke output/
        """
    )

    parser.add_argument(
        "url",
        type=str,
        help="URL target untuk di-fetch"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        choices=["markdown", "json", "txt", "all"],
        default="markdown",
        help="Format output (default: markdown)"
    )

    parser.add_argument(
        "-s", "--save",
        action="store_true",
        help="Simpan output ke folder output/ (default: print ke stdout)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Folder output kustom (default: ./output)"
    )

    parser.add_argument(
        "--no-js",
        action="store_true",
        help="Jangan gunakan JavaScript rendering (fetch statis saja)"
    )

    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Jangan ekstrak gambar"
    )

    parser.add_argument(
        "--no-links",
        action="store_true",
        help="Jangan ekstrak link"
    )

    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Jangan ekstrak metadata"
    )

    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=30,
        help="Timeout dalam detik (default: 30)"
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )

    return parser


def save_output(result: FetchResult, url: str, output_format: str, output_dir: Path) -> list[str]:
    """Simpan output ke file dalam folder output/.

    Returns:
        List nama file yang dibuat
    """
    # Buat nama file dari URL
    # Bersihkan karakter invalid untuk nama file
    safe_url = url.replace("https://", "").replace("http://", "")
    safe_url = safe_url.replace("/", "_").replace("?", "_").replace("&", "_")
    safe_url = safe_url.replace("=", "_").replace("%", "_")

    # Batasi panjang nama file
    if len(safe_url) > 100:
        safe_url = safe_url[:100]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{safe_url}_{timestamp}"

    files_created = []

    if output_format in ["markdown", "all"]:
        md_file = output_dir / f"{base_name}.md"
        if result.markdown:
            md_file.write_text(result.markdown, encoding="utf-8")
            files_created.append(str(md_file))

    if output_format in ["json", "all"]:
        json_file = output_dir / f"{base_name}.json"
        if result.json_str:
            json_file.write_text(result.json_str, encoding="utf-8")
            files_created.append(str(json_file))

    if output_format in ["txt", "all"]:
        txt_file = output_dir / f"{base_name}.txt"
        if result.text_str:
            txt_file.write_text(result.text_str, encoding="utf-8")
            files_created.append(str(txt_file))

    return files_created


async def main_async(args: argparse.Namespace) -> int:
    """Jalankan fetch secara async."""
    result: FetchResult = await fetch(
        url=args.url,
        output=args.output,
        javascript=not args.no_js,
        extract_images=not args.no_images,
        extract_links=not args.no_links,
        extract_metadata=not args.no_metadata,
        timeout=args.timeout
    )

    if result.error:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1

    # Tentukan folder output
    if args.save:
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            # Default: folder output/ di direktori kerja saat ini
            output_dir = Path.cwd() / "output"

        # Buat folder jika belum ada
        output_dir.mkdir(parents=True, exist_ok=True)

        # Simpan file
        files_created = save_output(result, args.url, args.output, output_dir)

        if files_created:
            print(f"Output disimpan ke:", file=sys.stderr)
            for f in files_created:
                print(f"  - {f}", file=sys.stderr)
        else:
            print("Tidak ada konten untuk disimpan.", file=sys.stderr)
            return 1
    else:
        # Output ke stdout (seperti sebelumnya)
        if args.output == "markdown":
            print(result.markdown or "")
        elif args.output == "json":
            print(result.json_str or "")
        elif args.output == "txt":
            print(result.text_str or "")
        elif args.output == "all":
            # Untuk 'all', output markdown sebagai default
            print(result.markdown or "")

    return 0


def main() -> int:
    """Entry point CLI."""
    parser = create_parser()

    # Handle kasus tanpa argumen
    if len(sys.argv) < 2:
        parser.print_help()
        return 1

    args = parser.parse_args()

    # Jalankan async loop
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nDibatalkan oleh pengguna.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error tak terduga: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
