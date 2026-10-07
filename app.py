"""
Taksitlio Haberler - Streamlit dashboard (sayfa yönetimi)
"""
import streamlit as st

st.set_page_config(page_title="Taksitlio Haberler", page_icon="📊", layout="wide")

sayfalar = [
    st.Page("sayfalar/finansal_veriler.py", title="Finansal Veriler", icon="📈", default=True),
]

st.title("Taksitlio Haberler")
st.navigation(sayfalar, position="top").run()
