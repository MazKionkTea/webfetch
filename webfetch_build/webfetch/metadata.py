"""
metadata.py
Ekstraksi metadata dokumen dari berbagai sumber di HTML: title tag,
meta tag standar, Open Graph tag, JSON-LD, dan canonical URL.
Prioritas: JSON-LD > Open Graph > meta tag > title tag.
"""


"""
Modul untuk ekstraksi metadata halaman web dari berbagai sumber HTML.

Mendukung ekstraksi dari:
1. JSON-LD (Structured Data / Schema.org) - Prioritas tertinggi.
2. Open Graph Tags (og:title, og:description, dll) - Standar media sosial.
3. Meta Tags Standar (name="author", name="description", dll).
4. Title Tag (<title>) - Fallback terakhir.

Hasil ekstraksi digabungkan menjadi objek `Metadata` sesuai model data project.
"""

import json
from typing import Optional, List, Dict, Any, Union
from bs4 import BeautifulSoup, Tag

from .model import Metadata


"""
Modul untuk ekstraksi metadata halaman web dari berbagai sumber HTML.

Mendukung ekstraksi dari:
1. JSON-LD (Structured Data / Schema.org) - Prioritas tertinggi.
2. Open Graph Tags (og:title, og:description, dll) - Standar media sosial.
3. Meta Tags Standar (name="author", name="description", dll).
4. Title Tag (<title>) - Fallback terakhir.

Hasil ekstraksi digabungkan menjadi objek `Metadata` sesuai model data project.
"""

import json
from typing import Optional, List, Dict, Any, Union
from bs4 import BeautifulSoup, Tag

from .model import Metadata


