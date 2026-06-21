"""Consultas e operacoes no banco de dados Supabase."""

from collections import Counter
from datetime import datetime, timezone

import streamlit as st

from lib.supabase_client import get_supabase_client, set_session_from_state


def _falha(msg: str, e: Exception) -> RuntimeError:
    """Registra o erro real nos logs (o Streamlit Cloud nao oculta logs) e
    devolve um RuntimeError com mensagem limpa em portugues para a UI."""
    print(f"[queries] {msg} :: {type(e).__name__}: {e}")
    return RuntimeError(msg)


def listar_condominios(incluir_inativos: bool = False) -> list[dict]:
    set_session_from_state()
    client = get_supabase_client()
    try:
        query = client.table("condominios").select("*")
        if not incluir_inativos:
            query = query.eq("ativo", True)
        resultado = query.order("nome").execute()
        return resultado.data
    except Exception as e:
        raise RuntimeError("Não foi possível carregar os condomínios.") from e


def criar_condominio(nome: str, cnpj: str | None, endereco: str | None) -> dict:
    set_session_from_state()
    client = get_supabase_client()
    try:
        resultado = (
            client.table("condominios")
            .insert({"nome": nome, "cnpj": cnpj, "endereco": endereco})
            .execute()
        )
        return resultado.data[0]
    except Exception as e:
        raise RuntimeError("Não foi possível criar o condomínio.") from e


def atualizar_condominio(
    id: str, nome: str, cnpj: str | None, endereco: str | None
) -> dict:
    set_session_from_state()
    client = get_supabase_client()
    try:
        resultado = (
            client.table("condominios")
            .update({"nome": nome, "cnpj": cnpj, "endereco": endereco})
            .eq("id", id)
            .execute()
        )
        return resultado.data[0]
    except Exception as e:
        raise RuntimeError("Não foi possível atualizar o condomínio.") from e


def desativar_condominio(id: str) -> None:
    set_session_from_state()
    client = get_supabase_client()
    try:
        client.table("condominios").update({"ativo": False}).eq("id", id).execute()
    except Exception as e:
        raise RuntimeError("Não foi possível desativar o condomínio.") from e


def reativar_condominio(id: str) -> None:
    set_session_from_state()
    client = get_supabase_client()
    try:
        client.table("condominios").update({"ativo": True}).eq("id", id).execute()
    except Exception as e:
        raise RuntimeError("Não foi possível reativar o condomínio.") from e


def listar_perfis() -> list[dict]:
    set_session_from_state()
    client = get_supabase_client()
    try:
        resultado = (
            client.table("perfis")
            .select("id, nome_completo, is_admin")
            .order("nome_completo")
            .execute()
        )
        return resultado.data
    except Exception as e:
        raise RuntimeError("Não foi possível carregar os usuários.") from e


# --- Pedidos (Fase 5) ---


def _montar_pedidos(dados: list[dict]) -> list[dict]:
    """Achata o embed condominios(nome) em condominio_nome."""
    pedidos = []
    for p in dados:
        p = dict(p)
        condominio = p.pop("condominios", None)
        # o embed pode vir como dict, lista (1->N detectado) ou None
        if isinstance(condominio, list):
            condominio = condominio[0] if condominio else None
        nome = condominio.get("nome") if isinstance(condominio, dict) else None
        pedidos.append({**p, "condominio_nome": nome})
    return pedidos


def listar_pedidos(condominio_id: str | None = None) -> list[dict]:
    set_session_from_state()
    client = get_supabase_client()
    try:
        query = client.table("pedidos").select(
            "id, numero_pedido, condominio_id, valor_total, status_pagamento, "
            "status_entrega, data_pedido, data_vencimento, data_entrega, "
            "linha_digitavel, nota_fiscal_path, boleto_path, condominios(nome)"
        )
        if condominio_id:
            query = query.eq("condominio_id", condominio_id)
        resultado = query.order("data_pedido", desc=True).execute()
        return _montar_pedidos(resultado.data)
    except Exception as e:
        raise _falha("Não foi possível carregar os pedidos.", e) from e


