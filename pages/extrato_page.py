from dash import dcc, html
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
from datetime import date

# ===============================
# DEFINIÇÃO DAS COLUNAS
# ===============================
columnDefs = [
    # Data
    {
        "field": "data", 
        "headerName": "DATA", 
        "sortable": True, 
        "filter": True, 
        "width": 110,
        "cellStyle": {"color": "#4B5563", "display": "flex", "alignItems": "center"} 
    },
    
    # Categoria
    {
        "field": "categoria", 
        "headerName": "CATEGORIA", 
        "sortable": True, 
        "filter": True, 
        "width": 180,
        "cellStyle": {"display": "flex", "alignItems": "center", "fontWeight": "500"}
    },
    
    # Descrição
    {
        "field": "descricao", 
        "headerName": "DESCRIÇÃO", 
        "sortable": True, 
        "filter": True, 
        "flex": 1,
        "cellStyle": {"display": "flex", "alignItems": "center"}
    },
    
    # Conta
    {
        "field": "conta", 
        "headerName": "CONTA", 
        "sortable": True, 
        "filter": True, 
        "width": 140,
        "cellStyle": {"display": "flex", "alignItems": "center", "color": "#6B7280"}
    },
    
    # Valor
    {
        "field": "valor", 
        "headerName": "VALOR", 
        "sortable": True, 
        "type": "numericColumn",
        "width": 140,
        "valueFormatter": {"function": "'R$ ' + params.value.toLocaleString('pt-BR', {minimumFractionDigits: 2})"},
        "cellClass": {"function": "params.data.tipo == 'Receita' ? 'valor-positivo' : 'valor-negativo'"},
        "cellStyle": {"display": "flex", "alignItems": "center", "justifyContent": "flex-end"}
    },
    
    # Status
    {
        "field": "status",
        "headerName": "STATUS",
        "width": 110,
        "sortable": True,
        "filter": True,
        "cellStyle": {"display": "flex", "alignItems": "center", "justifyContent": "center", "fontWeight": "600"},
        "cellClass": {"function": "params.value == 'Pago' ? 'text-success' : 'text-warning'"},
    },

    # Tipo (Escondido)
    {"field": "tipo", "hide": True},
    
    # Ações
    {
        "field": "editar",
        "headerName": "",
        "width": 60,
        "cellStyle": {"cursor": "pointer", "fontSize": "20px", "textAlign": "center", "display": "flex", "alignItems": "center", "justifyContent": "center"},
        "tooltipField": "editar",
        "valueFormatter": {"function": "'✏️'"},
    },
    {
        "field": "excluir",
        "headerName": "",
        "width": 60,
        "cellStyle": {"cursor": "pointer", "fontSize": "20px", "textAlign": "center", "display": "flex", "alignItems": "center", "justifyContent": "center"},
        "cellClass": "btn-trash",
        "valueFormatter": {"function": "'🗑️'"},
    },
]

# ===============================
# LAYOUT
# ===============================
layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H2("Extrato", className="fw-bold"),
            html.P("Histórico completo de transações", className="text-muted"),
        ], md=8),
        dbc.Col([
            dcc.DatePickerRange(
                id="extrato-periodo",
                start_date=date.today().replace(day=1),
                end_date=date.today(),
                display_format="DD/MM/YYYY",
                className="form-control d-inline-block shadow-sm",
                style={"border": "1px solid #ced4da", "borderRadius": "5px"}
            ),
        ], md=4, className="text-end"),
    ], className="mb-4 align-items-end"),
    
    dbc.Card([
        dbc.CardBody([
            dag.AgGrid(
                id="grid-transacoes",
                columnDefs=columnDefs,
                rowData=[],
                className="ag-theme-alpine",
                columnSize="sizeToFit",
                defaultColDef={
                    "resizable": True, 
                    "sortable": True, 
                    "filter": True,
                    "floatingFilter": True,
                },
                dashGridOptions={
                    "pagination": True, 
                    "paginationPageSize": 12, 
                    "domLayout": "autoHeight",
                    "rowHeight": 40,
                    "headerHeight": 45,
                    "animateRows": True,
                },
                style={"height": None},
            ),
        ], className="p-0")
    ], className="shadow-sm border-0 overflow-hidden"),

    # === NOVO: STORE PARA GUARDAR O ID QUE SERÁ EXCLUÍDO ===
    dcc.Store(id="store-id-exclusao", data=None),

    # === NOVO: MODAL DE CONFIRMAÇÃO ===
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Confirmar Exclusão")),
            dbc.ModalBody("Tem certeza que deseja excluir este lançamento? Esta ação não pode ser desfeita."),
            dbc.ModalFooter(
                [
                    dbc.Button("Cancelar", id="btn-cancelar-exclusao", className="ms-auto", n_clicks=0),
                    dbc.Button("Sim, Excluir", id="btn-confirmar-exclusao", color="danger", n_clicks=0),
                ]
            ),
        ],
        id="modal-confirmacao-exclusao",
        is_open=False,
    ),
])