# webfetch

Tool Web Fetch → Markdown untuk konsumsi AI/LLM/RAG. Didesain sebagai
**web content extraction pipeline** — arsitektur paralel dengan
[pdf2markdown](../pdf2markdown/README.md): ada Document Model perantara
sebelum dirender, bukan langsung URL → string Markdown.

Perbedaan utama dari PDF: masalah inti di web bukan koordinat/layout,
tapi **DOM, JavaScript rendering, boilerplate (nav/iklan/sidebar/komentar),
dan struktur semantik HTML**.

---

## 1. Filosofi Desain

1. **Bukan langsung URL → Markdown.** Ada Document Model perantara
   (title, metadata, blocks terstruktur) sebelum dirender. Format output
   baru (JSON, TXT) cukup tambah satu renderer, tanpa ubah logic ekstraksi.
2. **Playwright di depan, bukan `requests.get()`.** Banyak situs modern
   merender konten via JavaScript — HTML awal bisa cuma `<div id="app">`
   kosong. Browser rendering penuh diperlukan untuk mendapat DOM final.
3. **Deteksi konten berlapis, bukan sekali coba.** Prioritas:
   tag semantik (`<article>`/`<main>`) → content scoring → Readability-style
   fallback → screenshot fallback (kalau semua gagal).
4. **Jangan terlalu agresif membersihkan DOM.** Elemen seperti `<aside>`
   bisa jadi catatan penting, bukan cuma iklan. Pembersihan pasti
   (`cleaner.py`) dipisah dari pembersihan berbasis heuristik/skor
   (`scoring.py`, `boilerplate.py`) yang lebih hati-hati.
5. **Boilerplate dipelajari lintas halaman, bukan cuma per halaman.**
   Analog `headers.py` di pdf2markdown: nav/sidebar yang identik di semua
   halaman satu domain lebih akurat dikenali dari pengulangan antar-halaman
   daripada ditebak dari satu halaman saja.
6. **Dua output untuk dua kebutuhan.** Markdown = representasi
   human/LLM-readable. JSON = representasi internal untuk pipeline RAG.
7. **URL yang mengarah ke PDF tidak diproses ulang dari nol** — didelegasikan
   ke pipeline `pdf2markdown` yang sudah ada.

---

## 2. Arsitektur

```
                         URL
                          │
                          ▼
                 ┌─────────────────┐
                 │  robots.py      │  cek izin & rate limit per domain
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  fetcher.py     │  orkestrasi: browser + consent + cache + retry
                 │  (browser.py,   │
                 │   consent.py,   │
                 │   cache.py)     │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ content_type.py │──── PDF? ──→ delegasi ke pdf2markdown.convert()
                 └────────┬────────┘
                          │ HTML
                          ▼
                 ┌─────────────────┐
                 │  metadata.py    │  title, author, tanggal, JSON-LD, OG tag
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  cleaner.py     │  buang script/style/tracking (pasti bukan konten)
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ boilerplate.py  │  buang elemen berulang lintas halaman (opsional,
                 └────────┬────────┘  butuh sample >1 halaman per domain)
                          │
                          ▼
                 ┌─────────────────┐
                 │ scoring.py +    │  <article>/<main> → scoring → Readability
                 │ content.py      │
                 └────────┬────────┘
                          │
                 confidence rendah?
                          │
              ┌───────────┴───────────┐
              ▼ ya                    ▼ tidak
    screenshot_fallback.py      pagination.py (agregasi multi-halaman jika ada)
              │                        │
              └───────────┬────────────┘
                          ▼
                 ┌─────────────────┐
                 │  semantic.py    │  heading, paragraf, list, code, blockquote
                 │  + links.py     │
                 │  + images.py    │
                 │  + tables.py    │
                 │  + embeds.py    │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │   model.py      │  rakit jadi Document (metadata + blocks)
                 └────────┬────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
          Markdown       JSON        TXT
          (renderers/markdown.py, json.py, txt.py)
```

---

