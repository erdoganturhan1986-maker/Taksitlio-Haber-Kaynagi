"""
Finansal Veriler sayfası: Kredi hacimleri, takipteki alacaklar, kredi faiz oranları ve tüketici güveni.
"""
import streamlit as st

from faiz_grafik import faiz_grafigi
from giris import kredi_grafigi
from guven_grafik import guven_grafigi
from npl_grafik import npl_grafigi

kredi_grafigi()
st.divider()
npl_grafigi()
st.divider()
faiz_grafigi()
st.divider()
guven_grafigi()
