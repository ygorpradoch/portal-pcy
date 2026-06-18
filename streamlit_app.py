import streamlit as st

from lib.supabase_client import get_supabase_client

st.set_page_config(page_title="Portal PCY", page_icon="🟢")

st.title("Portal PCY — Notas e Boletos")

st.markdown(
    "O Portal PCY centraliza o acesso a notas fiscais e boletos, permitindo "
    "que clientes e equipe interna consultem, emitam e acompanhem documentos "
    "financeiros em um único lugar, de forma segura e organizada."
)

if st.button("Testar conexão Supabase"):
    try:
        client = get_supabase_client()
        client.auth.get_session()
        st.success("Conexão com Supabase OK")
    except Exception as e:
        st.error(f"Falha na conexão: {e}")

st.markdown("---")
st.markdown("[Repositório no GitHub](https://github.com/ygorpradoch/portal-pcy)")