## 3. Workflow Lengkap

```
URL
 │
 ▼
Normalize URL (fetcher.py)
 │
 ▼
Cek robots.txt & rate limit (robots.py)
 │
 ▼
Cek cache — masih fresh? (cache.py) ──ya──→ pakai hasil cache
 │ tidak
 ▼
Launch browser & load page (browser.py)
 │
 ├── wait DOM / wait network / eksekusi JS
 ├── tangani redirect
 └── dismiss cookie/consent banner (consent.py)
 │
 ▼
Rendered DOM + status/headers
 │
 ▼
Deteksi Content-Type (content_type.py)
 │
 ├── PDF ──→ delegasi ke pdf2markdown
 ├── gambar/tipe lain ──→ tangani sebagai block tunggal / tolak
 └── HTML ──→ lanjut
 │
 ▼
Ekstrak metadata: title, meta tag, OG tag, JSON-LD, canonical (metadata.py)
 │
 ▼
Bersihkan DOM: script/style/noscript/tracking (cleaner.py)
 │
 ▼
Buang boilerplate lintas halaman jika domain sudah pernah di-crawl (boilerplate.py)
 │
 ▼
Deteksi main content:
   <article> → <main> → [role=main] → content scoring → Readability (content.py)
 │
 ▼
Confidence rendah? ──ya──→ screenshot fallback (screenshot_fallback.py)
 │ tidak
 ▼
Ada indikasi artikel multi-halaman / infinite scroll? (pagination.py)
 │
 ▼
Ekstraksi semantik dari main content:
   heading, paragraf, list, code, blockquote (semantic.py)
   + link (normalisasi absolute) (links.py)
   + gambar (normalisasi absolute + caption) (images.py)
   + tabel (tables.py)
   + embed/iframe (embeds.py)
 │
 ▼
Rakit Document Model (model.py)
 │
 ▼
Render: Markdown (front matter + body) / JSON / TXT
 │
 ▼
Output
```

---

## 4. Struktur Project

```
webfetch/
├── webfetch/
│   ├── __init__.py         # expose async fetch()
│   ├── model.py             # Document Model (Block, Metadata, Document)
│   ├── errors.py            # taksonomi error (timeout, blocked, 404, paywall, dst)
│   ├── robots.py            # robots.txt + rate limiting per domain
│   ├── browser.py           # wrapper Playwright (launch, load, render)
│   ├── consent.py           # deteksi & dismiss cookie/consent banner
│   ├── cache.py             # caching & conditional fetch (ETag/Last-Modified)
│   ├── fetcher.py           # orkestrasi robots+browser+consent+cache+retry
│   ├── content_type.py      # deteksi Content-Type + dispatch (delegasi PDF)
│   ├── metadata.py          # ekstraksi title/author/JSON-LD/OG/canonical
│   ├── cleaner.py           # buang elemen pasti non-konten (per halaman)
│   ├── boilerplate.py       # buang elemen berulang lintas halaman
│   ├── scoring.py           # skor kandidat main-content
│   ├── content.py           # deteksi main content (tag semantik+scoring+readability)
│   ├── pagination.py        # agregasi artikel multi-halaman/infinite scroll
│   ├── semantic.py          # ekstraksi heading/paragraf/list/code/blockquote
│   ├── links.py             # ekstraksi & normalisasi link
│   ├── images.py            # ekstraksi & normalisasi gambar + caption
│   ├── tables.py            # ekstraksi tabel HTML
│   ├── embeds.py            # ekstraksi iframe/embed (YouTube, tweet, dll)
│   ├── screenshot_fallback.py  # fallback visual saat deteksi DOM gagal
│   └── renderers/
│       ├── __init__.py
│       ├── base.py          # interface BaseRenderer
│       ├── markdown.py      # renderer utama
│       ├── json.py
│       └── txt.py
│
├── tests/
│   ├── __init__.py
│   ├── test_article.py      # artikel/blog standar
│   ├── test_documentation.py  # halaman dokumentasi teknis (code block, sidebar)
│   ├── test_dynamic.py      # halaman SPA/JS-heavy
│   ├── test_table.py        # ekstraksi tabel
│   └── test_metadata.py     # prioritas sumber metadata
│
└── cli.py                   # entry point CLI + orchestrator
```