def listar_itens_pedido(pedido_id: str) -> list[dict]:
    set_session_from_state()
    client = get_supabase_client()
    try:
        resultado = (
            client.table("pedido_itens")
            .select("id, produto, quantidade, valor_unit")
            .eq("pedido_id", pedido_id)
            .order("created_at")
            .execute()
        )
        return [
            {**item, "valor_total_item": item["quantidade"] * item["valor_unit"]}
            for item in resultado.data
        ]
    except Exception as e:
        raise RuntimeError("Não foi possível carregar os itens do pedido.") from e


def criar_pedido(
    condominio_id: str,
    numero_pedido: str,
    data_pedido: str,
    data_vencimento: str,
    valor_total: float,
    itens: list[dict],
    linha_digitavel: str | None = None,
    nota_fiscal_path: str | None = None,
    boleto_path: str | None = None,
) -> dict:
    set_session_from_state()
    client = get_supabase_client()
    try:
        resultado = (
            client.table("pedidos")
            .insert(
                {
                    "condominio_id": condominio_id,
                    "numero_pedido": numero_pedido,
                    "data_pedido": data_pedido,
                    "data_vencimento": data_vencimento,
                    "valor_total": valor_total,
                    "linha_digitavel": linha_digitavel,
                    "nota_fiscal_path": nota_fiscal_path,
                    "boleto_path": boleto_path,
                }
            )
            .execute()
        )
        pedido = dict(resultado.data[0])
        pedido_id = pedido["id"]
    except Exception as e:
        raise _falha("Não foi possível criar o pedido.", e) from e

    try:
        client.table("pedido_itens").insert(
            [
                {
                    "pedido_id": pedido_id,
                    "produto": item["produto"],
                    "quantidade": item["quantidade"],
                    "valor_unit": item["valor_unit"],
                }
                for item in itens
            ]
        ).execute()
    except Exception as e:
        # rollback semântico: desfaz o pedido se os itens falharem
        try:
            client.table("pedidos").delete().eq("id", pedido_id).execute()
        except Exception as rollback_err:  # nao mascara o erro original
            print(f"[queries] rollback do pedido falhou :: {rollback_err}")
        raise _falha("Não foi possível salvar os itens do pedido.", e) from e

    return pedido


def atualizar_pedido(
    id: str,
    numero_pedido: str,
    data_pedido: str,
    data_vencimento: str,
    valor_total: float,
    status_pagamento: str,
    status_entrega: str,
    data_entrega: str | None,
    linha_digitavel: str | None,
    nota_fiscal_path: str | None,
    boleto_path: str | None,
    itens: list[dict],
) -> dict:
    set_session_from_state()
    client = get_supabase_client()
    try:
        resultado = (
            client.table("pedidos")
            .update(
                {
                    "numero_pedido": numero_pedido,
                    "data_pedido": data_pedido,
                    "data_vencimento": data_vencimento,
                    "valor_total": valor_total,
                    "status_pagamento": status_pagamento,
                    "status_entrega": status_entrega,
                    "data_entrega": data_entrega,
                    "linha_digitavel": linha_digitavel,
                    "nota_fiscal_path": nota_fiscal_path,
                    "boleto_path": boleto_path,
                }
            )
            .eq("id", id)
            .execute()
        )
        pedido = resultado.data[0]
        # estratégia simples: apaga todos os itens e reinsere a lista nova
        client.table("pedido_itens").delete().eq("pedido_id", id).execute()
        client.table("pedido_itens").insert(
            [
                {
                    "pedido_id": id,
                    "produto": item["produto"],
                    "quantidade": item["quantidade"],
                    "valor_unit": item["valor_unit"],
                }
                for item in itens
            ]
        ).execute()
        return pedido
    except Exception as e:
        raise RuntimeError("Não foi possível atualizar o pedido.") from e


