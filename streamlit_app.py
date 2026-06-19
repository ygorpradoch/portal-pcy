import streamlit as st

from components.login_form import render_login_form
from lib import auth
from lib.supabase_client import set_session_from_state

st.set_page_config(page_title="Portal PCY", page_icon="📦")

set_session_from_state()

user = auth.get_current_user()

if user is None:
    render_login_form()
    st.stop()

with st.sidebar:
    st.write(user["nome_completo"])
    st.write("👑 Admin" if user["is_admin"] else "👤 Cliente")
    if st.button("Logout"):
        auth.logout()

st.title("Portal PCY — Notas e Boletos")
st.write(f"Bem-vindo, {user['nome_completo']}")

if user["is_admin"]:
    st.info("Use o menu lateral para gerenciar condomínios, vínculos e usuários.")
else:
    st.info("Use o menu lateral para acessar seus pedidos.")
