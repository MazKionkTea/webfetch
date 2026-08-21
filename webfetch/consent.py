"""
consent.py
Deteksi & dismiss cookie consent banner / popup secara aktif.
Beberapa situs mengunci konten sampai banner ini di-klik "accept",
jadi tidak cukup hanya dihapus dari DOM setelah render (lihat cleaner.py).
"""


from playwright.async_api import Page
from typing import List, Optional

class CookieConsentHandler:
    """
    Handler otomatis untuk mendeteksi dan menutup banner persetujuan cookie (GDPR/CCPA).
    
    Kelas ini menggunakan daftar selector CSS umum dari penyedia banner populer 
    (OneTrust, Cookiebot, Quantcast, dll) untuk menemukan tombol "Accept All" atau "Close".
    Tujuannya adalah membersihkan halaman dari overlay yang menghalangi konten utama 
    sebelum proses ekstraksi dimulai.
    
    Strategi:
    1. Deteksi keberadaan elemen banner yang visible di DOM.
    2. Cari tombol aksi primer (Accept/Agree/OK) dalam konteks banner tersebut.
    3. Klik tombol tersebut dan tunggu hingga banner hilang atau tertutup.
    
    Attributes:
        COMMON_SELECTORS (list): Daftar tuple (selector_banner, selector_button_accept) 
                                 yang mencakup pola umum di internet.
    """

    # Daftar selector umum: (Selector Container Banner, Selector Tombol Accept/Close)
    COMMON_SELECTORS = [
        # OneTrust (sangat umum)
        ("#onetrust-banner-sdk", "#onetrust-accept-btn-handler"),
        ("#onetrust-consent-sdk", "#onetrust-accept-btn"),
        
        # Cookiebot
        ("#CybotCookiebotDialog", "#CybotCookiebotDialogBodyButtonDecline"), # Seringkali 'Decline' menutup juga
        ("#CybotCookiebotDialog", "#CybotCookiebotDialogBodyButtonAccept"),
        
        # Quantcast Choice
        ("#cmp-container", ".save-and-exit-btn"),
        ("#quantcast-choice", ".qc-cmp-button"),
        
        # Osano / Common EU Banner
        ("#osano-cm-dom-content", "#osano-cm-agree-button"),
        ("#eu-cookie-compliance-banner", ".cookie-agree-button"),
        
        # Generic / Custom selectors (sering digunakan tema WordPress/JS custom)
        (".cookie-consent", ".accept-cookies"),
        (".cookie-banner", ".btn-accept"),
        ("[data-testid='cookie-policy-drawer']", "button:has-text('Accept')"),
        ("div[class*='cookie-banner']", "button:has-text('OK')"),
        
        # Fallback: Cari tombol dengan teks umum di seluruh dokumen jika container tak terdeteksi
        (None, "button:has-text('Accept All')"),
        (None, "button:has-text('I Agree')"),
        (None, "button:has-text('Allow Cookies')"),
        (None, "a:has-text('Accept')"),
    ]

    async def detect_consent_banner(self, page: Page) -> bool:
        """
        Mendeteksi apakah ada banner persetujuan cookie yang terlihat di halaman.
        
        Metode ini melakukan iterasi melalui `COMMON_SELECTORS` dan memeriksa apakah
        elemen container banner ada di DOM dan memiliki properti `isVisible()` True.
        
        Args:
            page: Objek page Playwright yang sedang aktif.
            
        Returns:
            bool: True jika banner terdeteksi dan terlihat, False jika tidak.
        """
        for banner_selector, _ in self.COMMON_SELECTORS:
            if banner_selector is None:
                continue
                
            try:
                # Cek apakah elemen ada dan visible dengan timeout singkat (2 detik)
                element = await page.wait_for_selector(banner_selector, state="visible", timeout=2000)
                if element:
                    return True
            except Exception:
                # Timeout atau elemen tidak ditemukan, lanjut ke selector berikutnya
                continue
        
        return False

    async def dismiss(self, page: Page) -> bool:
        """
        Mencoba mengklik tombol accept/dismiss pada banner cookie jika ditemukan.
        
        Alur eksekusi:
        1. Iterasi daftar `COMMON_SELECTORS`.
        2. Jika container banner ditemukan (opsional), cari tombol accept di dalamnya.
        3. Jika container tidak dispesifikasikan (None), cari tombol accept global.
        4. Klik tombol pertama yang cocok dan visible.
        5. Tunggu sebentar agar animasi penutupan selesai.
        
        Args:
            page: Objek page Playwright yang sedang aktif.
            
        Returns:
            bool: True jika berhasil menemukan dan mengklik tombol, False jika gagal.
        """
        for banner_selector, button_selector in self.COMMON_SELECTORS:
            try:
                button_element = None
                
                # Strategi 1: Cari tombol di dalam container banner spesifik
                if banner_selector:
                    container = await page.query_selector(banner_selector)
                    if container:
                        # Coba cari tombol di dalam container ini
                        button_element = await container.query_selector(button_selector)
                        
                        # Fallback: Jika selector tombol relatif gagal, coba kombinasi CSS descendant
                        if not button_element:
                            combined_selector = f"{banner_selector} {button_selector}"
                            button_element = await page.query_selector(combined_selector)

                # Strategi 2: Jika tidak ada container atau gagal, cari tombol secara global
                # (Khusus untuk selector teks umum di akhir list COMMON_SELECTORS)
                if not button_element and button_selector:
                    # Cek apakah selector ini adalah selector teks Playwright
                    if "has-text" in button_selector or button_selector.startswith("button:") or button_selector.startswith("a:"):
                         button_element = await page.query_selector(button_selector)
                    else:
                        # Selector CSS biasa
                        button_element = await page.query_selector(button_selector)

                # Jika tombol ditemukan dan visible, klik
                if button_element:
                    is_visible = await button_element.is_visible()
                    if is_visible:
                        await button_element.click(timeout=3000)
                        # Beri waktu sebentar untuk animasi tutup/banner hilang
                        await page.wait_for_timeout(500) 
                        return True
                        
            except Exception:
                # Error saat query atau klik, lanjut ke opsi selector berikutnya
                continue
        
        return False