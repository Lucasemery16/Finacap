import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import dash.dash_table as dt
import pandas as pd
import psycopg2
import requests
import json

# Token de autenticação
TOKEN_CORRETO = "1"

# Função para obter os dados do banco de dados PostgreSQL
def fetch_postgres_data():
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="postgres",
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

# Função para obter os dados da API do Comdinheiro
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

        if not api_data or "tables" not in api_data or "tab0" not in api_data["tables"]:
            print("A resposta da API não contém os dados esperados.")
            return pd.DataFrame()

        table_data = api_data["tables"]["tab0"]

        data_list = []
        for key, value in table_data.items():
            record = {
                'col0': value.get('col0', 'Não disponível'),
                'col1': value.get('col1', 'Não disponível'),
                'col2': value.get('col2', 'Não disponível'),
                'col3': value.get('col3', 'Não disponível')
            }
            data_list.append(record)

        df_api = pd.DataFrame(data_list)
        print(f"Dados recuperados da API: {len(df_api)} registros.")
        return df_api

    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão: {e}")
        return pd.DataFrame()
    except KeyError as e:
        print(f"Erro no formato da resposta: {e}")
        return pd.DataFrame()

# Função para combinar os dados de ambas as fontes
def fetch_data(tipo="postgres"):
    print(f"Buscando dados da fonte: {tipo}")
    if tipo == "postgres":
        df = fetch_postgres_data()
        print("Dados do PostgreSQL carregados:")
        print(df.head())
        return df
    elif tipo == "api":
        df_api = fetch_comdinheiro_data()
        if df_api.empty:
            print("Erro ao recuperar dados da API ou dados vazios.")
            return pd.DataFrame()
        else:
            print("Dados da API carregados:")
            print(df_api.head())
            return df_api

# Inicializando a aplicação Dash
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Dashboard Finacap"
app.config.suppress_callback_exceptions = True

# Dados iniciais - Carrega tanto os dados do banco de dados quanto da API
df_postgres = fetch_data(tipo="postgres")  # Carregar dados do banco para clientes
df_api = fetch_data(tipo="api")  # Carregar dados da API para o relatório gerencial

if not df_api.empty:
    df_api = df_api.rename(columns={
        'col0': 'Carteira',
        'col1': 'Ativo',
        'col2': 'Descrição',
        'col3': 'Saldo Bruto'
    })

df_postgres["cliente_ativo"] = df_postgres["cliente_ativo"].str.strip().str.capitalize()
df_postgres["perfil_risco_ips"] = pd.to_numeric(df_postgres["perfil_risco_ips"], errors="coerce")

# Gráficos
fig_pie = px.pie(
    df_postgres,
    names="suitability_cliente",
    values="patrimonio",
    title="Distribuição de Patrimônio por Suitability",
)
fig_bar = px.bar(df_postgres, x="nome_cliente", y="patrimonio", title="Patrimônio por Cliente")

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

dash_layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        sidebar,
        html.Div(id="page-content", className="content"),
        footer,
    ]
)

# Páginas do dashboard
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

tabela_clientes_page = html.Div(
    [
        html.H3("Tabela de Clientes", className="page-title"),
        html.Div(
            [
                dcc.Input(
                    id="search-bar-clientes",
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
                    id="filter-column-clientes",
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

# Página de Relatório Gerencial
relatorio_gerencial_page = html.Div(
    [
        html.H3("Relatório Gerencial Carteiras", className="page-title"),
        html.Div(
            [
                dcc.Input(
                    id="search-bar-relatorio",
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
                    id="filter-column-relatorio",
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
            data=df_api.to_dict("records") if not df_api.empty else [],
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

# Callback para atualizar a tabela de relatórios gerenciais
@app.callback(
    Output("relatorio-table", "data"),
    [
        Input("update-data-btn", "n_clicks"),
        Input("search-bar-relatorio", "value"),
        Input("filter-column-relatorio", "value"),
    ],
)
def update_relatorio_gerencial_data(n_clicks, search_value, filter_column):
    print("Atualizando Relatório Gerencial...")
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    df_api = fetch_data(tipo="api")

    print("Dados carregados para Relatório Gerencial:")
    print(df_api.head())

    if df_api.empty:
        return []

    df_api = df_api.rename(columns={
        'col0': 'Carteira',
        'col1': 'Ativo',
        'col2': 'Descrição',
        'col3': 'Saldo Bruto'
    })

    filtered_df = df_api.copy()

    if search_value:
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row: row.astype(str)
                .str.contains(search_value, case=False)
                .any(),
                axis=1,
            )
        ]

    if filter_column and filter_column != "all":
        filtered_df = filtered_df[[filter_column]]

    return filtered_df.to_dict("records")

# Callback para alternar entre autenticação e dashboard
@app.callback(
    Output("auth-page-content", "children"),
    [Input("submit-button", "n_clicks"), Input("token-input", "n_submit")],
    [State("token-input", "value")],
)
def validar_token(n_clicks, n_submit, token):
    if (n_clicks > 0 or n_submit) and token == TOKEN_CORRETO:
        return dash_layout
    return auth_layout

# Callback para redefinir a URL após logout
@app.callback(
    Output("auth-url", "pathname"),
    [Input("auth-page-content", "children")],
)
def reset_url_on_logout(content):
    if content == auth_layout:
        return "/"
    return dash.no_update

# Callback para controle de rotas no dashboard
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def display_page(pathname):
    if pathname in ["/clientes-ativos", "/"]:
        return clientes_ativos_page
    elif pathname == "/clientes":
        return tabela_clientes_page
    elif pathname == "/relatorio-gerencial":
        return relatorio_gerencial_page
    elif pathname == "/lamina":
        return lamina_page
    elif pathname == "/sair":
        return auth_layout
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

@app.callback(
    Output("clientes-table", "data"),
    [
        Input("update-data-btn", "n_clicks"),
        Input("search-bar-clientes", "value"),
        Input("filter-column-clientes", "value"),
    ],
)
def update_clientes_table(n_clicks, search_value, filter_column):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # Recarregar dados do PostgreSQL
    df_postgres = fetch_data(tipo="postgres")

    filtered_df = df_postgres.copy()

    # Filtrar por valor da busca
    if search_value:
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row: row.astype(str)
                .str.contains(search_value, case=False)
                .any(),
                axis=1,
            )
        ]

    # Filtrar por coluna específica
    if filter_column and filter_column != "all":
        filtered_df = filtered_df[[filter_column]]

    return filtered_df.to_dict("records")


# Layout principal
app.layout = html.Div(
    [
        dcc.Location(
            id="auth-url", refresh=False
        ),
        dcc.Location(
            id="url", refresh=False
        ),
        html.Div(id="auth-page-content", children=auth_layout),
    ]
)

if __name__ == "__main__":
   app.run_server(debug=True, port=8052)
