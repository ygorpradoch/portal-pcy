-- Fase 2: schema inicial do dominio (perfis, condominios, vinculos, pedidos)

create extension if not exists pgcrypto;

create table public.perfis (
  id uuid primary key references auth.users(id) on delete cascade,
  nome_completo text,
  is_admin boolean not null default false,
  created_at timestamptz default now()
);

create table public.condominios (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  cnpj text,
  endereco text,
  ativo boolean default true,
  created_at timestamptz default now()
);

create table public.user_condominios (
  user_id uuid not null references auth.users(id) on delete cascade,
  condominio_id uuid not null references public.condominios(id) on delete cascade,
  created_at timestamptz default now(),
  primary key (user_id, condominio_id)
);

create table public.pedidos (
  id uuid primary key default gen_random_uuid(),
  condominio_id uuid not null references public.condominios(id) on delete restrict,
  numero_pedido text,
  valor numeric(10,2) not null,
  data_pedido date not null,
  data_vencimento date,
  status text not null default 'pendente' check (status in ('pendente', 'pago', 'cancelado')),
  nota_fiscal_path text,
  boleto_path text,
  observacoes text,
  pago_em timestamptz,
  created_at timestamptz default now()
);

create index idx_pedidos_condominio_id on public.pedidos (condominio_id);
create index idx_pedidos_status on public.pedidos (status);
create index idx_pedidos_data_pedido on public.pedidos (data_pedido desc);

-- Cria automaticamente o perfil ao registrar um novo usuario em auth.users
create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.perfis (id, nome_completo)
  values (new.id, coalesce(new.raw_user_meta_data->>'nome_completo', new.email));
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- handle_new_user e' apenas o handler do trigger; nao deve ser chamavel via API/RPC.
revoke execute on function public.handle_new_user() from public, anon, authenticated;
