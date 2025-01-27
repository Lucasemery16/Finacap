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
                    "mv(estrategia01)": value.get("col4", "Não disponível"),
                    "mv(estrategia02)": value.get("col5", "Não disponível"),
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
                dcc.Link(
                    "Enquadramento - IPS",
                    href="/enquadramento-ips",
                    className="menu-item",
                ),
                dcc.Link("Sair", href="/login", className="menu-item"),
            ],
            className="menu-container",
        ),
        html.Button("Atualizar Dados", id="update-data-btn", className="update-button"),
    ],
    className="sidebar",
)

footer = html.Div("\u00a9 2025 Finacap Investimentos Ltda", className="footer")

# Layout principal do dashboard com menu hambúrguer
dashboard_layout = html.Div(
    className="dashboard-container",
    children=[
        dcc.Location(id="url", refresh=False),
        html.Button(
            html.I(className="fas fa-bars"),  # Ícone do menu
            id="menu-toggle",
            className="menu-toggle",
        ),
        html.Div(id="sidebar", className="sidebar expanded", children=[
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
                    dcc.Link(
                        "Enquadramento - IPS",
                        href="/enquadramento-ips",
                        className="menu-item",
                    ),
                    dcc.Link("Sair", href="/login", className="menu-item"),
                ],
                className="menu-container",
            ),
        ]),
        html.Div(id="page-content", className="content expanded"),  # Conteúdo dinâmico
        footer,  # Rodapé fixo
    ],
)

# Callback para alternar a sidebar entre expandida e colapsada
@app.callback(
    [Output("sidebar", "className"), Output("page-content", "className")],
    [Input("menu-toggle", "n_clicks")],
    [State("sidebar", "className"), State("page-content", "className")],
)
def toggle_sidebar(n_clicks, sidebar_class, content_class):
    if n_clicks and "expanded" in sidebar_class:
        return "sidebar collapsed", "content collapsed"
    else:
        return "sidebar expanded", "content expanded"

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
        html.H3("Relatório Gerencial Carteiras", className="page-title", style={"textAlign": "center", "color": "#ffffff"}),
        html.Div(
            [
                dcc.Input(
                    id="search-bar",
                    type="text",
                    placeholder="Buscar...",
                    style={
                        "marginBottom": "20px",
                        "width": "80%",
                        "padding": "10px",
                        "fontSize": "18px",
                        "borderRadius": "10px",
                        "border": "1px solid #00aaff",
                        "backgroundColor": "#ffffff",
                        "color": "#000000",
                        "boxShadow": "0px 4px 8px rgba(0, 0, 0, 0.2)",
                        "display": "block",
                        "margin": "0 auto",
                    },
                ),
            ],
            style={"textAlign": "center"},
        ),
        dt.DataTable(
            id="relatorio-table",
            columns=[
                {"name": "Carteira", "id": "Carteira"},
                {"name": "Ativo", "id": "Ativo"},
                {"name": "Descrição", "id": "Descrição"},
                {"name": "Saldo Bruto", "id": "Saldo Bruto"},
                {"name": "mv(estrategia01)", "id": "mv(estrategia01)"},
                {"name": "mv(estrategia02)", "id": "mv(estrategia02)"},
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
    Output("relatorio-table", "data"),
    [Input("search-bar", "value")]
)
def update_relatorio_table(search_value):
    # Cópia do DataFrame original
    filtered_df = df_api.copy()

    if search_value:
        # Busca global em todas as colunas
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row: search_value.lower() in row.astype(str).str.lower().to_string(),
                axis=1
            )
        ]

    # Retorna os dados filtrados
    return filtered_df.to_dict("records")


    # Filtrar por coluna específica
    if filter_column and filter_column != "all":
        filtered_df = filtered_df[filtered_df[filter_column].str.contains(search_value, case=False, na=False)]

    # Retorna os dados filtrados como uma lista de dicionários
    return filtered_df.to_dict("records")

@app.callback(
    Output("clientes-table", "data"),
    [Input("search-bar-clientes", "value")]
)
def update_clientes_table(search_value):
    # Cópia do DataFrame original
    filtered_df = df_postgres.copy()

    if search_value:
        # Busca global em todas as colunas
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row: search_value.lower() in row.astype(str).str.lower().to_string(),
                axis=1
            )
        ]

    # Retorna os dados filtrados
    return filtered_df.to_dict("records")

