"""
Haber toplayıcı.
Google Haberler'den konu bazlı arama yapar, yeni haberleri data/haberler.csv dosyasına ekler.
Konuları değiştirmek için sadece ARAMALAR listesini düzenlemen yeterli.
"""
import os
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
import pandas as pd

VERI_DOSYASI = "data/haberler.csv"
SUTUNLAR = ["tarih", "kategori", "baslik", "kaynak", "link", "sorgu", "toplanma_zamani"]

# Kategori -> o kategori için yapılacak aramalar
ARAMALAR = {
    "Bankacılık": ["bankacılık sektörü", "BDDK", "mevduat faizi"],
    "Kredi & Faiz": ["kredi faizi", "TCMB faiz kararı", "tüketici kredisi"],
    "Kartlar & Ödeme": ["kredi kartı", "taksit", "dijital ödeme"],
    "Perakende": ["perakende sektörü", "zincir market", "perakende satışlar"],
    "E-ticaret": ["e-ticaret", "online alışveriş"],
    "Rakipler": ["Vatan Bilgisayar", "Teknosa", "MediaMarkt Türkiye", "elektronik perakende"],
    "Piyasa Göstergeleri": [
        "perakende satışlar TÜİK", "kartlı harcamalar", "tüketici güven endeksi",
        "enflasyon TÜFE", "dolar kuru", "beyaz eşya satışları",
    ],
}


def arama_adresi(sorgu: str) -> str:
    return f"https://news.google.com/rss/search?q={quote(sorgu)}&hl=tr&gl=TR&ceid=TR:tr"


def haberleri_topla() -> pd.DataFrame:
    simdi = datetime.now(timezone.utc)
    satirlar = []
    for kategori, sorgular in ARAMALAR.items():
        for sorgu in sorgular:
            akis = feedparser.parse(arama_adresi(sorgu))
            for h in akis.entries:
                baslik = h.get("title", "").strip()
                kaynak = h.get("source", {}).get("title", "").strip()
                # Google başlığın sonuna " - Kaynak" ekliyor, onu temizle
                if kaynak and baslik.endswith(" - " + kaynak):
                    baslik = baslik[: -len(" - " + kaynak)]
                if h.get("published_parsed"):
                    tarih = datetime(*h.published_parsed[:6], tzinfo=timezone.utc)
                else:
                    tarih = simdi
                satirlar.append({
                    "tarih": tarih.isoformat(),
                    "kategori": kategori,
                    "baslik": baslik,
                    "kaynak": kaynak,
                    "link": h.get("link", ""),
                    "sorgu": sorgu,
                    "toplanma_zamani": simdi.isoformat(),
                })
            print(f"{kategori} / {sorgu}: {len(akis.entries)} haber")
    return pd.DataFrame(satirlar, columns=SUTUNLAR)


def main():
    os.makedirs("data", exist_ok=True)
    yeni = haberleri_topla()

    if os.path.exists(VERI_DOSYASI):
        eski = pd.read_csv(VERI_DOSYASI)
    else:
        eski = pd.DataFrame(columns=SUTUNLAR)

    # Eski kayıtlar önce gelsin ki bir haberin ilk görüldüğü hali korunsun
    tumu = pd.concat([eski, yeni], ignore_index=True)
    tumu = tumu.drop_duplicates(subset="link", keep="first")
    tumu = tumu.drop_duplicates(subset=["baslik", "kaynak"], keep="first")
    tumu = tumu.sort_values("tarih", ascending=False)
    tumu.to_csv(VERI_DOSYASI, index=False)

    print(f"Yeni eklenen: {len(tumu) - len(eski)} | Toplam: {len(tumu)}")


if __name__ == "__main__":
    main()
