#!/usr/bin/env python3
"""
Package webfetch - ekstraksi konten web ke Markdown/JSON/TXT.
"""

# Import utama untuk kemudahan akses
from .model import Document, Metadata
from .fetcher import Fetcher

__all__ = ['Document', 'Metadata', 'Fetcher']
