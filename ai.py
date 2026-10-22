"""
Yapay zekâ katmanı: Haberleri doğrular ve yorumlar. Başka bir modele geçmek için sadece bu dosya değişir.
Ana servis Groq (ücretsiz katman, GROQ_API_KEY), yedek Google Gemini (ücretsiz katman, GEMINI_API_KEY).
Anahtarlar GitHub gizli bilgilerinden okunur. Her karar, onu veren servis ve modelin adını taşır.
"""
import json
import os
import time
import urllib.error
import urllib.request

SAGLAYICI = "Groq / Google Gemini"
GROQ_ADRES = "https://api.groq.com/openai/v1"
GROQ_TERCIH = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "moonshotai/kimi-k2-instruct", "openai/gpt-oss-20b"]
TARAYICI = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
TERCIH = ["gemini-flash-latest", "gemini-flash-lite-latest"]  # Gemini'de önce bunlar; kalanlar listeden seçilir
ADRES = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={anahtar}"
LISTE = "https://generativelanguage.googleapis.com/v1beta/models?key={anahtar}&pageSize=200"
SURE_SINIRI = 600  # bir çalışmada AI için harcanacak en fazla süre (saniye); aşılırsa kalanlar sonraki çalışmaya kalır
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
    karisik = [m for ikili in zip(tam, lite) for m in ikili] + tam[len(lite):] + lite[len(tam):]  # tam ve lite sırayla
    sirali = [m for m in TERCIH if m in adlar or not adlar] + karisik
    return list(dict.fromkeys(sirali))[:6] or TERCIH

TALIMAT = """Sen Taksitlio için çalışan titiz bir ekonomi editörüsün. Taksitlio, tüketicilerin elektronik, beyaz eşya,
telefon, mobilya, kuyum gibi ürünleri anlaşmalı bankaların alışveriş kredisiyle almasını sağlayan bir aracılık platformudur.

Sana numaralı haberler vereceğim (başlık, ilgili marka/kurum, kaynaklar ve varsa haber metninden kısa bir bölüm).
Marka/kurum alanındaki şirket ve bankalar Taksitlio'nun anlaşmalı iş ortaklarıdır.
Yorumu mutlaka TÜRKÇE yaz; İngilizce ya da başka bir dil kullanma.
Her haber için şu kararları ver:
- marka_dogru: Haber gerçekten belirtilen şirket/kurum hakkında mı? (Örneğin "vatandaş" kelimesi Vatan Bilgisayar değildir,
  "istikbal" kelimesi İstikbal Mobilya değildir, Karaca soyadı Karaca markası değildir.) Emin değilsen false.
  Marka/kurum alanı "Genel gündem" ise belirli bir marka aranmaz, marka_dogru true olur. "Sektör: ..." ise haberin
  gerçekten o sektörle ilgili olup olmadığına bakılır.
- ilgili: Haber Taksitlio'nun işi için anlamlı mı? İş ortağı bir markanın Türkiye'deki ticari faaliyetleri HER ZAMAN
  ilgilidir: yeni ürün ve hizmetler, mağaza açılışları, kampanyalar, satışlar, fiyatlar, yatırımlar, iş birlikleri,
  tedarik anlaşmaları, yönetim değişiklikleri ve finansal sonuçlar. Ayrıca bankaların bireysel kredi, alışveriş kredisi,
  taksit ve kart kampanyaları; tüketici kredisi, taksit, faiz ve perakendeyle ilgili düzenleme ve piyasa gelişmeleri;
  Türkiye'deki perakende, elektronik, beyaz eşya, telefon, mobilya ve kuyum sektörlerinin genel gidişatı ilgilidir.
  İlgisiz olanlar: emekli/maaş promosyonu, fon ve portföy raporları, borsa hedef fiyatları, spor ve sponsorluk, magazin,
  sosyal sorumluluk ve ödül haberleri, şirketin Türkiye perakendesiyle ilgisi olmayan küresel haberleri, haber yerine
  "ne zaman, saat kaçta, nasıl başvurulur, kimler alabilir" gibi takvim veya rehber bilgisi veren tıklama amaçlı yazılar,
  yerel tek bir dükkânın tanıtım ya da indirim yazıları, market aktüel ürün listeleri, altın/döviz fiyatları ve merkez
  bankası rezervleri gibi yatırım ve piyasa fiyatı haberleri, başka ülkelerin pazar verileri, iş ortağı olmayan
  perakendecilerin (BİM, A101, ŞOK, Migros, CarrefourSA gibi market zincirleri dahil) kampanya, ürün ve mağaza haberleri.
  Sektör haberlerinde yalnızca sektörün geneline dair veriler ve gelişmeler ilgilidir. Emin değilsen false.
- suc_asayis: Haber suç, asayiş, kaza, şiddet, dava veya soruşturma içeriyor mu? İçeriyorsa true.
- gundem: Tüketici kredisi ve perakende açısından bugün mutlaka bilinmesi gereken kritik bir gelişme mi
  (TCMB faiz kararı, BDDK düzenlemesi, büyük bir kampanya ya da şirket hamlesi gibi)? Sadece gerçekten kritikse true.
- onem: 1 (düşük) ile 5 (çok yüksek) arası, Taksitlio açısından önem.
- kategori: Haberin içeriğine göre şunlardan biri: elektronik (büyük elektronik perakendecileri), beyaz (beyaz eşya ve
  ev elektroniği), telefon (telefon ve telekom), finans (banka, kredi, faiz, düzenleme), mobilya, ev (mutfak, ev eşyası,
  yapı market), iklim (ısıtma ve soğutma), kuyum.
- ayni_olay: Bu listede daha önce gelen bir haber aynı olayı anlatıyorsa onun numarası, yoksa null. Farklı başlıklarla
  yazılmış olsa da aynı gelişmeyi anlatan haberler aynı olaydır (ör. "TCMB faiz beklentileri netleşti" ile
  "Merkez Bankası'nın ekim faiz kararı için beklentiler belli oldu").
- yorum: Haberi kendi cümlelerinle, tarafsız biçimde anlat. Haberin metninden cümle kopyalama.
  Uzunluk elindeki bilgiye bağlıdır: "Metinden bölüm" yeterli bilgi içeriyorsa 4-6 cümle yaz; ne olduğunu, kimin neyi
  açıkladığını, tarihleri, somut rakamları ve önemli ayrıntıları aktar. Elinde yalnızca başlık varsa ya da metin kısaysa
  1-2 cümleyle yetin ve başlıkta söylenenden fazlasını yazma. YALNIZCA sana verilen başlık ve metindeki bilgileri kullan:
  kendi bilgini, tahmin, yorum, olası sonuç veya etki değerlendirmesi ekleme. Uzatmak için tekrar ya da genel ifadeler kullanma.
marka_dogru veya ilgili false ise ya da suc_asayis true ise yorum alanını boş bırak.

Yanıtı yalnızca JSON dizisi olarak ver:
[{"no": 1, "marka_dogru": true, "ilgili": true, "suc_asayis": false, "gundem": false, "onem": 3,
  "kategori": "elektronik", "ayni_olay": null, "yorum": "..."}]"""


