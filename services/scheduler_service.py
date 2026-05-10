"""Background Job Scheduler usando APScheduler.

Executa tarefas automaticas em background:
1. Diariamente 00:05: Detecta contas vencidas e atualiza status para OVERDUE
2. Diariamente 00:10: Processa transacoes recorrentes do dia
3. A cada hora: Verifica metas atingidas e marca como concluidas
4. Toda sexta-feira 18:00: Envia resumo financeiro semanal por e-mail

Uso: importado e iniciado pelo app.py na inicializacao da aplicacao.
O scheduler roda em modo daemon (nao bloqueia o processo principal).
"""
from datetime import date, datetime, timezone, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from database.connection import get_db_session
from config.logging_config import app_logger

# Instancia global (singleton)
_scheduler: Optional[BackgroundScheduler] = None


# ------------------------------------------------------------------ #
# JOBS                                                                  #
# ------------------------------------------------------------------ #

def _job_update_overdue_bills() -> None:
    """Job: Atualiza contas vencidas para status OVERDUE.
    Execucao: diariamente as 00:05
    """
    app_logger.info("[Scheduler] Iniciando job: update_overdue_bills")
    try:
        from database.models.user import User
        from services.scheduled_bill_service import ScheduledBillService

        with get_db_session() as db:
            users = db.query(User).filter(User.is_active == True, User.is_deleted == False).all()
            total_updated = 0
            for user in users:
                svc = ScheduledBillService(db)
                updated = svc.update_overdue_bills(user.id)
                total_updated += updated

        app_logger.info(f"[Scheduler] update_overdue_bills concluido: {total_updated} contas vencidas encontradas")
    except Exception as exc:
        app_logger.error(f"[Scheduler] Erro em update_overdue_bills: {exc}", exc_info=True)


def _job_process_recurrences() -> None:
    """Job: Processa transacoes recorrentes do dia.
    Execucao: diariamente as 00:10
    """
    app_logger.info("[Scheduler] Iniciando job: process_recurrences")
    try:
        from database.models.user import User
        from services.recurrence_service import RecurrenceService

        with get_db_session() as db:
            users = db.query(User).filter(User.is_active == True, User.is_deleted == False).all()
            total_processed = 0
            for user in users:
                svc = RecurrenceService(db)
                if hasattr(svc, "process_due_recurrences"):
                    count = svc.process_due_recurrences(user.id)
                    total_processed += count

        app_logger.info(f"[Scheduler] process_recurrences concluido: {total_processed} recorrencias processadas")
    except Exception as exc:
        app_logger.error(f"[Scheduler] Erro em process_recurrences: {exc}", exc_info=True)


def _job_check_goals() -> None:
    """Job: Verifica metas atingidas e status.
    Execucao: a cada hora
    """
    app_logger.info("[Scheduler] Iniciando job: check_goals")
    try:
        from database.models.user import User
        from database.models.goal import Goal, GoalStatus
        from services.goal_service import GoalService

        with get_db_session() as db:
            users = db.query(User).filter(User.is_active == True, User.is_deleted == False).all()
            goals_completed = 0
            for user in users:
                svc = GoalService(db)
                active_goals = svc.list_goals(user.id, status=GoalStatus.ACTIVE)
                for goal in active_goals:
                    if goal.current_amount >= goal.target_amount:
                        svc._check_completion(goal)
                        if goal.status == GoalStatus.COMPLETED:
                            goals_completed += 1
                            db.commit()

        app_logger.info(f"[Scheduler] check_goals concluido: {goals_completed} metas concluidas")
    except Exception as exc:
        app_logger.error(f"[Scheduler] Erro em check_goals: {exc}", exc_info=True)


