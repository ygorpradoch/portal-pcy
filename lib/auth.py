"""Autenticacao e gerenciamento de sessao de usuario."""

import streamlit as st

from lib.supabase_client import get_supabase_client, set_session_from_state

MENSAGENS_ERRO = {
    "Invalid login credentials": "Email ou senha incorretos",
}
MENSAGEM_ERRO_GENERICA = "Não foi possível fazer login. Tente novamente."


def login(email: str, senha: str) -> tuple[bool, str | None]:
    client = get_supabase_client()
    try:
        response = client.auth.sign_in_with_password(
            {"email": email, "password": senha}
        )
    except Exception as e:
        return False, MENSAGENS_ERRO.get(str(e), MENSAGEM_ERRO_GENERICA)

    st.session_state["access_token"] = response.session.access_token
    st.session_state["refresh_token"] = response.session.refresh_token
    st.session_state["user"] = response.user
    return True, None


def logout() -> None:
    get_supabase_client().auth.sign_out()
    for chave in ("access_token", "refresh_token", "user", "perfil"):
        st.session_state.pop(chave, None)
    st.rerun()


def get_current_user() -> dict | None:
    user = st.session_state.get("user")
    if user is None:
        return None

    if "perfil" in st.session_state:
        return st.session_state["perfil"]

    set_session_from_state()
    client = get_supabase_client()
    resultado = (
        client.table("perfis").select("*").eq("id", user.id).single().execute()
    )
    perfil = {
        "id": resultado.data["id"],
        "email": user.email,
        "nome_completo": resultado.data["nome_completo"],
        "is_admin": resultado.data["is_admin"],
    }
    st.session_state["perfil"] = perfil
    return perfil


def require_auth() -> None:
    if get_current_user() is None:
        st.stop()


def require_admin() -> None:
    user = get_current_user()
    if user is None or not user["is_admin"]:
        st.error("Acesso restrito a administradores")
        st.stop()