_MODELLER = None  # ilk çağrıda belirlenir
_GROQ_MODELI = None


def _groq_iste(anahtar, metin):
    global _GROQ_MODELI
    if _GROQ_MODELI is None:
        istek = urllib.request.Request(f"{GROQ_ADRES}/models", headers={**TARAYICI, "Authorization": f"Bearer {anahtar}"})
        mevcut = [m["id"] for m in json.load(urllib.request.urlopen(istek, timeout=30))["data"]]
        _GROQ_MODELI = next((m for m in GROQ_TERCIH if m in mevcut), None)
        print("Groq modeli:", _GROQ_MODELI)
    if not _GROQ_MODELI:
        raise RuntimeError("Groq'ta uygun model bulunamadı")
    govde = {"model": _GROQ_MODELI, "temperature": 0.2,
             "messages": [{"role": "system", "content": TALIMAT}, {"role": "user", "content": metin}]}
    istek = urllib.request.Request(f"{GROQ_ADRES}/chat/completions", data=json.dumps(govde).encode(),
                                   headers={**TARAYICI, "Authorization": f"Bearer {anahtar}"})
    with urllib.request.urlopen(istek, timeout=90) as r:
        yazi = json.load(r)["choices"][0]["message"]["content"]
    return json.loads(yazi[yazi.find("["):yazi.rfind("]") + 1]), f"Groq ({_GROQ_MODELI})"


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
    if not haberler or not (anahtar or os.environ.get("GROQ_API_KEY", "").strip()):
        return None
    satirlar = []
    for i, h in enumerate(haberler, 1):
        satirlar.append(f"{i}. Başlık: {h['baslik']}\n   Marka/kurum: {h['marka']}\n   Kaynaklar: {', '.join(h['kaynaklar'])}"
                        + (f"\n   Metinden bölüm: {h['metin'][:3000]}" if h.get("metin") else "\n   (Yalnızca başlık mevcut)"))
    metin = "\n\n".join(satirlar)

    def sirala(sonuc, etiket):
        kararlar = {int(s.get("no", 0)): s for s in sonuc if isinstance(s, dict)}
        return [dict(kararlar.get(i, {}), model=etiket) for i in range(1, len(haberler) + 1)]

    # 1) Ana servis: Groq. Dakikalık sınıra takılırsa Groq'un söylediği süre kadar bekleyip tekrar dener.
    groq_anahtari = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_anahtari:
        for deneme in range(4):
            try:
                sonuc, etiket = _groq_iste(groq_anahtari, metin)
                return sirala(sonuc, etiket)
            except urllib.error.HTTPError as hata:
                ayrinti = hata.read().decode("utf-8", "replace")[:160]
                if hata.code in (429, 500, 502, 503, 504) and deneme < 3:
                    try:
                        bekle = min(60, float(hata.headers.get("retry-after") or 20) + 2)
                    except (TypeError, ValueError):
                        bekle = 20
                    print(f"AI Groq: HTTP {hata.code}, {bekle:.0f} sn bekleniyor ({deneme + 1}. deneme)")
                    time.sleep(bekle)
                    continue
                print(f"AI Groq: HTTP {hata.code} {ayrinti}")
                break
            except Exception as hata:
                print(f"AI Groq: {str(hata)[:150]}")
                break

    # 2) Yedek: Gemini (beklemeden modeller arasında dolaşır)
    if not anahtar:
        return None
    global _MODELLER
    if _MODELLER is None:
        _MODELLER = modelleri_bul(anahtar)
        print("Gemini yedek modelleri:", _MODELLER)
    for model in _MODELLER:
        if time.time() - _BASLANGIC > SURE_SINIRI:
            print("AI için ayrılan süre doldu; kalan haberler bir sonraki çalışmaya kaldı.")
            return None
        try:
            return sirala(_iste(anahtar, model, metin), f"Google Gemini ({model})")
        except urllib.error.HTTPError as hata:
            print(f"AI Gemini {model}: HTTP {hata.code}")
        except Exception as hata:
            print(f"AI Gemini {model}: {str(hata)[:150]}")
    return None
