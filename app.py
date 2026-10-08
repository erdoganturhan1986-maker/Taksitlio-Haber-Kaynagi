"""
Taksitlio Piyasalar - Streamlit dashboard (sayfa yönetimi)
"""
import streamlit as st

from kayan import kayan_yazi

st.set_page_config(page_title="Taksitlio Piyasalar", page_icon="📊", layout="wide")

# Yeni sayfa eklemek için bu listeye bir satır eklemek yeterli
SAYFALAR = [
    st.Page("sayfalar/finansal_veriler.py", title="Finansal Veriler", icon=":material/monitoring:", default=True),
]

secili = st.navigation(SAYFALAR, position="hidden")

kayan_yazi()
st.title("Taksitlio Piyasalar")

# Sayfa butonları: bulunulan sayfa dolu renkli, diğerleri çerçeveli
kolonlar = st.columns([1.4] * len(SAYFALAR) + [8 - len(SAYFALAR)])
for kolon, sayfa in zip(kolonlar, SAYFALAR):
    aktif = sayfa.url_path == secili.url_path
    if kolon.button(sayfa.title, icon=sayfa.icon, type="primary" if aktif else "secondary",
                    width="stretch", key=f"sayfa_{sayfa.url_path}") and not aktif:
        st.switch_page(sayfa)

st.divider()
secili.run()
