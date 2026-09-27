# ADR-005 — Rate Limit por IP + Hardening de Sessão (P1)

**Status:** Implementado (2026-09-27). Suíte: 124 passed.

## 1. Rate limiting (sem Redis, por decisão)

- Buckets sliding-window persistidos em `rate_limit_hits(scope, key, ts)`
  (`middleware/rate_limiter.hit`, com lock p/ servidor síncrono):
  login `30/5min por IP`, registro `20/h por IP`, HTTP `300/min por IP`.
- Login mantém o bucket legado por email + soma o bucket por IP (derrota
  rotação de email). Registro usa só IP.
- Hook Flask (`middleware/http_rate_limit.init_http_rate_limit`, ligado em
  `myindex.py`): `POST /_dash-update-component` em rajada → **HTTP 429** +
  `Retry-After` reais; desligável (`RATE_LIMIT_HTTP_ENABLED`).
- Callbacks exibem "Muitas tentativas. Aguarde Ns." (equivalente UI do 429).

## 2. Sessões (rotação + denylist)

- `refresh_tokens(jti, user_id, expires_at, revoked, replaced_by)`; `jti` em
  todo refresh emitido (`issue_refresh_token`).
- `refresh_session`: valida vivo → revoga antigo (`replaced_by`) → emite par
  novo. Reuso de revogado com assinatura válida = roubo → **revoga a árvore
  inteira** + 401 (`REVOKED_SESSION`).
- `AuthService.logout` revoga tudo server-side; callback de logout chama o
  serviço (antes era só `clear_data` client-side). Access segue stateless
  curto (30 min). Refresh trafega em `auth-store` (risco XSS herdado e
  documentado; cookie HttpOnly = P2 com CSRF).
- Testes provam: rotação, morte do antigo, morte da árvore no reuso, logout,
  expirado/adulterado negados, access não rotaciona.

## 3. Limites (P2)

`X-Forwarded-For` só confiável atrás de proxy próprio (ancorado em
`remote_addr`); CAPTCHA; limpeza agendada de `rate_limit_hits`; silent refresh
via `dcc.Interval`; denylist de access (hoje só refresh).
