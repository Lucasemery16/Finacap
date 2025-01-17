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
TOKEN_CORRETO = "#Finacap@"


# Função para obter os dados do banco de dados PostgreSQL
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


# Função para obter os dados da API do Comdinheiro
def fetch_comdinheiro_data(username, password, date, portfolio):
    url = "https://www.comdinheiro.com.br/Clientes/API/EndPoint001.php"
    querystring = {"code": "import_data"}

    # Criação do payload com o portfólio no formato solicitado
    portfolio_formatted = portfolio.replace("+", "%2B").replace(" ", "%25BE")
    payload = {
        "username": "consulta.finacap",
        "password": "#Consult@finac@p2025",
        "URL": (
            f"RelatorioGerencialCarteiras001.php?"
            f"&data_analise= 09012025"
            "&data_ini="
            f"&nome_portfolio=FINACAP056 + FINACAP096 + FINACAP130 + FINACAP137 + FINACAP147 + FINACAP148 + FINACAP149 + FINACAP150 + FINACAP157 + FINACAP002 + FINACAP003 + FINACAP004 + FINACAP005 + FINACAP006 + FINACAP007 + FINACAP008 + FINACAP009 + FINACAP010 + FINACAP011 + FINACAP012 + FINACAP056_BRL + FINACAP056_USD + FINACAP096_BRL + FINACAP096_USD + FINACAP130_USD + FINACAP137_BRL + FINACAP137_USD + FINACAP147_BRL + FINACAP147_USD + FINACAP148_BRL + FINACAP148_USD + FINACAP149_BRL + FINACAP149_USD + FINACAP150_BRL + FINACAP150_USD + FINACAP157_BRL + FINACAP157_USD + FINACAP165"
            "&variaveis=nome_portfolio+ativo+desc+saldo_bruto"
            "&filtro=all"
            "&ativo="
            "&filtro_IF=todos"
            "&relat_alias="
            "&layout=0"
            "&layoutB=0"
            "&num_casas="
            "&enviar_email=0"
            "&portfolio_editavel="
            "&filtro_id="
        ),
        "format": "json3",
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    response = requests.post(url, data=payload, headers=headers, params=querystring)

    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Failed to fetch data: {response.status_code}"}


# Função para combinar os dados de ambas as fontes
def fetch_data():
    postgres_df = fetch_postgres_data()

    api_data = fetch_comdinheiro_data(
        username="consulta.finacap",
        password="#Consult@finac@p2025",
        date="09012025",
        portfolio="FINACAP056 + FINACAP096 + FINACAP130 + FINACAP137 + FINACAP147 + FINACAP148 + FINACAP149 + FINACAP150 + FINACAP157 + FINACAP002 + FINACAP003 + FINACAP004 + FINACAP005 + FINACAP006 + FINACAP007 + FINACAP008 + FINACAP009 + FINACAP010 + FINACAP011 + FINACAP012 + FINACAP056_BRL + FINACAP056_USD + FINACAP096_BRL + FINACAP096_USD + FINACAP130_USD + FINACAP137_BRL + FINACAP137_USD + FINACAP147_BRL + FINACAP147_USD + FINACAP148_BRL + FINACAP148_USD + FINACAP149_BRL + FINACAP149_USD + FINACAP150_BRL + FINACAP150_USD + FINACAP157_BRL + FINACAP157_USD + FINACAP165",
    )

    if "error" not in api_data:
        api_df = pd.DataFrame(
            api_data["data"]
        )  # Ajustar conforme o formato do retorno da API
        combined_df = pd.concat([postgres_df, api_df], ignore_index=True)
        return combined_df
    else:
        print(api_data["error"])
        return postgres_df


# Inicializando a aplicação Dash
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Dashboard Finacap"
app.config.suppress_callback_exceptions = True

# Dados iniciais
df = fetch_data()
df["cliente_ativo"] = df["cliente_ativo"].str.strip().str.capitalize()
df["perfil_risco_ips"] = pd.to_numeric(df["perfil_risco_ips"], errors="coerce")

# Gráficos
fig_pie = px.pie(
    df,
    names="suitability_cliente",
    values="patrimonio",
    title="Distribuição de Patrimônio por Suitability",
)
fig_bar = px.bar(df, x="nome_cliente", y="patrimonio", title="Patrimônio por Cliente")

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

# Páginas do dashboard
clientes_ativos_page = html.Div(
    [
        html.H3("Clientes Ativos", className="page-title"),
        html.Div(
            [
                html.Div(
                    [
                        html.H3(
                            f"{df['cliente_ativo'].value_counts().get('Sim', 0)}",
                            className="card-value",
                        ),
                        html.P("Clientes Ativos", className="card-label"),
                    ],
                    className="card",
                ),
                html.Div(
                    [
                        html.H3(
                            f"{len(df[df['perfil_risco_ips'] > 4])}",
                            className="card-value",
                        ),
                        html.P("Revisões Pendentes", className="card-label"),
                    ],
                    className="card",
                ),
                html.Div(
                    [
                        html.H3(
                            f"{df['perfil_risco_ips'].mean():.1f}",
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
            columns=[{"name": col, "id": col} for col in df.columns],
            data=df.to_dict("records"),
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

relatorio_gerencial_page = html.Div(
    [
        html.H3("Relatório Gerencial Carteiras", className="page-title"),
        dt.DataTable(
            id="relatorio-table",
            columns=[
                {"name": "Carteira", "id": "carteira"},
                {"name": "Ativo", "id": "ativo"},
                {"name": "Descrição", "id": "descricao"},
                {"name": "Saldo Bruto", "id": "saldo_bruto"},
            ],
            data=[
                {
                    "carteira": "FINACAP009",
                    "ativo": "04.899.128/0001-90",
                    "descricao": "Sul América Excellence FI RF Créd Priv",
                    "saldo_bruto": "44.519,63",
                },
                {
                    "carteira": "FINACAP009",
                    "ativo": "05.964.067/0001-60",
                    "descricao": "Finacap Mauritstad FIA",
                    "saldo_bruto": "191.654,39",
                },
                {
                    "carteira": "FINACAP009",
                    "ativo": "29.562.673/0001-57",
                    "descricao": "BTG Pactual Digital Tesouro Selic Simples FI RF",
                    "saldo_bruto": "18.757,83",
                },
            ],
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

lamina_page = html.Div(
    [
        html.H3("Lamina", className="page-title"),
        html.Div(
            [
                html.P(
                    "Conteúdo da página de lamina em construção.",
                    className="page-content",
                )
            ]
        ),
    ]
)


# Callback para alternar entre autenticação e dashboard
@app.callback(
    Output("auth-page-content", "children"),
    [Input("submit-button", "n_clicks"), Input("token-input", "n_submit")],
    [State("token-input", "value")],
)
def validar_token(n_clicks, n_submit, token):
    if (n_clicks > 0 or n_submit) and token == TOKEN_CORRETO:
        return dashboard_layout
    return auth_layout


# Callback para redefinir a URL após logout
@app.callback(
    Output("auth-url", "pathname"),
    [Input("auth-page-content", "children")],
)
def reset_url_on_logout(content):
    # Redefine a URL para "/" sempre que o layout é trocado para a tela de login
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


# Callback combinado para atualizar a tabela de clientes
@app.callback(
    Output("clientes-table", "data"),
    [
        Input("update-data-btn", "n_clicks"),
        Input("search-bar", "value"),
        Input("filter-column", "value"),
    ],
)
def update_clientes_table_or_data(n_clicks, search_value, filter_column):
    ctx = dash.callback_context  # Obter contexto do callback
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    global df
    # Se o botão de atualização for clicado
    if triggered_id == "update-data-btn" and n_clicks:
        df = fetch_data()  # Atualiza os dados globais

    filtered_df = df.copy()

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


# Layout principal
app.layout = html.Div(
    [
        dcc.Location(
            id="auth-url", refresh=False
        ),  # Captura a URL inicial para controle de autenticação
        dcc.Location(
            id="url", refresh=False
        ),  # Captura a URL para navegação interna no dashboard
        html.Div(id="auth-page-content", children=auth_layout),
    ]
)

if __name__ == "__main__":
    app.run_server(debug=True, port=8051)
