"""
AI agent: Yeni haber başlıklarını okur, içindeki piyasa rakamlarını çıkarır
ve data/rakamlar.csv dosyasına kaydeder.
Ücretsiz GitHub Models hizmetini kullanır. Gereken izin (GITHUB_TOKEN) GitHub tarafından
otomatik verilir; kodda hiçbir şifre veya anahtar yoktur.
"""
import json
import os
import urllib.error
import urllib.request

import pandas as pd

HABERLER = "data/haberler.csv"
RAKAMLAR = "data/rakamlar.csv"
ISLENEN = "data/islenen_linkler.txt"

# Denenecek (adres, model) seçenekleri. İlk çalışan kullanılır.
SECENEKLER = [
    ("https://models.github.ai/inference/chat/completions", "openai/gpt-4o-mini"),
    ("https://models.github.ai/inference/chat/completions", "openai/gpt-4.1-mini"),
    ("https://models.inference.ai.azure.com/chat/completions", "gpt-4o-mini"),
]
PAKET_BOYUTU = 40      # tek seferde AI'a gönderilen başlık sayısı
CALISMA_LIMITI = 200   # bir çalışmada en fazla kaç başlık işlensin (maliyet kontrolü)

GOSTERGELER = [
    "Perakende satış (yıllık %)", "Perakende satış (aylık %)",
    "Kartlı harcama", "Tüketici güven endeksi", "Enflasyon TÜFE (yıllık %)",
    "Enflasyon TÜFE (aylık %)", "Politika faizi (%)", "Dolar/TL", "Euro/TL",
    "Beyaz eşya satışları", "Şirket cirosu", "Şirket net kârı",
    "Mağaza sayısı", "Diğer",
]

SUTUNLAR = ["haber_tarihi", "gosterge", "sirket", "deger", "birim", "donem",
            "aciklama", "baslik", "kaynak", "link"]

TALIMAT = f"""Türkiye perakende ve bankacılık piyasası için haber başlıklarından sayısal veri çıkaran bir analistsin.
Sana numaralı haber başlıkları vereceğim. Sadece başlıkta AÇIKÇA yazan sayısal piyasa rakamlarını çıkar.
Tahmin yapma, hesaplama yapma, başlıkta olmayan bilgi ekleme.

Kurallar:
- "gosterge" şu listeden biri olmalı: {", ".join(GOSTERGELER)}
- "sirket": rakam bir şirkete aitse şirket adı (ör. Teknosa), değilse boş metin.
- "deger": sayı olarak, ondalık ayırıcı nokta (ör. 12.5). Düşüş ise eksi işaretli.
- "birim": "%", "TL", "milyar TL", "puan", "adet" gibi.
- "donem": rakamın ait olduğu dönem (ör. "Eylül 2026", "2026 Q2"); belli değilse boş metin.
- "aciklama": en fazla 10 kelimelik açıklama.
- Bir başlıkta birden fazla rakam varsa her biri ayrı kayıt olsun.

Sadece JSON dizisi döndür, başka hiçbir şey yazma:
[{{"no": 1, "gosterge": "...", "sirket": "", "deger": 12.5, "birim": "%", "donem": "Eylül 2026", "aciklama": "..."}}]
Hiç rakam yoksa [] döndür."""


def json_ayikla(metin: str) -> list:
    bas, son = metin.find("["), metin.rfind("]")
    if bas == -1 or son == -1:
        return []
    return json.loads(metin[bas:son + 1])


def ai_sor(anahtar: str, metin: str, adres: str, model: str) -> str:
    istek = urllib.request.Request(
        adres,
        method="POST",
        data=json.dumps({
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": TALIMAT},
                {"role": "user", "content": metin},
            ],
        }).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {anahtar}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "haber-takip-agent/1.0",
        },
    )
    try:
        with urllib.request.urlopen(istek, timeout=120) as cevap:
            durum, govde = cevap.status, cevap.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as hata:
        govde = hata.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {hata.code}: {govde[:500]}") from None
    try:
        return json.loads(govde)["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise RuntimeError(f"Beklenmeyen cevap (HTTP {durum}): {govde[:500]!r}") from None


def calisan_secenegi_bul(anahtar: str):
    for adres, model in SECENEKLER:
        try:
            ai_sor(anahtar, "1. Perakende satışlar yüzde 10 arttı", adres, model)
            print(f"AI bağlantısı kuruldu: {adres} | {model}")
            return adres, model
        except Exception as hata:
            print(f"Olmadı: {adres} | {model} -> {hata}")
    return None


def paketi_isle(anahtar: str, paket: pd.DataFrame, adres: str, model: str) -> list:
    satirlar = "\n".join(f"{i + 1}. {b}" for i, b in enumerate(paket["baslik"]))
    metin = ai_sor(anahtar, satirlar, adres, model)
    try:
        sonuc = json_ayikla(metin)
    except ValueError:
        print(f"AI cevabı okunamadı, paket atlandı. Cevabın başı: {metin[:300]!r}")
        return None
    kayitlar = []
    for r in sonuc:
        try:
            haber = paket.iloc[int(r["no"]) - 1]
            kayitlar.append({
                "haber_tarihi": haber["tarih"],
                "gosterge": r.get("gosterge", "Diğer"),
                "sirket": r.get("sirket", ""),
                "deger": float(r["deger"]),
                "birim": r.get("birim", ""),
                "donem": r.get("donem", ""),
                "aciklama": r.get("aciklama", ""),
                "baslik": haber["baslik"],
                "kaynak": haber["kaynak"],
                "link": haber["link"],
            })
        except (KeyError, ValueError, IndexError, TypeError):
            continue  # hatalı kaydı atla
    return kayitlar


def main():
    anahtar = os.environ.get("GITHUB_TOKEN")
    if not anahtar:
