"""
Yapay zekâ katmanı: Haberleri doğrular ve yorumlar. Başka bir modele geçmek için sadece bu dosya değişir.
Şu an: Google Gemini (ücretsiz katman). Anahtar GitHub gizli bilgilerinden (GEMINI_API_KEY) okunur.
"""
import json
import os
import time
import urllib.error
import urllib.request

SAGLAYICI = "Google Gemini"
TERCIH = ["gemini-flash-latest"]  # önce denenecek model; kalanlar anahtarın erişebildiği listeden otomatik seçilir
ADRES = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={anahtar}"
LISTE = "https://generativelanguage.googleapis.com/v1beta/models?key={anahtar}&pageSize=200"
SURE_SINIRI = 300  # bir çalışmada AI için harcanacak en fazla süre (saniye); aşılırsa kalanlar sonraki çalışmaya kalır
_BASLANGIC = time.time()


def modelleri_bul(anahtar):
    """Anahtarın kullanabildiği metin modellerinden 'flash' olanları sıralı döner (önce tercih, sonra yeni sürümler)."""
    try:
        with urllib.request.urlopen(LISTE.format(anahtar=anahtar), timeout=30) as r:
            liste = json.loads(r.read().decode("utf-8")).get("models", [])
    except Exception as hata:
        print("Model listesi alınamadı:", str(hata)[:120])
        liste = []
    adlar = [m["name"].split("/", 1)[-1] for m in liste
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    uygun = [a for a in adlar if "flash" in a and not any(
        y in a for y in ("image", "tts", "audio", "live", "omni", "preview", "exp", "thinking"))]
    lite = sorted([a for a in uygun if "lite" in a], reverse=True)
    tam = sorted([a for a in uygun if "lite" not in a], reverse=True)
    sirali = [m for m in TERCIH if m in adlar or not adlar] + tam + lite
    return list(dict.fromkeys(sirali))[:5] or TERCIH

TALIMAT = """Sen Taksitlio için çalışan titiz bir ekonomi editörüsün. Taksitlio, tüketicilerin elektronik, beyaz eşya,
telefon, mobilya, kuyum gibi ürünleri anlaşmalı bankaların alışveriş kredisiyle almasını sağlayan bir aracılık platformudur.

Sana numaralı haberler vereceğim (başlık, ilgili marka/kurum, kaynaklar ve varsa haber metninden kısa bir bölüm).
Her haber için şu kararları ver:
- marka_dogru: Haber gerçekten belirtilen şirket/kurum hakkında mı? (Örneğin "vatandaş" kelimesi Vatan Bilgisayar değildir,
  "istikbal" kelimesi İstikbal Mobilya değildir, Karaca soyadı Karaca markası değildir.) Emin değilsen false.
- ilgili: Haber Taksitlio'nun işi için anlamlı mı? İlgili olanlar: markanın Türkiye'deki mağaza, ürün, kampanya, satış,
  fiyat, yatırım, yönetim, finansal sonuç haberleri; bankaların bireysel kredi, alışveriş kredisi, taksit ve kart
  kampanyaları; tüketici kredisi, taksit, faiz ve perakendeyle ilgili düzenleme ve piyasa gelişmeleri.
  İlgisiz olanlar: emekli/maaş promosyonu, fon ve portföy raporları, borsa hedef fiyatları, spor ve sponsorluk, magazin,
  sosyal sorumluluk ve ödül haberleri, şirketin Türkiye perakendesiyle ilgisi olmayan küresel haberleri. Emin değilsen false.
- suc_asayis: Haber suç, asayiş, kaza, şiddet, dava veya soruşturma içeriyor mu? İçeriyorsa true.
- gundem: Tüketici kredisi ve perakende açısından bugün mutlaka bilinmesi gereken kritik bir gelişme mi
  (TCMB faiz kararı, BDDK düzenlemesi, büyük bir kampanya ya da şirket hamlesi gibi)? Sadece gerçekten kritikse true.
- onem: 1 (düşük) ile 5 (çok yüksek) arası, Taksitlio açısından önem.
- kategori: Haberin içeriğine göre şunlardan biri: elektronik (büyük elektronik perakendecileri), beyaz (beyaz eşya ve
  ev elektroniği), telefon (telefon ve telekom), finans (banka, kredi, faiz, düzenleme), mobilya, ev (mutfak, ev eşyası,
  yapı market), iklim (ısıtma ve soğutma), kuyum.
- ayni_olay: Bu listede daha önce gelen bir haber aynı olayı anlatıyorsa onun numarası, yoksa null.
- yorum: Haberi kendi cümlelerinle 2-4 cümlede, tarafsız biçimde anlat. Haberin metninden cümle kopyalama.
  Haberde olmayan bilgi, tahmin veya yargı ekleme; olumsuz ya da olumlu yorum katma, sadece ne olduğunu aktar.
- neden: Bu haberin alışveriş kredisi aracılığı açısından neden önemli olduğunu tek ve ölçülü bir cümleyle yaz.
  Abartma; bağlantı zayıfsa bunu ölçülü ifade et.
marka_dogru veya ilgili false ise ya da suc_asayis true ise yorum ve neden alanlarını boş bırak.

Yanıtı yalnızca JSON dizisi olarak ver:
[{"no": 1, "marka_dogru": true, "ilgili": true, "suc_asayis": false, "gundem": false, "onem": 3,
  "kategori": "elektronik", "ayni_olay": null, "yorum": "...", "neden": "..."}]"""


_MODELLER = None  # ilk çağrıda belirlenir


def _iste(anahtar, model, metin):
    govde = {"systemInstruction": {"parts": [{"text": TALIMAT}]},
             "contents": [{"role": "user", "parts": [{"text": metin}]}],
             "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}
    istek = urllib.request.Request(ADRES.format(model=model, anahtar=anahtar), data=json.dumps(govde).encode(),
                                   headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(istek, timeout=60) as r:
        cevap = json.loads(r.read().decode("utf-8"))
    yazi = cevap["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(yazi[yazi.find("["):yazi.rfind("]") + 1])


def degerlendir(haberler):
    """haberler: [{baslik, marka, kaynaklar, metin}] -> aynı sırada karar sözlükleri; AI çalışmazsa None döner."""
    anahtar = os.environ.get("GEMINI_API_KEY", "").strip()
    if not anahtar or not haberler:
        return None
    satirlar = []
    for i, h in enumerate(haberler, 1):
        satirlar.append(f"{i}. Başlık: {h['baslik']}\n   Marka/kurum: {h['marka']}\n   Kaynaklar: {', '.join(h['kaynaklar'])}"
                        + (f"\n   Metinden bölüm: {h['metin'][:1200]}" if h.get("metin") else ""))
    metin = "\n\n".join(satirlar)
    global _MODELLER
    if _MODELLER is None:
        _MODELLER = modelleri_bul(anahtar)
        print("Kullanılacak modeller:", _MODELLER)
    for model in _MODELLER:
        for deneme, bekle in enumerate((15, 30, None)):
            if time.time() - _BASLANGIC > SURE_SINIRI:
                print("AI için ayrılan süre doldu; kalan haberler bir sonraki çalışmaya kaldı.")
                return None
            try:
                sonuc = _iste(anahtar, model, metin)
                kararlar = {int(s.get("no", 0)): s for s in sonuc if isinstance(s, dict)}
                return [dict(kararlar.get(i, {}), model=model) for i in range(1, len(haberler) + 1)]
            except urllib.error.HTTPError as hata:
                print(f"AI {model}: HTTP {hata.code} (deneme {deneme + 1})")
                if hata.code in (429, 500, 502, 503, 504) and bekle:  # geçici hata: bekleyip tekrar dene
                    time.sleep(bekle)
                    continue
                break  # 400/403/404: bu model kullanılamıyor, sıradakine geç
            except Exception as hata:
                print(f"AI {model}: {str(hata)[:150]}")
                break
    return None
