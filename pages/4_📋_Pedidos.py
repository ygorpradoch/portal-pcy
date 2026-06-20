import uuid
from datetime import date

import streamlit as st

from lib import auth, queries
from lib.supabase_client import set_session_from_state

set_session_from_state()
# auth.require_admin() removido: st.navigation() em streamlit_app.py já
# restringe esta página a administradores (páginas fora da lista de
# st.navigation() ficam inacessíveis). require_auth() fica como defesa
# em profundidade.
auth.require_auth()

st.title("📋 Pedidos")

STATUS_PAGAMENTO = ["pendente", "pago", "cancelado"]
STATUS_ENTREGA = ["pendente", "parcial", "entregue"]


# --- Helpers de formulário de itens ---


def _novo_item() -> dict:
    return {"_uid": uuid.uuid4().hex, "produto": "", "quantidade": 1.0, "valor_unit": 0.0}


def _add_item(state_key: str) -> None:
    # callback on_click: muta o estado sem st.rerun(), assim o dialog nao fecha
    st.session_state[state_key].append(_novo_item())


def _remove_item(state_key: str, uid: str) -> None:
    st.session_state[state_key] = [
        it for it in st.session_state[state_key] if it["_uid"] != uid
    ]


def _limpar_itens_form(state_key: str) -> None:
    for k in list(st.session_state.keys()):
        if k.startswith(state_key):
            del st.session_state[k]


def _to_date(valor: str | None) -> date | None:
    return date.fromisoformat(valor) if valor else None


def _render_itens(state_key: str, itens_iniciais: list[dict] | None = None) -> list[dict]:
    """Renderiza as linhas de itens e devolve os valores atuais coletados."""
    if state_key not in st.session_state:
        if itens_iniciais:
            st.session_state[state_key] = [
                {
                    "_uid": uuid.uuid4().hex,
                    "produto": i["produto"],
                    "quantidade": float(i["quantidade"]),
                    "valor_unit": float(i["valor_unit"]),
                }
                for i in itens_iniciais
            ]
        else:
            st.session_state[state_key] = [_novo_item()]

    h_prod, h_qtd, h_val, h_rem = st.columns([3, 2, 2, 1])
    h_prod.caption("Produto")
    h_qtd.caption("Quantidade")
    h_val.caption("Valor unit.")
    h_rem.caption("")

    coletados = []
    for item in st.session_state[state_key]:
        uid = item["_uid"]
        prod_key = f"{state_key}_prod_{uid}"
        qtd_key = f"{state_key}_qtd_{uid}"
        val_key = f"{state_key}_val_{uid}"
        st.session_state.setdefault(prod_key, item["produto"])
        st.session_state.setdefault(qtd_key, item["quantidade"])
        st.session_state.setdefault(val_key, item["valor_unit"])

        c_prod, c_qtd, c_val, c_rem = st.columns([3, 2, 2, 1])
        produto = c_prod.text_input(
            "Produto", key=prod_key, label_visibility="collapsed", placeholder="Produto"
        )
        quantidade = c_qtd.number_input(
            "Quantidade",
            key=qtd_key,
            min_value=0.0,
            step=1.0,
            label_visibility="collapsed",
        )
        valor_unit = c_val.number_input(
            "Valor unit.",
            key=val_key,
            min_value=0.0,
            step=0.01,
            format="%.2f",
            label_visibility="collapsed",
        )
        c_rem.button(
            "✕",
            key=f"{state_key}_rem_{uid}",
            on_click=_remove_item,
            args=(state_key, uid),
        )

        coletados.append(
            {"produto": produto, "quantidade": quantidade, "valor_unit": valor_unit}
        )

    st.button(
        "+ Adicionar item",
        key=f"{state_key}_add",
        on_click=_add_item,
        args=(state_key,),
    )

    return coletados


def _itens_validos(coletados: list[dict]) -> list[dict]:
    return [
        i for i in coletados if i["produto"].strip() and i["quantidade"] > 0
    ]


