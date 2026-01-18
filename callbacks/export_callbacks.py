"""
Callbacks para exportação de dados.
"""
from dash import Input, Output, State, dcc, callback_context
import dash_bootstrap_components as dbc
from datetime import datetime, date
from app import app
from database.connection import get_db_session
from config.logging_config import app_logger
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT



@app.callback(
    Output("download-extrato", "data"),
    Input("btn-export-pdf", "n_clicks"),
    State("store-user-id", "data"),
    State("extrato-periodo", "start_date"),
    State("extrato-periodo", "end_date"),
    State("extrato-tipo", "value"),
    State("extrato-status", "value"),
    prevent_initial_call=True,
)
def exportar_extrato(n_clicks, user_id, start_date, end_date, tipos, status_list):
    """
    Exporta extrato em PDF.
    """
    print(f"\n📄 EXPORTANDO EXTRATO")
    print(f"   user_id: {user_id}")
    
    try:
        if not n_clicks or not user_id:
            return None
        
        # Converte datas
        if start_date:
            data_inicio = datetime.fromisoformat(start_date).date()
        else:
            data_inicio = date.today().replace(day=1)
        
        if end_date:
            data_fim = datetime.fromisoformat(end_date).date()
        else:
            data_fim = date.today()
        
        print(f"   📅 Período: {data_inicio} até {data_fim}")
        
        with get_db_session() as db:
            from database.models.transaction import Transaction
            from database.models.category import TransactionType
            
            # Query
            query = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.due_date >= data_inicio,
                Transaction.due_date <= data_fim
            )
            
            # Filtros
            if tipos:
                query = query.filter(Transaction.transaction_type.in_(tipos))
            
            if status_list:
                if "PAID" in status_list and "PENDING" not in status_list:
                    query = query.filter(Transaction.paid_date.isnot(None))
                elif "PENDING" in status_list and "PAID" not in status_list:
                    query = query.filter(Transaction.paid_date.is_(None))
            
            query = query.order_by(Transaction.due_date.desc())
            transactions = query.all()
            
            print(f"   📊 Total de transações: {len(transactions)}")
            
            # Gera PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            elements.append(Paragraph("Extrato Financeiro", title_style))
            elements.append(Paragraph(
                f"Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
                styles['Normal']
            ))
            elements.append(Spacer(1, 20))
            
            # Tabela
            data = [["Data", "Descrição", "Categoria", "Tipo", "Valor", "Status"]]
            
            for t in transactions:
                tipo_str = "Receita" if t.transaction_type == TransactionType.INCOME else "Despesa"
                status_str = "Pago" if t.paid_date else "Pendente"
                valor_str = f"R$ {t.base_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                data_str = t.due_date.strftime("%d/%m/%Y")
                
                data.append([
                    data_str,
                    t.description[:30],
                    t.category.name[:20],
                    tipo_str,
                    valor_str,
                    status_str
                ])
            
            table = Table(data, colWidths=[1*inch, 2*inch, 1.5*inch, 1*inch, 1.2*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
            doc.build(elements)
            
            buffer.seek(0)
            filename = f"extrato_{data_inicio}_{data_fim}.pdf"
            
            print(f"   ✅ PDF gerado: {filename}")
            
            return dcc.send_bytes(buffer.getvalue(), filename=filename)
    
    except Exception as e:
        app_logger.error(f"Erro ao exportar: {e}")
        import traceback
        traceback.print_exc()
        return None



@app.callback(
    Output("download-dashboard", "data"),
    Input("btn-export-dashboard", "n_clicks"),
    State("store-user-id", "data"),
    State("dashboard-periodo", "start_date"),
    State("dashboard-periodo", "end_date"),
    prevent_initial_call=True,
)
def exportar_dashboard(n_clicks, user_id, start_date, end_date):
    """
    Exporta relatório do dashboard em PDF.
    """
    try:
        if not n_clicks or not user_id:
            return None
        
        # Converte datas
        if start_date:
            data_inicio = datetime.fromisoformat(start_date).date()
        else:
            data_inicio = date.today().replace(day=1)
        
        if end_date:
            data_fim = datetime.fromisoformat(end_date).date()
        else:
            data_fim = date.today()
        
        with get_db_session() as db:
            from database.models.transaction import Transaction
            from database.models.category import TransactionType
            
            # Calcula totais
            receitas = db.query(
                func.sum(Transaction.base_amount)
            ).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.INCOME,
                Transaction.paid_date.isnot(None),
                Transaction.paid_date >= data_inicio,
                Transaction.paid_date <= data_fim
            ).scalar() or 0
            
            despesas = db.query(
                func.sum(Transaction.base_amount)
            ).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.paid_date.isnot(None),
                Transaction.paid_date >= data_inicio,
                Transaction.paid_date <= data_fim
            ).scalar() or 0
            
            saldo = receitas - despesas
            
            # Gera PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            elements.append(Paragraph("Relatório Financeiro", title_style))
            elements.append(Paragraph(
                f"Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
                styles['Normal']
            ))
            elements.append(Spacer(1, 20))
            
            # Resumo
            data = [
                ["Métrica", "Valor"],
                ["Receitas", f"R$ {receitas:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")],
                ["Despesas", f"R$ {despesas:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")],
                ["Saldo", f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")],
            ]
            
            table = Table(data, colWidths=[3*inch, 3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
            doc.build(elements)
            
            buffer.seek(0)
            filename = f"dashboard_{data_inicio}_{data_fim}.pdf"
            
            return dcc.send_bytes(buffer.getvalue(), filename=filename)
    
    except Exception as e:
        app_logger.error(f"Erro ao exportar dashboard: {e}")
        import traceback
        traceback.print_exc()
        return None
