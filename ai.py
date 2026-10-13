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
MODELLER = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.5-flash-lite"]  # sırayla denenir
ADRES = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={anahtar}"

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
- kategori: Şunlardan biri: elektronik, beyaz, telefon, finans, mobilya, ev, iklim, kuyum.
- yorum: Haberi kendi cümlelerinle 2-4 cümlede, tarafsız biçimde anlat. Haberin metninden cümle kopyalama.
  Haberde olmayan bilgi, tahmin veya yargı ekleme; olumsuz ya da olumlu yorum katma, sadece ne olduğunu aktar.
- neden: Bu haberin alışveriş kredisi aracılığı açısından neden önemli olduğunu tek ve ölçülü bir cümleyle yaz.
  Abartma; bağlantı zayıfsa bunu ölçülü ifade et.
marka_dogru veya ilgili false ise ya da suc_asayis true ise yorum ve neden alanlarını boş bırak.

Yanıtı yalnızca JSON dizisi olarak ver:
[{"no": 1, "marka_dogru": true, "ilgili": true, "suc_asayis": false, "gundem": false, "onem": 3,
  "kategori": "elektronik", "yorum": "...", "neden": "..."}]"""


def _iste(anahtar, model, metin):
    govde = {"systemInstruction": {"parts": [{"text": TALIMAT}]},
             "contents": [{"role": "user", "parts": [{"text": metin}]}],
             "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}
    istek = urllib.request.Request(ADRES.format(model=model, anahtar=anahtar), data=json.dumps(govde).encode(),
                                   headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(istek, timeout=120) as r:
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
    for model in MODELLER:
        for deneme in range(2):
            try:
                sonuc = _iste(anahtar, model, metin)
                kararlar = {int(s.get("no", 0)): s for s in sonuc if isinstance(s, dict)}
                return [dict(kararlar.get(i, {}), model=model) for i in range(1, len(haberler) + 1)]
            except urllib.error.HTTPError as hata:
                print(f"AI {model}: HTTP {hata.code}")
                if hata.code == 429 and deneme == 0:
                    time.sleep(20)
                    continue
                break
            except Exception as hata:
                print(f"AI {model}: {str(hata)[:150]}")
                break
    return None