def _nome_arquivo(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _link_documento(label: str, path: str) -> None:
    try:
        url = queries.gerar_url_documento(path)
        st.link_button(label, url)
    except RuntimeError as e:
        st.error(str(e))


# --- Dialogs ---


@st.dialog("Novo pedido", width="large")
def dialog_novo_pedido(condominios: list[dict]):
    state_key = "itens_form_novo"
    opcoes = {c["nome"]: c["id"] for c in condominios}

    st.subheader("Dados do pedido")
    nome_cond = st.selectbox(
        "Condomínio *", list(opcoes.keys()), index=None, placeholder="Selecione..."
    )
    numero = st.text_input("Número do pedido *")
    data_pedido = st.date_input("Data do pedido", value=date.today())
    data_venc = st.date_input("Data de vencimento", value=date.today())

    st.subheader("Itens")
    itens = _render_itens(state_key)
    total = sum(i["quantidade"] * i["valor_unit"] for i in itens)
    st.metric("Valor total", f"R$ {total:.2f}")

    st.subheader("Documentos")
    nf_file = st.file_uploader("Nota Fiscal (PDF)", type=["pdf"])
    boleto_file = st.file_uploader(
        "Boleto (PDF ou imagem)", type=["pdf", "jpg", "jpeg", "png"]
    )
    linha = st.text_input("Linha digitável do boleto")

    if st.button("Criar pedido", type="primary"):
        if nome_cond is None:
            st.error("Selecione um condomínio.")
            return
        if not numero.strip():
            st.error("Número do pedido é obrigatório.")
            return
        validos = _itens_validos(itens)
        if not validos:
            st.error("Adicione ao menos um item com produto e quantidade.")
            return

        condominio_id = opcoes[nome_cond]
        try:
            pedido = queries.criar_pedido(
                condominio_id=condominio_id,
                numero_pedido=numero.strip(),
                data_pedido=data_pedido.isoformat(),
                data_vencimento=data_venc.isoformat() if data_venc else None,
                valor_total=total,
                itens=validos,
                linha_digitavel=linha or None,
            )
            pedido_id = pedido["id"]
            nf_path = None
            boleto_path = None
            if nf_file is not None:
                nf_path = queries.fazer_upload_documento(
                    f"{condominio_id}/{pedido_id}/nota_fiscal.pdf",
                    nf_file.getvalue(),
                    "application/pdf",
                )
            if boleto_file is not None:
                ext = boleto_file.name.rsplit(".", 1)[-1].lower()
                boleto_path = queries.fazer_upload_documento(
                    f"{condominio_id}/{pedido_id}/boleto.{ext}",
                    boleto_file.getvalue(),
                    boleto_file.type,
                )
            if nf_path or boleto_path:
                queries.atualizar_paths_pedido(pedido_id, nf_path, boleto_path)

            _limpar_itens_form(state_key)
            st.success("Pedido criado com sucesso.")
            st.rerun()
        except Exception as e:
            print(f"[pedidos] criar_pedido :: {type(e).__name__}: {e}")
            st.error("Não foi possível criar o pedido. Tente novamente.")


@st.dialog("Editar pedido", width="large")
def dialog_editar_pedido(pedido: dict, condominios: list[dict]):
    state_key = f"itens_form_editar_{pedido['id']}"
    opcoes = {c["nome"]: c["id"] for c in condominios}
    condominio_id = pedido["condominio_id"]

    st.subheader("Dados do pedido")
    st.write(f"**Condomínio:** {pedido.get('condominio_nome') or '—'}")
    numero = st.text_input("Número do pedido *", value=pedido.get("numero_pedido") or "")
    data_pedido = st.date_input(
        "Data do pedido", value=_to_date(pedido.get("data_pedido")) or date.today()
    )
    data_venc = st.date_input(
        "Data de vencimento", value=_to_date(pedido.get("data_vencimento"))
    )

    col_pgto, col_entrega = st.columns(2)
    status_pgto = col_pgto.selectbox(
        "Status de pagamento",
        STATUS_PAGAMENTO,
        index=STATUS_PAGAMENTO.index(pedido.get("status_pagamento", "pendente")),
    )
    status_entrega = col_entrega.selectbox(
        "Status de entrega",
        STATUS_ENTREGA,
        index=STATUS_ENTREGA.index(pedido.get("status_entrega", "pendente")),
    )
    data_entrega = st.date_input(
        "Data de entrega", value=_to_date(pedido.get("data_entrega"))
    )

    st.subheader("Itens")
    try:
        itens_atuais = queries.listar_itens_pedido(pedido["id"])
    except RuntimeError as e:
        st.error(str(e))
        itens_atuais = []
    itens = _render_itens(state_key, itens_iniciais=itens_atuais)
    total = sum(i["quantidade"] * i["valor_unit"] for i in itens)
    st.metric("Valor total", f"R$ {total:.2f}")

    st.subheader("Documentos")
    if pedido.get("nota_fiscal_path"):
        st.caption(f"NF atual: {_nome_arquivo(pedido['nota_fiscal_path'])}")
        _link_documento("⬇️ Ver NF atual", pedido["nota_fiscal_path"])
    nf_file = st.file_uploader("Substituir Nota Fiscal (PDF)", type=["pdf"])

    if pedido.get("boleto_path"):
        st.caption(f"Boleto atual: {_nome_arquivo(pedido['boleto_path'])}")
        _link_documento("⬇️ Ver boleto atual", pedido["boleto_path"])
    boleto_file = st.file_uploader(
        "Substituir Boleto (PDF ou imagem)", type=["pdf", "jpg", "jpeg", "png"]
    )
    linha = st.text_input(
        "Linha digitável do boleto", value=pedido.get("linha_digitavel") or ""
    )

    if st.button("Salvar alterações", type="primary"):
        if not numero.strip():
            st.error("Número do pedido é obrigatório.")
            return
        validos = _itens_validos(itens)
        if not validos:
            st.error("Adicione ao menos um item com produto e quantidade.")
            return

        try:
            nf_path = pedido.get("nota_fiscal_path")
            boleto_path = pedido.get("boleto_path")
            if nf_file is not None:
                nf_path = queries.fazer_upload_documento(
                    f"{condominio_id}/{pedido['id']}/nota_fiscal.pdf",
                    nf_file.getvalue(),
                    "application/pdf",
                )
            if boleto_file is not None:
                ext = boleto_file.name.rsplit(".", 1)[-1].lower()
                boleto_path = queries.fazer_upload_documento(
                    f"{condominio_id}/{pedido['id']}/boleto.{ext}",
                    boleto_file.getvalue(),
                    boleto_file.type,
                )

            queries.atualizar_pedido(
                id=pedido["id"],
                numero_pedido=numero.strip(),
                data_pedido=data_pedido.isoformat(),
                data_vencimento=data_venc.isoformat() if data_venc else None,
                valor_total=total,
                status_pagamento=status_pgto,
                status_entrega=status_entrega,
                data_entrega=data_entrega.isoformat() if data_entrega else None,
                linha_digitavel=linha or None,
                nota_fiscal_path=nf_path,
                boleto_path=boleto_path,
                itens=validos,
            )
            _limpar_itens_form(state_key)
            st.success("Pedido atualizado com sucesso.")
            st.rerun()
        except Exception as e:
            print(f"[pedidos] atualizar_pedido :: {type(e).__name__}: {e}")
            st.error("Não foi possível atualizar o pedido. Tente novamente.")


# --- Página ---

try:
    condominios = queries.listar_condominios()
except RuntimeError as e:
    st.error(str(e))
    condominios = []

opcoes_filtro = {"Todos": None} | {c["nome"]: c["id"] for c in condominios}
filtro_nome = st.selectbox("Filtrar por condomínio", list(opcoes_filtro.keys()))
filtro_id = opcoes_filtro[filtro_nome]

if st.button("+ Novo pedido"):
    if not condominios:
        st.error("Cadastre um condomínio antes de criar pedidos.")
    else:
        _limpar_itens_form("itens_form_novo")
        dialog_novo_pedido(condominios)

try:
    pedidos = queries.listar_pedidos(filtro_id)
except Exception as e:
    print(f"[pedidos] listar_pedidos :: {type(e).__name__}: {e}")
    st.error("Não foi possível carregar os pedidos. Tente novamente.")
    pedidos = []

if not pedidos:
    st.info("Nenhum pedido encontrado.")

if pedidos:
    h = st.columns([1.5, 2, 1.5, 1.5, 1.5, 1.5, 1, 1])
    h[0].caption("Nº Pedido")
    h[1].caption("Condomínio")
    h[2].caption("Valor Total")
    h[3].caption("Status Entrega")
    h[4].caption("Status Pgto")
    h[5].caption("Data Pedido")

for p in pedidos:
    cols = st.columns([1.5, 2, 1.5, 1.5, 1.5, 1.5, 1, 1])
    cols[0].write(p.get("numero_pedido") or "—")
    cols[1].write(p.get("condominio_nome") or "—")
    cols[2].write(f"R$ {p['valor_total']:.2f}")
    cols[3].write(p["status_entrega"])
    cols[4].write(p["status_pagamento"])
    cols[5].write(p.get("data_pedido") or "—")

    if cols[6].button("✏️", key=f"editar_{p['id']}"):
        _limpar_itens_form(f"itens_form_editar_{p['id']}")
        dialog_editar_pedido(p, condominios)

    flag = f"confirmar_del_pedido_{p['id']}"
    if st.session_state.get(flag):
        if cols[7].button("Confirmar?", key=f"conf_del_{p['id']}"):
            try:
                queries.deletar_pedido(p["id"])
                st.session_state.pop(flag, None)
                st.success("Pedido deletado.")
                st.rerun()
            except RuntimeError as e:
                st.error(str(e))
    else:
        if cols[7].button("🗑️", key=f"del_{p['id']}"):
            st.session_state[flag] = True
            st.rerun()
