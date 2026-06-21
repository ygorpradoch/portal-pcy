import streamlit as st
from PIL import Image

from components.login_form import render_login_form
from lib import auth
from lib.cookie_manager import get_cookie_manager
from lib.supabase_client import set_session_from_state

icon = Image.open("assets/pcy-icon.png")
st.set_page_config(
    page_title="Portal PCY",
    page_icon=icon,
    layout="wide",
)

st.markdown("""
<style>
#MainMenu {display: none !important;}
footer {display: none !important;}
header {display: none !important;}
[data-testid="manage-app-button"] {display: none !important;}
[data-testid="stToolbarActions"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
[data-testid="stDeployButton"] {display: none !important;}
div[class*="ProfileIcon"] {display: none !important;}
div[class*="AccountMenu"] {display: none !important;}
</style>
""", unsafe_allow_html=True)

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
    st.title("Portal de Pedidos, Notas e Boletos")
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

st.sidebar.image("assets/pcy-logo.png", use_container_width=True)
st.sidebar.divider()

pg = st.navigation(paginas_admin if user["is_admin"] else paginas_cliente)
pg.run()

st.sidebar.divider()
st.sidebar.write(user["nome_completo"])
badge_texto = "👑 Admin" if user["is_admin"] else "👤 Cliente"
st.sidebar.caption(badge_texto)
if st.sidebar.button("Sair da conta", use_container_width=True):
    auth.logout()