def _job_send_weekly_reports() -> None:
    """Job: Envia resumo financeiro semanal por e-mail.
    Execucao: toda sexta-feira as 18:00
    """
    app_logger.info("[Scheduler] Iniciando job: send_weekly_reports")
    try:
        from database.models.user import User
        from services.report_service import ReportService
        from services.email_service import send_email, render_email_template

        with get_db_session() as db:
            query = db.query(User).filter(
                User.is_active == True,
                User.is_deleted == False,
            )
            if hasattr(User, "email_notifications"):
                query = query.filter(User.email_notifications == True)

            users  = query.all()
            sent   = 0
            errors = 0

            for user in users:
                try:
                    svc   = ReportService(db)
                    today = date.today()
                    report = svc.generate_monthly_report(
                        user_id=user.id,
                        year=today.year,
                        month=today.month,
                    )

                    resumo     = report.get("resumo", {})
                    categorias = report.get("categorias", {})
                    top_cats   = sorted(
                        categorias.get("despesas", []),
                        key=lambda c: c.get("total", 0),
                        reverse=True,
                    )[:5]

                    summary = {
                        "week_label":     _get_week_label(),
                        "user_name":      getattr(user, "name", getattr(user, "username", "voce")),
                        "total_receitas": resumo.get("total_receitas", 0.0),
                        "total_despesas": resumo.get("total_despesas", 0.0),
                        "saldo":          resumo.get("saldo", 0.0),
                        "top_categorias": [
                            {"nome": c.get("category_name", c.get("nome", "-")), "valor": c.get("total", 0)}
                            for c in top_cats
                        ],
                        "alertas": [],
                    }

                    success = send_email(
                        to=user.email,
                        subject=f"💰 Seu resumo financeiro — {summary['week_label']}",
                        html_body=render_email_template(summary),
                    )
                    if success:
                        sent += 1
                    else:
                        errors += 1

                except Exception as user_exc:
                    errors += 1
                    app_logger.warning(f"[Scheduler] Falha para user_id={user.id}: {user_exc}")

        app_logger.info(f"[Scheduler] send_weekly_reports concluido: {sent} enviados, {errors} erros")

    except ImportError as exc:
        app_logger.warning(f"[Scheduler] email_service nao disponivel - job ignorado: {exc}")
    except Exception as exc:
        app_logger.error(f"[Scheduler] Erro em send_weekly_reports: {exc}", exc_info=True)


# ------------------------------------------------------------------ #
# HELPERS INTERNOS                                                      #
# ------------------------------------------------------------------ #

def _get_week_label() -> str:
    """Retorna label legivel da semana atual, ex: '05/05 a 11/05/2026'."""
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end   = start + timedelta(days=6)
    if start.month == end.month:
        return f"{start.day:02d} a {end.day:02d}/{end.month:02d}/{end.year}"
    return f"{start.day:02d}/{start.month:02d} a {end.day:02d}/{end.month:02d}/{end.year}"


# ------------------------------------------------------------------ #
# LISTENER DE EVENTOS                                                   #
# ------------------------------------------------------------------ #

def _scheduler_event_listener(event) -> None:
    """Loga erros de jobs em producao."""
    if event.exception:
        app_logger.error(f"[Scheduler] Job '{event.job_id}' falhou: {event.exception}")


# ------------------------------------------------------------------ #
# INICIALIZACAO E SHUTDOWN                                              #
# ------------------------------------------------------------------ #

def get_scheduler() -> Optional[BackgroundScheduler]:
    """Retorna a instancia do scheduler (singleton)."""
    return _scheduler


def start_scheduler() -> BackgroundScheduler:
    """Inicializa e inicia o scheduler em background.

    Deve ser chamado UMA vez durante a inicializacao do app.py.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        app_logger.warning("[Scheduler] Scheduler ja em execucao. Ignorado.")
        return _scheduler

    _scheduler = BackgroundScheduler(
        timezone="America/Sao_Paulo",
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,
        },
    )

    _scheduler.add_listener(_scheduler_event_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

    # Job 1: Contas vencidas - todo dia as 00:05
    _scheduler.add_job(
        _job_update_overdue_bills,
        trigger=CronTrigger(hour=0, minute=5, timezone="America/Sao_Paulo"),
        id="update_overdue_bills",
        name="Atualizar Contas Vencidas",
        replace_existing=True,
    )

    # Job 2: Recorrencias - todo dia as 00:10
    _scheduler.add_job(
        _job_process_recurrences,
        trigger=CronTrigger(hour=0, minute=10, timezone="America/Sao_Paulo"),
        id="process_recurrences",
        name="Processar Recorrencias",
        replace_existing=True,
    )

    # Job 3: Verificar metas - a cada hora
    _scheduler.add_job(
        _job_check_goals,
        trigger=CronTrigger(minute=0, timezone="America/Sao_Paulo"),
        id="check_goals",
        name="Verificar Metas Financeiras",
        replace_existing=True,
    )

    # Job 4: Relatorio semanal - toda sexta-feira as 18:00
    _scheduler.add_job(
        _job_send_weekly_reports,
        trigger=CronTrigger(day_of_week="fri", hour=18, minute=0, timezone="America/Sao_Paulo"),
        id="weekly_report",
        name="Relatorio Semanal por E-mail",
        replace_existing=True,
    )

    _scheduler.start()
    app_logger.info(
        f"[Scheduler] Scheduler iniciado. Jobs registrados: {len(_scheduler.get_jobs())}"
    )
    return _scheduler


def stop_scheduler() -> None:
    """Para o scheduler de forma segura."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=True)
        app_logger.info("[Scheduler] Scheduler parado com sucesso.")
    _scheduler = None
