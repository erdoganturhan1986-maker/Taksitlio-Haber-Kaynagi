"""
Finansal Veriler sayfası: BDDK kredi verileri, kredi faiz oranları ve enflasyon.
"""
import streamlit as st

from faiz_grafik import faiz_grafigi
from giris import kredi_grafigi

kredi_grafigi()
st.divider()
faiz_grafigi()
