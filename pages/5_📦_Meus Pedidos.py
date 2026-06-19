from datetime import date, timedelta

import streamlit as st

from lib import auth, queries
from lib.supabase_client import set_session_from_state

set_session_from_state()
auth.require_auth()

st.title("📦 Meus Pedidos")

STATUS_PAGAMENTO_OPCOES = ["Todos", "pendente", "pago", "cancelado"]
BADGES_PAGAMENTO = {
    "pendente": ("🟡 Pendente", "#f0ad4e"),
    "pago": ("🟢 Pago", "#28a745"),
    "cancelado": ("🔴 Cancelado", "#dc3545"),
}
BADGES_ENTREGA = {
    "pendente": ("⏳ Pendente", "#6c757d"),
    "parcial": ("🔄 Parcial", "#17a2b8"),
    "entregue": ("✅ Entregue", "#28a745"),
}
FILTROS_CHAVES = (
    "filtro_status",
    "filtro_data_inicio",
    "filtro_data_fim",
    "filtro_valor_min",
    "filtro_valor_max",
)


def _badge(texto: str, cor: str) -> str:
    return (
        f"<span style='background-color:{cor};color:white;padding:2px 10px;"
        f"border-radius:10px;font-size:0.85em;white-space:nowrap'>{texto}</span>"
    )


def _moeda(valor: float | None) -> str:
    if valor is None:
        return "—"
    texto = f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def _formatar_data(data_str: str | None) -> str:
    if not data_str:
        return "—"
    return date.fromisoformat(data_str).strftime("%d/%m/%Y")


def _baixar_documento(label: str, path: str) -> None:
    try:
        url = queries.gerar_url_documento(path)
        st.link_button(label, url)
    except RuntimeError as e:
        st.error(str(e))


# --- Seleção de condomínio ---

try:
    condominios = queries.listar_condominios_do_usuario_atual()
except RuntimeError as e:
    st.error(str(e))
    st.stop()

if not condominios:
    st.warning(
        "Nenhum condomínio vinculado à sua conta. Entre em contato com a PCY."
    )
    st.stop()

if len(condominios) == 1:
    condominio_id = condominios[0]["condominio_id"]
    st.caption(f"Condomínio: {condominios[0]['nome']}")
else:
    opcoes_condominio = {c["nome"]: c["condominio_id"] for c in condominios}
    nome_condominio = st.selectbox("Condomínio", list(opcoes_condominio.keys()))
    condominio_id = opcoes_condominio[nome_condominio]

# --- Filtros ---

st.session_state.setdefault("filtro_status", "Todos")
st.session_state.setdefault("filtro_data_inicio", date.today() - timedelta(days=90))
st.session_state.setdefault("filtro_data_fim", date.today())
st.session_state.setdefault("filtro_valor_min", None)
st.session_state.setdefault("filtro_valor_max", None)

with st.expander("🔍 Filtros", expanded=False):
    st.selectbox("Status de pagamento", STATUS_PAGAMENTO_OPCOES, key="filtro_status")

    col_data_ini, col_data_fim = st.columns(2)
    col_data_ini.date_input("De", key="filtro_data_inicio")
    col_data_fim.date_input("Até", key="filtro_data_fim")

    col_valor_min, col_valor_max = st.columns(2)
    col_valor_min.number_input(
        "Valor mínimo", key="filtro_valor_min", min_value=0.0, step=10.0, format="%.2f"
    )
    col_valor_max.number_input(
        "Valor máximo", key="filtro_valor_max", min_value=0.0, step=10.0, format="%.2f"
    )

    col_aplicar, col_limpar = st.columns(2)
    if col_aplicar.button("Aplicar filtros", type="primary"):
        st.rerun()
    if col_limpar.button("Limpar filtros"):
        for chave in FILTROS_CHAVES:
            st.session_state.pop(chave, None)
        st.rerun()

status_filtro = (
    None if st.session_state["filtro_status"] == "Todos" else st.session_state["filtro_status"]
)
data_inicio = st.session_state["filtro_data_inicio"]
data_fim = st.session_state["filtro_data_fim"]
data_inicio_iso = data_inicio.isoformat() if data_inicio else None
data_fim_iso = data_fim.isoformat() if data_fim else None
valor_min = st.session_state["filtro_valor_min"]
valor_max = st.session_state["filtro_valor_max"]

# --- Listagem de pedidos ---

try:
    pedidos = queries.listar_pedidos_do_cliente(
        condominio_id,
        status_pagamento=status_filtro,
        data_inicio=data_inicio_iso,
        data_fim=data_fim_iso,
        valor_min=valor_min,
        valor_max=valor_max,
    )
except RuntimeError as e:
    st.error(str(e))
    pedidos = []

if not pedidos:
    st.info("Nenhum pedido encontrado para os filtros selecionados.")

for pedido in pedidos:
    cols = st.columns([2, 1.5, 2, 2, 2])
    cols[0].write(f"**{pedido.get('numero_pedido') or '—'}**")
    cols[1].write(_formatar_data(pedido.get("data_pedido")))
    cols[2].write(_moeda(pedido["valor_total"]))

    texto_pgto, cor_pgto = BADGES_PAGAMENTO.get(
        pedido["status_pagamento"], (pedido["status_pagamento"], "#6c757d")
    )
    cols[3].markdown(_badge(texto_pgto, cor_pgto), unsafe_allow_html=True)

    texto_entrega, cor_entrega = BADGES_ENTREGA.get(
        pedido["status_entrega"], (pedido["status_entrega"], "#6c757d")
    )
    cols[4].markdown(_badge(texto_entrega, cor_entrega), unsafe_allow_html=True)

    with st.expander(
        f"📋 Detalhes — {pedido.get('numero_pedido') or pedido['id']}", expanded=False
    ):
        st.subheader("Itens do pedido")
        try:
            itens = queries.listar_itens_pedido(pedido["id"])
        except RuntimeError as e:
            st.error(str(e))
            itens = []

        if itens:
            tabela = [
                {
                    "Produto": item["produto"],
                    "Quantidade": item["quantidade"],
                    "Valor Unit.": _moeda(item["valor_unit"]),
                    "Total Item": _moeda(item["valor_total_item"]),
                }
                for item in itens
            ]
            st.dataframe(tabela, hide_index=True, use_container_width=True)
        else:
            st.caption("Nenhum item cadastrado.")
        st.write(f"**Total do pedido:** {_moeda(pedido['valor_total'])}")

        st.subheader("Datas")
        st.write(f"**Data do pedido:** {_formatar_data(pedido.get('data_pedido'))}")
        st.write(
            f"**Data de vencimento:** {_formatar_data(pedido.get('data_vencimento'))}"
        )
        if pedido.get("data_entrega"):
            st.write(f"**Data de entrega:** {_formatar_data(pedido['data_entrega'])}")

        st.subheader("Documentos")
        tem_documento = False
        if pedido.get("nota_fiscal_path"):
            tem_documento = True
            _baixar_documento("⬇️ Baixar Nota Fiscal", pedido["nota_fiscal_path"])
        if pedido.get("boleto_path"):
            tem_documento = True
            _baixar_documento("⬇️ Baixar Boleto", pedido["boleto_path"])
        if pedido.get("linha_digitavel"):
            tem_documento = True
            st.code(pedido["linha_digitavel"])
            st.caption("Copie a linha digitável para pagar o boleto")
        if not tem_documento:
            st.caption("Documentos não disponíveis ainda.")

    st.divider()