---

## 5. Document Model

```
Document
├── url: str
├── metadata: Metadata
│   ├── title, author, published, language
│   └── canonical_url, source (json-ld/og/meta/title-tag)
└── blocks: List[Block]
    ├── HeadingBlock    (level, text)
    ├── ParagraphBlock  (text)
    ├── ListBlock       (items, ordered)
    ├── TableBlock      (headers, rows)
    ├── ImageBlock      (src, alt, caption)
    ├── CodeBlock       (code, language)
    ├── BlockquoteBlock (text)
    └── EmbedBlock      (url, embed_type, title)
```

Setiap `Block` punya `confidence` (HIGH/MEDIUM/LOW) — hasil dari
`content.py`/`scoring.py` yang tidak yakin bisa ditandai, supaya
downstream (termasuk potensi fallback LLM di masa depan) tahu bagian
mana yang perlu perhatian ekstra tanpa memproses ulang seluruh dokumen.

Beda dari pdf2markdown: tidak ada konsep "Page" — satu `Document` mewakili
satu URL (atau hasil agregasi beberapa halaman lewat `pagination.py`).

---

## 6. Alur Pipeline Detail

| Tahap | Modul | Input | Output |
|---|---|---|---|
| 1. Cek izin & rate limit | `robots.py` | URL | boleh/tidak diakses + delay |
| 2. Fetch (dengan cache) | `cache.py`, `fetcher.py`, `browser.py`, `consent.py` | URL | rendered HTML, status, final URL |
| 3. Dispatch tipe konten | `content_type.py` | headers + konten | lanjut HTML / delegasi PDF / block gambar tunggal |
| 4. Ekstraksi metadata | `metadata.py` | HTML | objek `Metadata` |
| 5. Pembersihan DOM | `cleaner.py`, `boilerplate.py` | HTML | DOM bersih |
| 6. Deteksi main content | `scoring.py`, `content.py` | DOM bersih | elemen main-content + confidence |
| 7. Fallback (kondisional) | `screenshot_fallback.py` | confidence rendah | screenshot untuk review |
| 8. Agregasi multi-halaman (kondisional) | `pagination.py` | beberapa Document | satu Document gabungan |
| 9. Ekstraksi semantik | `semantic.py`, `links.py`, `images.py`, `tables.py`, `embeds.py` | main-content | list `Block` |
| 10. Rakit Document Model | `model.py` | metadata + blocks | objek `Document` |
| 11. Render output | `renderers/*.py` | `Document` | string Markdown/JSON/TXT |

---

## 7. Urutan Pengembangan

Berurutan berdasarkan dependency, supaya tiap modul bisa diuji begitu
dependensinya selesai:

