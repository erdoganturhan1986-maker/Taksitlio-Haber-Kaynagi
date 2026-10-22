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
RENK = {"guncel": "#22c55e", "gecikmeli": "#f59e0b", "hata": "#ef4444"}


def veri_durumu():
    """Kaynakların son verisini ve son kontrol zamanını gösteren, dipnot görünümünde kayan şerit."""
    dosya = Path(__file__).parent.parent / "data" / "kontrol.json"
    if not dosya.exists():
        return
    k = json.loads(dosya.read_text(encoding="utf-8"))

    def nokta(renk):
        return f'<span class="vd-n" style="background:{renk}"></span>'

    parcalar = []
    for v in k["kaynaklar"].values():
        if not v["son_veri"]:
            continue
        t = datetime.strptime(v["son_veri"], "%Y-%m-%d")
        tarih = f"{AY[t.month - 1]} {t.year}" if v["siklik"] == "aylık" else f"{t:%d.%m.%Y}"
        parcalar.append(f"{nokta(RENK.get(v['durum'], '#94a3b8'))}{v['ad']}: {tarih}")
    kontrol = datetime.fromisoformat(k["son_kontrol"]) + timedelta(hours=3)  # Türkiye saati
    metin = ("<b>Veri durumu</b> (kaynakların yayınladığı en güncel veri): " + " · ".join(parcalar)
             + f" · Son kontrol {kontrol:%d.%m.%Y %H:%M}; kaynaklar her gün 09:30, 13:30, 18:30 ve 22:30'da kontrol edilir"
             + f" · {nokta(RENK['guncel'])}güncel {nokta(RENK['gecikmeli'])}yayın takviminin gerisinde "
             + f"{nokta(RENK['hata'])}alınamadı")
    kopya = f'<span class="vd-k">{metin}</span>'
    st.markdown(f"""
<style>
.vd {{overflow:hidden; white-space:nowrap; font-size:12px; font-style:italic; color:#7b8794; padding:3px 0;
      margin:-8px 0 4px; border-top:1px solid rgba(100,116,139,.15); border-bottom:1px solid rgba(100,116,139,.15);
      -webkit-mask-image:linear-gradient(90deg,transparent,#000 3%,#000 97%,transparent);
      mask-image:linear-gradient(90deg,transparent,#000 3%,#000 97%,transparent);}}
.vd-s {{display:inline-flex; animation:vd-kay 90s linear infinite;}}
.vd:hover .vd-s {{animation-play-state:paused;}}
.vd-k {{display:inline-block; min-width:150vw; padding-right:6rem;}}
.vd-k b {{font-weight:600; color:#64748b;}}
.vd-n {{display:inline-block; width:7px; height:7px; border-radius:50%; margin:0 5px 1px 2px; vertical-align:middle;}}
@keyframes vd-kay {{from {{transform:translateX(0)}} to {{transform:translateX(-50%)}}}}
@media (prefers-reduced-motion: reduce) {{.vd-s {{animation:none}} .vd {{overflow-x:auto}}}}
</style>
<div class="vd" aria-label="Veri durumu"><div class="vd-s">{kopya}{kopya}</div></div>
""", unsafe_allow_html=True)


veri_durumu()
kredi_grafigi()
st.divider()
npl_grafigi()
st.divider()
faiz_grafigi()
st.divider()
guven_grafigi()
