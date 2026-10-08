"""
Sayfanın en üstündeki kayan piyasa bandı (gram altın, gram gümüş, dolar, euro, Brent, BIST 100).
Veri data/piyasa.csv dosyasından okunur; dosya yoksa bant gösterilmez.
"""
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

DOSYA = Path(__file__).parent / "data" / "piyasa.csv"
ONDALIK = {"Dolar": 4, "Euro": 4}


def tr(x, basamak=2):
    metin = f"{x:,.{basamak}f}"
    return metin.replace(",", "X").replace(".", ",").replace("X", ".")


def bant_html(df, saat):
    ogeler = []
    for _, r in df.iterrows():
        yukari = r["degisim"] >= 0
        rozet = f'{"▲" if yukari else "▼"} %{tr(abs(r["degisim"]), 2)}'
        birim = "" if r["birim"] == "puan" else f' <span class="tb-birim">{escape(r["birim"])}</span>'
        ogeler.append(
            f'<span class="tb-oge"><span class="tb-ad">{escape(r["ad"])}</span>'
            f'<span class="tb-deger">{tr(r["deger"], ONDALIK.get(r["ad"], 2))}{birim}</span>'
            f'<span class="tb-rozet {"tb-artis" if yukari else "tb-dusus"}">{rozet}</span></span>')
    dizi = '<span class="tb-ayrac">•</span>'.join(ogeler)
    sure = max(25, 6 * len(ogeler))
    return f"""
<style>
.tb-kap {{display:flex; align-items:stretch; background:#0b1b3a; border-radius:8px; overflow:hidden;
  font-size:13px; line-height:1; color:#e2e8f0; font-variant-numeric:tabular-nums; margin:-0.5rem 0 1rem 0;
  box-shadow:0 1px 2px rgba(0,0,0,.15);}}
.tb-etiket {{display:flex; align-items:center; gap:8px; padding:10px 14px; background:#1d4ed8; color:#fff;
  font-weight:700; letter-spacing:.08em; font-size:11px; white-space:nowrap; z-index:2;}}
.tb-nokta {{width:7px; height:7px; border-radius:50%; background:#4ade80; animation:tb-nabiz 1.6s infinite;}}
@keyframes tb-nabiz {{0%{{box-shadow:0 0 0 0 rgba(74,222,128,.7)}} 70%{{box-shadow:0 0 0 7px rgba(74,222,128,0)}}
  100%{{box-shadow:0 0 0 0 rgba(74,222,128,0)}}}}
.tb-pencere {{position:relative; flex:1; overflow:hidden; display:flex; align-items:center;
  -webkit-mask-image:linear-gradient(90deg,transparent,#000 4%,#000 96%,transparent);
  mask-image:linear-gradient(90deg,transparent,#000 4%,#000 96%,transparent);}}
.tb-serit {{display:inline-flex; white-space:nowrap; animation:tb-kay {sure}s linear infinite; padding-left:16px;}}
.tb-pencere:hover .tb-serit {{animation-play-state:paused;}}
@keyframes tb-kay {{from{{transform:translateX(0)}} to{{transform:translateX(-50%)}}}}
.tb-oge {{display:inline-flex; align-items:center; gap:7px; padding:0 4px;}}
.tb-ad {{color:#94a3b8; font-size:12px;}}
.tb-deger {{color:#fff; font-weight:600;}}
.tb-birim {{color:#94a3b8; font-weight:400; font-size:11px;}}
.tb-rozet {{font-size:11px; font-weight:600; padding:3px 6px; border-radius:4px;}}
.tb-artis {{color:#4ade80; background:rgba(74,222,128,.12);}}
.tb-dusus {{color:#f87171; background:rgba(248,113,113,.12);}}
.tb-ayrac {{color:#334155; padding:0 14px;}}
.tb-saat {{display:flex; align-items:center; padding:0 14px; color:#94a3b8; font-size:11px; white-space:nowrap;
  border-left:1px solid #1e3a6e; z-index:2; background:#0b1b3a;}}
@media (max-width:640px) {{ .tb-saat {{display:none;}} }}
</style>
<div class="tb-kap">
  <div class="tb-etiket"><span class="tb-nokta"></span>PİYASALAR</div>
  <div class="tb-pencere"><div class="tb-serit">{dizi}<span class="tb-ayrac">•</span>{dizi}<span class="tb-ayrac">•</span></div></div>
  <div class="tb-saat">Son güncelleme {escape(saat)}</div>
</div>"""


@st.cache_data(ttl=600)
def piyasa_verisi():
    if not DOSYA.exists():
        return pd.DataFrame()
    return pd.read_csv(DOSYA)


def kayan_yazi():
    df = piyasa_verisi()
    if df.empty:
        return
    zaman = pd.to_datetime(df["guncelleme"].iloc[0], utc=True).tz_convert("Europe/Istanbul")
    st.markdown(bant_html(df, f"{zaman:%d.%m %H:%M}"), unsafe_allow_html=True)
