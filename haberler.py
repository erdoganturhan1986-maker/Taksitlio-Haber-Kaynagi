"""
Haber toplayıcı: Markaları ve bankaları arar, gündem akışlarını okur, eleme kurallarını uygular,
aynı olayı farklı kaynaklardan birleştirir, sadece güvenilir kaynakta da yer alan olayları AI'a doğrulatır ve yorumlatır.
Çıktı: data/haberler.json (sayfanın okuduğu) ve data/haber_onbellek.json (AI'ın daha önce baktığı olaylar).
"""
import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import ai
from haber_ayar import ELEME, GUNDEM_AKISLARI, GUNDEM_DESENI, HABER_GUNU, KATEGORILER, MARKALAR, desen, guvenilir_mi, kucuk
from haber_kaynak import akis_oku, google_ara, orijinal_link, sayfa_bilgisi

CIKTI, ONBELLEK = "data/haberler.json", "data/haber_onbellek.json"
GUN = HABER_GUNU        # en fazla bu kadar gün geriye gidilir (haber_ayar.py'den)
YENI_OLAY_SINIRI = 60   # bir çalışmada AI'a gönderilecek en fazla yeni olay
PAKET = 5               # AI'a tek seferde gönderilen olay sayısı
# Değerlendirme sürümü: AI talimatı değişince kendiliğinden değişir ve haberler yeniden değerlendirilir
# (eleme kuralları ayrıca her çıktıda yeniden uygulandığı için onların değişmesi yeniden değerlendirme gerektirmez)
SURUM = hashlib.sha1(ai.TALIMAT.encode()).hexdigest()[:8]

# Yorumlardan çıkarılacak dolgu cümleleri: haberde olmayan tahmin ve genel değerlendirmeler
DOLGU_CUMLE = re.compile(r"yaratabilir|izleyebilir|yakından izle|işaret ediyor|fırsatlar? (sunabilir|yarat)|önem taşı|"
                         r"dikkat çek|etkileyebilir|artırabilir|azaltabilir|sağlayabilir|kolaylaştırabilir|"
                         r"belirtilmemiş|açıklanmamış|yer almıyor|bilgi verilmemiş")
KAYNAK_ATFI = re.compile(r"belirtti|açıkladı|öngör|bekliyor|ifade etti|dedi|göre|bildirdi|duyurdu|tahmin ediyor")


def yorumu_temizle(yorum, metin_var):
    """Dolgu cümlelerini çıkarır; haber metni yoksa (AI yalnızca başlığı gördüyse) yorum tek cümleyle sınırlanır."""
    cumleler = [c.strip() for c in re.split(r"(?<=[.!?])\s+", yorum.strip()) if c.strip()]
    temiz = [c for c in cumleler if not (DOLGU_CUMLE.search(kucuk(c)) and not KAYNAK_ATFI.search(kucuk(c)))]
    temiz = temiz or cumleler[:1]
    return " ".join(temiz if metin_var else temiz[:1])
SIMDI = datetime.now(timezone.utc)


DOLGU = {"için", "ile", "olarak", "yeni", "kadar", "gibi", "daha", "çok", "oldu", "etti", "bir", "yılı", "yılın", "ve", "da", "de"}


def kelimeler(baslik, marka=""):
    """Başlığın anlamlı kelimeleri; Türkçe ekler sorun olmasın diye kelimelerin ilk 5 harfi alınır."""
    marka_kokleri = {k[:5] for k in re.findall(r"\w+", kucuk(marka))}
    return {k[:5] for k in re.findall(r"\w+", kucuk(baslik))
            if len(k) > 2 and k not in DOLGU and not k.isdigit()} - marka_kokleri


def ayni_olay(a, b):
    """İki haber aynı olayı mı anlatıyor? En fazla 3 gün arayla ve yeterli ortak kelime.
    Farklı arama gruplarından gelen haberler (ör. bir marka ile gündem) için daha sıkı ölçüt uygulanır."""
    if abs((a["tarih"] - b["tarih"]).total_seconds()) > 3 * 86400:
        return False
    ka, kb = kelimeler(a["baslik"], a["marka"]), kelimeler(b["baslik"], b["marka"])
    ortak = len(ka & kb)
    if a["marka"] != b["marka"]:
        return ortak >= 3 and ortak / max(1, len(ka | kb)) >= 0.4
    return ortak >= 3 or (ortak >= 2 and ortak / max(1, len(ka | kb)) >= 0.25)


