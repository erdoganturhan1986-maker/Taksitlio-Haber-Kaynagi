"""
Haber kaynaklarına erişim: Google Haberler araması, güvenilir yayınların akışları,
Google Haberler linkinden orijinal habere ulaşma ve haber sayfasından görsel ile metin bölümü alma.
"""
import calendar
import html
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import feedparser

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def _tarih(girdi):
    zaman = girdi.get("published_parsed") or girdi.get("updated_parsed")
    return datetime.fromtimestamp(calendar.timegm(zaman), tz=timezone.utc) if zaman else None


def google_ara(sorgu, gun=10):
    """Google Haberler'de son `gun` gündeki haberleri arar."""
    adres = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(f"{sorgu} when:{gun}d")
             + "&hl=tr&gl=TR&ceid=TR:tr")
    sonuc = []
    for g in feedparser.parse(adres, agent=UA).entries:
        kaynak = g.get("source", {}).get("title", "").strip()
        baslik = g.get("title", "").strip()
        if kaynak and baslik.endswith(" - " + kaynak):
            baslik = baslik[: -len(" - " + kaynak)]
        sonuc.append({"baslik": html.unescape(baslik), "kaynak": kaynak, "tarih": _tarih(g),
                      "link": g.get("link", ""), "google": True})
    return sonuc


def akis_oku(ad, adres):
    """Bir yayının kendi haber akışını okur (görsel ve kısa özetle birlikte)."""
    sonuc = []
    for g in feedparser.parse(adres, agent=UA).entries:
        gorsel = None
        for alan in ("media_content", "media_thumbnail"):
            if g.get(alan):
                gorsel = g[alan][0].get("url")
                break
        if not gorsel:
            for ek in g.get("enclosures", []):
                if str(ek.get("type", "")).startswith("image"):
                    gorsel = ek.get("href")
        ozet = re.sub(r"<[^>]+>", " ", g.get("summary", ""))
        if not gorsel:
            resim = re.search(r'<img[^>]+src="([^"]+)"', g.get("summary", ""))
            gorsel = resim.group(1) if resim else None
        sonuc.append({"baslik": html.unescape(g.get("title", "").strip()), "kaynak": ad, "tarih": _tarih(g),
                      "link": g.get("link", ""), "gorsel": gorsel, "metin": html.unescape(re.sub(r"\s+", " ", ozet)).strip(),
                      "google": False})
    return sonuc


def orijinal_link(google_linki):
    """Google Haberler linkini haberin asıl adresine çevirir; çevrilemezse None."""
    try:
        from googlenewsdecoder import gnewsdecoder
        sonuc = gnewsdecoder(google_linki, interval=1)
        return sonuc.get("decoded_url") if sonuc.get("status") else None
    except Exception as hata:
        print("Link çözülemedi:", str(hata)[:120])
        return None


def sayfa_bilgisi(adres):
    """Haber sayfasından görsel, kısa açıklama ve AI'ın okuması için metin bölümü alır (sayfada yayınlanmaz)."""
    try:
        istek = urllib.request.Request(adres, headers={"User-Agent": UA})
        with urllib.request.urlopen(istek, timeout=25) as r:
            sayfa = r.read(800_000).decode("utf-8", "replace")
    except Exception as hata:
        print("Sayfa okunamadı:", str(hata)[:120])
        return {}

    def meta(ad):
        m = (re.search(rf'<meta[^>]+(?:property|name)=["\']{ad}["\'][^>]+content=["\']([^"\']+)', sayfa)
             or re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{ad}["\']', sayfa))
        return html.unescape(m.group(1)).strip() if m else None

    paragraflar = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", p))).strip()
                   for p in re.findall(r"<p[^>]*>(.*?)</p>", sayfa, re.S)]
    metin = " ".join(p for p in paragraflar if len(p) > 60)[:1500]
    return {"gorsel": meta("og:image"), "ozet": meta("og:description"), "metin": metin}
