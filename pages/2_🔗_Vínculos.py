import streamlit as st

from lib import auth, queries
from lib.supabase_client import set_session_from_state

set_session_from_state()
auth.require_admin()

st.title("🔗 Vínculos Cliente ↔ Condomínio")

try:
    condominios = queries.listar_condominios()
except RuntimeError as e:
    st.error(str(e))
    condominios = []

if not condominios:
    st.info("Nenhum condomínio ativo encontrado.")
    st.stop()

opcoes_condominio = {c["nome"]: c["id"] for c in condominios}
nome_selecionado = st.selectbox("Condomínio", list(opcoes_condominio.keys()))
condominio_id = opcoes_condominio[nome_selecionado]

try:
    vinculados = queries.listar_vinculos(condominio_id)
except RuntimeError as e:
    st.error(str(e))
    vinculados = []

st.subheader("Vinculados")
if not vinculados:
    st.write("Nenhum usuário vinculado a este condomínio.")
for vinculo in vinculados:
    col_nome, col_acao = st.columns([3, 1])
    col_nome.write(vinculo["nome_completo"])
    if col_acao.button("Desvincular", key=f"desvincular_{vinculo['user_id']}"):
        try:
            queries.remover_vinculo(vinculo["user_id"], condominio_id)
            st.success("Usuário desvinculado.")
            st.rerun()
        except RuntimeError as e:
            st.error(str(e))

st.subheader("Vincular novos usuários")
try:
    perfis = queries.listar_perfis()
except RuntimeError as e:
    st.error(str(e))
    perfis = []

ids_vinculados = {v["user_id"] for v in vinculados}
candidatos = {
    p["nome_completo"]: p["id"]
    for p in perfis
    if not p["is_admin"] and p["id"] not in ids_vinculados
}

selecionados = st.multiselect("Usuários disponíveis", list(candidatos.keys()))

if st.button("Vincular selecionados"):
    if not selecionados:
        st.error("Selecione ao menos um usuário.")
    else:
        try:
            for nome in selecionados:
                queries.criar_vinculo(candidatos[nome], condominio_id)
            st.success("Usuários vinculados com sucesso.")
            st.rerun()
        except RuntimeError as e:
            st.error(str(e))
