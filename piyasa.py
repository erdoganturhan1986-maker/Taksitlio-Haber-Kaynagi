"""
Yahoo Finance'ten piyasa verilerini çeker, TL karşılıklarını hesaplar ve data/piyasa.csv dosyasına yazar.
Herkese açık veri okunur; şifre veya anahtar gerekmez.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

CIKTI = "data/piyasa.csv"
ONS_GRAM = 31.1034768
SEMBOLLER = {"USD": ["USDTRY=X"], "EUR": ["EURTRY=X"], "ALTIN": ["GC=F"],
             "GUMUS": ["SI=F"], "BRENT": ["BZ=F"], "BIST": ["XU100.IS"]}
# Gram altın piyasada spot (anlık) ons fiyatından hesaplanır; vadeli fiyat (GC=F) biraz daha yüksek seyreder.
# Spot fiyat için anahtar istemeyen servisler sırayla denenir; hiçbiri olmazsa vadeli fiyat kullanılır.
SPOT_SERVISLERI = [
    ("gold-api.com", "https://api.gold-api.com/price/{metal}", lambda d, metal: d["price"]),
    ("goldprice.org", "https://data-asg.goldprice.org/dbXRates/USD",
     lambda d, metal: d["items"][0]["xauPrice" if metal == "XAU" else "xagPrice"]),
]


def spot_fiyat(metal, vadeli):
    """Spot ons fiyatını (USD) döner; bulunamazsa ya da vadeli fiyattan %5'ten fazla saparsa None."""
    for ad, adres, oku in SPOT_SERVISLERI:
        try:
            istek = urllib.request.Request(adres.format(metal=metal), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(istek, timeout=20) as r:
                fiyat = float(oku(json.loads(r.read().decode("utf-8")), metal))
            sapma = abs(fiyat / vadeli - 1)
            print(f"{metal} spot ({ad}): {fiyat:.2f} | vadeli: {vadeli:.2f} | fark: %{sapma * 100:.2f}")
            if sapma <= 0.05:
                return fiyat, ad
            print(f"{metal}: {ad} fiyatı vadeli fiyattan çok farklı, kullanılmadı.")
        except Exception as hata:
            print(f"{metal} spot ({ad}) alınamadı: {str(hata)[:120]}")
    return None, None


def son_iki_kapanis(sembol):
    gecmis = yf.Ticker(sembol).history(period="10d", interval="1d")["Close"].dropna()
    if len(gecmis) < 2:
        raise RuntimeError(f"{sembol}: yeterli veri yok")
    return float(gecmis.iloc[-1]), float(gecmis.iloc[-2])


def main():
    ham, kaynak = {}, {}
    for ad, semboller in SEMBOLLER.items():
        for sembol in semboller:
            try:
                deger = son_iki_kapanis(sembol)
                print(f"{ad} ({sembol}): son {deger[0]:.4f} | önceki {deger[1]:.4f}")
                if ad not in ham:  # listedeki ilk başarılı sembol kullanılır, diğerleri karşılaştırma için yazılır
                    ham[ad], kaynak[ad] = deger, sembol
            except Exception as hata:
                print(f"{ad} ({sembol}) alınamadı: {hata}")
    for ad, metal in (("ALTIN", "XAU"), ("GUMUS", "XAG")):  # vadeli yerine spot fiyat (günlük değişim oranı korunur)
        if ad in ham:
            spot, servis = spot_fiyat(metal, ham[ad][0])
            if spot:
                ham[ad] = (spot, spot * ham[ad][1] / ham[ad][0])
                kaynak[ad] = f"spot ({servis})"
            print(f"{ad} için kullanılan fiyat: {kaynak[ad]}")
    if "USD" not in ham:
        print("Dolar kuru alınamadı; TL hesaplanamaz, mevcut dosya korunuyor.")
        return

    usd, usd_onceki = ham["USD"]
    satirlar = []

    def ekle(ad, deger, onceki, birim, sembol=""):
        satirlar.append({"ad": ad, "deger": round(deger, 4), "onceki": round(onceki, 4),
                         "degisim": round((deger / onceki - 1) * 100, 2), "birim": birim, "kaynak": sembol})

    if "ALTIN" in ham:
        ekle("Gram Altın", ham["ALTIN"][0] * usd / ONS_GRAM, ham["ALTIN"][1] * usd_onceki / ONS_GRAM, "TL", kaynak["ALTIN"])
    if "GUMUS" in ham:
        ekle("Gram Gümüş", ham["GUMUS"][0] * usd / ONS_GRAM, ham["GUMUS"][1] * usd_onceki / ONS_GRAM, "TL", kaynak["GUMUS"])
    ekle("Dolar", usd, usd_onceki, "TL")
    if "EUR" in ham:
        ekle("Euro", *ham["EUR"], "TL")
    if "BRENT" in ham:
        ekle("Brent Petrol", ham["BRENT"][0], ham["BRENT"][1], "$/varil")
    if "BIST" in ham:
        ekle("BIST 100", *ham["BIST"], "puan")

    df = pd.DataFrame(satirlar)
    df["guncelleme"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs("data", exist_ok=True)
    df.to_csv(CIKTI, index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