def atualizar_paths_pedido(
    id: str,
    nota_fiscal_path: str | None = None,
    boleto_path: str | None = None,
) -> None:
    set_session_from_state()
    client = get_supabase_client()
    try:
        client.table("pedidos").update(
            {"nota_fiscal_path": nota_fiscal_path, "boleto_path": boleto_path}
        ).eq("id", id).execute()
    except Exception as e:
        raise RuntimeError("Não foi possível salvar os documentos do pedido.") from e


def deletar_pedido(id: str) -> None:
    set_session_from_state()
    client = get_supabase_client()
    try:
        client.table("pedidos").delete().eq("id", id).execute()
    except Exception as e:
        raise RuntimeError("Não foi possível deletar o pedido.") from e


def fazer_upload_documento(
    caminho_storage: str,
    bytes_arquivo: bytes,
    content_type: str,
) -> str:
    set_session_from_state()
    client = get_supabase_client()
    try:
        client.storage.from_("documentos").upload(
            path=caminho_storage,
            file=bytes_arquivo,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        return caminho_storage
    except Exception as e:
        raise RuntimeError("Não foi possível enviar o documento.") from e


def gerar_url_documento(caminho_storage: str) -> str:
    set_session_from_state()
    client = get_supabase_client()
    try:
        resposta = client.storage.from_("documentos").create_signed_url(
            caminho_storage, 300
        )
    except Exception as e:
        raise _falha("Não foi possível gerar o link do documento.", e) from e

    url = None
    for chave in ("signedURL", "signedUrl", "signed_url"):
        if isinstance(resposta, dict):
            url = resposta.get(chave)
        else:
            url = getattr(resposta, chave, None)
        if url:
            break
    if not url:
        print(f"[queries] create_signed_url sem URL :: {resposta!r}")
        raise RuntimeError("Não foi possível gerar o link do documento.")
    return url


def listar_vinculos(condominio_id: str) -> list[dict]:
    set_session_from_state()
    client = get_supabase_client()
    try:
        vinculos = (
            client.table("user_condominios")
            .select("user_id")
            .eq("condominio_id", condominio_id)
            .execute()
        )
        user_ids = [v["user_id"] for v in vinculos.data]
        if not user_ids:
            return []
        perfis = (
            client.table("perfis")
            .select("id, nome_completo")
            .in_("id", user_ids)
            .execute()
        )
        return [
            {"user_id": p["id"], "nome_completo": p["nome_completo"]}
            for p in perfis.data
        ]
    except Exception as e:
        raise RuntimeError("Não foi possível carregar os vínculos.") from e


def listar_condominios_do_usuario(user_id: str) -> list[dict]:
    set_session_from_state()
    client = get_supabase_client()
    try:
        resultado = (
            client.table("user_condominios")
            .select("condominio_id, condominios(nome)")
            .eq("user_id", user_id)
            .execute()
        )
        return [
            {"condominio_id": r["condominio_id"], "nome": r["condominios"]["nome"]}
            for r in resultado.data
        ]
    except Exception as e:
        raise RuntimeError(
            "Não foi possível carregar os condomínios do usuário."
        ) from e


def criar_vinculo(user_id: str, condominio_id: str) -> None:
    set_session_from_state()
    client = get_supabase_client()
    try:
        client.table("user_condominios").insert(
            {"user_id": user_id, "condominio_id": condominio_id}
        ).execute()
    except Exception as e:
        if getattr(e, "code", None) == "23505":
            return
        raise RuntimeError("Não foi possível criar o vínculo.") from e


def remover_vinculo(user_id: str, condominio_id: str) -> None:
    set_session_from_state()
    client = get_supabase_client()
    try:
        client.table("user_condominios").delete().eq("user_id", user_id).eq(
            "condominio_id", condominio_id
        ).execute()
    except Exception as e:
        raise RuntimeError("Não foi possível remover o vínculo.") from e


def listar_perfis_com_contagem() -> list[dict]:
    set_session_from_state()
    client = get_supabase_client()
    try:
        perfis = (
            client.table("perfis")
            .select("id, nome_completo, is_admin")
            .order("nome_completo")
            .execute()
        )
        vinculos = client.table("user_condominios").select("user_id").execute()
        contagem = Counter(v["user_id"] for v in vinculos.data)
        return [
            {**perfil, "total_condominios": contagem.get(perfil["id"], 0)}
            for perfil in perfis.data
        ]
    except Exception as e:
        raise RuntimeError("Não foi possível carregar os usuários.") from e


# --- Tela do cliente (Fase 6) ---


def listar_condominios_do_usuario_atual() -> list[dict]:
    """Condomínios vinculados ao usuário logado (via auth.uid() na RLS)."""
    user = st.session_state.get("user")
    if user is None:
        return []
    return listar_condominios_do_usuario(user.id)


def listar_pedidos_do_cliente(
    condominio_id: str,
    status_pagamento: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
) -> list[dict]:
    """Pedidos do condomínio informado, com filtros opcionais.

    A RLS já restringe os pedidos visíveis ao usuário logado; aqui só
    aplicamos os filtros adicionais pedidos pelo cliente na tela.
    """
    set_session_from_state()
    client = get_supabase_client()
    try:
        query = (
            client.table("pedidos")
            .select(
                "id, numero_pedido, condominio_id, valor_total, status_pagamento, "
                "status_entrega, data_pedido, data_vencimento, data_entrega, "
                "linha_digitavel, nota_fiscal_path, boleto_path, condominios(nome)"
            )
            .eq("condominio_id", condominio_id)
        )
        if status_pagamento:
            query = query.eq("status_pagamento", status_pagamento)
        if data_inicio:
            query = query.gte("data_pedido", data_inicio)
        if data_fim:
            query = query.lte("data_pedido", data_fim)
        if valor_min is not None:
            query = query.gte("valor_total", valor_min)
        if valor_max is not None:
            query = query.lte("valor_total", valor_max)
        resultado = query.order("data_pedido", desc=True).execute()
        return _montar_pedidos(resultado.data)
    except Exception as e:
        raise _falha("Não foi possível carregar os pedidos.", e) from e


def marcar_pedido_como_pago(pedido_id: str) -> None:
    """Marca o pedido como pago. A RLS só permite o UPDATE se o pedido
    pertencer ao condomínio do usuário logado e estiver pendente."""
    set_session_from_state()
    client = get_supabase_client()
    pago_em = datetime.now(timezone.utc).isoformat()
    try:
        resultado = (
            client.table("pedidos")
            .update({"status_pagamento": "pago", "pago_em": pago_em})
            .eq("id", pedido_id)
            .execute()
        )
    except Exception as e:
        raise _falha("Não foi possível marcar o pedido como pago.", e) from e

    if not resultado.data:
        raise RuntimeError(
            "Não foi possível marcar o pedido como pago. "
            "Ele pode já estar pago ou você não tem permissão."
        )


def listar_todos_pedidos_do_cliente() -> list[dict]:
    """Pedidos de todos os condomínios vinculados ao usuário logado.

    A RLS já restringe os pedidos visíveis ao usuário logado, então não
    é preciso filtrar por condominio_id aqui.
    """
    set_session_from_state()
    client = get_supabase_client()
    try:
        resultado = (
            client.table("pedidos")
            .select(
                "id, numero_pedido, condominio_id, valor_total, status_pagamento, "
                "status_entrega, data_pedido, data_vencimento, data_entrega, "
                "linha_digitavel, nota_fiscal_path, boleto_path, condominios(nome)"
            )
            .order("data_pedido", desc=True)
            .execute()
        )
        return _montar_pedidos(resultado.data)
    except Exception as e:
        raise _falha("Não foi possível carregar os pedidos.", e) from e
