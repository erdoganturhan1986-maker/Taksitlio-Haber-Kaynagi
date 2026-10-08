"""
TCMB EVDS'den aylık tüketici güven endeksi ve seçili alt endeksleri çeker,
data/tuketici_guven.csv dosyasına yazar.
Erişim anahtarı GitHub'ın gizli bilgilerinden (EVDS_API_KEY) okunur, kodda yer almaz.
"""
import json
import os
import ssl
import urllib.request
from datetime import date

import pandas as pd

ANA = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"
CIKTI = "data/tuketici_guven.csv"
SERILER = {
    "TP.TG2.Y01": "Tüketici güven endeksi",
    "TP.TG2.Y08": "Dayanıklı mal almaya uygunluk",
    "TP.TG2.Y09": "Dayanıklı mal harcama beklentisi",
    "TP.TG2.Y13": "Borçla tüketim ihtimali",
    "TP.TG2.Y15": "Fiyat artış beklentisi",
}
BASLANGIC = "01-01-2023"

ESNEK = ssl.create_default_context()
ESNEK.check_hostname = False
ESNEK.verify_mode = ssl.CERT_NONE


def ay_cevir(metin):
    """EVDS aylık tarihlerini ('2026-9' ya da '01-09-2026') ayın ilk gününe çevirir."""
    metin = str(metin).strip()
    for bicim in ("%Y-%m", "%d-%m-%Y"):
        try:
            return pd.to_datetime(metin, format=bicim).strftime("%Y-%m-01")
        except ValueError:
            continue
    raise ValueError(f"Tarih anlaşılamadı: {metin}")


def seri_getir(anahtar, kod):
    bitis = date.today().strftime("%d-%m-%Y")
    yol = f"series={kod}&startDate={BASLANGIC}&endDate={bitis}&type=json"
    istek = urllib.request.Request(ANA + yol, headers={"key": anahtar, "User-Agent": "Mozilla/5.0"})
    son = ""
    for baglam in (None, ESNEK):
        try:
            with urllib.request.urlopen(istek, timeout=60, context=baglam) as r:
                veri = json.loads(r.read().decode("utf-8", "replace"))
            break
        except Exception as hata:
            son = str(hata)[:200]
    else:
        raise RuntimeError(son)
    alan = kod.replace(".", "_")
    satirlar = []
    for kayit in veri.get("items", []):
        deger = kayit.get(alan)
        if deger in (None, "", "null"):
            continue
        satirlar.append({"ay": ay_cevir(kayit["Tarih"]), "deger": float(deger)})
    return satirlar


def main():
    anahtar = os.environ.get("EVDS_API_KEY", "").strip()
    if not anahtar:
        print("EVDS_API_KEY tanımlı değil, atlandı.")
        return
    tum = []
    for kod, ad in SERILER.items():
        try:
            satirlar = seri_getir(anahtar, kod)
            print(f"{ad}: {len(satirlar)} ay")
            tum += [{"seri": ad, "kod": kod, **s} for s in satirlar]
        except Exception as hata:
            print(f"{ad} alınamadı: {hata}")
    if not tum:
        print("Hiç veri alınamadı, mevcut dosya korunuyor.")
        return
    df = pd.DataFrame(tum).drop_duplicates(["seri", "ay"]).sort_values(["seri", "ay"])
    os.makedirs("data", exist_ok=True)
    df.to_csv(CIKTI, index=False)
    print(f"{CIKTI} yazıldı: {len(df)} satır, {df['ay'].min()} -> {df['ay'].max()}")
    print(df.groupby("seri").tail(2).to_string(index=False))


if __name__ == "__main__":
    main()
