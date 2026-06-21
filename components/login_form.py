"""Formulario de login do Portal PCY."""

import streamlit as st

from lib import auth


def render_login_form() -> None:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        _, col_logo, _ = st.columns([2, 1, 2])
        with col_logo:
            st.image("assets/pcy-icon.png", use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>Portal PCY</h2>", unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("Email")
            senha = st.text_input("Senha", type="password")
            enviado = st.form_submit_button("Entrar")

        if enviado:
            sucesso, mensagem = auth.login(email, senha)
            if sucesso:
                st.rerun()
            else:
                st.error(mensagem)
