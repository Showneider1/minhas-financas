"""
Servico de envio de e-mails transacionais.

Configuracao necessaria em .env:
    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=587
    EMAIL_USER=seu@email.com
    EMAIL_PASSWORD=sua_senha_de_app
    EMAIL_FROM_NAME=Minhas Financas
"""
import smtplib
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any
from config.logging_config import app_logger


def _get_smtp_config() -> dict:
    return {
        "host":      os.getenv("EMAIL_HOST",      "smtp.gmail.com"),
        "port":      int(os.getenv("EMAIL_PORT",  "587")),
        "user":      os.getenv("EMAIL_USER",      ""),
        "password":  os.getenv("EMAIL_PASSWORD",  ""),
        "from_name": os.getenv("EMAIL_FROM_NAME", "Minhas Financas"),
    }


def send_email(to: str, subject: str, html_body: str) -> bool:
    """
    Envia e-mail via SMTP com corpo em HTML.

    Returns:
        True se enviado com sucesso, False caso contrario.
    """
    cfg = _get_smtp_config()

    if not cfg["user"] or not cfg["password"]:
        app_logger.warning(
            "[EmailService] Credenciais SMTP nao configuradas. "
            "Defina EMAIL_USER e EMAIL_PASSWORD no .env"
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{cfg['from_name']} <{cfg['user']}>"
    msg["To"]      = to

    plain_text = re.sub(r"<[^>]+>", "", html_body).strip()
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_body,  "html",  "utf-8"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], to, msg.as_string())
        app_logger.info(f"[EmailService] E-mail enviado para {to} | Assunto: {subject}")
        return True
    except smtplib.SMTPAuthenticationError:
        app_logger.error("[EmailService] Falha de autenticacao SMTP. Verifique EMAIL_USER e EMAIL_PASSWORD.")
    except smtplib.SMTPException as exc:
        app_logger.error(f"[EmailService] Erro SMTP ao enviar para {to}: {exc}")
    except Exception as exc:
        app_logger.error(f"[EmailService] Erro inesperado ao enviar e-mail: {exc}", exc_info=True)
    return False


def render_email_template(summary: Dict[str, Any]) -> str:
    """
    Renderiza o template HTML do relatorio semanal.

    Args:
        summary: dict com week_label, user_name, total_receitas,
                 total_despesas, saldo, top_categorias, alertas
    """
    week_label     = summary.get("week_label",     "esta semana")
    user_name      = summary.get("user_name",      "voce")
    total_receitas = summary.get("total_receitas", 0.0)
    total_despesas = summary.get("total_despesas", 0.0)
    saldo          = summary.get("saldo",          0.0)
    top_categorias = summary.get("top_categorias", [])
    alertas        = summary.get("alertas",        [])

    saldo_color = "#2e7d32" if saldo >= 0 else "#c62828"
    saldo_sinal = "+"       if saldo >= 0 else ""
    saldo_emoji = "✅"      if saldo >= 0 else "⚠️"

    def fmt(value: float) -> str:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    cat_rows = ""
    for i, cat in enumerate(top_categorias[:5], start=1):
        cat_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;color:#555;">{i}. {cat.get('nome', '-')}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:right;color:#c62828;font-weight:600;">{fmt(cat.get('valor', 0))}</td>
        </tr>"""

    if not cat_rows:
        cat_rows = '<tr><td colspan="2" style="padding:12px;text-align:center;color:#aaa;">Nenhuma despesa registrada esta semana.</td></tr>'

    alertas_html = ""
    if alertas:
        itens = "".join(f'<li style="margin:4px 0;color:#7b1fa2;">{a}</li>' for a in alertas)
        alertas_html = f"""
        <div style="background:#f3e5f5;border-left:4px solid #ab47bc;border-radius:6px;padding:12px 16px;margin:20px 0;">
          <p style="margin:0 0 8px;font-weight:700;color:#6a1b9a;">⚠️ Alertas da semana</p>
          <ul style="margin:0;padding-left:18px;">{itens}</ul>
        </div>"""

    alertas_block = f'<tr><td style="padding:0 32px;">{alertas_html}</td></tr>' if alertas_html else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Resumo Financeiro Semanal</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.08);overflow:hidden;max-width:600px;width:100%;">
        <tr>
          <td style="background:linear-gradient(135deg,#1b5e20,#388e3c);padding:28px 32px;text-align:center;">
            <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;">💰 Minhas Financas</h1>
            <p style="margin:6px 0 0;color:#c8e6c9;font-size:14px;">Resumo da semana &middot; {week_label}</p>
          </td>
        </tr>
        <tr>
          <td style="padding:28px 32px 0;">
            <p style="margin:0;font-size:16px;color:#333;">Ola, <strong>{user_name}</strong>! Aqui esta seu resumo de <strong>{week_label}</strong>.</p>
          </td>
        </tr>
        <tr>
          <td style="padding:20px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="32%" style="background:#e8f5e9;border-radius:8px;padding:16px;text-align:center;">
                  <p style="margin:0;font-size:11px;color:#555;text-transform:uppercase;font-weight:700;">Receitas</p>
                  <p style="margin:6px 0 0;font-size:20px;font-weight:700;color:#2e7d32;">{fmt(total_receitas)}</p>
                </td>
                <td width="4%"></td>
                <td width="32%" style="background:#ffebee;border-radius:8px;padding:16px;text-align:center;">
                  <p style="margin:0;font-size:11px;color:#555;text-transform:uppercase;font-weight:700;">Despesas</p>
                  <p style="margin:6px 0 0;font-size:20px;font-weight:700;color:#c62828;">{fmt(total_despesas)}</p>
                </td>
                <td width="4%"></td>
                <td width="32%" style="background:#f3f3f3;border-radius:8px;padding:16px;text-align:center;">
                  <p style="margin:0;font-size:11px;color:#555;text-transform:uppercase;font-weight:700;">Saldo {saldo_emoji}</p>
                  <p style="margin:6px 0 0;font-size:20px;font-weight:700;color:{saldo_color};">{saldo_sinal}{fmt(saldo)}</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        {alertas_block}
        <tr>
          <td style="padding:4px 32px 24px;">
            <p style="margin:0 0 12px;font-size:14px;font-weight:700;color:#333;">📊 Top categorias de despesa</p>
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #eee;border-radius:8px;overflow:hidden;">
              {cat_rows}
            </table>
          </td>
        </tr>
        <tr>
          <td style="background:#fafafa;border-top:1px solid #eee;padding:20px 32px;text-align:center;">
            <p style="margin:0;font-size:12px;color:#999;">Voce esta recebendo este e-mail pois ativou os relatorios semanais.<br>Para cancelar, acesse as configuracoes do aplicativo.</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
