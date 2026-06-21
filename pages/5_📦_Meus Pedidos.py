from collections import defaultdict
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
MESES_PT = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Março",
    "04": "Abril", "05": "Maio", "06": "Junho",
    "07": "Julho", "08": "Agosto", "09": "Setembro",
    "10": "Outubro", "11": "Novembro", "12": "Dezembro",
}


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


def _badge_vencimento(pedido: dict) -> str | None:
    """Badge de urgência de cobrança — só para pendentes com vencimento."""
    if pedido["status_pagamento"] != "pendente":
        return None
    venc = pedido.get("data_vencimento")
    if not venc:
        return None
    dias = (date.fromisoformat(venc) - date.today()).days
    if dias < 0:
        return _badge(f"⚠️ Vencido há {abs(dias)} dia(s)", "#dc3545")
    if dias == 0:
        return _badge("⚠️ Vence hoje", "#dc3545")
    if dias <= 3:
        return _badge(f"⏰ Vence em {dias} dia(s)", "#f0ad4e")
    return None


def _legenda_data(pedido: dict) -> str:
    legenda = f"Pedido em {_formatar_data(pedido.get('data_pedido'))}"
    if pedido["status_pagamento"] == "pendente" and pedido.get("data_vencimento"):
        legenda += f" · vence {_formatar_data(pedido['data_vencimento'])}"
    elif pedido.get("data_entrega"):
        legenda += f" · entregue {_formatar_data(pedido['data_entrega'])}"
    return legenda


def _render_card_pedido(pedido: dict, mostrar_condominio: bool = False) -> None:
    """Renderiza um card de pedido dentro de st.container(border=True)."""
    with st.container(border=True):
        col_info, col_valor = st.columns([3, 2])
        with col_info:
            st.markdown(f"**{pedido.get('numero_pedido') or '—'}**")
            if mostrar_condominio:
                st.caption(pedido.get("condominio_nome", ""))
            st.caption(_legenda_data(pedido))
        with col_valor:
            st.markdown(
                f"<div style='text-align:right;font-size:1.5em;font-weight:700'>"
                f"{_moeda(pedido['valor_total'])}</div>",
                unsafe_allow_html=True,
            )

        badges = [
            _badge(*BADGES_PAGAMENTO.get(
                pedido["status_pagamento"],
                (pedido["status_pagamento"], "#6c757d"),
            )),
            _badge(*BADGES_ENTREGA.get(
                pedido["status_entrega"],
                (pedido["status_entrega"], "#6c757d"),
            )),
        ]
        venc = _badge_vencimento(pedido)
        if venc:
            badges.append(venc)
        st.markdown(" ".join(badges), unsafe_allow_html=True)

        if pedido["status_pagamento"] == "pendente":
            chave_flag = f"confirmar_pagamento_{pedido['id']}"
            if not st.session_state.get(chave_flag):
                if st.button("✅ Marcar como pago", key=f"btn_pagar_{pedido['id']}"):
                    st.session_state[chave_flag] = True
                    st.rerun()
            else:
                st.warning("Confirmar pagamento? Esta ação não pode ser desfeita.")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✔ Confirmar",
                        key=f"btn_confirmar_{pedido['id']}",
                        type="primary",
                    ):
                        try:
                            queries.marcar_pedido_como_pago(pedido["id"])
                            st.session_state.pop(chave_flag, None)
                            st.success("Pedido marcado como pago com sucesso.")
                            st.rerun()
                        except RuntimeError as e:
                            st.error(str(e))
                            st.session_state.pop(chave_flag, None)
                with col2:
                    if st.button("✖ Cancelar", key=f"btn_cancelar_{pedido['id']}"):
                        st.session_state.pop(chave_flag, None)
                        st.rerun()

        with st.expander("Ver itens e documentos", expanded=False):
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
                st.write(
                    f"**Data de entrega:** {_formatar_data(pedido['data_entrega'])}"
                )

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

st.session_state.setdefault("filtro_status", "Todos")
st.session_state.setdefault("filtro_data_inicio", date.today() - timedelta(days=90))
st.session_state.setdefault("filtro_data_fim", date.today())
st.session_state.setdefault("filtro_valor_min", None)
st.session_state.setdefault("filtro_valor_max", None)

col_busca, col_filtros = st.columns([3, 1])

with col_busca:
    if len(condominios) == 1:
        condominio_id = condominios[0]["condominio_id"]
        st.caption(f"Condomínio: {condominios[0]['nome']}")
    else:
        opcoes_condominio = {c["nome"]: c["condominio_id"] for c in condominios}
        opcoes = ["Todos os condomínios"] + list(opcoes_condominio.keys())
        nome_condominio = st.selectbox(
            "Condomínio",
            opcoes,
            index=0,
            placeholder="Pesquisar condomínio…",
            label_visibility="collapsed",
            key="sel_condominio",
        )
        if nome_condominio == "Todos os condomínios":
            condominio_id = None
        else:
            condominio_id = opcoes_condominio[nome_condominio]