# Página de clientes
tabela_clientes_page = html.Div(
    [
        html.H3("Tabela de Clientes", className="page-title", style={"textAlign": "center", "color": "#ffffff"}),
        html.Div(
            [
                dcc.Input(
                    id="search-bar-clientes",
                    type="text",
                    placeholder="Buscar em todas as colunas...",
                    debounce=True,  # Atualiza somente após o término da digitação
                    style={
                        "marginBottom": "20px",
                        "width": "80%",
                        "padding": "10px",
                        "fontSize": "18px",
                        "borderRadius": "10px",
                        "border": "1px solid #00aaff",
                        "backgroundColor": "#ffffff",
                        "color": "#000000",
                        "boxShadow": "0px 4px 8px rgba(0, 0, 0, 0.2)",
                        "display": "block",
                        "margin": "0 auto",
                    },
                ),
            ],
            style={"textAlign": "center"},
        ),
        dt.DataTable(
            id="clientes-table",
            columns=[{"name": col, "id": col} for col in df_postgres.columns],
            data=df_postgres.to_dict("records"),
            style_table={"overflowX": "auto", "maxHeight": "500px"},
            style_header={
                "backgroundColor": "#1b51b1",
                "color": "white",
                "fontWeight": "bold",
            },
            style_cell={"textAlign": "center", "padding": "10px"},
            page_size=10,  # Paginação com 10 linhas por página
        ),
    ]
)




lamina_page = html.Div(
    [
        html.H3(
            "Digite o Código Finacap do Cliente",
            className="page-title",
            style={
                "color": "#ffffff",
                "fontWeight": "bold",
                "textAlign": "center",
                "marginBottom": "20px",
                "fontSize": "24px",
            },
        ),
        
        # Input estilizado
        dcc.Input(
            id="codigo-finacap-input",
            type="text",
            placeholder="Digite o Código Finacap...",
            style={
                "marginBottom": "20px",
                "width": "80%",
                "padding": "10px",
                "fontSize": "18px",
                "borderRadius": "10px",
                "border": "1px solid #00aaff",
                "display": "block",
                "margin": "0 auto",
                "backgroundColor": "#ffffff",
                "color": "#000000",
                "boxShadow": "0px 4px 8px rgba(0, 0, 0, 0.2)",
            },
        ),
        
        # Detalhes do cliente
        html.Div(
            id="client-detail-info",
            style={
                "marginTop": "30px",
                "color": "#ffffff",
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fit, minmax(300px, 1fr))",
                "gap": "20px",
                "padding": "20px",
            },
        ),
    ],
    style={
        "backgroundColor": "#001f3f",
        "padding": "20px",
        "borderRadius": "10px",
        "boxShadow": "0px 4px 10px rgba(0, 0, 0, 0.3)",
    },
)


