"""
TCMB EVDS'den haftalık kart harcama tutarlarını çeker ve data/kart_harcama.csv dosyasına yazar.
Erişim anahtarı GitHub'ın gizli bilgilerinden (EVDS_API_KEY) okunur, kodda yer almaz.
"""
import json
import os
import ssl
import urllib.request
from datetime import date

import pandas as pd

ANA = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"
CIKTI = "data/kart_harcama.csv"
SERILER = {
    "TP.KKHARTUT.KT1": "Kart harcaması (toplam)",
    "TP.KKHARTUT.KT8": "Elektrik-elektronik eşya, bilgisayar",
}
BASLANGIC = "01-01-2024"

ESNEK = ssl.create_default_context()
ESNEK.check_hostname = False
ESNEK.verify_mode = ssl.CERT_NONE


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
        satirlar.append({"tarih": kayit["Tarih"], "deger": float(deger)})
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
            print(f"{ad}: {len(satirlar)} hafta")
            tum += [{"seri": ad, "kod": kod, **s} for s in satirlar]
        except Exception as hata:
            print(f"{ad} alınamadı: {hata}")
    if not tum:
        print("Hiç veri alınamadı, mevcut dosya korunuyor.")
        return
    df = pd.DataFrame(tum)
    df["tarih"] = pd.to_datetime(df["tarih"], dayfirst=True).dt.strftime("%Y-%m-%d")
    df = df.drop_duplicates(["seri", "tarih"]).sort_values(["seri", "tarih"])
    os.makedirs("data", exist_ok=True)
    df.to_csv(CIKTI, index=False)
    print(f"{CIKTI} yazıldı: {len(df)} satır, {df['tarih'].min()} -> {df['tarih'].max()}")
    print(df.tail(6).to_string(index=False))


if __name__ == "__main__":
    main()
