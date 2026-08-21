"""
embeds.py
Deteksi & ekstraksi elemen embed (iframe YouTube, tweet, embedded
PDF, dll) menjadi EmbedBlock, supaya tidak hilang begitu saja
saat DOM dibersihkan.
"""

from typing import Optional, List
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup, Tag

# Import model yang sudah dibuat
from .model import EmbedBlock, ConfidenceLevel

class EmbedExtractor:
    """
    Detektor dan ekstraktor konten embed pihak ketiga (iframe).
    
    Kelas ini memastikan konten kaya seperti video, peta, atau tweet
    tidak hilang saat proses pembersihan DOM (`cleaner.py`) atau ekstraksi teks biasa.
    Ia mengidentifikasi tipe embed berdasarkan URL sumber dan membuat `EmbedBlock`
    yang dapat dirender khusus oleh renderer (misal: menyisipkan shortcode Markdown).
    
    Tipe Embed yang Didukung:
    - YouTube / YouTube Shorts
    - Vimeo
    - Twitter / X
    - Google Maps
    - Generic (iframe lainnya)
    """

    def detect_embed_type(self, iframe_element: Tag) -> str:
        """
        Menentukan jenis embed berdasarkan atribut `src` dari iframe.
        
        Logika deteksi menggunakan pencocokan domain dan pola path URL.
        
        Args:
            iframe_element: Tag <iframe> dari BeautifulSoup.
            
        Returns:
            str: Tipe embed ('youtube', 'vimeo', 'twitter', 'google_maps', 'generic').
        """
        src = iframe_element.get('src', '')
        if not src:
            return 'generic'
            
        parsed = urlparse(src)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        
        # YouTube (termasuk embed dan shorts)
        if any(x in domain for x in ['youtube.com', 'youtu.be', 'youtube-nocookie.com']):
            return 'youtube'
            
        # Vimeo
        if 'vimeo.com' in domain:
            return 'vimeo'
            
        # Twitter / X
        if any(x in domain for x in ['twitter.com', 'x.com', 'tweetdeck.twitter.com']):
            return 'twitter'
            
        # Google Maps
        if 'google.com' in domain and 'maps' in path:
            return 'google_maps'
            
        # Facebook Page/Post
        if 'facebook.com' in domain or 'fb.com' in domain:
            return 'facebook'
            
        # Spotify
        if 'spotify.com' in domain:
            return 'spotify'
            
        return 'generic'

    def extract_embed(self, iframe_element: Tag) -> Optional[EmbedBlock]:
        """
        Membangun objek EmbedBlock dari elemen iframe.
        
        Ekstraksi meliputi:
        1. URL sumber (`src`).
        2. Tipe embed (dari `detect_embed_type`).
        3. Judul (`title` attribute atau fallback dari tipe).
        4. Dimensi (opsional, untuk referensi renderer).
        
        Args:
            iframe_element: Tag <iframe> yang sudah terdeteksi.
            
        Returns:
            EmbedBlock | None: Objek block jika valid, None jika src kosong.
        """
        src = iframe_element.get('src', '')
        if not src:
            return None
            
        embed_type = self.detect_embed_type(iframe_element)
        title = iframe_element.get('title')
        
        # Fallback judul jika tidak ada atribut title
        if not title:
            if embed_type == 'youtube':
                title = "YouTube Video"
            elif embed_type == 'vimeo':
                title = "Vimeo Video"
            elif embed_type == 'twitter':
                title = "Twitter Post"
            elif embed_type == 'google_maps':
                title = "Google Maps Location"
            else:
                title = "Embedded Content"
                
        # Generate ID yang unik untuk embed
        embed_id = iframe_element.get('id', '') or f"embed-{embed_type}-{title[:20].replace(' ', '-').lower() if title else 'unknown'}"
        return EmbedBlock(
            id=embed_id,
            type="embed",
            confidence=ConfidenceLevel.HIGH, # Iframe biasanya eksplisit
            url=src,
            embed_type=embed_type,
            title=title
        )

    def extract_all(self, element: Tag) -> List[EmbedBlock]:
        """
        Ekstrak semua elemen embed dalam satu container konten.
        
        Args:
            element: Tag root (misal: main content) untuk dicari iframenya.
            
        Returns:
            list: Daftar objek EmbedBlock yang ditemukan.
        """
        embeds = []
        iframes = element.find_all('iframe')
        
        for iframe in iframes:
            block = self.extract_embed(iframe)
            if block:
                embeds.append(block)
                
        # Opsional: Cek juga tag <embed> lama (jarang dipakai sekarang tapi masih valid HTML)
        embed_tags = element.find_all('embed')
        for emb in embed_tags:
            src = emb.get('src', '')
            if src:
                # Tag <embed> biasanya generic atau plugin lama
                embed_id = emb.get('id', '') or f"embed-generic-{src.split('/')[-1][:20]}"
                block = EmbedBlock(
                    id=embed_id,
                    type="embed",
                    confidence=ConfidenceLevel.MEDIUM,
                    url=src,
                    embed_type='generic',
                    title="Legacy Embedded Object"
                )
                embeds.append(block)
                
        return embeds
