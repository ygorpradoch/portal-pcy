from collections import defaultdict
from datetime import date, timedelta
from textwrap import dedent

import streamlit as st

from lib import auth, queries
from lib.supabase_client import set_session_from_state

set_session_from_state()
auth.require_auth()

st.title("📦 Meus Pedidos")

st.markdown(
    dedent("""
        <style>
        div[class*="st-key-btn_detalhe_"] {
            display: flex !important;
            justify-content: flex-end !important;
            margin-top: -2.3rem !important;
        }
        div[class*="st-key-btn_detalhe_"] button {
            background: #ffffff !important;
            border: 0.5px solid #dee2e6 !important;
            border-radius: 6px !important;
            color: #6c757d !important;
            font-size: 11px !important;
            padding: 3px 10px !important;
            width: auto !important;
            height: auto !important;
            cursor: pointer !important;
        }
        div[class*="st-key-lista_pedidos"] [data-testid="stElementContainer"] {
            margin-bottom: 0.4rem !important;
        }
        </style>
    """).strip(),
    unsafe_allow_html=True,
)

STATUS_PAGAMENTO_OPCOES = ["Todos", "pendente", "pago", "cancelado"]
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


def _html(template: str) -> str:
    """Remove indentação e linhas vazias para o Markdown não confundir
    o HTML com um bloco de código (CommonMark trata linha em branco como
    fim de bloco HTML, e indentação residual cai na regra de code block)."""
    linhas = dedent(template).strip().splitlines()
    return "\n".join(linha for linha in linhas if linha.strip())


COR_BG_PAR = "#F0F2F6"
COR_BG_IMPAR = "#FFFFFF"
COR_TEXT_PRIMARIA = "#262730"
COR_TEXT_SECUNDARIA = "#6c757d"
COR_TEXT_TERCIARIA = "#adb5bd"
COR_BORDA_SEPARADOR = "#dee2e6"
COR_URGENTE = "#dc3545"
COR_BORDA_STATUS = {
    "pendente": "#f0ad4e",
    "pago": "#28a745",
}
CORES_PGTO = {
    "pendente": ("#fff3cd", "#856404", "🟡 Pendente"),
    "pago": ("#d1e7dd", "#0a3622", "🟢 Pago"),
    "cancelado": ("#f8d7da", "#58151c", "🔴 Cancelado"),
}
CORES_ENTREGA = {
    "pendente": ("#e2e3e5", "#41464b", "⏳ Pendente"),
    "parcial": ("#cff4fc", "#055160", "🔄 Parcial"),
    "entregue": ("#d1e7dd", "#0a3622", "✅ Entregue"),
}


def _badge_pill(texto: str, bg: str, cor: str) -> str:
    return (
        f'<span style="font-size:11px;background:{bg};color:{cor};'
        f'padding:2px 8px;border-radius:20px;white-space:nowrap;">{texto}</span>'
    )


def _dias_vencimento(pedido: dict) -> int | None:
    """Dias até o vencimento — só para pendentes com data de vencimento."""
    if pedido["status_pagamento"] != "pendente":
        return None
    venc = pedido.get("data_vencimento")
    if not venc:
        return None
    return (date.fromisoformat(venc) - date.today()).days


@st.dialog("Detalhes do Pedido")
def _dialog_detalhes(pedido: dict) -> None:
    """Dialog com itens, datas, documentos e marcar como pago."""
    numero = pedido.get("numero_pedido") or "—"
    cond = pedido.get("condominio_nome", "")
    st.markdown(f"**{numero}** — {cond}" if cond else f"**{numero}**")
    if pedido.get("data_vencimento"):
        st.caption(
            f"{_formatar_data(pedido.get('data_pedido'))} · "
            f"vence {_formatar_data(pedido['data_vencimento'])}"
        )
    else:
        st.caption(_formatar_data(pedido.get("data_pedido")))
    st.divider()

    st.subheader("Itens")
    try:
        itens = queries.listar_itens_pedido(pedido["id"])
    except RuntimeError as e:
        st.error(str(e))
        itens = []
    if itens:
        st.dataframe(
            [
                {
                    "Produto": item["produto"],
                    "Qtd": item["quantidade"],
                    "Unit.": _moeda(item["valor_unit"]),
                    "Total": _moeda(item["valor_total_item"]),
                }
                for item in itens
            ],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.caption("Nenhum item cadastrado.")
    st.write(f"**Total:** {_moeda(pedido['valor_total'])}")

    if pedido.get("data_entrega"):
        st.caption(f"Entregue em {_formatar_data(pedido['data_entrega'])}")

    st.divider()

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

    if pedido["status_pagamento"] == "pendente":
        st.divider()
        chave_flag = f"confirmar_pagamento_{pedido['id']}"
        if not st.session_state.get(chave_flag):
            if st.button(
                "✅ Marcar como pago",
                key=f"btn_pagar_{pedido['id']}",
                use_container_width=True,
            ):
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
                    use_container_width=True,
                ):
                    try:
                        queries.marcar_pedido_como_pago(pedido["id"])
                        st.session_state.pop(chave_flag, None)
                        st.success("Marcado como pago com sucesso.")
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))
                        st.session_state.pop(chave_flag, None)
            with col2:
                if st.button(
                    "✖ Cancelar",
                    key=f"btn_cancelar_{pedido['id']}",
                    use_container_width=True,
                ):
                    st.session_state.pop(chave_flag, None)
                    st.rerun()


