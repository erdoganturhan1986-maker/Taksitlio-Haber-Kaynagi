"""
Türkiye Perakende Piyasası Dashboard'u - Streamlit
"""
import streamlit as st

from giris import kredi_grafigi

st.set_page_config(page_title="Perakende Piyasası Takibi", page_icon="📊", layout="wide")

st.title("Türkiye Perakende Piyasası Takibi")
kredi_grafigi()
