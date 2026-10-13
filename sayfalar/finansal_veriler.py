"""
Finansal Veriler sayfası: Kredi hacimleri, takipteki alacaklar, kredi faiz oranları ve tüketici güveni.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from faiz_grafik import faiz_grafigi
from giris import kredi_grafigi
from guven_grafik import guven_grafigi
from npl_grafik import npl_grafigi

AY = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
DURUM = {"guncel": "🟢", "gecikmeli": "🟠", "hata": "🔴"}


def veri_durumu():
    """Her kaynağın son verisini ve son kontrol zamanını gösteren küçük durum satırı."""
    dosya = Path(__file__).parent.parent / "data" / "kontrol.json"
    if not dosya.exists():
        return
    k = json.loads(dosya.read_text(encoding="utf-8"))
    parcalar = []
    for v in k["kaynaklar"].values():
        if not v["son_veri"]:
            continue
        t = datetime.strptime(v["son_veri"], "%Y-%m-%d")
        tarih = f"{AY[t.month - 1]} {t.year}" if v["siklik"] == "aylık" else f"{t:%d.%m.%Y}"
        parcalar.append(f"{DURUM.get(v['durum'], '⚪')} {v['ad']}: {tarih}")
    kontrol = datetime.fromisoformat(k["son_kontrol"]) + timedelta(hours=3)  # Türkiye saati
    st.caption("**Veri durumu** (kaynakların yayınladığı en güncel veri)  \n" + " · ".join(parcalar)
               + f"  \nSon kontrol: {kontrol:%d.%m.%Y %H:%M}. Kaynaklar her gün 09:30, 13:30, 18:30 ve 22:30'da "
               "kontrol edilir; 🟠 yayın takviminin gerisinde kalan, 🔴 alınamayan veriyi gösterir.")


veri_durumu()
kredi_grafigi()
st.divider()
npl_grafigi()
st.divider()
faiz_grafigi()
st.divider()
guven_grafigi()
