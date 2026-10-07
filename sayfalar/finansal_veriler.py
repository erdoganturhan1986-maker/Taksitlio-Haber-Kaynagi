"""
Finansal Veriler sayfası: BDDK kredi verileri ve enflasyon.
"""
import streamlit as st

from giris import kredi_grafigi

st.header("Finansal Veriler")
kredi_grafigi()
