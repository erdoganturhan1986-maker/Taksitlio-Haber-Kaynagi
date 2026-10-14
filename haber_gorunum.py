"""
Haberler sayfasının görünümü: data/haberler.json'u okuyup Gündem şeridi, filtre, manşet,
kategori şeritleri ve AI yorum penceresinden oluşan HTML'i haber_sablon.html şablonuyla üretir.
"""
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from haber_ayar import ELEME, HABER_GUNU, KATEGORILER, kucuk

KLASOR = Path(__file__).parent
YENI_SAAT, GUNDEM_SAAT, MANSET_GUN = 3, 48, 3
AY = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


@st.cache_data(ttl=600)
def haber_verisi():
    dosya = KLASOR / "data" / "haberler.json"
    return json.loads(dosya.read_text(encoding="utf-8")) if dosya.exists() else {"haberler": []}


def ne_zaman(tarih, simdi):
    fark = (simdi - tarih).total_seconds()
    if fark < 3600:
        return f"{max(1, int(fark // 60))} dk önce"
    if fark < 86400:
        return f"{int(fark // 3600)} saat önce"
    return f"{tarih.day} {AY[tarih.month - 1]}"


def zaman_tr(tarih):
    yerel = tarih.astimezone(timezone.utc).timestamp() + 3 * 3600  # Türkiye saati (UTC+3)
    t = datetime.fromtimestamp(yerel, tz=timezone.utc)
    return f"{t:%d.%m.%Y %H:%M}"


def model_adi(model, veri):
    """Haberi yorumlayan servis ve model; eski kayıtlarda yalnızca Gemini model adı tutuluyordu."""
    if not model:
        return veri.get("saglayici", "yapay zekâ")
    return model if "(" in model else f"Google Gemini, {model}"


def hazirla(veri):
    simdi = datetime.now(timezone.utc)
    haberler = []
    for h in veri.get("haberler", []):
        if ELEME.search(kucuk(h["baslik"])):  # eleme kuralları sonradan sıkılaştırıldıysa eski kayıtlar da gizlenir
            continue
        ad, renk, koyu = KATEGORILER.get(h["kategori"], KATEGORILER["finans"])
        tarih = datetime.fromisoformat(h["tarih"])
        kaynak_adlari = [k["ad"].split(" | ")[0] for k in h["kaynaklar"]]
        liste = ", ".join(f"{k['ad'].split(' | ')[0]} ({zaman_tr(datetime.fromisoformat(k['tarih']))})"
                          for k in h["kaynaklar"][:4])
        haberler.append(dict(h, kat_ad=ad, renk=renk, koyu=koyu, tarih_dt=tarih,
                             yeni=(simdi - tarih).total_seconds() < YENI_SAAT * 3600,
                             zaman=ne_zaman(tarih, simdi), kaynak_kisa=kaynak_adlari[0] + (
                                 f" +{len(kaynak_adlari) - 1}" if len(kaynak_adlari) > 1 else ""),
                             not_=(f"Bu yorum {liste} kaynaklarında yayımlanan haberlerden ücretsiz bir yapay zekâ "
                                   f"modeli ({model_adi(h.get('model'), veri)}) ile hazırlanmıştır; haberin tam "
                                   f"metni yer almaz. Ayrıntılar ve doğrulama için kaynaklara bakınız.")))
    return haberler, simdi


def meta_html(h):
    yeni = '<span class="yeni">Yeni</span>' if h["yeni"] else ""
    return f'<span class="kaynak">{escape(h["kaynak_kisa"])}</span><span class="zaman">{h["zaman"]}</span>{yeni}'


def gorsel_html(h):
    if not h.get("gorsel"):
        return ""
    return f'<img src="{escape(h["gorsel"])}" alt="" loading="lazy" referrerpolicy="no-referrer" data-yedek>'


