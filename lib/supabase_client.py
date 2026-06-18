"""Criacao e gerenciamento do cliente Supabase."""

import streamlit as st
from supabase import Client, create_client

from config.settings import get_settings


@st.cache_resource
def get_supabase_client() -> Client:
    url, key = get_settings()
    return create_client(url, key)
