"""
Finansal Veriler sayfası: Tüketici güven endeksi ve seçili alt endeksler (TÜİK-TCMB, aylık).
100 nötr seviyedir: üstü iyimserlik, altı kötümserlik.
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from giris import AY, RENK, VURGU, tr

DOSYA = Path(__file__).parent / "data" / "tuketici_guven.csv"
SERILER = ["Tüketici güven endeksi", "Dayanıklı mal almaya uygunluk", "Dayanıklı mal harcama beklentisi",
           "Borçla tüketim ihtimali"]
ACIKLAMA = {
    "Tüketici güven endeksi": "Hanelerin maddi durumları ve genel ekonomiye dair değerlendirme ve beklentilerinin özeti.",
    "Dayanıklı mal almaya uygunluk": "Hanelerin, şu anın beyaz eşya, elektronik, mobilya gibi ürünleri almak için uygun bir "
                                     "zaman olup olmadığına dair değerlendirmesi.",
    "Dayanıklı mal harcama beklentisi": "Hanelerin, gelecek 12 ayda dayanıklı tüketim mallarına geçen yıla göre daha çok mu "
                                        "daha az mı harcama yapmayı planladığı.",
    "Borçla tüketim ihtimali": "Hanelerin, gelecek 3 ayda tüketimlerini finanse etmek için kredi, kart ya da taksitle borç "
                               "kullanma ihtimali. Yüksek değer, borçla alışveriş niyetinin arttığını gösterir.",
    "Fiyat artış beklentisi": "Hanelerin gelecek 12 aydaki fiyat değişimine dair beklentisi. Yüksek değer, daha fazla fiyat "
                              "artışı beklendiğini gösterir.",
}


@st.cache_data(ttl=3600)
def guven_verisi():
    if not DOSYA.exists():
        return pd.DataFrame()
    d = pd.read_csv(DOSYA)
    d["ay"] = pd.to_datetime(d["ay"]).dt.to_period("M")
    return d


def puan(x):
    return f"{'+' if x > 0 else ''}{tr(x, 1)} puan"


def guven_grafigi():
    d = guven_verisi()
    if d.empty:
        return
    st.subheader("Tüketici Güven Endeksi")
    secenekler = [s for s in SERILER if s in set(d["seri"])]
    seri = st.radio("Endeks", secenekler, horizontal=True, label_visibility="collapsed", key="guven_seri")
    d = d[d["seri"] == seri].sort_values("ay").tail(14)
    st.caption(ACIKLAMA.get(seri, ""))
    son = d.iloc[-1]

    k1, k2, k3 = st.columns(3)
    k1.metric(f"{AY[son['ay'].month - 1]} {son['ay'].year}", tr(son["deger"], 1),
              help="100'ün üzeri iyimserlik, altı kötümserlik anlamına gelir.")
    if len(d) >= 2:
        onceki = d.iloc[-2]
        k2.metric("Önceki aya göre", puan(son["deger"] - onceki["deger"]),
                  help=f"{AY[onceki['ay'].month - 1]} {onceki['ay'].year}: {tr(onceki['deger'], 1)}")
    gecen = d[d["ay"] == son["ay"] - 12]
    if not gecen.empty:
        k3.metric("Geçen yılın aynı ayına göre", puan(son["deger"] - gecen.iloc[0]["deger"]),
                  help=f"{AY[(son['ay'] - 12).month - 1]} {(son['ay'] - 12).year}: {tr(gecen.iloc[0]['deger'], 1)}")

    noktalar = pd.DataFrame({
        "ay": [f"{AY[p.month - 1]} {p.year % 100:02d}" for p in d["ay"]],
        "deger": d["deger"].values,
        "donem": [f"{AY[p.month - 1]} {p.year}" for p in d["ay"]],
    })
    noktalar["etiket"] = noktalar["deger"].map(lambda x: tr(x, 1))
    sira = list(noktalar["ay"])
    taban = alt.Chart(noktalar).encode(
        x=alt.X("ay:N", sort=sira, title=None, axis=alt.Axis(labelAngle=0, labelPadding=8)),
        y=alt.Y("deger:Q", title="Endeks", scale=alt.Scale(zero=False, padding=28),
                axis=alt.Axis(labelExpr="replace(format(datum.value, '.0f'), '.', ',')", tickCount=5)),
    )
    ipucu = [alt.Tooltip("donem:N", title="Ay"), alt.Tooltip("etiket:N", title="Endeks")]
    notr = alt.Chart(pd.DataFrame({"y": [100]})).mark_rule(strokeDash=[5, 4], color="#94a3b8").encode(y="y:Q")
    notr_yazi = alt.Chart(pd.DataFrame({"y": [100], "t": ["100 = nötr"]})).mark_text(
        align="left", dx=4, dy=-7, fontSize=11, color="#64748b").encode(y="y:Q", x=alt.value(0), text="t:N")
    cizgi = taban.mark_line(color=RENK, strokeWidth=2.5)
    nokta = taban.mark_circle(size=55, color=RENK, opacity=1).encode(tooltip=ipucu)
    etiket = taban.mark_text(dy=-14, fontSize=12, fontWeight=600).encode(text="etiket:N")
    son_nokta = alt.Chart(noktalar.tail(1)).mark_circle(size=150, color=VURGU, opacity=1).encode(
        x=alt.X("ay:N", sort=sira), y="deger:Q", tooltip=ipucu)
    st.altair_chart((notr + notr_yazi + cizgi + nokta + etiket + son_nokta).properties(height=380), width="stretch")
    st.caption("Kaynak: TÜİK-TCMB Tüketici Eğilim Anketi (TCMB EVDS), aylık. Kesikli çizgi 100 nötr seviyesidir: "
               "üstü iyimserlik, altı kötümserlik. Turuncu nokta son açıklanan ay.")
