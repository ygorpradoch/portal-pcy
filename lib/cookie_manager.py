"""Instancia singleton do CookieManager (extra-streamlit-components)."""

import streamlit as st
from extra_streamlit_components import CookieManager


@st.cache_resource
def get_cookie_manager() -> CookieManager:
    return CookieManager()
