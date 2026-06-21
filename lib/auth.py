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


def aplicar_cookie_pendente() -> bool:
    """Aplica no topo do script as operacoes de cookie adiadas por
    login()/logout().

    Por que adiar: o componente de cookie (extra-streamlit-components) so
    grava/apaga o cookie no browser quando seu iframe e renderizado e
    PERMANECE montado no DOM ate completar o round-trip. login()/logout()
    chamam st.rerun() logo em seguida; se a operacao de cookie fosse feita
    ali, o rerun desmontaria o iframe antes dele rodar e o cookie nunca
    seria persistido. Chamando aqui no topo, o script segue e renderiza a
    app inteira sem rerun imediato, dando tempo do iframe concluir.

    Retorna True se um logout (remocao) foi processado, para o chamador
    pular a restauracao da sessao neste run (senao ele releria o cookie
    ainda-nao-apagado e re-logaria)."""
    if st.session_state.pop("pending_cookie_delete", False):
        get_cookie_manager().delete(NOME_COOKIE, key="delete_pcy_refresh_token")
        return True

    token = st.session_state.pop("pending_cookie_save", None)
    if token:
        _salvar_cookie_refresh_token(token)
    return False


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
    # Adia a gravacao do cookie para o topo do proximo run (ver
    # aplicar_cookie_pendente). Gravar aqui nao persiste: o st.rerun() do
    # login_form desmonta o iframe do componente antes dele escrever.
    st.session_state["pending_cookie_save"] = response.session.refresh_token
    return True, None


def logout() -> None:
    get_supabase_client().auth.sign_out()
    for chave in ("access_token", "refresh_token", "user", "perfil"):
        st.session_state.pop(chave, None)
    # Adia a remocao do cookie para o topo do proximo run, pela mesma razao
    # do login: senao o st.rerun() abaixo desmonta o iframe antes de apagar.
    st.session_state["pending_cookie_delete"] = True
    st.rerun()


def restaurar_sessao_do_cookie() -> None:
    """Restaura a sessao a partir do refresh_token salvo em cookie quando a
    sessao em memoria (session_state) esta vazia — caso de F5 ou nova aba.

    Usa get_all() (nao get()): get() so le o dict interno do CookieManager,
    populado uma unica vez no __init__; get_all() reconsulta o componente a
    cada run, deixando o browser entregar os cookies reais (via rerun
    automatico da lib) quando o round-trip completa."""
    if st.session_state.get("refresh_token"):
        return

    cm = get_cookie_manager()
    cookies = cm.get_all(key="get_all_cookies")
    refresh_token = cookies.get(NOME_COOKIE) if cookies else None

    # DEBUG TEMPORÁRIO — remover após confirmar a persistência
    st.write(f"[DEBUG] cookies do browser: {repr(cookies)}")
    st.write(f"[DEBUG] pcy_refresh_token: {repr(refresh_token)}")

    if not refresh_token:
        return

    try:
        response = get_supabase_client().auth.refresh_session(refresh_token)
    except Exception as e:
        st.write(f"[DEBUG] refresh_session falhou: {repr(e)}")
        cm.delete(NOME_COOKIE, key="delete_pcy_refresh_token")
        return

    st.session_state["access_token"] = response.session.access_token
    st.session_state["refresh_token"] = response.session.refresh_token
    st.session_state["user"] = response.user
    set_session_from_state()
    # Supabase rotaciona o refresh token a cada refresh_session(); regrava o
    # cookie com o valor novo para o proximo F5 nao usar um token invalido.
    # (set() aqui persiste porque o script segue renderizando a app.)
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