def adaylari_topla():
    adaylar = []
    for ad, kategori, oncelik, sorgular, ifade in MARKALAR:
        marka_deseni = desen(ifade)
        for sorgu in sorgular:
            try:
                sonuclar = google_ara(sorgu, GUN)
            except Exception as hata:
                print(f"Arama başarısız ({sorgu}): {hata}")
                continue
            for h in sonuclar:
                k = kucuk(h["baslik"])
                if not h["tarih"] or SIMDI - h["tarih"] > timedelta(days=GUN):
                    continue
                if not marka_deseni.search(k) or ELEME.search(k):
                    continue
                adaylar.append(dict(h, marka=ad, kategori=kategori, oncelik=oncelik))
            time.sleep(1)
    for ad, adres in GUNDEM_AKISLARI:
        try:
            for h in akis_oku(ad, adres):
                k = kucuk(h["baslik"] + " " + h.get("metin", ""))
                if (h["tarih"] and SIMDI - h["tarih"] <= timedelta(days=2) and GUNDEM_DESENI.search(k)
                        and not ELEME.search(k)):
                    adaylar.append(dict(h, marka="Gündem", kategori=None, oncelik=2))
        except Exception as hata:
            print(f"Akış okunamadı ({ad}): {hata}")
    return adaylar


def olaylara_ayir(adaylar):
    """Aynı olayı anlatan haberleri birleştirir; güvenilir kaynakta yer almayan olayları atar."""
    adaylar = sorted(adaylar, key=lambda x: x["tarih"])
    ust = list(range(len(adaylar)))  # zincirleme birleştirme: A~B ve B~C ise A, B, C aynı olay

    def kok(i):
        while ust[i] != i:
            ust[i] = ust[ust[i]]
            i = ust[i]
        return i

    for i in range(len(adaylar)):
        for j in range(i + 1, len(adaylar)):
            if ayni_olay(adaylar[i], adaylar[j]):
                ust[kok(j)] = kok(i)
    gruplar = {}
    for i, h in enumerate(adaylar):
        gruplar.setdefault(kok(i), []).append(h)
    olaylar = list(gruplar.values())
    sonuc = []
    for o in olaylar:
        guvenilirler = [x for x in o if guvenilir_mi(x["kaynak"])]
        if not guvenilirler:
            continue  # sadece küçük kaynaklarda geçen olay gösterilmez
        ana = next((x for x in guvenilirler if not x["google"]), guvenilirler[0])
        markalar = [x["marka"] for x in o if x["marka"] != "Gündem"]
        markalar = [m for m in markalar if not m.startswith("Sektör:")] or markalar  # marka, sektör aramasından önce gelir
        kaynaklar, gorulen = [], set()
        for x in sorted(o, key=lambda x: (not guvenilir_mi(x["kaynak"]), x["tarih"])):
            if x["kaynak"] not in gorulen:
                gorulen.add(x["kaynak"])
                kaynaklar.append({"ad": x["kaynak"], "url": x["link"], "tarih": x["tarih"].isoformat(),
                                  "guvenilir": guvenilir_mi(x["kaynak"])})
        sonuc.append({"id": hashlib.sha1(kucuk(ana["baslik"]).encode()).hexdigest()[:12], "baslik": ana["baslik"],
                      "marka": max(set(markalar), key=markalar.count) if markalar else "Gündem",
                      "kategori": next((x["kategori"] for x in o if x["kategori"]), None),
                      "oncelik": min(x["oncelik"] for x in o), "tarih": o[0]["tarih"].isoformat(),
                      "kaynaklar": kaynaklar, "_ana": ana})
    return sonuc


