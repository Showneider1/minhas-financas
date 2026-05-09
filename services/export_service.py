"""
Serviço de exportação de dados para PDF, Excel e CSV.
"""
import pandas as pd
from io import BytesIO
from typing import List, Dict, Any
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from config.settings import settings
from config.logging_config import app_logger


class ExportService:
    """
    Serviço responsável por exportação de dados.
    """
    
    @staticmethod
    def to_excel(
        data: List[Dict[str, Any]],
        sheet_name: str = "Dados",
        title: str = "Relatório Financeiro",
    ) -> BytesIO:
        """
        Exporta dados para Excel com formatação.
        
        Args:
            data: Lista de dicionários com dados
            sheet_name: Nome da planilha
            title: Título do relatório
        
        Returns:
            BytesIO com arquivo Excel
        """
        if not data:
            data = [{"mensagem": "Sem dados para exportar"}]
        
        df = pd.DataFrame(data)
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=2)
            
            # Acessa workbook e worksheet
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]
            
            # Formatos
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4F46E5',
                'font_color': 'white',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
            })
            
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 16,
                'align': 'center',
            })
            
            money_format = workbook.add_format({'num_format': 'R$ #,##0.00'})
            date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
            
            # Título
            worksheet.merge_range('A1:' + chr(65 + len(df.columns) - 1) + '1', title, title_format)
            
            # Cabeçalhos
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(2, col_num, value, header_format)
            
            # Ajusta largura das colunas
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(max_len, 50))
        
        output.seek(0)
        app_logger.info("Arquivo Excel gerado com sucesso")
        return output
    
    @staticmethod
    def to_csv(
        data: List[Dict[str, Any]],
        delimiter: str = ";",
    ) -> BytesIO:
        """
        Exporta dados para CSV.
        
        Args:
            data: Lista de dicionários
            delimiter: Delimitador (padrão: ponto e vírgula)
        
        Returns:
            BytesIO com arquivo CSV
        """
        if not data:
            data = [{"mensagem": "Sem dados para exportar"}]
        
        df = pd.DataFrame(data)
        output = BytesIO()
        
        # Escreve CSV com encoding UTF-8
        csv_string = df.to_csv(index=False, sep=delimiter, encoding='utf-8-sig')
        output.write(csv_string.encode('utf-8-sig'))
        output.seek(0)
        
        app_logger.info("Arquivo CSV gerado com sucesso")
        return output
    
    @staticmethod
    def to_pdf(
        data: List[Dict[str, Any]],
        title: str = "Relatório Financeiro",
        subtitle: str = "",
    ) -> BytesIO:
        """
        Exporta dados para PDF com formatação.
        
        Args:
            data: Lista de dicionários
            title: Título do relatório
            subtitle: Subtítulo
        
        Returns:
            BytesIO com arquivo PDF
        """
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Estilo customizado para título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1F2937'),
            spaceAfter=12,
            alignment=TA_CENTER,
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#6B7280'),
            spaceAfter=20,
            alignment=TA_CENTER,
        )
        
        # Adiciona título
        elements.append(Paragraph(title, title_style))
        
        if subtitle:
            elements.append(Paragraph(subtitle, subtitle_style))
        
        elements.append(Spacer(1, 0.2 * inch))
        
        # Adiciona data de geração
        date_text = f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
        elements.append(Paragraph(date_text, styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))
        
        if not data:
            elements.append(Paragraph("Sem dados para exibir", styles['Normal']))
        else:
            # Prepara dados da tabela
            df = pd.DataFrame(data)
            
            # Limita colunas se necessário
            if len(df.columns) > 6:
                df = df.iloc[:, :6]
            
            # Converte para lista de listas
            table_data = [df.columns.tolist()] + df.values.tolist()
            
            # Cria tabela
            table = Table(table_data)
            table.setStyle(TableStyle([
                # Cabeçalho
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Corpo
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                
                # Linhas alternadas
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            
            elements.append(table)
        
        # Gera PDF
        doc.build(elements)
        output.seek(0)
        
        app_logger.info("Arquivo PDF gerado com sucesso")
        return output
