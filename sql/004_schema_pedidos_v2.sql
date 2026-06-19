-- Fase 5: pedidos v2 (itens + documentos)
-- Renomeia colunas de pedidos, adiciona status de entrega, cria pedido_itens
-- com RLS e configura storage policies do bucket "documentos".

-- 1. Renomear valor -> valor_total
alter table public.pedidos rename column valor to valor_total;

-- 2. Renomear status -> status_pagamento (separa de status_entrega)
--    O check constraint (pendente|pago|cancelado) acompanha o rename.
alter table public.pedidos rename column status to status_pagamento;

-- 3. Novas colunas de pedidos
alter table public.pedidos
  add column if not exists data_entrega date,
  add column if not exists linha_digitavel text,
  add column if not exists status_entrega text not null default 'pendente'
    check (status_entrega in ('pendente', 'parcial', 'entregue'));

-- Recria a policy de cliente apontando explicitamente para status_pagamento
-- (o Postgres reescreve a referencia no rename, mas recriamos para deixar claro).
drop policy if exists "pedidos_update_cliente_marca_pago" on public.pedidos;
create policy "pedidos_update_cliente_marca_pago"
  on public.pedidos for update
  using (
    condominio_id in (
      select uc.condominio_id from public.user_condominios uc
      where uc.user_id = auth.uid()
    )
    and status_pagamento = 'pendente'
  )
  with check (status_pagamento = 'pago');

-- 4. Tabela de itens do pedido
--    valor_total_item e calculado em Python (quantidade * valor_unit),
--    nao armazenado, para evitar inconsistencia.
create table if not exists public.pedido_itens (
  id          uuid primary key default gen_random_uuid(),
  pedido_id   uuid not null references public.pedidos(id) on delete cascade,
  produto     text not null,
  quantidade  numeric(10, 2) not null check (quantidade > 0),
  valor_unit  numeric(10, 2) not null check (valor_unit >= 0),
  created_at  timestamptz not null default now()
);

create index if not exists idx_pedido_itens_pedido_id
  on public.pedido_itens (pedido_id);

-- 5. RLS em pedido_itens (mesmo padrao de pedidos)
alter table public.pedido_itens enable row level security;

-- Admin: acesso total
create policy "admin_all_pedido_itens"
  on public.pedido_itens for all
  using (public.is_admin())
  with check (public.is_admin());

-- Cliente: select apenas em itens de pedidos do seu condominio
create policy "cliente_select_pedido_itens"
  on public.pedido_itens for select
  using (
    exists (
      select 1 from public.pedidos p
      join public.user_condominios uc on uc.condominio_id = p.condominio_id
      where p.id = pedido_itens.pedido_id
        and uc.user_id = auth.uid()
    )
  );

-- 6. Storage policies no bucket "documentos"
--    Path: {condominio_id}/{pedido_id}/arquivo.pdf
--    (storage.foldername(name))[1] extrai o condominio_id do path.

-- Admin: upload
create policy "admin_insert_documentos"
  on storage.objects for insert
  with check (
    bucket_id = 'documentos' and public.is_admin()
  );

-- Admin: delete
create policy "admin_delete_documentos"
  on storage.objects for delete
  using (
    bucket_id = 'documentos' and public.is_admin()
  );

-- Admin: leitura total
create policy "admin_select_documentos"
  on storage.objects for select
  using (
    bucket_id = 'documentos' and public.is_admin()
  );

-- Cliente: leitura apenas do seu condominio
create policy "cliente_select_documentos"
  on storage.objects for select
  using (
    bucket_id = 'documentos'
    and exists (
      select 1 from public.user_condominios
      where user_id = auth.uid()
        and condominio_id::text = (storage.foldername(name))[1]
    )
  );