def main():
    onbellek = json.load(open(ONBELLEK)) if os.path.exists(ONBELLEK) else {}
    # Eski sürümle değerlendirilmiş olaylar silinmez: yeniden değerlendirilene kadar gösterilmeye devam eder.
    onbellek = {k: v for k, v in onbellek.items() if SIMDI - datetime.fromisoformat(v["tarih"]) <= timedelta(days=GUN)}
    olaylar = olaylara_ayir(adaylari_topla())
    print(f"Güvenilir kaynakta yer alan olay: {len(olaylar)} | önbellekte: {len(onbellek)} "
          f"(güncel sürüm: {sum(v.get('surum') == SURUM for v in onbellek.values())})")

    yeniler = []
    for o in olaylar:
        if o["id"] in onbellek and onbellek[o["id"]].get("surum") == SURUM:  # güncel değerlendirme var
            eski = onbellek[o["id"]]
            adlar = {k["ad"] for k in eski["kaynaklar"]}
            eski["kaynaklar"] += [k for k in o["kaynaklar"] if k["ad"] not in adlar]
        else:
            yeniler.append(o)
    yeniler = sorted(yeniler, key=lambda o: (o["oncelik"], o["tarih"]))[:YENI_OLAY_SINIRI]
    yeniler.sort(key=lambda o: (o["marka"], o["tarih"]))  # aynı markanın haberleri aynı pakette karşılaştırılsın

    sayac = {"google": 0, "cozulen": 0, "sayfa": 0, "gorsel": 0}
    for o in yeniler:  # görsel ve AI'ın okuyacağı metin bölümü
        ana = o.pop("_ana")
        adres = ana["link"] if not ana["google"] else orijinal_link(ana["link"])
        sayac["google"] += ana["google"]
        sayac["cozulen"] += bool(ana["google"] and adres)
        bilgi = sayfa_bilgisi(adres) if adres else {}
        sayac["sayfa"] += bool(bilgi)
        if adres:
            o["kaynaklar"][0]["url"] = adres if o["kaynaklar"][0]["ad"] == ana["kaynak"] else o["kaynaklar"][0]["url"]
        o["gorsel"] = ana.get("gorsel") or bilgi.get("gorsel")
        o["_metin"] = bilgi.get("metin") or ana.get("metin") or bilgi.get("ozet") or ""
        sayac["gorsel"] += bool(o["gorsel"])
    print(f"Teşhis: Google linki {sayac['google']}, çözülen {sayac['cozulen']}, okunan sayfa {sayac['sayfa']}, "
          f"görsel bulunan {sayac['gorsel']} / {len(yeniler)}")

    for i in range(0, len(yeniler), PAKET):
        paket = yeniler[i:i + PAKET]
        kararlar = ai.degerlendir([{"baslik": o["baslik"], "metin": o["_metin"],
                                    "marka": "Genel gündem" if o["marka"] == "Gündem" else o["marka"],
                                    "kaynaklar": [k["ad"] for k in o["kaynaklar"]]} for o in paket])
        if kararlar is None:
            print("AI şu an değerlendirme yapamadı; kalan olaylar bir sonraki çalışmaya bırakıldı.")
            break
        for no, (o, karar) in enumerate(zip(paket, kararlar), 1):
            o["metin_var"] = len(o.pop("_metin", "") or "") >= 300
            tekrar = karar.get("ayni_olay")
            if isinstance(tekrar, int) and 1 <= tekrar < no and paket[tekrar - 1]["id"] in onbellek:
                asil = onbellek[paket[tekrar - 1]["id"]]  # aynı olay: kaynakları asıl habere ekle, bunu gösterme
                adlar = {k["ad"] for k in asil["kaynaklar"]}
                asil["kaynaklar"] += [k for k in o["kaynaklar"] if k["ad"] not in adlar]
                asil["gorsel"] = asil.get("gorsel") or o.get("gorsel")
                karar = {"tekrar": asil["id"], "model": karar.get("model")}
            onbellek[o["id"]] = dict(o, karar=karar, degerlendirme=SIMDI.isoformat(), surum=SURUM)
        time.sleep(8)

    gecerli = []
    for o in onbellek.values():
        k = o.get("karar", {})
        if (k.get("marka_dogru") and k.get("ilgili") and not k.get("suc_asayis") and k.get("yorum")
                and not ELEME.search(kucuk(o["baslik"]))):
            gecerli.append({"id": o["id"], "baslik": o["baslik"], "marka": o["marka"],
                            # haberin içeriğine göre AI'ın seçtiği kategori; geçersizse markanın kategorisi
                            "kategori": k.get("kategori") if k.get("kategori") in KATEGORILER
                                        else (o.get("kategori") or "finans"), "oncelik": o["oncelik"],
                            "tarih": o["tarih"], "kaynaklar": o["kaynaklar"], "gorsel": o.get("gorsel"),
                            "yorum": yorumu_temizle(k["yorum"], o.get("metin_var", False)), "neden": "",
                            "gundem": bool(k.get("gundem")),
                            "onem": int(k.get("onem") or 2), "model": k.get("model", "")})
    gecerli.sort(key=lambda x: x["tarih"], reverse=True)
    os.makedirs("data", exist_ok=True)
    json.dump(onbellek, open(ONBELLEK, "w"), ensure_ascii=False)
    json.dump({"guncelleme": SIMDI.isoformat(), "saglayici": ai.SAGLAYICI, "haberler": gecerli},
              open(CIKTI, "w"), ensure_ascii=False, indent=1)
    print(f"Gösterilecek haber: {len(gecerli)} (yeni değerlendirilen: {len(yeniler)})")


if __name__ == "__main__":
    main()