@app.callback(
    Output("client-detail-info", "children"),
    [Input("codigo-finacap-input", "value")]
)
def display_client_details(codigo_finacap):
    if codigo_finacap:
        client_data = df_postgres[df_postgres["codigo_finacap"] == codigo_finacap]

        if not client_data.empty:
            # Cards com conteúdo bem formatado
            return [
                html.Div(
                    [
                        html.H4("1. DADOS DO CLIENTE", style={"marginBottom": "10px", "color": "#00aaff"}),
                        html.P(f"Nome: {client_data['nome_cliente'].iloc[0]}"),
                        html.P(f"Gestor: {client_data['gestor'].iloc[0]}"),
                        html.P(f"Conta: {client_data['codigo_finacap'].iloc[0]}"),
                        html.P(f"Perfil: {client_data['suitability_cliente'].iloc[0]}"),
                    ],
                    style={
                        "backgroundColor": "#ffffff",
                        "color": "#001f3f",
                        "padding": "20px",
                        "borderRadius": "10px",
                        "boxShadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
                    },
                ),
                html.Div(
                    [
                        html.H4("2. CARTEIRA", style={"marginBottom": "10px", "color": "#00aaff"}),
                        html.P(f"Patrimônio Líquido: R$ {client_data['patrimonio'].iloc[0]:,.2f}"),
                        html.P("Saldo em conta: Não disponível"),
                    ],
                    style={
                        "backgroundColor": "#ffffff",
                        "color": "#001f3f",
                        "padding": "20px",
                        "borderRadius": "10px",
                        "boxShadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
                    },
                ),
                html.Div(
                    [
                        html.H4("3. MONITORAMENTO", style={"marginBottom": "10px", "color": "#00aaff"}),
                        html.P("Alocação Carteira: Não disponível"),
                        html.P("Alocação Estratégica: Não disponível"),
                        html.P("Alocação Tática: Não disponível"),
                        html.P("Mínimo: Não disponível"),
                        html.P("Máximo: Não disponível"),
                    ],
                    style={
                        "backgroundColor": "#ffffff",
                        "color": "#001f3f",
                        "padding": "20px",
                        "borderRadius": "10px",
                        "boxShadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
                    },
                ),
                html.Div(
                    [
                        html.H4("4. REBALANCEAMENTO", style={"marginBottom": "10px", "color": "#00aaff"}),
                        html.P("Rebalanceamento Estratégico: Não disponível"),
                        html.P("Rebalanceamento Máximo: Não disponível"),
                    ],
                    style={
                        "backgroundColor": "#ffffff",
                        "color": "#001f3f",
                        "padding": "20px",
                        "borderRadius": "10px",
                        "boxShadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
                    },
                ),
                html.Div(
                    [
                        html.H4("5. EXECUÇÃO", style={"marginBottom": "10px", "color": "#00aaff"}),
                        html.P("Mov. Ativo: Não disponível"),
                        html.P("Mov. Caixa: Não disponível"),
                    ],
                    style={
                        "backgroundColor": "#ffffff",
                        "color": "#001f3f",
                        "padding": "20px",
                        "borderRadius": "10px",
                        "boxShadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
                    },
                ),
                html.Div(
                    [
                        html.H4("TOTAL", style={"marginBottom": "10px", "color": "#00aaff"}),
                        html.P("Saldo em conta após movimentações: Não disponível"),
                    ],
                    style={
                        "backgroundColor": "#ffffff",
                        "color": "#001f3f",
                        "padding": "20px",
                        "borderRadius": "10px",
                        "boxShadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
                    },
                ),
            ]
        else:
            return html.Div(
                "Cliente não encontrado. Verifique o código e tente novamente.",
                style={"color": "red", "textAlign": "center", "fontWeight": "bold"},
            )

    return html.Div(
        "Digite um código para buscar os detalhes do cliente.",
        style={"color": "#ffffff", "textAlign": "center"},
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

    # Aplicar busca global
    if search_value:
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row: search_value.lower() in row.astype(str).str.lower().to_string(),
                axis=1,
            )
        ]

    # Aplicar filtro de coluna
    if filter_column and filter_column != "all":
        filtered_df = filtered_df[[filter_column]]

    return filtered_df.to_dict("records")


