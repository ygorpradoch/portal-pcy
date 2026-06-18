-- Fase 2: Row Level Security para perfis, condominios, user_condominios, pedidos

alter table public.perfis enable row level security;
alter table public.condominios enable row level security;
alter table public.user_condominios enable row level security;
alter table public.pedidos enable row level security;

-- security definer evita recursao de RLS: a leitura de perfis aqui ignora
-- a propria policy de perfis, ao contrario de uma query normal do chamador.
create function public.is_admin()
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select coalesce((select is_admin from public.perfis where id = auth.uid()), false);
$$;

-- perfis
create policy "perfis_select_own_or_admin"
  on public.perfis for select
  using (id = auth.uid() or public.is_admin());

create policy "perfis_update_own"
  on public.perfis for update
  using (id = auth.uid())
  with check (id = auth.uid());

create policy "perfis_admin_all"
  on public.perfis for all
  using (public.is_admin())
  with check (public.is_admin());

-- condominios
create policy "condominios_select_vinculado_or_admin"
  on public.condominios for select
  using (
    exists (
      select 1 from public.user_condominios uc
      where uc.condominio_id = condominios.id and uc.user_id = auth.uid()
    )
    or public.is_admin()
  );

create policy "condominios_admin_all"
  on public.condominios for all
  using (public.is_admin())
  with check (public.is_admin());

-- user_condominios
create policy "user_condominios_select_own_or_admin"
  on public.user_condominios for select
  using (user_id = auth.uid() or public.is_admin());

create policy "user_condominios_admin_all"
  on public.user_condominios for all
  using (public.is_admin())
  with check (public.is_admin());

-- pedidos
create policy "pedidos_select_vinculado_or_admin"
  on public.pedidos for select
  using (
    condominio_id in (
      select uc.condominio_id from public.user_condominios uc
      where uc.user_id = auth.uid()
    )
    or public.is_admin()
  );

create policy "pedidos_admin_all"
  on public.pedidos for all
  using (public.is_admin())
  with check (public.is_admin());

-- cliente so pode marcar um pedido pendente do seu condominio como pago;
-- nao pode reverter pago->pendente nem alterar para cancelado.
create policy "pedidos_update_cliente_marca_pago"
  on public.pedidos for update
  using (
    condominio_id in (
      select uc.condominio_id from public.user_condominios uc
      where uc.user_id = auth.uid()
    )
    and status = 'pendente'
  )
  with check (status = 'pago');
