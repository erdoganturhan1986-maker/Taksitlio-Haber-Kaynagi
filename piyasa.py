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
SEMBOLLER = {"USD": "USDTRY=X", "EUR": "EURTRY=X", "ALTIN": "GC=F",
             "GUMUS": "SI=F", "BRENT": "BZ=F", "BIST": "XU100.IS"}


def son_iki_kapanis(sembol):
    gecmis = yf.Ticker(sembol).history(period="10d", interval="1d")["Close"].dropna()
    if len(gecmis) < 2:
        raise RuntimeError(f"{sembol}: yeterli veri yok")
    return float(gecmis.iloc[-1]), float(gecmis.iloc[-2])


def main():
    ham = {}
    for ad, sembol in SEMBOLLER.items():
        try:
            ham[ad] = son_iki_kapanis(sembol)
            print(f"{ad} ({sembol}): son {ham[ad][0]:.4f} | önceki {ham[ad][1]:.4f}")
        except Exception as hata:
            print(f"{ad} ({sembol}) alınamadı: {hata}")
    if "USD" not in ham:
        print("Dolar kuru alınamadı; TL hesaplanamaz, mevcut dosya korunuyor.")
        return

    usd, usd_onceki = ham["USD"]
    satirlar = []

    def ekle(ad, deger, onceki, birim):
        satirlar.append({"ad": ad, "deger": round(deger, 4), "onceki": round(onceki, 4),
                         "degisim": round((deger / onceki - 1) * 100, 2), "birim": birim})

    if "ALTIN" in ham:
        ekle("Gram Altın", ham["ALTIN"][0] * usd / ONS_GRAM, ham["ALTIN"][1] * usd_onceki / ONS_GRAM, "TL")
    if "GUMUS" in ham:
        ekle("Gram Gümüş", ham["GUMUS"][0] * usd / ONS_GRAM, ham["GUMUS"][1] * usd_onceki / ONS_GRAM, "TL")
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
