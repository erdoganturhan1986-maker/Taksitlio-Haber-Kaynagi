def main():
    anahtar = os.environ.get("GITHUB_TOKEN")
    if not anahtar:
        print("GITHUB_TOKEN tanımlı değil, agent atlandı.")
        return
    if not os.path.exists(HABERLER):
        print("Haber dosyası yok.")
        return

    secenek = calisan_secenegi_bul(anahtar)
    if not secenek:
        print("Hiçbir AI seçeneği çalışmadı, agent bu sefer atlandı.")
        return
    adres, model = secenek

    haberler = pd.read_csv(HABERLER)
    islenen = set(open(ISLENEN).read().split()) if os.path.exists(ISLENEN) else set()
    yeni = haberler[~haberler["link"].isin(islenen)].head(CALISMA_LIMITI)
    print(f"İşlenecek yeni haber: {len(yeni)}")

    rakamlar = pd.read_csv(RAKAMLAR) if os.path.exists(RAKAMLAR) else pd.DataFrame(columns=SUTUNLAR)

    for bas in range(0, len(yeni), PAKET_BOYUTU):
        paket = yeni.iloc[bas:bas + PAKET_BOYUTU].reset_index(drop=True)
        try:
            kayitlar = paketi_isle(anahtar, paket, adres, model)
        except Exception as hata:
            print(f"AI hatası, kalan haberler sonraki çalışmaya kaldı: {hata}")
            break
        if kayitlar is None:
            continue
        if kayitlar:
            rakamlar = pd.concat([rakamlar, pd.DataFrame(kayitlar, columns=SUTUNLAR)], ignore_index=True)
        islenen.update(paket["link"])
        print(f"{bas + len(paket)} haber işlendi, {len(kayitlar)} rakam bulundu")

    rakamlar = rakamlar.drop_duplicates(subset=["link", "gosterge", "deger"])
    rakamlar.sort_values("haber_tarihi", ascending=False).to_csv(RAKAMLAR, index=False)
    with open(ISLENEN, "w") as f:
        f.write("\n".join(sorted(islenen)))


if __name__ == "__main__":
    main()
