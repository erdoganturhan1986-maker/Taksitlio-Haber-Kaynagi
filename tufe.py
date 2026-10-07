"""
TCMB tüketici fiyatları sayfasından aylık TÜFE değişimlerini çeker,
bunlardan bir fiyat endeksi oluşturur ve data/tufe.csv dosyasına yazar.
Herkese açık veri okunur; şifre veya anahtar gerekmez.
"""
import html
import os
import re
import ssl
import urllib.request

import pandas as pd

ADRES = ("https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/"
         "Istatistikler/Enflasyon+Verileri/Tuketici+Fiyatlari")
CIKTI = "data/tufe.csv"
HAM = "data/tufe_ham.html"

ESNEK = ssl.create_default_context()
ESNEK.check_hostname = False
ESNEK.verify_mode = ssl.CERT_NONE


def sayfa_al():
    istek = urllib.request.Request(ADRES, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    for baglam in (None, ESNEK):
        try:
            with urllib.request.urlopen(istek, timeout=60, context=baglam) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as hata:
            son_hata = hata
    raise RuntimeError(f"TCMB sayfası alınamadı: {son_hata}")


def sayi(x):
    return float(x.replace(".", "").replace(",", ".")) if "," in x else float(x)


def main():
    os.makedirs("data", exist_ok=True)
    sayfa = sayfa_al()
    with open(HAM, "w") as f:
        f.write(sayfa)
    metin = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", sayfa)))
    # Satır biçimi: "09-2026 29,73 1,84"  (ay-yıl, yıllık %, aylık %)
    bulunan = re.findall(r"\b(\d{2})-(\d{4})\s+(-?\d+[.,]\d+)\s+(-?\d+[.,]\d+)", metin)
    if not bulunan:
        print("Tablo bulunamadı; sayfa data/tufe_ham.html olarak kaydedildi.")
        return
    df = pd.DataFrame(bulunan, columns=["ay", "yil", "yillik", "aylik"])
    df["donem"] = df["yil"] + "-" + df["ay"]
    df["yillik"] = df["yillik"].map(sayi)
    df["aylik"] = df["aylik"].map(sayi)
    df = df.drop_duplicates("donem").sort_values("donem")[["donem", "yillik", "aylik"]]
    # Aylık değişimleri zincirleyerek endeks oluştur (ilk ay = 100)
    endeks, degerler = 100.0, []
    for i, aylik in enumerate(df["aylik"]):
        endeks = 100.0 if i == 0 else endeks * (1 + aylik / 100)
        degerler.append(round(endeks, 4))
    df["endeks"] = degerler
    df.to_csv(CIKTI, index=False)
    print(f"{CIKTI} yazıldı: {len(df)} ay, {df['donem'].min()} -> {df['donem'].max()}")
    print(df.tail(4).to_string(index=False))


if __name__ == "__main__":
    main()
