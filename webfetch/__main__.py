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

from . import fetch, FetchResult


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

    # Output sesuai format yang diminta
    if args.output == "markdown":
        print(result.markdown or "")
    elif args.output == "json":
        print(result.json_str or "")
    elif args.output == "txt":
        print(result.text_str or "")
    elif args.output == "all":
        # Untuk 'all', output markdown sebagai default,
        # user bisa redirect ke file berbeda jika butuh format lain
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
