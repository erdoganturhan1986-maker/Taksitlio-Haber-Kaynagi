"""
Haberler bölümünün ayarları: kategoriler, takip edilen markalar ve bankalar, güvenilir kaynaklar ve eleme kuralları.
Öncelik seviyeleri kaba tutulur (1 yüksek, 2 orta, 3 standart); gerçek satış payları burada yer almaz.
"""
import re

KATEGORILER = {  # anahtar: (görünen ad, renk, koyu renk)
    "elektronik": ("Büyük elektronik", "#1d4ed8", "#0b1b3a"),
    "beyaz": ("Beyaz eşya ve ev elektroniği", "#0369a1", "#082f49"),
    "telefon": ("Telefon ve telekom", "#7c3aed", "#2e1065"),
    "finans": ("Banka ve finans kampanyaları", "#0f766e", "#042f2e"),
    "mobilya": ("Ev mobilyası", "#9a3412", "#431407"),
    "ev": ("Ev, mutfak ve yapı", "#be123c", "#4c0519"),
    "iklim": ("Isıtma ve soğutma", "#4d7c0f", "#1a2e05"),
    "kuyum": ("Kuyum ve mücevherat", "#a16207", "#422006"),
}

# ad, kategori, öncelik, arama sorguları, başlık/özette geçmesi gereken desen
MARKALAR = [
    ("Vatan Bilgisayar", "elektronik", 1, ['"Vatan Bilgisayar"'], r"Vatan Bilgisayar"),
    ("Teknosa", "elektronik", 1, ["Teknosa"], r"Teknosa"),
    ("Gürgençler", "elektronik", 2, ["Gürgençler"], r"Gürgençler"),
    ("Arçelik", "beyaz", 2, ["Arçelik", "Beko"], r"Arçelik|Beko"),
    ("BSH", "beyaz", 2, ['"BSH" beyaz eşya', '"Bosch" beyaz eşya', '"Siemens" beyaz eşya', "Profilo beyaz eşya"],
     r"BSH|Bosch|Siemens|Profilo"),
    ("Samsung", "beyaz", 2, ['"Samsung" Türkiye'], r"Samsung"),
    ("Xiaomi", "telefon", 3, ['"Xiaomi" Türkiye', "Evofone"], r"Xiaomi|Evofone"),
    ("EasyCep", "telefon", 3, ["EasyCep"], r"EasyCep"),
    ("Vodafone", "telefon", 3, ['"Vodafone" telefon kampanya'], r"Vodafone"),
    ("Reeder", "telefon", 3, ['"Reeder" telefon'], r"Reeder"),
    ("Kutup", "telefon", 3, ['"Kutup" telefon mağaza'], r"Kutup"),
    ("Yenilio", "telefon", 3, ["Yenilio"], r"Yenilio"),
    ("İstikbal", "mobilya", 3, ['"İstikbal Mobilya"', '"İstikbal" mobilya'], r"İstikbal"),
    ("Yataş", "mobilya", 3, ["Yataş"], r"Yataş"),
    ("Bambi", "mobilya", 3, ['"Bambi Yatak"'], r"Bambi"),
    ("İdaş", "mobilya", 3, ['"İdaş" mobilya'], r"İdaş"),
    ("Karaca", "ev", 3, ['"Karaca" züccaciye', '"Karaca Home"'], r"Karaca"),
    ("Schafer", "ev", 3, ['"Schafer" mutfak'], r"Schafer"),
    ("Koçtaş", "ev", 3, ["Koçtaş"], r"Koçtaş"),
    ("Alarko Carrier", "iklim", 3, ['"Alarko Carrier"'], r"Alarko"),
    ("Daikin", "iklim", 3, ['"Daikin Türkiye"'], r"Daikin"),
    ("Zen Pırlanta", "kuyum", 2, ['"Zen Pırlanta"'], r"Zen Pırlanta"),
    ("Lizay", "kuyum", 3, ['"Lizay Pırlanta"'], r"Lizay"),
    # Banka ve finans kuruluşları: kredi ve kampanya bağlamında aranır
    ("Fibabanka", "finans", 2, ['"Fibabanka" kredi OR kampanya'], r"Fibabanka"),
    ("Yapı Kredi", "finans", 2, ['"Yapı Kredi" kredi kampanya'], r"Yapı Kredi"),
    ("İş Bankası", "finans", 2, ['"İş Bankası" kredi kampanya'], r"İş Bankası|İşbank"),
    ("Albaraka Türk", "finans", 2, ['"Albaraka" finansman OR kampanya'], r"Albaraka"),
    ("Kuveyt Türk", "finans", 2, ['"Kuveyt Türk" finansman OR kampanya'], r"Kuveyt Türk"),
    ("Alternatifbank", "finans", 2, ['"Alternatifbank" kredi OR kampanya'], r"Alternatif ?bank"),
    ("Financell", "finans", 2, ["Financell"], r"Financell"),
    ("Tombank", "finans", 2, ['"Tombank" OR "TOM Bank"'], r"Tombank|TOM Bank"),
    ("Getirfinans", "finans", 2, ['"Getirfinans" OR "GetirFinans"'], r"Getir ?finans"),
    ("Fairfinans", "finans", 2, ['"Fairfinans" OR "Fair Finans"'], r"Fair ?finans"),
    ("Alışveriş kredisi", "finans", 1, ['"alışveriş kredisi"', '"taksitli alışveriş" kredi'], r"alışveriş kredi|taksit"),
    # Sektör aramaları: belirli bir markaya bağlı olmayan sektör haberleri (kategori boşsa AI belirler)
    ("Sektör: perakende", None, 2, ['"perakende sektörü"', '"perakende satış"'], r"perakende"),
    ("Sektör: elektronik perakende", "elektronik", 2, ['"elektronik perakende"', '"teknoloji perakendecisi"'],
     r"elektronik|teknoloji"),
    ("Sektör: beyaz eşya", "beyaz", 2, ['"beyaz eşya" satış', '"beyaz eşya" sektör'], r"beyaz eşya"),
    ("Sektör: cep telefonu", "telefon", 2, ['"cep telefonu" satış', '"akıllı telefon" pazar'], r"telefon"),
    ("Sektör: mobilya", "mobilya", 3, ['"mobilya sektörü"', '"mobilya" satış'], r"mobilya"),
    ("Sektör: kuyum", "kuyum", 3, ['"kuyum sektörü"', '"mücevher" satış'], r"kuyum|mücevher"),
    ("Sektör: ısıtma ve soğutma", "iklim", 3, ['"klima" satış', '"kombi" satış'], r"klima|kombi|iklimlendirme"),
]