# Ajuste para garantir que a tabela receba os dados corretamente
@app.callback(
    Output("enquadramento-ips-table", "data"),
    [Input("update-data-btn", "n_clicks")]
)
def update_enquadramento_ips(n_clicks):
    # Obter dados da API
    df_api = fetch_comdinheiro_data()

    if df_api.empty:
        return []  # Retorna uma lista vazia se não houver dados

    # Limpeza e processamento de dados
    df_api['Saldo Bruto'] = df_api['Saldo Bruto'].astype(str).replace('[R$\s]', '', regex=True).str.replace('.', '').str.replace(',', '.').astype(float)
    df_api['moeda'] = df_api['minha_variavel(serie_moeda)'].fillna('real').str.lower().str.strip()
    df_api['moeda'] = df_api['moeda'].replace('nd', 'real')  # Considerar 'nd' como 'real'
    df_api.loc[df_api['moeda'] == 'usd', 'Saldo Bruto'] *= 6.20  # Conversão de USD para reais
    df_api['moeda'] = 'real'

    # Definir as carteiras e suas respectivas alocações
    carteira_alocacao = {
        'U': {
            'Selic': 0.35, 'Crédito Privado Pós': 0.50, 'IPCA/Pré Fixado': 0.10, 
            'Renda Variável': 0.05, 'Offshore': 0.00, 'Alternativo': 0.00
        },
        'C': {
            'Selic': 0.30, 'Crédito Privado Pós': 0.40, 'IPCA/Pré Fixado': 0.15,
            'Renda Variável': 0.15, 'Offshore': 0.00, 'Alternativo': 0.00
        },
        'M': {
            'Selic': 0.20, 'Crédito Privado Pós': 0.25, 'IPCA/Pré Fixado': 0.15,
            'Renda Variável': 0.30, 'Offshore': 0.05, 'Alternativo': 0.05
        },
        'S': {
            'Selic': 0.10, 'Crédito Privado Pós': 0.10, 'IPCA/Pré Fixado': 0.30,
            'Renda Variável': 0.40, 'Offshore': 0.05, 'Alternativo': 0.05
        },
        'A': {
            'Selic': 0.05, 'Crédito Privado Pós': 0.05, 'IPCA/Pré Fixado': 0.30,
            'Renda Variável': 0.50, 'Offshore': 0.05, 'Alternativo': 0.05
        }
    }

    # Definir os clientes em cada lógica
    clientes_lógicas = {
        'A': ['FINACAP044'],
        'C': ['FINACAP027', 'FINACAP026', 'FINACAP045', 'FINACAP050', 'FINACAP052', 'FINACAP016', 'FINACAP012', 'FINACAP088', 'FINACAP101', 'FINACAP094', 'FINACAP109', 'FINACAP114'],
        'M': ['FINACAP039', 'FINACAP003', 'FINACAP010', 'FINACAP019', 'FINACAP005', 'FINACAP007', 'FINACAP086', 'FINACAP087'],
        'S': ['FINACAP031', 'FINACAP020', 'FINACAP032', 'FINACAP051', 'FINACAP048', 'FINACAP049', 'FINACAP057', 'FINACAP061', 'FINACAP075'],
        'U': ['FINACAP031', 'FINACAP020', 'FINACAP032', 'FINACAP051', 'FINACAP048', 'FINACAP049', 'FINACAP057', 'FINACAP061', 'FINACAP075']
    }

    # Função para calcular o enquadramento de cada carteira individualmente
    def calcular_enquadramento_individual(carteira_data, tipo, tipo_carteira):
        cnpj_especial = '19.038.997/0001-05'  # CNPJ sem a barra e os pontos
        alocacao_fim = carteira_data[carteira_data['Ativo'] == cnpj_especial]

        soma_fim = 0
        if not alocacao_fim.empty:
            patrimonio_fim = alocacao_fim['Saldo Bruto'].sum()

            if tipo == 'Selic':
                soma_fim = patrimonio_fim * carteira_alocacao[tipo_carteira]['Selic']
            elif tipo == 'Crédito Privado Pós':
                soma_fim = patrimonio_fim * carteira_alocacao[tipo_carteira]['Crédito Privado Pós']
            elif tipo == 'IPCA/Pré Fixado':
                soma_fim = patrimonio_fim * carteira_alocacao[tipo_carteira]['IPCA/Pré Fixado']
            elif tipo == 'Renda Variável':
                soma_fim = patrimonio_fim * carteira_alocacao[tipo_carteira]['Renda Variável']
            elif tipo == 'Offshore':
                soma_fim = patrimonio_fim * carteira_alocacao[tipo_carteira]['Offshore']
            elif tipo == 'Alternativo':
                soma_fim = patrimonio_fim * carteira_alocacao[tipo_carteira]['Alternativo']

        soma_tipo = carteira_data[carteira_data['minha_variavel(estrategia01)'].str.contains(tipo, case=False, na=False)]['Saldo Bruto'].sum()

        total = soma_tipo + soma_fim
        patrimonio_total = carteira_data['Saldo Bruto'].sum()

        if total > patrimonio_total:
            total = patrimonio_total

        return (total / patrimonio_total) * 100 if patrimonio_total > 0 else 0

    # Calcular os diferentes tipos de alocação para as carteiras definidas
    resultados = []

    for carteira in carteira_alocacao.keys():
        clientes_na_carteira = clientes_lógicas[carteira]  # Obter os clientes dessa lógica
        carteira_data = df_api[df_api['Carteira'].isin(clientes_na_carteira)]

        if not carteira_data.empty:
            resultado = {
                'Perfil - IPS': carteira,
                'Patrimônio Líquido': carteira_data['Saldo Bruto'].sum(),
                'Selic': f"{calcular_enquadramento_individual(carteira_data, 'Selic', carteira):.2f}%",
                'Alocação Estratégica Selic': f"{carteira_alocacao[carteira]['Selic'] * 100:.2f}%",
                'Crédito Privado Pós': f"{calcular_enquadramento_individual(carteira_data, 'Crédito Privado Pós', carteira):.2f}%",
                'Alocação Estratégica Crédito Privado Pós': f"{carteira_alocacao[carteira]['Crédito Privado Pós'] * 100:.2f}%",
                'IPCA/Pré Fixado': f"{calcular_enquadramento_individual(carteira_data, 'IPCA/Pré Fixado', carteira):.2f}%",
                'Alocação Estratégica IPCA/Pré Fixado': f"{carteira_alocacao[carteira]['IPCA/Pré Fixado'] * 100:.2f}%",
                'Renda Variável': f"{calcular_enquadramento_individual(carteira_data, 'Renda Variável', carteira):.2f}%",
                'Alocação Estratégica Renda Variável': f"{carteira_alocacao[carteira]['Renda Variável'] * 100:.2f}%",
                'Offshore': f"{calcular_enquadramento_individual(carteira_data, 'Offshore', carteira):.2f}%",
                'Alocação Estratégica Offshore': f"{carteira_alocacao[carteira]['Offshore'] * 100:.2f}%",
                'Alternativo': f"{calcular_enquadramento_individual(carteira_data, 'Alternativo', carteira):.2f}%",
                'Alocação Estratégica Alternativo': f"{carteira_alocacao[carteira]['Alternativo'] * 100:.2f}%",
                'Status (OK/NÃO)': 'OK',  # Aqui você pode aplicar uma lógica de status, caso necessário
                'Exposição CP': carteira_data['Exposição CP'].sum(),
                'Liquidez imediata': 'Sim',
                'Período (dias)': 30
            }
            resultados.append(resultado)

    # Criar um DataFrame com os resultados
    resultados_df = pd.DataFrame(resultados)

    # Retornar os dados para exibição na tabela
    return resultados_df.to_dict("records")