def _render_linha_pedido(pedido: dict, i: int, mostrar_condominio: bool = False) -> None:
    """Renderiza uma linha compacta de pedido em HTML puro + botão de detalhes."""
    status_pgto = pedido["status_pagamento"]
    cor_borda = COR_BORDA_STATUS.get(status_pgto, "#6c757d")
    bg = COR_BG_PAR if i % 2 == 0 else COR_BG_IMPAR
    data_curta = _formatar_data(pedido["data_pedido"])[:-5]

    bg_pgto, cor_pgto, texto_pgto = CORES_PGTO.get(
        status_pgto, ("#e2e3e5", "#41464b", status_pgto)
    )
    badge_pgto = _badge_pill(texto_pgto, bg_pgto, cor_pgto)

    status_entrega = pedido["status_entrega"]
    bg_entrega, cor_entrega, texto_entrega = CORES_ENTREGA.get(
        status_entrega, ("#e2e3e5", "#41464b", status_entrega)
    )
    badge_entrega = _badge_pill(texto_entrega, bg_entrega, cor_entrega)

    dias = _dias_vencimento(pedido)
    badge_venc = ""
    if dias is not None:
        if dias < 0:
            badge_venc = _badge_pill(f"⚠️ Vencido há {abs(dias)} dia(s)", "#f8d7da", "#58151c")
        elif dias == 0:
            badge_venc = _badge_pill("⚠️ Vence hoje", "#f8d7da", "#58151c")
        elif dias <= 3:
            badge_venc = _badge_pill(f"⏰ Vence em {dias} dia(s)", "#fff3cd", "#856404")
    badges_html = f"{badge_pgto} {badge_entrega} {badge_venc}"

    venc_html = ""
    if dias is not None:
        cor_v = COR_URGENTE if dias <= 3 else COR_TEXT_TERCIARIA
        venc_html = (
            f'<span style="font-size:11px;color:{cor_v};">'
            f'vence {_formatar_data(pedido["data_vencimento"])}</span>'
        )
    elif status_pgto == "pago":
        venc_html = f'<span style="font-size:11px;color:{COR_TEXT_TERCIARIA};">pago</span>'

    cond_html = ""
    if mostrar_condominio:
        cond_html = (
            f'<span style="font-size:12px;color:{COR_TEXT_SECUNDARIA};">'
            f'{pedido.get("condominio_nome", "")}</span>'
        )

    html = _html(f"""
        <div style="border-left:3px solid {cor_borda};
                    padding:10px 14px;background:{bg};
                    border-bottom:0.5px solid {COR_BORDA_SEPARADOR};">
          <div style="display:flex;justify-content:space-between;
                      align-items:center;gap:8px;">
            <div style="flex:1;min-width:0;">
              <div style="display:flex;align-items:baseline;gap:6px;
                          margin-bottom:5px;flex-wrap:wrap;">
                <span style="font-size:12px;color:{COR_TEXT_TERCIARIA};">{data_curta}</span>
                <span style="font-size:13px;font-weight:500;
                             color:{COR_TEXT_PRIMARIA};">{pedido.get('numero_pedido') or '—'}</span>
                {cond_html}
              </div>
              <div style="display:flex;gap:5px;flex-wrap:wrap;">
                {badges_html}
              </div>
            </div>
            <div style="display:flex;flex-direction:column;
                        align-items:flex-end;gap:4px;flex-shrink:0;">
              <span style="font-size:13px;font-weight:500;
                           color:{COR_TEXT_PRIMARIA};">{_moeda(pedido['valor_total'])}</span>
              {venc_html}
            </div>
          </div>
        </div>
    """)
    st.markdown(html, unsafe_allow_html=True)

    if st.button("Ver detalhes ›", key=f"btn_detalhe_{pedido['id']}"):
        _dialog_detalhes(pedido)


def _render_pedidos_agrupados(pedidos: list[dict], mostrar_condominio: bool = False) -> None:
    """Agrupa pedidos por mês numa lista contínua, com um divisor por mês."""
    if not pedidos:
        st.info("Nenhum pedido encontrado para os filtros selecionados.")
        return

    grupos = defaultdict(list)
    for p in pedidos:
        grupos[p["data_pedido"][:7]].append(p)

    with st.container(key="lista_pedidos"):
        for mes_key in sorted(grupos.keys(), reverse=True):
            ano, mes_num = mes_key.split("-")
            label = f"{MESES_PT[mes_num]} {ano}"
            html = _html(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:14px 16px;">
                  <div style="height:1px;flex:1;background:{COR_BORDA_SEPARADOR};"></div>
                  <span style="font-size:18px !important;font-weight:500;color:{COR_TEXT_SECUNDARIA};
                               white-space:nowrap;padding:0 14px;">{label}</span>
                  <div style="height:1px;flex:1;background:{COR_BORDA_SEPARADOR};"></div>
                </div>
            """)
            st.markdown(html, unsafe_allow_html=True)
            for i, pedido in enumerate(grupos[mes_key]):
                _render_linha_pedido(pedido, i, mostrar_condominio)


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

    _render_pedidos_agrupados(pedidos, mostrar_condominio=True)
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

    _render_pedidos_agrupados(pedidos, mostrar_condominio=False)
