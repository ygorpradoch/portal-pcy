import streamlit as st

from components.login_form import render_login_form
from lib import auth
from lib.cookie_manager import get_cookie_manager
from lib.supabase_client import set_session_from_state

st.set_page_config(page_title="Portal PCY", page_icon="📦")

get_cookie_manager()  # monta o componente de cookie no DOM

# Aplica escrita/remoção de cookie adiada por login()/logout(). Precisa rodar
# no topo, num run que segue renderizando a app, para o iframe persistir.
fez_logout = auth.aplicar_cookie_pendente()

set_session_from_state()
if not fez_logout:
    auth.restaurar_sessao_do_cookie()

user = auth.get_current_user()

if user is None:
    render_login_form()
    st.stop()


def _pagina_inicio() -> None:
    st.title("Portal PCY — Notas e Boletos")
    st.write(f"Bem-vindo, {user['nome_completo']}")
    if user["is_admin"]:
        st.info("Use o menu lateral para gerenciar condomínios, vínculos e usuários.")
    else:
        st.info("Use o menu lateral para acessar seus pedidos.")


paginas_admin = [
    st.Page(_pagina_inicio, title="Início", icon="🏠", default=True),
    st.Page("pages/1_🏢_Condomínios.py", title="Condomínios", icon="🏢"),
    st.Page("pages/2_🔗_Vínculos.py", title="Vínculos", icon="🔗"),
    st.Page("pages/3_👥_Usuários.py", title="Usuários", icon="👥"),
    st.Page("pages/4_📋_Pedidos.py", title="Pedidos", icon="📋"),
]
paginas_cliente = [
    st.Page(_pagina_inicio, title="Início", icon="🏠", default=True),
    st.Page("pages/5_📦_Meus Pedidos.py", title="Meus Pedidos", icon="📦"),
]

with st.sidebar:
    st.write(user["nome_completo"])
    st.write("👑 Admin" if user["is_admin"] else "👤 Cliente")
    if st.button("Logout"):
        auth.logout()

pg = st.navigation(paginas_admin if user["is_admin"] else paginas_cliente)
pg.run()
