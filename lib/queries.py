"""Consultas e operacoes no banco de dados Supabase."""

from collections import Counter

from lib.supabase_client import get_supabase_client, set_session_from_state


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
