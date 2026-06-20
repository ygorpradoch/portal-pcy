"""Autenticacao e gerenciamento de sessao de usuario."""

from datetime import datetime, timedelta, timezone

import streamlit as st

from lib.cookie_manager import get_cookie_manager
from lib.supabase_client import get_supabase_client, set_session_from_state

MENSAGENS_ERRO = {
    "Invalid login credentials": "Email ou senha incorretos",
}
MENSAGEM_ERRO_GENERICA = "Não foi possível fazer login. Tente novamente."

NOME_COOKIE = "pcy_refresh_token"


def _salvar_cookie_refresh_token(refresh_token: str) -> None:
    expira_em = datetime.now(timezone.utc) + timedelta(days=30)
    get_cookie_manager().set(
        NOME_COOKIE,
        refresh_token,
        key="set_pcy_refresh_token",
        expires_at=expira_em,
        secure=True,
        same_site="lax",
    )


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
    _salvar_cookie_refresh_token(response.session.refresh_token)
    return True, None


def logout() -> None:
    get_supabase_client().auth.sign_out()
    for chave in ("access_token", "refresh_token", "user", "perfil"):
        st.session_state.pop(chave, None)
    get_cookie_manager().delete(NOME_COOKIE, key="delete_pcy_refresh_token")
    st.rerun()


def restaurar_sessao_do_cookie() -> None:
    """Restaura a sessao a partir do refresh_token salvo em cookie, se a
    sessao em memoria (session_state) estiver vazia — caso de F5 ou nova
    aba. Sem cookie ou com cookie invalido, segue para a tela de login."""
    if st.session_state.get("refresh_token"):
        return

    cookies = get_cookie_manager().get_all(key="get_all_cookies")
    refresh_token = cookies.get(NOME_COOKIE) if cookies else None
    if not refresh_token:
        return

    client = get_supabase_client()
    try:
        response = client.auth.refresh_session(refresh_token)
    except Exception:
        get_cookie_manager().delete(NOME_COOKIE, key="delete_pcy_refresh_token")
        return

    st.session_state["access_token"] = response.session.access_token
    st.session_state["refresh_token"] = response.session.refresh_token
    st.session_state["user"] = response.user
    set_session_from_state()
    # Supabase rotaciona o refresh token a cada refresh_session(); regrava
    # o cookie com o valor novo, senao o proximo F5 usaria um token ja
    # invalidado.
    _salvar_cookie_refresh_token(response.session.refresh_token)


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
