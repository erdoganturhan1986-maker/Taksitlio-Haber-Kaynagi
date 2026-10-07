"""
BDDK haftalık bülteninden kredi hacmi geçmişini çeker ve data/bddk_krediler.csv dosyasına yazar.
Herkese açık veri okunur; şifre veya anahtar gerekmez.
"""
import html
import http.cookiejar
import json
import os
import re
import ssl
import urllib.parse
import urllib.request

import pandas as pd

ANA = "https://www.bddk.org.tr/BultenHaftalik"
SERVIS = ANA + "/tr/Home/KiyaslamaJsonGetir"
CIKTI = "data/bddk_krediler.csv"
HAM = "data/bddk_ham"
SERILER = {
    "1.0.3": "Tüketici kredileri (toplam)",
    "1.0.6": "İhtiyaç kredileri",
    "1.0.4": "Konut kredileri",
    "1.0.8": "Bireysel kredi kartları",
}
PARCA_SAYISI = 5   # her parça 13 hafta -> yaklaşık 15 aylık geçmiş
AYLAR = {"Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Haziran": 6, "Temmuz": 7,
         "Ağustos": 8, "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12}

# BDDK sertifika zincirini eksik gönderiyor; sadece herkese açık veriyi okumak için esnek mod
ESNEK = ssl.create_default_context()
ESNEK.check_hostname = False
ESNEK.verify_mode = ssl.CERT_NONE
ACICI = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
    urllib.request.HTTPSHandler(context=ESNEK),
)
ACICI.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")]


def sayiya(x):
    if isinstance(x, (int, float)):
        return float(x)
    x = str(x).strip()
    if "," in x:
        x = x.replace(".", "").replace(",", ".")
    return float(x)


def bulten_tarihleri():
    """Sayfadaki dönem listesinden tüm haftalık bülten tarihlerini (yeniden eskiye) çıkarır."""
    with ACICI.open(ANA, timeout=60) as r:
        sayfa = html.unescape(r.read().decode("utf-8", "replace"))
    tarihler = []
    for yil, ay, gun in re.findall(r'class="Yil-(\d{4}) YilDonem"[^>]*>\s*([^/<\s]+)/(\d{1,2})', sayfa):
        if ay in AYLAR:
            tarihler.append(f"{int(gun):02d}.{AYLAR[ay]:02d}.{yil}")
    if not tarihler:
        raise RuntimeError("Bülten tarihleri sayfada bulunamadı")
    return tarihler


def seri_getir(kimlik, tarih, gun=90):
    veri = urllib.parse.urlencode({
        "dil": "tr", "tarih": tarih, "id": kimlik, "parabirimi": "TRY",
        "sutun": 3, "tarafKodu": "10001", "gun": gun,
    }).encode()
    istek = urllib.request.Request(SERVIS, data=veri, headers={
        "X-Requested-With": "XMLHttpRequest", "Referer": ANA,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    })
    with ACICI.open(istek, timeout=60) as r:
        govde = r.read().decode("utf-8", "replace")
    with open(f"{HAM}/{kimlik}_{tarih}.json", "w") as f:
        f.write(govde)
    sonuc = json.loads(govde)
    x = sonuc.get("XEkseni") or []
    y = sonuc.get("YEkseni") or []
    if y and isinstance(y[0], dict):  # grafik veri seti biçimi
        y = y[0].get("data", [])
    return [(tx, sayiya(ty)) for tx, ty in zip(x, y)]


def main():
    os.makedirs(HAM, exist_ok=True)
    for eski in os.listdir(HAM):  # önceki ham dosyaları temizle
        os.remove(os.path.join(HAM, eski))
    tarihler = bulten_tarihleri()
    secilen = tarihler[0:13 * PARCA_SAYISI:13]  # her 13 haftada bir bülten tarihi
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
    if os.path.exists(CIKTI):  # eski geçmişi koru, yenisiyle birleştir
        df = pd.concat([df, pd.read_csv(CIKTI)], ignore_index=True)
    df = df.dropna().drop_duplicates(["seri", "tarih"]).sort_values(["seri", "tarih"])
    df.to_csv(CIKTI, index=False)
    print(f"{CIKTI} yazıldı: {len(df)} satır, {df['tarih'].min()} -> {df['tarih'].max()}")


if __name__ == "__main__":
    main()
