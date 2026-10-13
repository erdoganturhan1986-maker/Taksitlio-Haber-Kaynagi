"""
Yahoo Finance'ten piyasa verilerini çeker, TL karşılıklarını hesaplar ve data/piyasa.csv dosyasına yazar.
Herkese açık veri okunur; şifre veya anahtar gerekmez.
"""
import os
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

CIKTI = "data/piyasa.csv"
ONS_GRAM = 31.1034768
# Altın ve gümüşte önce spot (anlık) fiyat denenir; gram altın piyasada spot fiyattan hesaplanır.
# Spot alınamazsa vadeli işlem fiyatına (biraz daha yüksek seyreder) dönülür.
SEMBOLLER = {"USD": ["USDTRY=X"], "EUR": ["EURTRY=X"], "ALTIN": ["XAUUSD=X", "GC=F"],
             "GUMUS": ["XAGUSD=X", "SI=F"], "BRENT": ["BZ=F"], "BIST": ["XU100.IS"]}


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
    for ad in ("ALTIN", "GUMUS"):
        if ad in kaynak:
            print(f"{ad} için kullanılan fiyat: {kaynak[ad]} ({'spot' if kaynak[ad].endswith('=X') else 'vadeli'})")
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
        ekle("Brent Petrol", ham["BRENT"][0] * usd, ham["BRENT"][1] * usd_onceki, "TL/varil")
    if "BIST" in ham:
        ekle("BIST 100", *ham["BIST"], "puan")

    df = pd.DataFrame(satirlar)
    df["guncelleme"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs("data", exist_ok=True)
    df.to_csv(CIKTI, index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
