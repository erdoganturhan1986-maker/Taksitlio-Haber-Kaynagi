"""
Kural tabanlı agent: Haber başlıklarındaki piyasa rakamlarını kalıplarla yakalar.
Hiçbir dış servise bağlanmaz, ücretsizdir. Her çalışmada tüm başlıkları baştan işler.
"""
import re

import pandas as pd

HABERLER = "data/haberler.csv"
RAKAMLAR = "data/rakamlar.csv"
SUTUNLAR = ["haber_tarihi", "gosterge", "sirket", "deger", "birim", "donem",
            "aciklama", "baslik", "kaynak", "link"]

SIRKETLER = {"Vatan": ["vatan bilgisayar", "vatan"], "Teknosa": ["teknosa"],
             "MediaMarkt": ["mediamarkt", "media markt"]}
DUSUS = ["düştü", "geriledi", "azaldı", "daraldı", "düşüş", "kaybetti", "eksi"]
YABANCI = ["abd", "amerika", "euro bölgesi", "avro bölgesi", "avrupa", "almanya", "ingiltere",
           "fransa", "italya", "ispanya", "isveç", "yunanistan", "avustralya", "japonya", "çin",
           "kanada", "rusya", "hindistan", "afrika", "brezilya", "meksika", "kore", "polonya",
           "tayland", "vietnam", "endonezya", "arjantin", "macaristan",
           "vnd", "karaborsa"]
ALT_KALEM = ["kira", "eğitim", "gıda", "konut", "ulaştırma", "sağlık", "giyim"]
DEGISIM = ["arttı", "artış", "yükseldi", "büyüdü", "geriledi", "azaldı", "düştü", "daraldı", "düşüş"]
AYLAR = "ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık"
SAYI = r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)"
YUZDE = re.compile(r"(?:yüzde\s*|%\s*)" + SAYI)
PARA = re.compile(SAYI + r"\s*(trilyon|milyar|milyon|bin)?\s*(tl|lira)\b")
PUAN = re.compile(SAYI + r"\s*puan")
KUR = re.compile(r"\b(\d{2}[.,]\d{2,4})\b")
MAGAZA = re.compile(r"(\d+)\s*(?:yeni\s+)?mağaza")


def kucuk(metin):
    return str(metin).replace("I", "ı").replace("İ", "i").lower()


def sayi(metin):
    if "," in metin:
        metin = metin.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", metin):
        metin = metin.replace(".", "")
    return float(metin)


def donem_bul(b):
    ay = re.search(rf"\b({AYLAR})\w*(?:\s+(\d{{4}}))?", b)
    if ay:
        return (ay.group(1).capitalize() + (" " + ay.group(2) if ay.group(2) else "")).strip()
    ceyrek = re.search(r"(\d)\.?\s*çeyrek", b)
    return f"Q{ceyrek.group(1)}" if ceyrek else ""


def yuzde(b, isaretli=False, sonrasi=""):
    if sonrasi and sonrasi in b:
        b = b[b.find(sonrasi):]  # rakamı ilgili kelimeden sonra ara
    m = YUZDE.search(b)
    if not m:
        return None
    deger = sayi(m.group(1))
    if isaretli and any(k in b for k in DUSUS):
        deger = -abs(deger)
    return deger, "%"


def para(b):
    m = PARA.search(b)
    return (sayi(m.group(1)), f"{m.group(2) or ''} TL".strip()) if m else None


def cozumle(b):
    """Başlıktan (gösterge, şirket, (değer, birim)) çıkarır; bulamazsa None."""
    if any(re.search(rf"\b{y}", b) for y in YABANCI):
        return None
    sirket = next((ad for ad, k in SIRKETLER.items() if any(x in b for x in k)), "")
    donem_tipi = "yıllık" if "yıllık" in b or "aylık" not in b else "aylık"
    if sirket:
        if "mağaza" in b and (m := MAGAZA.search(b)):
            return "Mağaza sayısı", sirket, (float(m.group(1)), "adet")
        if any(k in b for k in ["net kâr", "net kar", "kârı", "karı"]):
            return "Şirket net kârı", sirket, para(b)
        if any(k in b for k in ["ciro", "hasılat", "gelir", "satış"]):
            return "Şirket cirosu", sirket, para(b)
        return None
    if "perakende satış" in b and any(k in b for k in DEGISIM):
        return f"Perakende satış ({donem_tipi} %)", "", yuzde(b, isaretli=True, sonrasi="perakende satış")
    if "kartlı harcama" in b or "kartlı ödeme" in b:
        return "Kartlı harcama", "", para(b) or yuzde(b, isaretli=True)
    if "tüketici güven" in b:
        m = PUAN.search(b) or re.search(r"(\d{2,3}[.,]\d)", b)
        return "Tüketici güven endeksi", "", (sayi(m.group(1)), "puan") if m else None
    if ("enflasyon" in b or "tüfe" in b) and not any(k in b for k in ALT_KALEM):
        return f"Enflasyon TÜFE ({donem_tipi} %)", "", yuzde(b, sonrasi=donem_tipi if donem_tipi in b else "")
    if "politika faizi" in b or ("faiz" in b and ("merkez bankası" in b or "tcmb" in b)):
        return "Politika faizi (%)", "", yuzde(b)
    if "beyaz eşya" in b:
        return "Beyaz eşya satışları", "", yuzde(b, isaretli=True)
    if "dolar" in b and ("kur" in b or "tl" in b) and (m := KUR.search(b)):
        return "Dolar/TL", "", (sayi(m.group(1)), "TL")
    if "euro" in b and ("kur" in b or "tl" in b) and (m := KUR.search(b)):
        return "Euro/TL", "", (sayi(m.group(1)), "TL")
    return None


def main():
    haberler = pd.read_csv(HABERLER)
    kayitlar = []
    for _, h in haberler.iterrows():
        b = kucuk(h["baslik"])
        sonuc = cozumle(b)
        if not sonuc or not sonuc[2]:
            continue
        gosterge, sirket, (deger, birim) = sonuc
        kayitlar.append({
            "haber_tarihi": h["tarih"], "gosterge": gosterge, "sirket": sirket,
            "deger": deger, "birim": birim, "donem": donem_bul(b),
            "aciklama": "kural ile çıkarıldı", "baslik": h["baslik"],
            "kaynak": h["kaynak"], "link": h["link"],
        })
    rakamlar = pd.DataFrame(kayitlar, columns=SUTUNLAR).drop_duplicates(subset=["baslik"])
    rakamlar.sort_values("haber_tarihi", ascending=False).to_csv(RAKAMLAR, index=False)
    print(f"{len(haberler)} başlık tarandı, {len(rakamlar)} rakam bulundu")
    print(rakamlar["gosterge"].value_counts().to_string())


if __name__ == "__main__":
    main()
