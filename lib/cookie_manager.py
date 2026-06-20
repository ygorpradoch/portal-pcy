"""Instancia singleton do CookieManager (extra-streamlit-components)."""

import streamlit as st
from extra_streamlit_components import CookieManager


def get_cookie_manager() -> CookieManager:
    """
    Retorna instância singleton do CookieManager via st.session_state.
    NÃO usar @st.cache_resource (CookieManager usa widget interno
    e lança CachedWidgetWarning nesse contexto).
    st.session_state é reiniciado a cada sessão do browser —
    comportamento correto para um widget component.
    """
    if "cookie_manager" not in st.session_state:
        st.session_state["cookie_manager"] = CookieManager()
    return st.session_state["cookie_manager"]
