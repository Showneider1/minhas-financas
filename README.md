# 💰 Sistema de Gestão Financeira Pessoal

Sistema completo de controle financeiro desenvolvido em Python com Dash, oferecendo gestão de receitas, despesas, categorias e análises financeiras.

## 🚀 Tecnologias

- **Backend:** Python 3.10+
- **Framework:** Dash + Plotly
- **Database:** SQLite + SQLAlchemy
- **Frontend:** Dash Bootstrap Components
- **Autenticação:** JWT

## 📋 Funcionalidades

- ✅ Dashboard financeiro interativo
- ✅ Gestão de receitas e despesas
- ✅ Categorização de transações
- ✅ Extrato detalhado com filtros
- ✅ Relatórios em PDF
- ✅ Gráficos e análises
- ✅ Autenticação de usuários

## 🔧 Instalação

1. Clone o repositório
2. Crie um ambiente virtual: `python -m venv venv`
3. Ative: `venv\Scripts\activate` (Windows) ou `source venv/bin/activate` (Linux/macOS)
4. Instale dependências: `pip install -r requirements.txt`
5. Configure o `.env` (veja `.env.example`)
6. Execute: `gunicorn wsgi:server` (ou `python -m gunicorn wsgi:server`)

> **Entrypoint único:** `wsgi:server` — usado pelo `Dockerfile` e pelo `Procfile`.
> Ele chama `initialize_application()` (criação de tabelas + seeds idempotentes)
> antes de expor o servidor. `python myindex.py` inicia apenas o servidor Dash,
> **sem** inicializar o banco — evite esse caminho em produção.
>
> Com Docker: `docker compose up --build`.

## 📦 Estrutura

MinhasFinanças/
├── callbacks/ # Callbacks Dash
├── components/ # Componentes reutilizáveis
├── database/ # Models e conexão
├── pages/ # Páginas da aplicação
├── services/ # Lógica de negócio
├── schemas/ # Schemas Pydantic
└── utils/ # Utilitários

## 🔒 Segurança

- Senhas hasheadas com bcrypt
- Tokens JWT
- Variáveis de ambiente protegidas

## 📝 Licença

Projeto pessoal - Todos os direitos reservados