def sayfa_html(haberler, simdi):
    # Gündem: son 48 saatin kritik haberleri; az ise en önemli yeni haberlerle tamamlanır
    taze = [h for h in haberler if (simdi - h["tarih_dt"]).total_seconds() < GUNDEM_SAAT * 3600]
    gundem = sorted([h for h in taze if h["gundem"]], key=lambda h: h["tarih_dt"], reverse=True)
    gundem += sorted([h for h in taze if not h["gundem"]], key=lambda h: (-h["onem"], -h["tarih_dt"].timestamp()))
    gundem = gundem[:8]
    if gundem:
        oge = '<span class="g-ayrac">•</span>'.join(
            f'<button class="g-oge" data-id="{h["id"]}"><span class="g-saat">{zaman_tr(h["tarih_dt"])[-5:]}</span>'
            f'<span class="g-baslik">{escape(h["baslik"])}</span><span class="g-kaynak">{escape(h["kaynak_kisa"])}</span></button>'
            for h in gundem)
        gundem_html = (f'<div class="gundem" aria-label="Gündem: son dakika haberleri"><div class="g-etiket">'
                       f'<span class="g-nokta"></span>Gündem</div><div class="g-pencere"><div class="g-serit" '
                       f'style="--sure:{max(30, 9 * len(gundem))}s">{oge}<span class="g-ayrac">•</span>{oge}'
                       f'<span class="g-ayrac">•</span></div></div></div>')
    else:
        gundem_html = ""

    # Manşet: önce son 3 günün en önemlileri, yetmezse daha eski önemli haberler; her markadan en fazla bir haber
    # (gündem haberlerinden en fazla iki)
    def sira(h):
        return ((simdi - h["tarih_dt"]).days >= MANSET_GUN, not h["gundem"], -h["onem"], h["oncelik"],
                -h["tarih_dt"].timestamp())
    manset, sayac = [], {}
    for h in sorted(haberler, key=sira):
        sinir = 2 if h["marka"] == "Gündem" else 1
        if sayac.get(h["marka"], 0) < sinir:
            manset.append(h)
            sayac[h["marka"]] = sayac.get(h["marka"], 0) + 1
        if len(manset) == 5:
            break
    if manset:
        slaytlar = "".join(
            f'<button class="slayt{"" if h.get("gorsel") else " tipolu"}" data-id="{h["id"]}" data-tipo '
            f'style="--k:{h["renk"]};--kk:{h["koyu"]}">{gorsel_html(h)}<span class="kat-etiket">{h["kat_ad"]}</span>'
            f'<h3>{escape(h["baslik"])}</h3><span class="meta">{meta_html(h)}</span></button>' for h in manset)
        noktalar = "".join(f'<button class="nokta{" aktif" if i == 0 else ""}" aria-label="{i + 1}. manşet"></button>'
                           for i in range(len(manset)))
        manset_html = (f'<section class="manset" aria-label="Manşet haberler"><div class="manset-pencere"><div '
                       f'class="manset-serit">{slaytlar}</div></div><div class="manset-alt"><div class="noktalar">'
                       f'{noktalar}</div><div class="oklar"><button class="ok m-geri" aria-label="Önceki manşet">‹</button>'
                       f'<button class="ok m-ileri" aria-label="Sonraki manşet">›</button></div></div></section>')
    else:
        manset_html = f'<div class="bos-mesaj" style="display:block">Son {HABER_GUNU} günde gösterilecek haber bulunamadı.</div>'

    # Kategori şeritleri ve filtre
    satirlar, filtre = [], ['<button class="filtre aktif" data-kat="hepsi">Tümü</button>']
    for anahtar, (ad, renk, koyu) in KATEGORILER.items():
        kategori = sorted([h for h in haberler if h["kategori"] == anahtar], key=lambda h: h["tarih_dt"], reverse=True)
        filtre.append(f'<button class="filtre{"" if kategori else " bos"}" data-kat="{anahtar}" style="--k:{renk}">'
                      f'{ad} <span class="sayi">({len(kategori)})</span></button>')
        if not kategori:
            continue
        kartlar = "".join(
            f'<button class="kart" data-id="{h["id"]}"><div class="kapak" data-tipo>{gorsel_html(h)}'
            f'<div class="tipo"{" hidden" if h.get("gorsel") else ""}><span>{escape(h["baslik"])}</span></div></div>'
            f'<div class="govde">{"<h4>" + escape(h["baslik"]) + "</h4>" if h.get("gorsel") else ""}'
            f'<span class="meta">{meta_html(h)}</span></div></button>' for h in kategori)
        satirlar.append(f'<section class="satir" data-kat="{anahtar}" style="--k:{renk};--kk:{koyu}"><div class="satir-bas">'
                        f'<h2>{ad}</h2><div class="oklar"><button class="ok" data-yon="-1" aria-label="{ad} geri">‹</button>'
                        f'<button class="ok" data-yon="1" aria-label="{ad} ileri">›</button></div></div>'
                        f'<div class="serit" tabindex="0">{kartlar}</div></section>')

    veri = {h["id"]: {"baslik": h["baslik"], "yorum": h["yorum"], "neden": h["neden"], "kat_ad": h["kat_ad"],
                      "renk": h["renk"], "koyu": h["koyu"], "gorsel": h.get("gorsel"), "yeni": h["yeni"],
                      "not": h["not_"], "kaynaklar": [{"ad": k["ad"].split(" | ")[0], "url": k["url"]} for k in h["kaynaklar"]]}
            for h in haberler}
    sablon = (KLASOR / "haber_sablon.html").read_text(encoding="utf-8")
    html = (sablon.replace("__GUNDEM__", gundem_html).replace("__FILTRE__", "".join(filtre))
            .replace("Son 10 günde", f"Son {HABER_GUNU} günde").replace("__MANSET__", manset_html).replace("__SATIRLAR__", "".join(satirlar))
            .replace("__VERI__", json.dumps(veri, ensure_ascii=False).replace("</", "<\\/")))
    yukseklik = 140 + (440 if manset else 80) + 330 * len(satirlar)
    return html, yukseklik


def haber_sayfasi():
    veri = haber_verisi()
    haberler, simdi = hazirla(veri)
    html, yukseklik = sayfa_html(haberler, simdi)
    components.html(html, height=yukseklik, scrolling=False)
    if veri.get("guncelleme"):
        st.caption(f"Son güncelleme: {zaman_tr(datetime.fromisoformat(veri['guncelleme']))}. Haberler son {HABER_GUNU} günün "
                   f"güvenilir kaynaklarından derlenir ve yapay zekâ ile doğrulanıp yorumlanır.")
