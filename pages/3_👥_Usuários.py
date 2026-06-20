import streamlit as st

from lib import auth, queries
from lib.supabase_client import set_session_from_state

set_session_from_state()
# auth.require_admin() removido: st.navigation() em streamlit_app.py já
# restringe esta página a administradores (páginas fora da lista de
# st.navigation() ficam inacessíveis). require_auth() fica como defesa
# em profundidade.
auth.require_auth()

st.title("👥 Usuários")

st.info(
    "Para criar novos usuários, use o painel do Supabase Auth. "
    "O vínculo a condomínios é feito na página Vínculos."
)

try:
    perfis = queries.listar_perfis_com_contagem()
except RuntimeError as e:
    st.error(str(e))
    perfis = []

if not perfis:
    st.write("Nenhum usuário encontrado.")

for perfil in perfis:
    col_nome, col_papel, col_total = st.columns([3, 1, 1])
    col_nome.write(perfil["nome_completo"])
    col_papel.write("👑 Admin" if perfil["is_admin"] else "👤 Cliente")
    col_total.write(f"{perfil['total_condominios']} condomínio(s)")
