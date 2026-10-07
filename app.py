"""
Taksitlio Haberler - Streamlit dashboard
"""
import streamlit as st

from giris import kredi_grafigi

st.set_page_config(page_title="Taksitlio Haberler", page_icon="📊", layout="wide")

st.title("Taksitlio Haberler")
kredi_grafigi()