# Página de Enquadramento - IPS
enquadramento_ips_page = html.Div(
    [
        html.H3("Enquadramento - IPS", className="page-title"),
        dt.DataTable(
            id="enquadramento-ips-table",
            columns=[
                {"name": "Perfil - IPS", "id": "Perfil - IPS"},
                {"name": "Patrimônio Líquido", "id": "Patrimônio Líquido"},
                {"name": "Selic", "id": "Selic"},
                {"name": "Alocação Estratégica Selic", "id": "Alocação Estratégica Selic"},
                {"name": "Crédito Privado Pós", "id": "Crédito Privado Pós"},
                {"name": "Alocação Estratégica Crédito Privado Pós", "id": "Alocação Estratégica Crédito Privado Pós"},
                {"name": "IPCA/Pré Fixado", "id": "IPCA/Pré Fixado"},
                {"name": "Alocação Estratégica IPCA/Pré Fixado", "id": "Alocação Estratégica IPCA/Pré Fixado"},
                {"name": "Renda Variável", "id": "Renda Variável"},
                {"name": "Alocação Estratégica Renda Variável", "id": "Alocação Estratégica Renda Variável"},
                {"name": "Offshore", "id": "Offshore"},
                {"name": "Alocação Estratégica Offshore", "id": "Alocação Estratégica Offshore"},
                {"name": "Alternativo", "id": "Alternativo"},
                {"name": "Alocação Estratégica Alternativo", "id": "Alocação Estratégica Alternativo"},
                {"name": "Status (OK/NÃO)", "id": "Status (OK/NÃO)"},
                {"name": "Exposição CP", "id": "Exposição CP"},
                {"name": "Liquidez imediata", "id": "Liquidez imediata"},
                {"name": "Período (dias)", "id": "Período (dias)"}
            ],
            data=[],  # Inicialmente vazio
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": "#1b51b1",
                "color": "white",
                "fontWeight": "bold",
                "textAlign": "center",
            },
            style_cell={"textAlign": "center", "padding": "5px"},
        ),
    ]
)


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
    elif pathname == "/enquadramento-ips":
        return enquadramento_ips_page
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