with col_filtros:
    with st.popover("🔍 Filtros", use_container_width=True):
        st.selectbox(
            "Status de pagamento", STATUS_PAGAMENTO_OPCOES, key="filtro_status"
        )
        col_data_ini, col_data_fim = st.columns(2)
        col_data_ini.date_input("De", key="filtro_data_inicio")
        col_data_fim.date_input("Até", key="filtro_data_fim")
        col_valor_min, col_valor_max = st.columns(2)
        col_valor_min.number_input(
            "Valor mínimo", key="filtro_valor_min", min_value=0.0, step=10.0,
            format="%.2f",
        )
        col_valor_max.number_input(
            "Valor máximo", key="filtro_valor_max", min_value=0.0, step=10.0,
            format="%.2f",
        )
        col_aplicar, col_limpar = st.columns(2)
        if col_aplicar.button("Aplicar filtros", type="primary"):
            st.rerun()
        if col_limpar.button("Limpar filtros"):
            for chave in FILTROS_CHAVES:
                st.session_state.pop(chave, None)
            st.rerun()

# --- Métrica: total em aberto (todos os pendentes, ignora filtros) ---
# Modo "todos os condomínios" não mostra a métrica: somar valores de
# condomínios diferentes seria confuso sem o contexto de cada um.

if condominio_id is not None:
    try:
        todos = queries.listar_pedidos_do_cliente(condominio_id)
        total_em_aberto = sum(
            p["valor_total"] for p in todos if p["status_pagamento"] == "pendente"
        )
    except RuntimeError:
        total_em_aberto = 0.0

    st.metric("Em aberto", _moeda(total_em_aberto))

# --- Filtros aplicados à listagem ---

status_filtro = (
    None
    if st.session_state["filtro_status"] == "Todos"
    else st.session_state["filtro_status"]
)
data_inicio = st.session_state["filtro_data_inicio"]
data_fim = st.session_state["filtro_data_fim"]
data_inicio_iso = data_inicio.isoformat() if data_inicio else None
data_fim_iso = data_fim.isoformat() if data_fim else None
valor_min = st.session_state["filtro_valor_min"]
valor_max = st.session_state["filtro_valor_max"]

# --- Listagem de pedidos ---

if condominio_id is None:
    # Modo "Todos os condomínios": busca tudo e aplica os mesmos filtros
    # em Python (sem nova query ao banco), depois agrupa por mês.
    try:
        pedidos = queries.listar_todos_pedidos_do_cliente()
    except RuntimeError as e:
        st.error(str(e))
        pedidos = []

    if status_filtro:
        pedidos = [p for p in pedidos if p["status_pagamento"] == status_filtro]
    if data_inicio_iso:
        pedidos = [
            p for p in pedidos
            if p.get("data_pedido") and p["data_pedido"] >= data_inicio_iso
        ]
    if data_fim_iso:
        pedidos = [
            p for p in pedidos
            if p.get("data_pedido") and p["data_pedido"] <= data_fim_iso
        ]
    if valor_min is not None:
        pedidos = [p for p in pedidos if p["valor_total"] >= valor_min]
    if valor_max is not None:
        pedidos = [p for p in pedidos if p["valor_total"] <= valor_max]

    if not pedidos:
        st.info("Nenhum pedido encontrado para os filtros selecionados.")

    grupos = defaultdict(list)
    for p in pedidos:
        mes_key = p["data_pedido"][:7]
        grupos[mes_key].append(p)

    for mes_key in sorted(grupos.keys(), reverse=True):
        ano, mes_num = mes_key.split("-")
        label = f"{MESES_PT[mes_num]} {ano}"
        st.markdown(
            f"<h3 style='text-align:center; color:#6c757d; "
            f"margin: 1.5rem 0 0.5rem;'>{label}</h3>",
            unsafe_allow_html=True,
        )
        st.divider()
        for pedido in grupos[mes_key]:
            _render_card_pedido(pedido, mostrar_condominio=True)
else:
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

    grupos = defaultdict(list)
    for p in pedidos:
        mes_key = p["data_pedido"][:7]
        grupos[mes_key].append(p)

    for mes_key in sorted(grupos.keys(), reverse=True):
        ano, mes_num = mes_key.split("-")
        label = f"{MESES_PT[mes_num]} {ano}"
        st.markdown(
            f"<h3 style='text-align:center; color:#6c757d; "
            f"margin: 1.5rem 0 0.5rem;'>{label}</h3>",
            unsafe_allow_html=True,
        )
        st.divider()
        for pedido in grupos[mes_key]:
            _render_card_pedido(pedido, mostrar_condominio=False)
