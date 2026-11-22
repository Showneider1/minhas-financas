# Segurança — Finance OS (inventário de controles)

Revisado em 22/11/2026. Estado atual do código em produção.

## Controles implementados

| Controle | Onde | Observação |
|---|---|---|
| Hash de senha | `config/security.py` (bcrypt) | — |
| JWT access/refresh/reset | `config/security.py` | `exp`/`iat`/`jti`; refresh com denylist e revogação em árvore |
| Anti-IDOR | `middleware/auth_context.py::resolve_user` | `user_id` derivado do JWT, nunca do `store-user-id` |
| Logout server-side | `callbacks/auth_callbacks.py` | usa `resolve_user` — payload forjado não revoga outras sessões |
| Rate limit de login/registro/HTTP | `middleware/rate_limiter.py`, `middleware/http_rate_limit.py` | ver limite efetivo em ADR-005 |
| CSRF no endpoint de escrita | `middleware/http_rate_limit.py::_csrf_violation` | valida `Origin`/`Referer` same-origin em POST `/_dash-update-component` |
| Cabeçalhos de segurança | `Caddyfile` | HSTS, nosniff, X-Frame-Options, Referrer-Policy, CSP |
| Segredos fora do repo | `.gitignore`, `.dockerignore` | Caddy recebe só `DOMAIN` (não o `.env` inteiro) |
| Fail-fast de segredos | `config/settings.py` | somente quando `ENVIRONMENT=production` (ver ressalva) |
| Isolamento de testes | `tests/conftest.py` | `DATABASE_URL` forçado para `:memory:` + guarda autouse |
| RLS (preparado) | `supabase/migrations/0002_rls.sql` | **não aplicado** — aguardando cutover Postgres |

## Pendências priorizadas

1. **LGPD:** não há exportação completa nem exclusão/anonimização de titular — ver `LGPD.md`.
2. **Sessão:** access/refresh em `sessionStorage` (risco XSS herdado). CSP já reduz o vetor.
3. **Rate limit:** o bucket é por processo; 4 workers multiplicam o limite efetivo (ADR-005).
4. **RLS:** depende do cutover Postgres e da definição `app.user_id` / `auth.uid()`.
5. **CI:** sem SAST, secret scanning ou auditoria de dependências (`pip-audit`, `bandit`).
6. **Logs:** e-mails completos em `services/auth_services.py` e `middleware/audit_log.py` —
   mascarar/transformar.
7. **Registro:** sem verificação de e-mail nem CAPTCHA (`ENABLE_EMAIL_VERIFICATION=False`).
8. **Exports:** fórmula injection em CSV/XLSX e HTML injection em e-mails transacionais.
9. **Fail-fast:** validação de segredos só em `production`; defaults `dev-*` aceitos em staging.

## Ressalva de deploy

`Procfile.txt` e `Dockerfile` usam `wsgi:server`. `python myindex.py` inicia o servidor
Dash **sem** `initialize_application()` — não usar em produção.