# Gündem şeridi için güvenilir yayınların kendi akışları
GUNDEM_AKISLARI = [
    ("Bloomberg HT", "https://www.bloomberght.com/rss"),
    ("Dünya", "https://www.dunya.com/rss"),
    ("Ekonomim", "https://www.ekonomim.com/rss"),
    ("NTV", "https://www.ntv.com.tr/ekonomi.rss"),
    ("Habertürk", "https://www.haberturk.com/rss/ekonomi.xml"),
    ("Anadolu Ajansı", "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"),
]
GUNDEM_DESENI = re.compile(
    r"taksit|alışveriş kredi|tüketici kredi|ihtiyaç kredi|kredi kart|bddk|politika faiz|faiz karar|"
    r"merkez bankası|perakende|beyaz eşya|cep telefon|elektronik|e-ticaret|kartlı harcama")

# Güvenilir kaynaklar (Google Haberler'deki kaynak adında geçen ifade)
GUVENILIR = ["anadolu ajansı", "dha", "ihlas haber", "iha", "reuters", "bloomberg ht", "dünya", "ekonomim", "cnbc-e",
             "para dergi", "paratic", "ntv", "habertürk", "hürriyet", "milliyet", "sabah", "sözcü", "oksijen",
             "webrazzi", "mall report"]

# Kesin eleme: suç/asayiş ve konu dışı başlıklar. Metin önce Türkçe küçük harfe çevrilir (bkz. kucuk);
# kalıplar kelime başından eşleşir, "kazanç", "operasyonel", "amaç" gibi masum kelimeler yakalanmaz.
ELEME = re.compile(
    r"\bgözaltı|\btutukla|\boperasyon(?!el)|\bcinayet|\böldür|\btehdit|\bsilahlı|\bsaldırı|\bdolandırıc|"
    r"\byaralı|\bkaza(?!n)|\byangın|\bhırsız|\bgasp|\bsoygun|\bşüpheli|\bmahkeme|\bdava aç|\biddianame|"
    r"\bemekli promosyon|\bmaaş promosyon|\bkap \*|fon toplam gider|portföy dağılım|katılım fonu|yatırım fonu|"
    r"\bbasketbol|\bfutbol|\bvoleybol|\bmaç(ı|ta|tan|lar|ın)?\b|\bşampiyon|\bburs\b|\bteknofest|"
    r"hedef fiyat|\btemettü")


def kucuk(metin):
    """Türkçe kurallarına göre küçük harfe çevirir (İ -> i, I -> ı)."""
    return str(metin).replace("İ", "i").replace("I", "ı").lower()


def desen(ifade):
    """Marka desenini Türkçe küçük harfle, kelime başından eşleşecek şekilde derler."""
    return re.compile(r"\b(" + kucuk(ifade) + r")")


def guvenilir_mi(kaynak):
    k = kucuk(kaynak)
    return any(re.search(rf"(^|\W){re.escape(g)}(\W|$)", k) for g in GUVENILIR)
