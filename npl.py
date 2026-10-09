"""
BDDK haftalık bülteninin Takipteki Alacaklar tablosundan takipteki kredi tutarlarını
(yaklaşık 15 aylık geçmişle) çeker ve data/bddk_takipteki.csv dosyasına yazar.
NPL oranı dashboard'da canlı kredilerle (data/bddk_krediler.csv) birleştirilerek hesaplanır.
Herkese açık veri okunur; şifre veya anahtar gerekmez.
"""
import html
import os
import re
import urllib.parse
import urllib.request

import pandas as pd

from bddk import ACICI, ANA, AYLAR, HAM, PARCA_SAYISI, seri_getir

CIKTI = "data/bddk_takipteki.csv"
TAKIPTEKI_TABLOSU = "290"
SERILER = {  # Takipteki Alacaklar tablosundaki satır kodları; adlar bddk_krediler.csv ile aynı
    "2.0.2": "Tüketici kredileri (toplam)",
    "2.0.12": "İhtiyaç kredileri",
    "2.0.10": "Konut kredileri",
    "2.0.3": "Bireysel kredi kartları",
}


def tabloyu_ac():
    """Ana sayfayı açar, bülten tarihlerini okur ve oturumu Takipteki Alacaklar tablosuna geçirir."""
    with ACICI.open(ANA, timeout=60) as r:
        sayfa = html.unescape(r.read().decode("utf-8", "replace"))
    tarihler = [f"{int(g):02d}.{AYLAR[a]:02d}.{y}"
                for y, a, g in re.findall(r'class="Yil-(\d{4}) YilDonem"[^>]*>\s*([^/<\s]+)/(\d{1,2})', sayfa)
                if a in AYLAR]
    form = next((f for f in re.findall(r'(?is)<form[^>]*>.*?</form>', sayfa) if 'name="tabloId"' in f), "")
    token = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', form)
    if not tarihler or not token:
        raise RuntimeError("Bülten tarihleri ya da form anahtarı bulunamadı")
    veri = urllib.parse.urlencode({"__RequestVerificationToken": token.group(1),
                                   "tabloId": TAKIPTEKI_TABLOSU}).encode()
    istek = urllib.request.Request(ANA + "/", data=veri, headers={
        "Referer": ANA, "Content-Type": "application/x-www-form-urlencoded"})
    with ACICI.open(istek, timeout=60) as r:
        tablo = r.read().decode("utf-8", "replace")
    if "Takipteki Alacaklar (2+8)" not in html.unescape(tablo):
        raise RuntimeError("Takipteki Alacaklar tablosuna geçilemedi")
    return tarihler


def main():
    os.makedirs(HAM, exist_ok=True)
    tarihler = tabloyu_ac()
    secilen = tarihler[0:13 * PARCA_SAYISI:13]
    print(f"Son bülten: {tarihler[0]} | sorgulanacak tarihler: {secilen}")
    satirlar = []
    for kimlik, ad in SERILER.items():
        adet = 0
        for tarih in secilen:
            try:
                for t, deger in seri_getir(kimlik, tarih):
                    satirlar.append({"seri": ad, "tarih": t, "milyon_tl": deger})
                    adet += 1
            except Exception as hata:
                print(f"{ad} ({tarih}) alınamadı: {hata}")
        print(f"{ad}: {adet} nokta")
    if not satirlar:
        print("Hiç veri alınamadı, mevcut dosya korunuyor.")
        return
    df = pd.DataFrame(satirlar)
    df["tarih"] = pd.to_datetime(df["tarih"], dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    if os.path.exists(CIKTI):
        df = pd.concat([df, pd.read_csv(CIKTI)], ignore_index=True)
    df = df.dropna().drop_duplicates(["seri", "tarih"]).sort_values(["seri", "tarih"])
    df.to_csv(CIKTI, index=False)
    print(f"{CIKTI} yazıldı: {len(df)} satır, {df['tarih'].min()} -> {df['tarih'].max()}")


if __name__ == "__main__":
    main()
