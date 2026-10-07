"""
Dashboard giriş bölümü: BDDK verisinden Aylık Tüketici Kredileri Gelişimi grafiği.
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DOSYA = Path(__file__).parent / "data" / "bddk_krediler.csv"
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
    noktalar["etiket"] = noktalar["trilyon"].map(tr)
    noktalar["tarih_metin"] = noktalar["tarih"].dt.strftime("%d.%m.%Y")
    noktalar["tur"] = ["Ay sonu"] * (len(noktalar) - 1) + ["Son bülten"]

    # Özet rakamlar
    onceki_ay = ay_sonu.iloc[-1] if not ay_sonu.empty else None
    gecen_yil = d[d["tarih"] <= son["tarih"] - pd.Timedelta(days=364)]
    k1, k2, k3 = st.columns(3)
    k1.metric(f"Son bülten ({son['tarih']:%d.%m.%Y})", f"{tr(son['trilyon'])} trilyon TL")
    if onceki_ay is not None:
        k2.metric("Önceki ay sonuna göre", f"%{tr((son['trilyon'] / onceki_ay['trilyon'] - 1) * 100, 1)}",
                  help=f"{onceki_ay['tarih']:%d.%m.%Y} tarihli bültenle karşılaştırma")
    if not gecen_yil.empty:
        gy = gecen_yil.iloc[-1]
        k3.metric("Geçen yılın aynı haftasına göre", f"%{tr((son['trilyon'] / gy['trilyon'] - 1) * 100, 1)}",
                  help=f"{gy['tarih']:%d.%m.%Y} tarihli bültenle karşılaştırma")

    # Grafik
    sira = list(noktalar["ay"])
    taban = alt.Chart(noktalar).encode(
        x=alt.X("ay:N", sort=sira, title=None, axis=alt.Axis(labelAngle=0, labelPadding=8)),
        y=alt.Y("trilyon:Q", title="Trilyon TL", scale=alt.Scale(zero=False, padding=28),
                axis=alt.Axis(labelExpr="replace(format(datum.value, '.1f'), '.', ',')", tickCount=5)),
    )
    ipucu = [alt.Tooltip("tarih_metin:N", title="Bülten tarihi"),
             alt.Tooltip("etiket:N", title="Trilyon TL"), alt.Tooltip("tur:N", title="Nokta")]
    cizgi = taban.mark_line(color=RENK, strokeWidth=2.5)
    nokta = taban.mark_circle(size=55, color=RENK, opacity=1).encode(tooltip=ipucu)
    etiket = taban.mark_text(dy=-14, fontSize=12, fontWeight=600).encode(text="etiket:N")
    son_nokta = alt.Chart(noktalar.tail(1)).mark_circle(size=150, color=VURGU, opacity=1).encode(
        x=alt.X("ay:N", sort=sira), y="trilyon:Q", tooltip=ipucu)
    st.altair_chart((cizgi + nokta + etiket + son_nokta).properties(height=380), width="stretch")
    st.caption(f"Kaynak: BDDK Haftalık Bülten, sektör toplamı (TP+YP), milyon TL'den trilyon TL'ye çevrilmiştir. "
               f"Mavi noktalar her ayın son bülteni, turuncu nokta son yayınlanan bülten ({son['tarih']:%d.%m.%Y}). "
               f"Tutarlar nominaldir, enflasyon etkisini içerir.")
