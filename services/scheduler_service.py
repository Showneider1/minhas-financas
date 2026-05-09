"""Background Job Scheduler usando APScheduler.

Executa tarefas automaticas em background:
1. Diariamente 00:05: Detecta contas vencidas e atualiza status para OVERDUE
2. Diariamente 00:10: Processa transacoes recorrentes do dia
3. A cada hora: Verifica metas atingidas e marca como concluidas

Uso: importado e iniciado pelo app.py na inicializacao da aplicacao.
O scheduler roda em modo daemon (nao bloqueia o processo principal).
"""
import logging
from datetime import date, datetime, timezone
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

    Percorre todos os usuarios ativos e verifica se alguma conta
    com status PENDING tem due_date anterior a hoje.

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

        app_logger.info(
            f"[Scheduler] update_overdue_bills concluido: {total_updated} contas vencidas encontradas"
        )
    except Exception as exc:
        app_logger.error(f"[Scheduler] Erro em update_overdue_bills: {exc}", exc_info=True)


def _job_process_recurrences() -> None:
    """Job: Processa transacoes recorrentes do dia.

    Verifica transacoes marcadas como recorrentes que tenham
    data de vencimento igual a hoje e ainda nao foram geradas.

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
                # Verifica se o service tem o metodo process_due_recurrences
                if hasattr(svc, "process_due_recurrences"):
                    count = svc.process_due_recurrences(user.id)
                    total_processed += count

        app_logger.info(
            f"[Scheduler] process_recurrences concluido: {total_processed} recorrencias processadas"
        )
    except Exception as exc:
        app_logger.error(f"[Scheduler] Erro em process_recurrences: {exc}", exc_info=True)


def _job_check_goals() -> None:
    """Job: Verifica metas atingidas e status.

    Para cada usuario, percorre as metas ativas e verifica se
    alguma foi concluida ou esta proxima do prazo.

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

        app_logger.info(
            f"[Scheduler] check_goals concluido: {goals_completed} metas concluidas"
        )
    except Exception as exc:
        app_logger.error(f"[Scheduler] Erro em check_goals: {exc}", exc_info=True)


# ------------------------------------------------------------------ #
# LISTENER DE EVENTOS                                                   #
# ------------------------------------------------------------------ #

def _scheduler_event_listener(event) -> None:
    """Loga erros de jobs em producao."""
    if event.exception:
        app_logger.error(
            f"[Scheduler] Job '{event.job_id}' falhou com excecao: {event.exception}"
        )


# ------------------------------------------------------------------ #
# INICIALIZACAO E SHUTDOWN                                              #
# ------------------------------------------------------------------ #

def get_scheduler() -> Optional[BackgroundScheduler]:
    """Retorna a instancia do scheduler (singleton)."""
    return _scheduler


def start_scheduler() -> BackgroundScheduler:
    """Inicializa e inicia o scheduler em background.

    Deve ser chamado UMA vez durante a inicializacao do app.py.
    O scheduler roda como daemon e para automaticamente quando o
    processo principal encerra.

    Returns:
        Instancia do BackgroundScheduler configurado e iniciado
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        app_logger.warning("[Scheduler] Tentativa de iniciar scheduler ja em execucao. Ignorado.")
        return _scheduler

    _scheduler = BackgroundScheduler(
        timezone="America/Sao_Paulo",
        job_defaults={
            "coalesce": True,       # Se atrasado, executa apenas 1x
            "max_instances": 1,     # Nao permite execucoes paralelas
            "misfire_grace_time": 300,  # Aceita ate 5min de atraso
        },
    )

    # Registrar listener de erros
    _scheduler.add_listener(_scheduler_event_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

    # ---- Registrar Jobs ---- #

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
        trigger=CronTrigger(minute=0, timezone="America/Sao_Paulo"),  # Topo de cada hora
        id="check_goals",
        name="Verificar Metas Financeiras",
        replace_existing=True,
    )

    _scheduler.start()
    app_logger.info(
        "[Scheduler] Background scheduler iniciado com sucesso. "
        f"Jobs registrados: {len(_scheduler.get_jobs())}"
    )
    return _scheduler


def stop_scheduler() -> None:
    """Para o scheduler de forma segura.

    Deve ser chamado no shutdown do servidor para evitar
    threads orfas em producao.
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=True)  # Aguarda jobs ativos terminarem
        app_logger.info("[Scheduler] Scheduler parado com sucesso.")
    _scheduler = None
