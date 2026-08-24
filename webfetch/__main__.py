#!/usr/bin/env python3
"""
CLI entry point untuk webfetch.

Penggunaan:
    python -m webfetch <url> [options]

Contoh:
    python -m webfetch https://example.com
    python -m webfetch https://example.com --output json
    python -m webfetch https://example.com --output all --no-js
"""

import sys
import asyncio
import argparse
from typing import Optional
from pathlib import Path
import importlib.util

# Tambahkan parent directory ke path agar bisa import dari webfetch.py
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

# Import fungsi fetch dari webfetch.py (di parent directory) secara eksplisit
_webfetch_main_path = _parent_dir / "webfetch.py"
_spec = importlib.util.spec_from_file_location("webfetch_main", _webfetch_main_path)
_webfetch_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_webfetch_main)
fetch = _webfetch_main.fetch


def create_parser() -> argparse.ArgumentParser:
    """Buat parser argumen CLI."""
    parser = argparse.ArgumentParser(
        prog="webfetch",
        description="Konversi URL ke Markdown/JSON/TXT dengan ekstraksi konten cerdas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  python -m webfetch https://example.com
  python -m webfetch https://example.com --output json
  python -m webfetch https://example.com --output all --no-js
  python -m webfetch "https://example.com/page?param=value" --timeout 60
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


async def main_async(args: argparse.Namespace) -> int:
    """Jalankan fetch secara async."""
    # Tentukan format output
    output_format = args.output if args.output != "all" else "markdown"

    result = await fetch(
        url=args.url,
        output=None,  # None = print ke stdout
        format=output_format,
        javascript=not args.no_js,
        extract_images=not args.no_images,
        extract_links=not args.no_links,
        extract_metadata=not args.no_metadata
    )

    if not result:
        print("Error: Gagal mengambil konten dari URL.", file=sys.stderr)
        return 1

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
