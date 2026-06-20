import streamlit as st

from lib import auth, queries
from lib.supabase_client import set_session_from_state

set_session_from_state()
# auth.require_admin() removido: st.navigation() em streamlit_app.py já
# restringe esta página a administradores (páginas fora da lista de
# st.navigation() ficam inacessíveis). require_auth() fica como defesa
# em profundidade.
auth.require_auth()

st.title("🏢 Condomínios")

mostrar_inativos = st.toggle("Mostrar inativos", value=False)


@st.dialog("Novo condomínio")
def dialog_novo_condominio():
    nome = st.text_input("Nome *")
    cnpj = st.text_input("CNPJ")
    endereco = st.text_input("Endereço")
    if st.button("Criar"):
        if not nome:
            st.error("Nome é obrigatório.")
            return
        try:
            queries.criar_condominio(nome, cnpj or None, endereco or None)
            st.success("Condomínio criado com sucesso.")
            st.rerun()
        except RuntimeError as e:
            st.error(str(e))


@st.dialog("Editar condomínio")
def dialog_editar_condominio(condominio: dict):
    nome = st.text_input("Nome *", value=condominio["nome"])
    cnpj = st.text_input("CNPJ", value=condominio.get("cnpj") or "")
    endereco = st.text_input("Endereço", value=condominio.get("endereco") or "")
    if st.button("Salvar"):
        if not nome:
            st.error("Nome é obrigatório.")
            return
        try:
            queries.atualizar_condominio(
                condominio["id"], nome, cnpj or None, endereco or None
            )
            st.success("Condomínio atualizado com sucesso.")
            st.rerun()
        except RuntimeError as e:
            st.error(str(e))


if st.button("+ Novo condomínio"):
    dialog_novo_condominio()

try:
    condominios = queries.listar_condominios(incluir_inativos=mostrar_inativos)
except RuntimeError as e:
    st.error(str(e))
    condominios = []

if not condominios:
    st.info("Nenhum condomínio encontrado.")

for condominio in condominios:
    col_nome, col_cnpj, col_endereco, col_status, col_editar, col_acao = st.columns(
        [2, 2, 3, 1, 1, 1]
    )
    col_nome.write(condominio["nome"])
    col_cnpj.write(condominio.get("cnpj") or "—")
    col_endereco.write(condominio.get("endereco") or "—")
    col_status.write("Ativo" if condominio["ativo"] else "Inativo")

    if col_editar.button("✏️ Editar", key=f"editar_{condominio['id']}"):
        dialog_editar_condominio(condominio)

    flag_confirmacao = f"confirmar_desativacao_{condominio['id']}"
    if condominio["ativo"]:
        if st.session_state.get(flag_confirmacao):
            if col_acao.button("Confirmar?", key=f"confirmar_{condominio['id']}"):
                try:
                    queries.desativar_condominio(condominio["id"])
                    st.session_state.pop(flag_confirmacao, None)
                    st.success("Condomínio desativado.")
                    st.rerun()
                except RuntimeError as e:
                    st.error(str(e))
        else:
            if col_acao.button("🚫 Desativar", key=f"desativar_{condominio['id']}"):
                st.session_state[flag_confirmacao] = True
                st.rerun()
    else:
        if col_acao.button("✅ Reativar", key=f"reativar_{condominio['id']}"):
            try:
                queries.reativar_condominio(condominio["id"])
                st.success("Condomínio reativado.")
                st.rerun()
            except RuntimeError as e:
                st.error(str(e))
