"""
BDDK haftalık bülteninden kredi hacmi geçmişini çeker ve data/bddk_krediler.csv dosyasına yazar.
Herkese açık veri okunur; şifre veya anahtar gerekmez.
"""
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
GUN_SECENEKLERI = [430, 400, 365]  # 13 aydan fazla geçmiş için

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


def son_bulten_tarihi():
    with ACICI.open(ANA, timeout=60) as r:
        sayfa = r.read().decode("utf-8", "replace")
    m = re.search(r'"tarih"\s*:\s*\'(\d{2}\.\d{2}\.\d{4})\'', sayfa)
    if not m:
        raise RuntimeError("Bülten tarihi sayfada bulunamadı")
    return m.group(1)


def seri_getir(kimlik, tarih, gun):
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
    with open(f"{HAM}/{kimlik}_{gun}.json", "w") as f:
        f.write(govde)
    sonuc = json.loads(govde)
    x = sonuc.get("XEkseni") or []
    y = sonuc.get("YEkseni") or []
    if y and isinstance(y[0], dict):  # grafik veri seti biçimi
        y = y[0].get("data", [])
    return [(tx, sayiya(ty)) for tx, ty in zip(x, y)]


def main():
    os.makedirs(HAM, exist_ok=True)
    tarih = son_bulten_tarihi()
    print(f"Son bülten tarihi: {tarih}")
    satirlar = []
    for kimlik, ad in SERILER.items():
        noktalar = []
        for gun in GUN_SECENEKLERI:
            try:
                noktalar = seri_getir(kimlik, tarih, gun)
                if noktalar:
                    break
            except Exception as hata:
                print(f"{ad} ({gun} gün) alınamadı: {hata}")
        print(f"{ad}: {len(noktalar)} hafta")
        for t, deger in noktalar:
            satirlar.append({"seri": ad, "tarih": t, "milyon_tl": deger})
    if not satirlar:
        print("Hiç veri alınamadı, mevcut dosya korunuyor.")
        return
    df = pd.DataFrame(satirlar)
    df["tarih"] = pd.to_datetime(df["tarih"], dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna().drop_duplicates(["seri", "tarih"]).sort_values(["seri", "tarih"])
    df.to_csv(CIKTI, index=False)
    print(f"{CIKTI} yazıldı: {len(df)} satır, {df['tarih'].min()} -> {df['tarih'].max()}")


if __name__ == "__main__":
    main()
