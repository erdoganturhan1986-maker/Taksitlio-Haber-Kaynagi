"""
Finansal Veriler sayfası: Ağırlıklı ortalama tüketici kredisi faiz oranları (TCMB, akım).
Aylık değer, o ayın haftalık faizlerinin ortalamasıdır; son nokta en son açıklanan haftadır.
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from giris import AY, RENK, VURGU, tr

DOSYA = Path(__file__).parent / "data" / "faiz_oranlari.csv"
SERILER = ["Tüketici kredisi (toplam)", "İhtiyaç kredisi", "Taşıt kredisi", "Konut kredisi"]


@st.cache_data(ttl=3600)
def faiz_verisi():
    if not DOSYA.exists():
        return pd.DataFrame()
    d = pd.read_csv(DOSYA)
    d["tarih"] = pd.to_datetime(d["tarih"])
    return d


def puan(x, basamak=1):
    return f"{'+' if x > 0 else ''}{tr(x, basamak)} puan"


def faiz_grafigi():
    d = faiz_verisi()
    if d.empty:
        return
    st.subheader("Ağırlıklı Ortalama Tüketici Kredisi Faiz Oranları")
    seri = st.radio("Faiz türü", SERILER, horizontal=True, label_visibility="collapsed", key="faiz_seri")
    d = d[d["seri"] == seri].sort_values("tarih")
    if d.empty:
        st.info("Bu seri için veri yok.")
        return
    aylik_goster = st.toggle("Aylık Faiz", value=True, key="faiz_aylik",
                             help="TCMB'nin yıllık bileşik faiz oranını aylık orana çevirir: (1 + yıllık)^(1/12) - 1.")
    if aylik_goster:
        d = d.assign(faiz=((1 + d["faiz"] / 100) ** (1 / 12) - 1) * 100)
    birim = "Aylık faiz (%)" if aylik_goster else "Yıllık faiz (%)"
    son = d.iloc[-1]
    son_ay = son["tarih"].to_period("M")

    # Tamamlanmış ayların haftalık ortalaması + son açıklanan hafta
    aylik = d.groupby(d["tarih"].dt.to_period("M"))["faiz"].mean()
    tamam = aylik[aylik.index < son_ay].tail(13)
    noktalar = pd.DataFrame({
        "ay": [f"{AY[p.month - 1]} {p.year % 100:02d}" for p in tamam.index]
              + [f"{son['tarih'].day} {AY[son['tarih'].month - 1]} {son['tarih']:%y}"],
        "faiz": list(tamam.values) + [son["faiz"]],
        "aciklama": [f"{AY[p.month - 1]} {p.year} haftalık ortalaması" for p in tamam.index]
                    + [f"{son['tarih']:%d.%m.%Y} haftası"],
    })
    noktalar["etiket"] = noktalar["faiz"].map(lambda x: tr(x, 2))

    # Özet rakamlar
    k1, k2, k3 = st.columns(3)
    k1.metric(f"Son hafta ({son['tarih']:%d.%m.%Y})", f"%{tr(son['faiz'], 2)}")
    if not tamam.empty:
        onceki = tamam.iloc[-1]
        k2.metric("Önceki ay ortalamasına göre", puan(son["faiz"] - onceki, 2 if aylik_goster else 1),
                  help=f"{AY[tamam.index[-1].month - 1]} {tamam.index[-1].year} ortalaması: %{tr(onceki, 2)}")
    gecen_yil = d[d["tarih"] <= son["tarih"] - pd.Timedelta(days=364)]
    if not gecen_yil.empty:
        gy = gecen_yil.iloc[-1]
        k3.metric("Geçen yılın aynı haftasına göre", puan(son["faiz"] - gy["faiz"], 2 if aylik_goster else 1),
                  help=f"{gy['tarih']:%d.%m.%Y} haftası: %{tr(gy['faiz'], 2)}")

    # Grafik
    sira = list(noktalar["ay"])
    taban = alt.Chart(noktalar).encode(
        x=alt.X("ay:N", sort=sira, title=None, axis=alt.Axis(labelAngle=0, labelPadding=8)),
        y=alt.Y("faiz:Q", title=birim, scale=alt.Scale(zero=False, padding=28),
                axis=alt.Axis(labelExpr=f"replace(format(datum.value, '{'.2f' if aylik_goster else '.1f'}'), '.', ',')",
                              tickCount=5)),
    )
    ipucu = [alt.Tooltip("aciklama:N", title="Dönem"), alt.Tooltip("etiket:N", title=birim)]
    cizgi = taban.mark_line(color=RENK, strokeWidth=2.5)
    nokta = taban.mark_circle(size=55, color=RENK, opacity=1).encode(tooltip=ipucu)
    etiket = taban.mark_text(dy=-14, fontSize=12, fontWeight=600).encode(text="etiket:N")
    son_nokta = alt.Chart(noktalar.tail(1)).mark_circle(size=150, color=VURGU, opacity=1).encode(
        x=alt.X("ay:N", sort=sira), y="faiz:Q", tooltip=ipucu)
    st.altair_chart((cizgi + nokta + etiket + son_nokta).properties(height=380), width="stretch")
    st.caption("Kaynak: TCMB EVDS, bankalarca yeni açılan TL kredilere uygulanan ağırlıklı ortalama faiz "
               "oranları (akım). " + ("Aylık oran, yıllık bileşik orandan (1 + yıllık)^(1/12) - 1 formülüyle hesaplanmıştır. " if aylik_goster else "")
               + "Mavi noktalar her ayın haftalık değerlerinin ortalaması, "
               f"turuncu nokta son açıklanan hafta ({son['tarih']:%d.%m.%Y}).")
