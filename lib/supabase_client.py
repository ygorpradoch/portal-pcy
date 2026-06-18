"""Criacao e gerenciamento do cliente Supabase."""

import streamlit as st
from supabase import Client, create_client

from config.settings import get_settings


@st.cache_resource
def get_supabase_client() -> Client:
    url, key = get_settings()
    return create_client(url, key)


def set_session_from_state() -> None:
    """Reaplica o JWT da sessao no cliente cacheado a cada rerun do Streamlit."""
    access_token = st.session_state.get("access_token")
    refresh_token = st.session_state.get("refresh_token")
    if access_token and refresh_token:
        get_supabase_client().auth.set_session(access_token, refresh_token)
