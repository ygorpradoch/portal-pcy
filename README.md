# portal-pcy

Portal web para gestao de informacoes da PCY, construido com Streamlit e Supabase.

## Stack

- [Streamlit](https://streamlit.io/) — interface web
- [Supabase](https://supabase.com/) — banco de dados, autenticacao e storage
- Python 3.11

## Como rodar localmente

1. Abra este repositorio em um Codespace (ou devcontainer local).
2. Copie `.env.example` para `.env` e/ou `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`, preenchendo `SUPABASE_URL` e `SUPABASE_ANON_KEY`.
3. Instale as dependencias (ja feito automaticamente no Codespace via `postCreateCommand`):
   ```bash
   pip install -r requirements.txt
   ```
4. Rode a aplicacao:
   ```bash
   streamlit run streamlit_app.py
   ```

## Producao

URL de producao: _a definir_
