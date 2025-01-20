import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import dash.dash_table as dt
import pandas as pd
import psycopg2
import requests
import json
from flask_caching import Cache

# Token de autenticação
TOKEN_CORRETO = "#Finacap@"

# Inicializando o aplicativo Dash
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Dashboard Finacap"
app.config.suppress_callback_exceptions = True

# Inicialize o cache
cache = Cache(app.server, config={'CACHE_TYPE': 'simple'})

# Função para obter os dados do banco de dados PostgreSQL com cache
@cache.memoize(timeout=60)  # Cache por 60 segundos
def fetch_postgres_data():
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="Nautico1901",
        host="localhost",
        port="5432",
    )
    query = """
    SELECT codigo_finacap, cliente_ativo, nome_cliente, gestor, suitability_cliente,
           perfil_risco_ips, tipo_ips, patrimonio
    FROM clientes;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Função para obter os dados da API do Comdinheiro com alterações e cache
@cache.memoize(timeout=60)  # Cache por 60 segundos
def fetch_comdinheiro_data():
    url = "https://www.comdinheiro.com.br/Clientes/API/EndPoint001.php"
    querystring = {"code": "import_data"}

    payload = {
        "username": "consulta.finacap",
        "password": "#Consult@finac@p2025",
        "URL": "RelatorioGerencialCarteiras001.php?&data_analise=10012025",
        "format": "json3",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, data=payload, headers=headers, params=querystring)
        response.raise_for_status()
        api_data = response.json()

        if "tables" in api_data and "tab0" in api_data["tables"]:
            table_data = api_data["tables"]["tab0"]

            # Processar as linhas para criar registros
            data_list = []
            for key, value in table_data.items():
                record = {
                    "Carteira": value.get("col0", "Não disponível"),
                    "Ativo": value.get("col1", "Não disponível"),
                    "Descrição": value.get("col2", "Não disponível"),
                    "Saldo Bruto": value.get("col3", "Não disponível"),
                }
                data_list.append(record)

            df_api = pd.DataFrame(data_list)
            return df_api
        else:
            return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão: {e}")
        return pd.DataFrame()
    except KeyError as e:
        print(f"Erro no formato da resposta: {e}")
        return pd.DataFrame()

# Função para combinar os dados de ambas as fontes
def fetch_data(tipo="postgres"):
    print(f"Buscando dados da fonte: {tipo}")  # Debugging
    if tipo == "postgres":
        # Retorna os dados do banco de dados para clientes e clientes ativos
        df = fetch_postgres_data()
        print("Dados do PostgreSQL carregados:")
        print(df.head())  # Exibe as primeiras linhas para depuração
        return df
    elif tipo == "api":
        # Retorna os dados da API para o relatório gerencial
        df_api = fetch_comdinheiro_data()
        if df_api.empty:
            print("Erro ao recuperar dados da API ou dados vazios.")
            return pd.DataFrame()  # Retorna um DataFrame vazio se der erro
        else:
            print("Dados da API carregados:")
            print(
                df_api.head()
            )  # Exibe as primeiras linhas dos dados da API para depuração
            return df_api

# Dados iniciais - Carrega tanto os dados do banco de dados quanto da API
df_postgres = fetch_data(tipo="postgres")  # Carregar dados do banco para clientes
df_api = fetch_data(tipo="api")  # Carregar dados da API para o relatório gerencial

df_postgres["cliente_ativo"] = df_postgres["cliente_ativo"].str.strip().str.capitalize()
df_postgres["perfil_risco_ips"] = pd.to_numeric(
    df_postgres["perfil_risco_ips"], errors="coerce"
)

# Gráficos
fig_pie = px.pie(
    df_postgres,
    names="suitability_cliente",
    values="patrimonio",
    title="Distribuição de Patrimônio por Suitability",
)
fig_bar = px.bar(
    df_postgres, x="nome_cliente", y="patrimonio", title="Patrimônio por Cliente"
)

# Layout da tela de autenticação
auth_layout = html.Div(
    [
        html.Div(
            [
                html.Img(src="/assets/logo_finacap.png", className="logo"),
                html.H3("Acesso ao Sistema", className="auth-title"),
                dcc.Input(
                    id="token-input",
                    type="password",
                    placeholder="Digite o token...",
                    className="input-field",
                ),
                html.Button(
                    html.I(className="fa fa-eye"),
                    id="toggle-password",
                    n_clicks=0,
                    className="eye-button",
                ),
                html.Button(
                    "Entrar", id="submit-button", n_clicks=0, className="button"
                ),
                html.Div(id="token-status", className="status-message"),
            ],
            className="auth-box",
        )
    ],
    className="main-container",
)

# Layout principal do dashboard
sidebar = html.Div(
    [
        html.Img(src="/assets/logo_finacap.png", className="logo"),
        html.H2("Dashboard Finacap", className="title"),
        html.Hr(),
        html.Div(
            [
                dcc.Link(
                    "Clientes Ativos", href="/clientes-ativos", className="menu-item"
                ),
                dcc.Link("Clientes", href="/clientes", className="menu-item"),
                dcc.Link(
                    "Revisões Pendentes",
                    href="/revisoes-pendentes",
                    className="menu-item",
                ),
                dcc.Link(
                    "Relatório Gerencial",
                    href="/relatorio-gerencial",
                    className="menu-item",
                ),
                dcc.Link("Lamina", href="/lamina", className="menu-item"),
                dcc.Link("Sair", href="/sair", className="menu-item"),
            ],
            className="menu-container",
        ),
        html.Button("Atualizar Dados", id="update-data-btn", className="update-button"),
    ],
    className="sidebar",
)

footer = html.Div("\u00a9 2025 Finacap Investimentos Ltda", className="footer")

dashboard_layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        sidebar,
        html.Div(id="page-content", className="content"),
        footer,
    ]
)

# Página de login com autenticação
@app.callback(
    [Output("auth-page-content", "children"), Output("token-status", "children")],
    [Input("submit-button", "n_clicks")],
    [State("token-input", "value")],
)
def validate_login(n_clicks, token_value):
    if n_clicks > 0:
        if token_value == TOKEN_CORRETO:
            return dashboard_layout, ""
        else:
            return auth_layout, "Token inválido! Tente novamente."
    return auth_layout, ""


# Ajuste no layout da página "Relatório Gerencial"
relatorio_gerencial_page = html.Div(
    [
        html.H3("Relatório Gerencial Carteiras", className="page-title"),
        html.Div(
            [
                dcc.Input(
                    id="search-bar",
                    type="text",
                    placeholder="Buscar...",
                    style={
                        "marginBottom": "10px",
                        "width": "50%",
                        "padding": "5px",
                        "fontSize": "14px",
                    },
                ),
                dcc.Dropdown(
                    id="filter-column",
                    options=[
                        {"label": "Todos", "value": "all"},
                        {"label": "Carteira", "value": "Carteira"},
                        {"label": "Ativo", "value": "Ativo"},
                        {"label": "Descrição", "value": "Descrição"},
                        {"label": "Saldo Bruto", "value": "Saldo Bruto"},
                    ],
                    placeholder="Filtrar por coluna...",
                    style={"marginBottom": "10px", "width": "50%"},
                ),
            ],
            style={"display": "flex", "justifyContent": "space-between"},
        ),
        dt.DataTable(
            id="relatorio-table",
            columns=[
                {"name": "Carteira", "id": "Carteira"},
                {"name": "Ativo", "id": "Ativo"},
                {"name": "Descrição", "id": "Descrição"},
                {"name": "Saldo Bruto", "id": "Saldo Bruto"},
            ],
            data=fetch_comdinheiro_data().to_dict("records"),  # Dados da API
            style_table={"overflowX": "auto", "maxHeight": "500px"},
            style_header={
                "backgroundColor": "#1b51b1",
                "color": "white",
                "fontWeight": "bold",
            },
            style_cell={"textAlign": "center", "padding": "10px"},
        ),
    ]
)


# Página de clientes
clientes_ativos_page = html.Div(
    [
        html.H3("Clientes Ativos", className="page-title"),
        html.Div(
            [
                html.Div(
                    [
                        html.H3(
                            f"{df_postgres['cliente_ativo'].value_counts().get('Sim', 0)}",
                            className="card-value",
                        ),
                        html.P("Clientes Ativos", className="card-label"),
                    ],
                    className="card",
                ),
                html.Div(
                    [
                        html.H3(
                            f"{len(df_postgres[df_postgres['perfil_risco_ips'] > 4])}",
                            className="card-value",
                        ),
                        html.P("Revisões Pendentes", className="card-label"),
                    ],
                    className="card",
                ),
                html.Div(
                    [
                        html.H3(
                            f"{df_postgres['perfil_risco_ips'].mean():.1f}",
                            className="card-value",
                        ),
                        html.P("Exposição CP Média", className="card-label"),
                    ],
                    className="card",
                ),
            ],
            className="cards-container",
        ),
        html.Div(
            [
                dcc.Graph(figure=fig_pie, className="graph"),
                dcc.Graph(figure=fig_bar, className="graph"),
            ],
            className="graphs-container",
        ),
    ]
)

# Página de clientes
tabela_clientes_page = html.Div(
    [
        html.H3("Tabela de Clientes", className="page-title"),
        html.Div(
            [
                dcc.Input(
                    id="search-bar",
                    type="text",
                    placeholder="Buscar...",
                    style={
                        "marginBottom": "10px",
                        "width": "50%",
                        "padding": "5px",
                        "fontSize": "14px",
                    },
                ),
                dcc.Dropdown(
                    id="filter-column",
                    options=[
                        {"label": "Todos", "value": "all"},
                        {"label": "Nome Cliente", "value": "nome_cliente"},
                        {"label": "Patrimônio", "value": "patrimonio"},
                        {"label": "Gestor", "value": "gestor"},
                        {"label": "Cliente Ativo", "value": "cliente_ativo"},
                        {
                            "label": "Suitability Cliente",
                            "value": "suitability_cliente",
                        },
                        {"label": "Perfil Risco IPS", "value": "perfil_risco_ips"},
                        {"label": "Tipo IPS", "value": "tipo_ips"},
                        {"label": "Código Finacap", "value": "codigo_finacap"},
                    ],
                    placeholder="Filtrar por coluna...",
                    style={"marginBottom": "10px", "width": "50%"},
                ),
            ],
            style={"display": "flex", "justifyContent": "space-between"},
        ),
        dt.DataTable(
            id="clientes-table",
            columns=[{"name": col, "id": col} for col in df_postgres.columns],
            data=df_postgres.to_dict("records"),
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": "#1b51b1",
                "color": "white",
                "fontWeight": "bold",
            },
            style_cell={"textAlign": "center", "padding": "10px"},
        ),
    ]
)

# Página "Lamina"
lamina_page = html.Div(
    [
        html.H3("Selecione um Cliente", className="page-title"),
        # Tabela de clientes
        dt.DataTable(
            id="clientes-list-table",
            columns=[
                {"name": "Código Finacap", "id": "codigo_finacap"},
                {"name": "Nome Cliente", "id": "nome_cliente"},
                {"name": "Gestor", "id": "gestor"},
                {"name": "Suitability Cliente", "id": "suitability_cliente"},
                {"name": "Patrimônio", "id": "patrimonio"},
            ],
            data=df_postgres.to_dict("records"),
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": "#1b51b1",
                "color": "white",
                "fontWeight": "bold",
            },
            style_cell={"textAlign": "center", "padding": "10px"},
            # Seleção de uma linha
            row_selectable="single",
            selected_rows=[],
        ),
        # Div para mostrar as informações detalhadas do cliente selecionado
        html.Div(id="client-detail-info", style={"marginTop": "20px"}),
    ]
)

# Callback para exibir as informações detalhadas do cliente
@app.callback(
    Output("client-detail-info", "children"),
    [Input("clientes-list-table", "selected_rows")]
)
def display_client_details(selected_rows):
    if selected_rows:
        # Pegando o índice da linha selecionada
        selected_row = selected_rows[0]
        client_data = df_postgres.iloc[selected_row]
        
        # Detalhes do cliente selecionado
        client_details = html.Div(
            [
                html.H4(f"Detalhes do Cliente: {client_data['nome_cliente']}"),
                html.Div(f"Código Finacap: {client_data['codigo_finacap']}"),
                html.Div(f"Gestor: {client_data['gestor']}"),
                html.Div(f"Suitability Cliente: {client_data['suitability_cliente']}"),
                html.Div(f"Patrimônio: R$ {client_data['patrimonio']:.2f}"),
                html.Div(f"Perfil de Risco IPS: {client_data['perfil_risco_ips']}"),
                html.Div(f"Tipo IPS: {client_data['tipo_ips']}"),
            ]
        )
        return client_details
    return html.Div("Selecione um cliente para ver os detalhes.")

# Callbacks para atualizar as tabelas e gráficos
@app.callback(
    Output("relatorio-table", "data"),
    [
        Input("update-data-btn", "n_clicks"),
        Input("search-bar", "value"),
        Input("filter-column", "value"),
    ],
)
def update_relatorio_gerencial_data(n_clicks, search_value, filter_column):
    print("Atualizando Relatório Gerencial...")
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # Usar dados da API para a tabela de Relatório Gerencial
    df_api = fetch_comdinheiro_data()

    print("Dados carregados para Relatório Gerencial:")
    print(df_api.head())

    if df_api.empty:
        return []  # Retorna uma lista vazia se não houver dados

    # Garantir que os dados estejam sendo enviados corretamente
    filtered_df = df_api.copy()

    # Aplicar busca
    if search_value:
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row: row.astype(str)
                .str.contains(search_value, case=False)
                .any(),
                axis=1,
            )
        ]

    # Aplicar filtro de coluna
    if filter_column and filter_column != "all":
        filtered_df = filtered_df[[filter_column]]

    return filtered_df.to_dict("records")


# Callback para atualizar a página de conteúdo de acordo com a URL
@app.callback(
    Output("page-content", "children"), [Input("url", "pathname")]
)
def display_page(pathname):
    if pathname in ["/clientes-ativos", "/"]:
        return clientes_ativos_page
    elif pathname == "/clientes":
        return tabela_clientes_page
    elif pathname == "/relatorio-gerencial":
        return relatorio_gerencial_page
    elif pathname == "/lamina":
        return lamina_page
    else:
        return html.Div([html.H3("Página não encontrada!!", className="error-message")])

# Callback para alternar visibilidade do campo de senha
@app.callback(
    Output("token-input", "type"),
    [Input("toggle-password", "n_clicks")],
    [State("token-input", "type")],
)
def toggle_password_visibility(n_clicks, current_type):
    if n_clicks % 2 == 1:
        return "text"
    return "password"


# Layout principal
app.layout = html.Div(
    [
        dcc.Location(id="auth-url", refresh=False),
        dcc.Location(id="url", refresh=False),
        html.Div(id="auth-page-content", children=auth_layout),
    ]
)

if __name__ == "__main__":
    app.run_server(debug=True, port=8052)
