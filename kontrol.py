"""
Veri kontrolü: Her veri güncellemesinin sonunda kaynakların tazeliğini ve adımların sonucunu denetler.
data/kontrol.json dosyasını yazar (dashboard'daki veri durumu satırı bunu okur).
Sorun varsa GitHub'a bildirir; çalışma kırmızı çarpıyla biter ve e-posta uyarısı gider.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import pandas as pd

# anahtar: (görünen ad, dosya, tarih sütunu, sıklık, en fazla kaç gün eski olabilir, adım ortam değişkeni)
KAYNAKLAR = {
    "bddk": ("BDDK krediler", "data/bddk_krediler.csv", "tarih", "haftalık", 13, "ADIM_BDDK"),
    "npl": ("BDDK takipteki alacaklar", "data/bddk_takipteki.csv", "tarih", "haftalık", 13, "ADIM_NPL"),
    "faiz": ("TCMB kredi faizleri", "data/faiz_oranlari.csv", "tarih", "haftalık", 13, "ADIM_FAIZ"),
    "tufe": ("TÜFE", "data/tufe.csv", "donem", "aylık", 66, "ADIM_TUFE"),
    "guven": ("Tüketici güveni", "data/tuketici_guven.csv", "ay", "aylık", 66, "ADIM_GUVEN"),
}


def main():
    simdi = datetime.now(timezone.utc)
    sonuc, sorunlar = {}, []
    for anahtar, (ad, dosya, sutun, siklik, sinir, ortam) in KAYNAKLAR.items():
        adim = os.environ.get(ortam, "bilinmiyor")
        try:
            son = pd.to_datetime(pd.read_csv(dosya)[sutun].astype(str)).max()
            son = son.tz_localize("UTC") if son.tzinfo is None else son
            yas = (simdi - son).days
        except Exception as hata:
            son, yas = None, None
            print(f"{ad}: dosya okunamadı ({hata})")
        if adim == "failure":
            durum = "hata"
        elif yas is None or yas > sinir:
            durum = "gecikmeli"
        else:
            durum = "guncel"
        if durum != "guncel":
            sorunlar.append(f"{ad}: {durum} (son veri: {son.date() if son is not None else 'yok'}, adım: {adim})")
        sonuc[anahtar] = {"ad": ad, "siklik": siklik, "son_veri": son.strftime("%Y-%m-%d") if son is not None else None,
                          "durum": durum, "adim": adim}
        print(f"{ad}: son veri {sonuc[anahtar]['son_veri']} | {yas} gün | adım {adim} | {durum}")
    os.makedirs("data", exist_ok=True)
    json.dump({"son_kontrol": simdi.isoformat(), "kaynaklar": sonuc}, open("data/kontrol.json", "w"),
              ensure_ascii=False, indent=1)
    if sorunlar:
        print("SORUN:\n  " + "\n  ".join(sorunlar))
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as cikti:
        cikti.write(f"sorun={'evet' if sorunlar else 'hayir'}\n")


if __name__ == "__main__":
    main()
