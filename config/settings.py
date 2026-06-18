import logging
import os

logger = logging.getLogger(__name__)


def get_settings():
    """Retorna (supabase_url, supabase_anon_key) de st.secrets ou variaveis de ambiente."""
    url = ""
    key = ""

    try:
        import streamlit as st

        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_ANON_KEY", "")
    except Exception:
        pass

    if not url:
        url = os.environ.get("SUPABASE_URL", "")
    if not key:
        key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not url:
        logger.warning("SUPABASE_URL nao configurado")
    if not key:
        logger.warning("SUPABASE_ANON_KEY nao configurado")

    return url, key
