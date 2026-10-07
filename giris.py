"""
Dashboard giriş bölümü: BDDK verisinden Aylık Tüketici Kredileri Gelişimi grafiği.
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DOSYA = Path(__file__).parent / "data" / "bddk_krediler.csv"
TUFE = Path(__file__).parent / "data" / "tufe.csv"
SERILER = ["Tüketici kredileri (toplam)", "İhtiyaç kredileri", "Konut kredileri", "Bireysel kredi kartları"]
AY = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
RENK, VURGU = "#1d4ed8", "#ea580c"


def tr(x, basamak=2):
    metin = f"{x:,.{basamak}f}"
    return metin.replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data(ttl=3600)
def veri():
    if not DOSYA.exists():
        return pd.DataFrame()
    d = pd.read_csv(DOSYA)
    d["tarih"] = pd.to_datetime(d["tarih"])
    d["trilyon"] = d["milyon_tl"] / 1_000_000
    return d


@st.cache_data(ttl=3600)
def tufe_verisi():
    """Ay -> fiyat endeksi eşlemesi. Veri yoksa boş döner."""
    if not TUFE.exists():
        return pd.Series(dtype=float)
    t = pd.read_csv(TUFE)
    return pd.Series(t["endeks"].values, index=pd.PeriodIndex(t["donem"], freq="M")).sort_index()


def ay_endeksi(endeks, tarih):
    """O ayın endeksi; o ay henüz açıklanmadıysa son açıklanan ay."""
    onceki = endeks[endeks.index <= tarih.to_period("M")]
    return onceki.iloc[-1] if not onceki.empty else None


def kredi_grafigi():
    d = veri()
    if d.empty:
        return
    st.subheader("Aylık Tüketici Kredileri Gelişimi")
    seri = st.radio("Kredi türü", SERILER, horizontal=True, label_visibility="collapsed")
    d = d[d["seri"] == seri].sort_values("tarih")
    son = d.iloc[-1]

    # Tamamlanmış ayların son bülteni (ay sonu) + en son yayınlanan bülten
    ay_sonu = d.groupby(d["tarih"].dt.to_period("M")).tail(1)
    ay_sonu = ay_sonu[ay_sonu["tarih"].dt.to_period("M") < son["tarih"].to_period("M")].tail(13)
    noktalar = pd.concat([ay_sonu, d.tail(1)]).copy()
    noktalar["ay"] = [f"{AY[t.month - 1]} {t:%y}" for t in noktalar["tarih"]]
    noktalar.iloc[-1, noktalar.columns.get_loc("ay")] = f"{son['tarih'].day} {AY[son['tarih'].month - 1]} {son['tarih']:%y}"
    # Enflasyondan arındırma: her tutarı son ayın fiyatlarına çevir
    endeks = tufe_verisi()
    taban_endeks = ay_endeksi(endeks, son["tarih"]) if not endeks.empty else None
    arindir = st.toggle("Enflasyondan Arındır", disabled=taban_endeks is None,
                        help="Her ayın tutarını son ayın fiyatlarına çevirir (TÜFE ile).")
    if arindir and taban_endeks is not None:
        oran = [taban_endeks / (ay_endeksi(endeks, t) or taban_endeks) for t in noktalar["tarih"]]
        noktalar["deger"] = noktalar["trilyon"] * oran
        baz_ay = endeks[endeks.index <= son["tarih"].to_period("M")].index[-1]
        eksen = f"Trilyon TL ({AY[baz_ay.month - 1]} {baz_ay.year} fiyatlarıyla)"
    else:
        noktalar["deger"] = noktalar["trilyon"]
        eksen = "Trilyon TL"
    noktalar["etiket"] = noktalar["deger"].map(tr)
    noktalar["tarih_metin"] = noktalar["tarih"].dt.strftime("%d.%m.%Y")
    noktalar["tur"] = ["Ay sonu"] * (len(noktalar) - 1) + ["Son bülten"]

    # Özet rakamlar: anahtar açıksa değişimler enflasyondan arındırılmış hesaplanır
    def yuzde(x):
        return f"{'-' if x < 0 else ''}%{tr(abs(x) * 100, 1)}"

    def degisim_kutusu(kolon, baslik, onceki):
        degisim = son["trilyon"] / onceki["trilyon"] - 1
        aciklama = f"{onceki['tarih']:%d.%m.%Y} tarihli bültenle karşılaştırma."
        onceki_endeks = ay_endeksi(endeks, onceki["tarih"]) if arindir and taban_endeks is not None else None
        if onceki_endeks:
            enflasyon = taban_endeks / onceki_endeks - 1
            degisim = (1 + degisim) / (1 + enflasyon) - 1
            aciklama += f" Aynı dönemdeki