1. **`model.py`** — fondasi skema, semua modul lain bergantung ke sini.
2. **`errors.py`** — taksonomi error, dipakai `fetcher.py`; ringan & tanpa dependensi lain.
3. **`robots.py`** — independen, dipanggil paling awal sebelum browser dibuka.
4. **`browser.py`** — wrapper Playwright inti, dasar semua modul fetch.
5. **`consent.py`** — butuh `browser.py` (perlu `page` untuk klik dismiss).
6. **`cache.py`** — independen secara logic, tapi dipakai di dalam `fetcher.py`.
7. **`fetcher.py`** — orkestrasi robots+browser+consent+cache+retry → HTML mentah.
8. **`content_type.py`** — jalan begitu `fetcher.py` mengembalikan headers/konten.
9. **`metadata.py`** — butuh HTML hasil fetch, independen dari cleaner/content.
10. **`cleaner.py`** — pembersihan pasti, tahap pertama sebelum analisis lebih lanjut.
11. **`boilerplate.py`** — butuh output `cleaner.py` + sample dari beberapa halaman domain yang sama.
12. **`scoring.py`** — dipakai oleh `content.py`, jadi diisi lebih dulu/bersamaan.
13. **`content.py`** — butuh `scoring.py` sudah punya kontrak fungsi.
14. **`pagination.py`** — butuh hasil deteksi `content.py` sebagai basis agregasi.
15. **`semantic.py`** — ekstraksi block dari main-content hasil tahap 12–14.
16. **`links.py`, `images.py`, `tables.py`, `embeds.py`** — independen satu sama lain, bisa dikerjakan paralel setelah `semantic.py` punya struktur dasar.
17. **`screenshot_fallback.py`** — fallback, baru relevan setelah alur normal (tahap 1–16) berjalan.
18. **`renderers/base.py` → `markdown.py` → `json.py` → `txt.py`** — butuh `Document` yang stabil; `markdown.py` diprioritaskan karena target utama.
19. **`cli.py`** — orchestrator, butuh semua modul di atas sudah punya kontrak fungsi jelas.
20. **`tests/*.py`** — dikerjakan berdampingan begitu modul terkait mulai diisi, bukan di akhir sekali.

> Catatan: seperti pdf2markdown, tiap file skeleton yang sudah dibuat
> isinya masih `pass` + komentar `# TODO:` — isi bertahap sesuai urutan
> di atas.

---

## 8. Instalasi (rencana dependensi)

```bash
pip install playwright beautifulsoup4 lxml readability-lxml httpx
playwright install chromium
```

- `playwright` — rendering browser (JS execution)
- `beautifulsoup4` + `lxml` — parsing & manipulasi DOM
- `readability-lxml` — fallback ekstraksi ala Readability
- `httpx` — request ringan untuk robots.txt & conditional fetch (cache.py)

---

## 9. Penggunaan (target API — belum diimplementasi)

### Sebagai library

```python
from webfetch import fetch

result = await fetch("https://example.com/article")
print(result.markdown)
```

```python
result = await fetch(
    "https://example.com/article",
    output="markdown",
    javascript=True,
    extract_images=True,
    extract_links=True,
    extract_metadata=True,
)

print(result.title)
print(result.author)
print(result.metadata)
```

### CLI

```bash
# tampilkan ke stdout
webfetch https://example.com

# simpan ke file
webfetch https://example.com -o article.md

# format lain
webfetch https://example.com --format json
webfetch https://example.com --format txt

# batch dari daftar URL
webfetch urls.txt -o ./output/
```

---

## 10. Prioritas Kualitas

Selaras dengan pdf2markdown — reading order & struktur semantik lebih
penting daripada tampilan Markdown:

```
1. Main content detection    (salah pilih elemen = seluruh hasil rusak)
2. Boilerplate removal        (nav/iklan yang lolos = noise besar buat LLM)
3. Heading hierarchy
4. Paragraph & reading order
5. Table extraction
6. Metadata accuracy
7. Links & images
8. Embeds
9. Styling                    (paling rendah, sama seperti pdf2markdown)
```

---

## 11. Roadmap / Next Steps

- Isi implementasi mengikuti urutan di bagian 7.
- Bangun sample domain kecil (3–5 domain, tiap domain 3+ halaman) untuk
  menguji `boilerplate.py` — modul ini butuh data lintas halaman, jadi
  tidak bisa divalidasi dengan satu halaman saja.
- Setelah alur inti (tahap 1–11 di bagian 6) jalan untuk kasus artikel
  sederhana, baru masuk ke `pagination.py` dan `screenshot_fallback.py`.
- Integrasikan `content_type.py` dengan `pdf2markdown.convert()` secara
  nyata (bukan cuma TODO) begitu kedua pipeline sama-sama siap diuji.
- Pertimbangkan folder `eval/` seperti di pdf2markdown (golden dataset +
  metric akurasi deteksi main-content) begitu pipeline inti stabil.
