"""
Türkiye Perakende Piyasası Dashboard'u - Streamlit
"""
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Perakende Piyasası Takibi", page_icon="📊", layout="wide")

KLASOR = Path(__file__).parent / "data"
SAAT_DILIMI = "Europe/Istanbul"
RAKIPLER = ["Vatan", "Teknosa", "MediaMarkt"]


def tarihe_cevir(seri):
    return pd.to_datetime(seri, utc=True, format="ISO8601").dt.tz_convert(SAAT_DILIMI)


@st.cache_data(ttl=600)
def yukle(dosya, tarih_sutunu):
    yol = KLASOR / dosya
    if not yol.exists():
        return pd.DataFrame()
    df = pd.read_csv(yol)
    if df.empty:
        return df
    metin = [c for c in df.columns if c not in (tarih_sutunu, "deger")]
    df[metin] = df[metin].fillna("").astype(str)
    df[tarih_sutunu] = tarihe_cevir(df[tarih_sutunu])
    return df


haberler = yukle("haberler.csv", "tarih")
rakamlar = yukle("rakamlar.csv", "haber_tarihi")
simdi = pd.Timestamp.now(tz=SAAT_DILIMI)

st.title("📊 Türkiye Perakende Piyasası Takibi")
if haberler.empty:
    st.info("Henüz veri yok. GitHub'da Actions sekmesinden 'Haberleri topla' işini bir kez çalıştır.")
    st.stop()
st.caption(f"Son güncelleme: {haberler['tarih'].max():%d.%m.%Y %H:%M}  |  "
           f"{len(haberler)} haber, {len(rakamlar)} rakam")

sekme_piyasa, sekme_rakip, sekme_haber = st.tabs(["Piyasa rakamları", "Rakipler", "Haberler"])

link_ayari = {"link": st.column_config.LinkColumn("Kaynak", display_text="Habere git")}

# ---------- Piyasa rakamları ----------
with sekme_piyasa:
    if rakamlar.empty:
        st.info("AI agent henüz rakam çıkarmadı. API anahtarı eklendikten sonraki ilk çalışmada burası dolacak.")
    else:
        piyasa = rakamlar[(rakamlar["sirket"] == "") & (rakamlar["gosterge"] != "Diğer")]
        gostergeler = piyasa["gosterge"].value_counts().index.tolist()

        st.subheader("Son değerler")
        kolonlar = st.columns(4)
        for i, g in enumerate(gostergeler):
            v = piyasa[piyasa["gosterge"] == g].sort_values("haber_tarihi", ascending=False)
            son = v.iloc[0]
            onceki = v[v["deger"] != son["deger"]]
            fark = round(son["deger"] - onceki.iloc[0]["deger"], 2) if not onceki.empty else None
            kolonlar[i % 4].metric(
                g, f"{son['deger']:g} {son['birim']}", fark,
                help=f"{son['donem'] or 'Dönem belirtilmemiş'} | {son['kaynak']}",
            )

        st.subheader("Gösterge geçmişi")
        secilen = st.selectbox("Gösterge seç", gostergeler)
        v = piyasa[piyasa["gosterge"] == secilen].sort_values("haber_tarihi")
        st.line_chart(v.set_index("haber_tarihi")["deger"])
        st.dataframe(
            v.sort_values("haber_tarihi", ascending=False)[
                ["haber_tarihi", "deger", "birim", "donem", "aciklama", "kaynak", "link"]],
            column_config=link_ayari, hide_index=True, width="stretch",
        )
        st.caption("Rakamlar AI tarafından haber başlıklarından çıkarılır. Şüpheli bir değeri kaynağından kontrol et.")

# ---------- Rakipler ----------
with sekme_rakip:
    son30 = haberler[haberler["tarih"] >= simdi - pd.Timedelta(days=30)]
    sayilar = {r: int(son30["baslik"].str.contains(r, case=False, regex=False).sum()) for r in RAKIPLER}
    st.subheader("Son 30 günde haber sayısı")
    st.bar_chart(pd.Series(sayilar))

    rakip = st.radio("Perakendeci", RAKIPLER, horizontal=True)
    if not rakamlar.empty:
        r = rakamlar[rakamlar["sirket"].str.contains(rakip, case=False, regex=False)]
        if not r.empty:
            st.markdown(f"**{rakip} ile ilgili rakamlar**")
            st.dataframe(r[["haber_tarihi", "gosterge", "deger", "birim", "donem", "aciklama", "link"]],
                         column_config=link_ayari, hide_index=True, width="stretch")
    st.markdown(f"**{rakip} son haberler**")
    rh = haberler[haberler["baslik"].str.contains(rakip, case=False, regex=False)].head(20)
    if rh.empty:
        st.write("Bu perakendeci için henüz haber yok.")
    for _, h in rh.iterrows():
        st.markdown(f"[{h['baslik']}]({h['link']})  \n{h['kaynak']} | {h['tarih']:%d.%m.%Y %H:%M}")

# ---------- Haberler ----------
with sekme_haber:
    sol, sag, ara = st.columns([2, 1, 2])
    tum = sorted(haberler["kategori"].unique())
    kategoriler = sol.multiselect("Kategori", tum, default=tum)
    gun = sag.selectbox("Zaman", [1, 7, 30, 90], index=1,
                        format_func=lambda g: "Son 24 saat" if g == 1 else f"Son {g} gün")
    arama = ara.text_input("Başlıkta ara")
    f = haberler[haberler["kategori"].isin(kategoriler) & (haberler["tarih"] >= simdi - pd.Timedelta(days=gun))]
    if arama:
        f = f[f["baslik"].str.contains(arama, case=False, regex=False)]
    st.caption(f"{len(f)} haber")
    for _, h in f.head(100).iterrows():
        st.markdown(f"[{h['baslik']}]({h['link']})  \n{h['kaynak']} | {h['kategori']} | {h['tarih']:%d.%m.%Y %H:%M}")