class MetadataExtractor:
    """
    Ekstraktor metadata halaman web yang menggabungkan data dari berbagai sumber HTML.
    
    Kelas ini mengimplementasikan strategi ekstraksi berlapis dengan prioritas:
    1. JSON-LD (Structured Data) - Sumber paling kaya dan terstruktur (Schema.org).
    2. Open Graph (OG Tags) - Standar de facto untuk preview media sosial (Facebook/Twitter).
    3. Meta Tags Standar - Fallback tradisional HTML5.
    4. Title Tag - Fallback terakhir jika tidak ada metadata lain.
    
    Contoh penggunaan:
        extractor = MetadataExtractor()
        soup = BeautifulSoup(html_content, 'html.parser')
        metadata = extractor.extract_all(soup, url="https://example.com/article-123")
        
        print(metadata.title)
        print(metadata.author)
    """

    def extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Ekstrak judul halaman dari tag <title>.
        
        Metode ini mencari tag <title> di dalam <head> dan mengambil teksnya.
        Hasil akan di-strip dari whitespace berlebih.
        
        Args:
            soup: Objek BeautifulSoup dari dokumen HTML yang sudah diparsing.
            
        Returns:
            str | None: Teks judul halaman jika ditemukan, None jika tag <title> tidak ada atau kosong.
        """
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        return None

    def extract_from_meta_tags(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """
        Ambil metadata dari tag <meta> standar (name="...", itemprop="...").
        
        Mencari field berikut:
        - author (dari name="author" atau itemprop="author")
        - description (dari name="description")
        - language (dari name="lang" atau atribut lang di tag <html>)
        - published date (dari name="date", "publish_date", atau "article:published_time")
        
        Args:
            soup: Objek BeautifulSoup dari dokumen HTML.
            
        Returns:
            dict: Dictionary dengan key 'author', 'description', 'language', 'published'.
                  Nilai adalah string atau None jika tidak ditemukan.
        """
        data = {
            "author": None,
            "description": None,
            "language": None,
            "published": None
        }
        
        # Mapping nama meta tag ke key output
        meta_map = {
            "author": "author",
            "description": "description",
            "lang": "language",
            "date": "published",
            "publish_date": "published",
            "article:published_time": "published",
            "article:modified_time": "modified" # Tambahan untuk tanggal modifikasi
        }
        
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            content = meta.get('content')
            itemprop = meta.get('itemprop', '').lower()
            
            if not content:
                continue
            
            # Cek berdasarkan atribut 'name'
            if name in meta_map:
                key = meta_map[name]
                if key in data and not data[key]:
                    data[key] = content.strip()
            
            # Cek berdasarkan atribut 'itemprop' (Microdata)
            if itemprop in meta_map:
                key = meta_map[itemprop]
                if key in data and not data[key]:
                    data[key] = content.strip()
        
        # Fallback bahasa dari atribut <html lang="...">
        if not data["language"]:
            html_tag = soup.find('html')
            if html_tag:
                lang_attr = html_tag.get('lang') or html_tag.get('xml:lang')
                if lang_attr:
                    data["language"] = lang_attr.strip()
                    
        return data

    def extract_from_og_tags(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """
        Ambil metadata dari Open Graph tags (<meta property="og:...">).
        
        OG tags biasanya lebih konsisten daripada meta tags biasa karena ditujukan
        untuk menghasilkan preview yang rapi di media sosial (Facebook, LinkedIn, Slack).
        
        Field yang diekstraksi:
        - og:title
        - og:description
        - og:image
        - og:url (sering digunakan sebagai canonical URL)
        - og:site_name
        - og:type
        
        Args:
            soup: Objek BeautifulSoup dari dokumen HTML.
            
        Returns:
            dict: Dictionary dengan key 'title', 'description', 'image', 'url', 'site_name', 'type'.
        """
        data = {
            "title": None,
            "description": None,
            "image": None,
            "url": None,
            "site_name": None,
            "type": None
        }
        
        og_map = {
            "og:title": "title",
            "og:description": "description",
            "og:image": "image",
            "og:url": "url",
            "og:site_name": "site_name",
            "og:type": "type"
        }
        
        for meta in soup.find_all('meta'):
            prop = meta.get('property', '').lower()
            content = meta.get('content')
            
            if prop in og_map and content:
                key = og_map[prop]
                # Hanya isi jika belum ada (prioritas pertama yang ditemukan)
                if not data[key]:
                    data[key] = content.strip()
                    
        return data

    def extract_from_json_ld(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Parse script JSON-LD (<script type="application/ld+json">) untuk structured data.
        
        Mencari schema.org types yang relevan dengan konten artikel/halaman:
        - Article, NewsArticle, BlogPosting, TechArticle
        - WebPage
        
        Mendukung format single object, array of objects, maupun @graph.
        Melakukan flattening pada field nested seperti 'author' (bisa berupa string atau object Person).
        
        Args:
            soup: Objek BeautifulSoup dari dokumen HTML.
            
        Returns:
            dict: Dictionary flattened berisi field:
                  'title' (headline), 'author', 'published' (datePublished), 
                  'modified' (dateModified), 'description', 'image'.
        """
        result = {
            "title": None,
            "author": None,
            "published": None,
            "modified": None,
            "description": None,
            "image": None,
            "type": None
        }
        
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            if not script.string:
                continue
            
            try:
                data = json.loads(script.string)
                
                # Normalisasi: pastikan selalu list objek untuk diiterasi
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    # Handle @graph (kumpulan node terhubung)
                    if '@graph' in data:
                        items = data['@graph']
                    else:
                        items = [data]
                else:
                    continue
                
                for item in items:
                    if not isinstance(item, dict):
                        continue
                        
                    item_type = item.get('@type', '')
                    # Handle tipe berupa list atau string
                    if isinstance(item_type, list):
                        item_type = item_type[0]
                    
                    # Filter tipe yang relevan dengan artikel/konten utama
                    relevant_types = ['Article', 'NewsArticle', 'BlogPosting', 'TechArticle', 'WebPage']
                    if not any(t in str(item_type) for t in relevant_types):
                        continue
                    
                    # Ekstrak field dengan prioritas (jangan timpa jika sudah ada dari item sebelumnya yang mungkin lebih spesifik)
                    if not result["title"] and item.get('headline'):
                        result["title"] = item['headline']
                    
                    if not result["description"] and item.get('description'):
                        result["description"] = item['description']
                        
                    if not result["published"] and item.get('datePublished'):
                        result["published"] = item['datePublished']
                        
                    if not result["modified"] and item.get('dateModified'):
                        result["modified"] = item['dateModified']
                        
                    # Ekstraksi Author (bisa string, object, atau list)
                    if not result["author"]:
                        author = item.get('author')
                        if isinstance(author, dict):
                            result["author"] = author.get('name')
                        elif isinstance(author, list) and len(author) > 0:
                            a = author[0]
                            result["author"] = a.get('name') if isinstance(a, dict) else str(a)
                        elif isinstance(author, str):
                            result["author"] = author
                            
                    # Ekstraksi Image (bisa string, object, atau list)
                    if not result["image"]:
                        img = item.get('image')
                        if isinstance(img, dict):
                            result["image"] = img.get('url')
                        elif isinstance(img, list) and len(img) > 0:
                            i = img[0]
                            result["image"] = i.get('url') if isinstance(i, dict) else str(i)
                        elif isinstance(img, str):
                            result["image"] = img
                            
            except json.JSONDecodeError:
                # Skip script yang malformed JSON-nya
                continue
                
        return result

    def extract_canonical_url(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Ekstrak URL kanonik dari tag <link rel="canonical">.
        
        URL kanonik memberi tahu mesin pencari versi utama dari halaman ini
        jika ada duplikat konten di URL berbeda.
        
        Args:
            soup: Objek BeautifulSoup dari dokumen HTML.
            
        Returns:
            str | None: URL kanonik absolut jika ditemukan, None jika tidak ada tag canonical.
        """
        link = soup.find('link', rel='canonical')
        if link and link.get('href'):
            return link['href'].strip()
        return None

    def merge_metadata_sources(self, sources: List[Dict], url: str) -> Metadata:
        """
        Gabungkan hasil ekstraksi dari berbagai sumber menjadi satu objek Metadata.
        
        Strategi merging menggunakan prioritas per field (dari tertinggi ke terendah):
        1. JSON-LD (Structured Data) - Paling akurat secara semantik.
        2. Open Graph (OG Tags) - Sangat lengkap untuk konten media.
        3. Meta Tags Standar - Fallback umum.
        4. Title Tag - Fallback dasar.
        
        Argumen `sources` diharapkan berupa list dictionary dengan urutan:
        [json_ld_data, og_data, meta_data, title_data]
        
        Args:
            sources: List of dict hasil ekstraksi per metode.
            url: URL asli dokumen (digunakan sebagai fallback jika canonical tidak ditemukan).
            
        Returns:
            Metadata: Instance objek model Metadata yang sudah terisi datanya.
        """
        # Unpack sources sesuai urutan prioritas
        json_ld = sources[0] if len(sources) > 0 and sources[0] else {}
        og = sources[1] if len(sources) > 1 and sources[1] else {}
        meta = sources[2] if len(sources) > 2 and sources[2] else {}
        title_data = sources[3] if len(sources) > 3 and sources[3] else {}
        
        # Helper lokal untuk mengambil nilai pertama yang tidak None dari beberapa sumber
        def get_first(*dicts_and_keys):
            # Format args: (dict1, key1), (dict2, key2), ...
            for d, k in dicts_and_keys:
                if d and k in d and d[k]:
                    return d[k]
            return None

        # 1. Title: JSON-LD (headline) > OG > Title Tag
        title = get_first(
            (json_ld, 'title'),
            (og, 'title'),
            (meta, 'title'), # Jarang ada
            (title_data, 'title')
        )

        # 2. Author: JSON-LD > Meta
        author = get_first(
            (json_ld, 'author'),
            (meta, 'author')
        )

        # 3. Published Date: JSON-LD > Meta
        published = get_first(
            (json_ld, 'published'),
            (meta, 'published')
        )

        # 4. Language: Meta > JSON-LD (jarang ada di JSON-LD article)
        language = get_first(
            (meta, 'language'),
            (json_ld, 'language')
        )

        # 5. Canonical URL: Explicit Canonical Tag > OG URL > Input URL
        # Kita asumsikan caller sudah menyuntikkan hasil extract_canonical_url ke salah satu dict
        # atau kita cek manual di sini jika perlu. Untuk simplifikasi, kita ambil dari OG atau argumen url.
        canonical_url = get_first(
            (og, 'url'), # OG url sering dianggap canonical oleh publisher
            ({'url': url}, 'url') # Fallback ke input
        )
        
        # Tentukan indikator sumber dominan untuk keperluan debugging/audit
        source_indicator = 'title-tag'
        if meta.get('author') or meta.get('description'):
            source_indicator = 'meta'
        if og.get('title') or og.get('description'):
            source_indicator = 'og'
        if json_ld.get('title') or json_ld.get('headline'):
            source_indicator = 'json-ld'

        return Metadata(
            url=url,
            title=title,
            author=author,
            published=published,
            language=language,
            canonical_url=canonical_url,
            source=source_indicator
        )

    def extract_all(self, soup: BeautifulSoup, url: str) -> Metadata:
        """
        Metode convenience untuk menjalankan seluruh proses ekstraksi dan merging.
        
        Ini adalah entry point utama kelas ini. Memanggil semua metode `extract_*`
        secara berurutan, lalu menggabungkannya dengan `merge_metadata_sources`.
        
        Args:
            soup: Objek BeautifulSoup dari HTML yang sudah di-fetch dan diparsing.
            url: URL asli dokumen (sebagai fallback dan konteks).
            
        Returns:
            Metadata: Objek metadata lengkap yang siap digunakan oleh pipeline.
        """
        # 1. Ekstraksi per layer (dari paling spesifik ke umum)
        json_ld_data = self.extract_from_json_ld(soup)
        og_data = self.extract_from_og_tags(soup)
        meta_data = self.extract_from_meta_tags(soup)
        
        # 2. Ekstraksi elemen dasar
        title_str = self.extract_title(soup)
        canonical_url = self.extract_canonical_url(soup)
        
        # 3. Siapkan dict khusus untuk title dan canonical
        title_data = {"title": title_str}
        
        # Inject canonical URL ke data OG jika ditemukan (karena OG:url sering dianggap canonical)
        # Jika OG:url sudah ada, kita prioritaskan itu, kalau tidak pakai yang dari tag link
        if canonical_url and not og_data.get('url'):
            og_data['url'] = canonical_url
        elif canonical_url and og_data.get('url'):
            # Jika keduanya ada, biasanya sama. Jika beda, tag link rel=canonical lebih otoritatif.
            # Tapi untuk simplifikasi, kita biarkan OG dulu kecuali logic merge diubah.
            pass

        # Urutan sumber sesuai prioritas: JSON-LD -> OG -> Meta -> Title
        sources = [json_ld_data, og_data, meta_data, title_data]
        
        return self.merge_metadata_sources(sources, url)