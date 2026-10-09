"""
Finansal Veriler sayfası: Takipteki alacaklar (sütun, sol eksen) ve NPL oranı (çizgi, sağ eksen).
NPL oranı = Takipteki / (Canlı kredi + Takipteki). Veri BDDK haftalık bülteninden; 13 ay sonu + son bülten.
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from giris import AY, RENK, VURGU, ay_endeksi, tr, tufe_verisi

KLASOR = Path(__file__).parent / "data"
SERILER = ["İhtiyaç kredileri", "Bireysel kredi kartları", "Tüketici kredileri (toplam)", "Konut kredileri"]


@st.cache_data(ttl=3600)
def npl_verisi():
    takip_dosya, canli_dosya = KLASOR / "bddk_takipteki.csv", KLASOR / "bddk_krediler.csv"
    if not takip_dosya.exists() or not canli_dosya.exists():
        return pd.DataFrame()
    takip = pd.read_csv(takip_dosya).rename(columns={"milyon_tl": "takip"})
    canli = pd.read_csv(canli_dosya).rename(columns={"milyon_tl": "canli"})
    d = takip.merge(canli, on=["seri", "tarih"], how="inner")
    d["tarih"] = pd.to_datetime(d["tarih"])
    d["npl"] = d["takip"] / (d["canli"] + d["takip"]) * 100
    d["milyar"] = d["takip"] / 1000
    return d


def puan(x):
    return f"{'+' if x > 0 else ''}{tr(x, 2)} puan"


def npl_grafigi():
    d = npl_verisi()
    if d.empty:
        return
    st.subheader("Takipteki Alacaklar ve NPL Oranı")
    secenekler = [s for s in SERILER if s in set(d["seri"])]
    seri = st.radio("NPL kredi türü", secenekler, horizontal=True, label_visibility="collapsed", key="npl_seri")
    d = d[d["seri"] == seri].sort_values("tarih")
    son = d.iloc[-1]

    # Tamamlanmış ayların son bülteni (ay sonu) + en son yayınlanan bülten
    ay_sonu = d.groupby(d["tarih"].dt.to_period("M")).tail(1)
    ay_sonu = ay_sonu[ay_sonu["tarih"].dt.to_period("M") < son["tarih"].to_period("M")].tail(13)
    noktalar = pd.concat([ay_sonu, d.tail(1)]).copy()
    noktalar["ay"] = [f"{AY[t.month - 1]} {t:%y}" for t in noktalar["tarih"]]
    noktalar.iloc[-1, noktalar.columns.get_loc("ay")] = f"{son['tarih'].day} {AY[son['tarih'].month - 1]} {son['tarih']:%y}"

    # Enflasyondan arındırma (sadece takipteki tutar için; NPL oranı zaten enflasyondan bağımsız)
    endeks = tufe_verisi()
    taban_endeks = ay_endeksi(endeks, son["tarih"]) if not endeks.empty else None
    arindir = st.toggle("Enflasyondan Arındır", value=False, key="npl_arindir", disabled=taban_endeks is None,
                        help="Takipteki alacak tutarlarını son ayın fiyatlarına çevirir (TÜFE ile). "
                             "NPL oranı bir oran olduğu için değişmez.")

    def duzelt(tutar, tarih):
        if not (arindir and taban_endeks is not None):
            return tutar
        e = ay_endeksi(endeks, tarih)
        return tutar * taban_endeks / e if e else tutar

    noktalar["tutar"] = [duzelt(m, t) for m, t in zip(noktalar["milyar"], noktalar["tarih"])]
    if arindir and taban_endeks is not None:
        baz_ay = endeks[endeks.index <= son["tarih"].to_period("M")].index[-1]
        sol_eksen = f"Takipteki alacak (milyar TL, {AY[baz_ay.month - 1]} {baz_ay.year} fiyatlarıyla)"
    else:
        sol_eksen = "Takipteki alacak (milyar TL)"

    # Özet kutuları
    gecen_yil = d[d["tarih"] <= son["tarih"] - pd.Timedelta(days=364)]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"NPL oranı ({son['tarih']:%d.%m.%Y})", f"%{tr(son['npl'], 2)}")
    if not ay_sonu.empty:
        o = ay_sonu.iloc[-1]
        k2.metric("Önceki ay sonuna göre", puan(son["npl"] - o["npl"]),
                  help=f"{o['tarih']:%d.%m.%Y} NPL oranı: %{tr(o['npl'], 2)}")
    if not gecen_yil.empty:
        gy = gecen_yil.iloc[-1]
        k3.metric("Geçen yılın aynı haftasına göre", puan(son["npl"] - gy["npl"]),
                  help=f"{gy['tarih']:%d.%m.%Y} NPL oranı: %{tr(gy['npl'], 2)}")
        degisim = son["milyar"] / gy["milyar"] - 1
        aciklama = f"{gy['tarih']:%d.%m.%Y} tarihine göre takipteki tutar değişimi."
        e = ay_endeksi(endeks, gy["tarih"]) if arindir and taban_endeks is not None else None
        if e:
            enflasyon = taban_endeks / e - 1
            degisim = (1 + degisim) / (1 + enflasyon) - 1
            aciklama += f" Aynı dönemdeki %{tr(enflasyon * 100, 1)} TÜFE artışı düşülmüştür."
        k4.metric("Takipteki alacak", f"{tr(son['milyar'], 1)} milyar TL",
                  delta=f"{'-' if degisim < 0 else '+'}%{tr(abs(degisim) * 100, 1)} yıllık", delta_color="inverse",
                  help=aciklama)

    # Grafik: sütunlar alt yarıda, çizgi üst bölgede kalacak şekilde iki eksen ölçeklenir
    noktalar["t_et"] = noktalar["tutar"].map(lambda x: tr(x, 1))
    noktalar["n_et"] = noktalar["npl"].map(lambda x: f"%{tr(x, 2)}")
    noktalar["son"] = [False] * (len(noktalar) - 1) + [True]
    noktalar["tarih_metin"] = noktalar["tarih"].dt.strftime("%d.%m.%Y")
    veri = noktalar[["ay", "tutar", "npl", "t_et", "n_et", "son", "tarih_metin"]]
    sira = list(veri["ay"])
    aralik = max(veri["npl"].max() - veri["npl"].min(), 0.5)
    x = alt.X("ay:N", sort=sira, title=None, axis=alt.Axis(labelAngle=0, labelPadding=8))
    y_sutun = alt.Y("tutar:Q", title=sol_eksen, scale=alt.Scale(domain=[0, veri["tutar"].max() * 2.2]),
                    axis=alt.Axis(labelExpr="replace(format(datum.value, ',.0f'), ',', '.')", tickCount=4, grid=False))
    y_cizgi = alt.Y("npl:Q", title="NPL oranı (%)",
                    scale=alt.Scale(domain=[veri["npl"].min() - 1.8 * aralik, veri["npl"].max() + 0.3 * aralik]),
                    axis=alt.Axis(orient="right", labelExpr="replace(format(datum.value, '.1f'), '.', ',')", tickCount=5))
    ipucu = [alt.Tooltip("tarih_metin:N", title="Bülten tarihi"), alt.Tooltip("t_et:N", title="Takipteki (milyar TL)"),
             alt.Tooltip("n_et:N", title="NPL oranı")]
    taban = alt.Chart(veri)
    sutun = taban.mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, size=36).encode(
        x=x, y=y_sutun, color=alt.condition("datum.son", alt.value("#fdba74"), alt.value("#bfdbfe")), tooltip=ipucu)
    sutun_etiket = taban.mark_text(dy=-8, fontSize=11, color="#475569").encode(x=x, y=y_sutun, text="t_et:N")
    cizgi = taban.mark_line(color=RENK, strokeWidth=2.5).encode(x=x, y=y_cizgi)
    nokta = taban.mark_circle(opacity=1).encode(
        x=x, y=y_cizgi, color=alt.condition("datum.son", alt.value(VURGU), alt.value(RENK)),
        size=alt.condition("datum.son", alt.value(150), alt.value(55)), tooltip=ipucu)
    nokta_etiket = taban.mark_text(dy=-14, fontSize=12, fontWeight=600).encode(x=x, y=y_cizgi, text="n_et:N")
    grafik = alt.layer(alt.layer(sutun, sutun_etiket), alt.layer(cizgi, nokta, nokta_etiket)).resolve_scale(y="independent")
    st.altair_chart(grafik.properties(height=400), width="stretch")
    st.caption("Kaynak: BDDK Haftalık Bülten, takipteki alacaklar ve krediler (sektör, TP+YP). "
               "NPL oranı = takipteki alacak / (canlı kredi + takipteki alacak). "
               f"Her ayın son bülteni ve en son yayınlanan bülten ({son['tarih']:%d.%m.%Y}) gösterilmektedir. "
               + ("Takipteki tutarlar TCMB TÜFE verisiyle enflasyondan arındırılmıştır." if arindir
                  else "Tutarlar nominaldir."))
