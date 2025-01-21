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
TOKEN_CORRETO = "1"

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
        password="@QWEasd132",
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
        "URL": "RelatorioGerencialCarteiras001.php?&data_analise=14012025&data_ini=&nome_portfolio=&variaveis=nome_portfolio+ativo+desc+saldo_bruto+minha_variavel(estrategia01)+minha_variavel(estrategia02)+data_analise+tipo_ativo+Pu+instituicao_financeira+prazo_liquidez+minha_variavel(serie_moeda)&filtro=all&ativo=&filtro_IF=todos&relat_alias=&layout=0&layoutB=0&num_casas=&enviar_email=0&portfolio_editavel=&filtro_id=",
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
                    "Minha variavel 01": value.get("col4", "Não disponível"),
                    "Minha variavel 02": value.get("col5", "Não disponível"),
                    "Data analise": value.get("col6", "Não disponível"),
                    "Tipo ativo": value.get("col7", "Não disponível"),
                    "PU": value.get("col8", "Não disponível"),
                    "Instituicao financeira": value.get("col9", "Não disponível"),
                    "Prazo da liquidez": value.get("col10", "Não disponível"),
                    "minha_variavel(serie_moeda)": value.get("col11", "Não disponível"),

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
                    n_submit=0  # Adiciona esse parâmetro para capturar a submissão com a tecla Enter
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
                dcc.Link("Sair", href="/login", className="menu-item"),

            ],
            className="menu-container",
        ),
        html.Button("Atualizar Dados", id="update-data-btn", className="update-button"),
    ],
    className="sidebar",
)

footer = html.Div("\u00a9 2025 Finacap Investimentos Ltda", className="footer")

# Layout principal do dashboard
dashboard_layout = html.Div(
    className="dashboard-container",
    children=[
        dcc.Location(id="url", refresh=False),
        sidebar,  # Sidebar fixa
        html.Div(id="page-content", className="content"),  # Conteúdo dinâmico
        footer,  # Rodapé fixo
    ],
)


# Página de login com autenticação
@app.callback(
    [Output("auth-page-content", "children"), Output("token-status", "children")],
    [Input("submit-button", "n_clicks"), Input("token-input", "n_submit")],  # Adicionando Input para n_submit
    [State("token-input", "value")],
)
def validate_login(n_clicks, n_submit, token_value):
    # A função será chamada quando o botão for clicado ou o "Enter" for pressionado
    if n_clicks > 0 or n_submit > 0:  # Verifica se o botão ou Enter foi pressionado
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
                        {"label": "minha_variavel(estrategia01)", "value": "minha_variavel(estrategia01)"},
                        {"label": "minha_variavel(estrategia02)", "value": "minha_variavel(estrategia02)"},
                        {"label": "Data analise", "value": "Data analise"},
                        {"label": "Tipo ativo", "value": "Tipo ativo"},
                        {"label": "PU", "value": "PU"},
                        {"label": "Instituicao financeira", "value": "Instituicao financeira"},
                        {"label": "Prazo da liquidez", "value": "Prazo da liquidez"},
                        {"label": "minha_variavel(serie_moeda)", "value": "minha_variavel(serie_moeda)"},

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
                {"name": "minha_variavel(estrategia01)", "id": "minha_variavel(estrategia01)"},
                {"name": "minha_variavel(estrategia02)", "id": "minha_variavel(estrategia02)"},
                {"name": "Data analise", "id": "Data analise"},
                {"name": "Tipo ativo", "id": "Tipo ativo"},
                {"name": "PU", "id": "PU"},
                {"name": "Instituicao financeira", "id": "Instituicao financeira"},
                {"name": "Prazo da liquidez", "id": "Prazo da liquidez"},
                {"name": "minha_variavel(serie_moeda)", "id": "minha_variavel(serie_moeda)"},
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

# Página de clientes
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

lamina_page = html.Div(
    [
        html.H3("Digite o Código Finacap do Cliente", className="page-title"),
        
        # Barra de pesquisa para o código_finacap
        dcc.Input(
            id="codigo-finacap-input",
            type="text",
            placeholder="Digite o Código Finacap...",
            style={"marginBottom": "10px", "width": "50%", "padding": "5px", "fontSize": "14px"},
        ),
        
        # Seção para mostrar os detalhes do cliente
        html.Div(id="client-detail-info", style={"marginTop": "20px"}),
    ]
)

# Callback para exibir as informações detalhadas do cliente com base no código_finacap
@app.callback(
    Output("client-detail-info", "children"),
    [Input("codigo-finacap-input", "value")]
)
def display_client_details(codigo_finacap):
    if codigo_finacap:
        # Filtra os dados do cliente com base no código_finacap
        client_data = df_postgres[df_postgres["codigo_finacap"] == codigo_finacap]
        
        if not client_data.empty:
            # Detalhes do cliente
            client_details = html.Div(
                [
                    # Dados do Cliente
                    html.H4(f"1. DADOS - CLIENTE: {client_data['nome_cliente'].iloc[0]}", style={"color": "white"}),
                    html.Div(f"Nome: {client_data['nome_cliente'].iloc[0]}", style={"color": "white"}),
                    html.Div(f"Gestor: {client_data['gestor'].iloc[0]}", style={"color": "white"}),
                    html.Div(f"Conta: {client_data['codigo_finacap'].iloc[0]}", style={"color": "white"}),
                    html.Div(f"Perfil: {client_data['suitability_cliente'].iloc[0]}", style={"color": "white"}),

                    # Carteira
                    html.H4("2. CARTEIRA", style={"color": "white"}),
                    html.Div(f"Patrimônio Líquido: R$ {client_data['patrimonio'].iloc[0]:.2f}", style={"color": "white"}),
                    html.Div(f"Saldo em conta: Não disponível", style={"color": "white"}),

                    # Monitoramento
                    html.H4("3. MONITORAMENTO", style={"color": "white"}),
                    html.Div(f"Alocação Carteira: Não disponível", style={"color": "white"}),
                    html.Div(f"Alocação Estratégica: Não disponível", style={"color": "white"}),
                    html.Div(f"Alocação Tática: Não disponível", style={"color": "white"}),
                    html.Div(f"Minimo: Não disponível", style={"color": "white"}),
                    html.Div(f"Máximo: Não disponível", style={"color": "white"}),

                    # Rebalanceamento
                    html.H4("4. REBALANCEAMENTO", style={"color": "white"}),
                    html.Div(f"Rebalanceamento Estratégico: Não disponível", style={"color": "white"}),
                    html.Div(f"Rebalanceamento Máximo: Não disponível", style={"color": "white"}),

                    # Execução
                    html.H4("5. EXECUÇÃO", style={"color": "white"}),
                    html.Div(f"Mov. Ativo: Não disponível", style={"color": "white"}),
                    html.Div(f"Mov. Caixa: Não disponível", style={"color": "white"}),

                    # Total
                    html.H4("TOTAL", style={"color": "white"}),
                    html.Div(f"Saldo em conta após movimentações: Não disponível", style={"color": "white"}),

                ]
            )
            return client_details
        else:
            return html.Div("Cliente não encontrado. Verifique o código e tente novamente.", style={"color": "red"})
    return html.Div("Digite um código para buscar os detalhes do cliente.", style={"color": "white"})

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


@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")]
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
    elif pathname == "/login":
        return auth_layout  # Quando a URL for "/login", retorna o layout de login
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