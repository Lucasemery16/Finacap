import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import dash.dash_table as dt
import pandas as pd
import psycopg2
import requests
import json

# Função para obter os dados do banco de dados PostgreSQL
def fetch_postgres_data():
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="Nautico1901",
        host="localhost",
        port="5432"
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
    payload = (
        f"username={username}&password={password}&URL=RelatorioGerencialCarteiras001.php%3F"
        f"%26data_analise%3D{date}%26data_ini%3D%26nome_portfolio%3D{portfolio}"
        f"%26variaveis%3Dnome_portfolio%2Bativo%2Bdesc%2Bsaldo_bruto%26filtro%3Dall"
        f"%26ativo%3D%26filtro_IF%3Dtodos%26relat_alias%3D%26layout%3D0%26layoutB%3D0"
        f"%26num_casas%3D%26enviar_email%3D0%26portfolio_editavel%3D%26filtro_id%3D&format=json3"
    )
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    response = requests.post(url, data=payload, headers=headers, params=querystring)
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return {"error": f"Failed to fetch data: {response.status_code}"}

# Função para combinar os dados de ambas as fontes
def fetch_data():
    postgres_df = fetch_postgres_data()

    api_data = fetch_comdinheiro_data(
        username="consulta.finacap",
        password="#Consult@finac@p2025",
        date="31122024",
        portfolio="FINACAP009+FINACAP147"
    )

    if "error" not in api_data:
        api_df = pd.DataFrame(api_data['data'])  # Ajustar conforme o formato do retorno da API
        combined_df = pd.concat([postgres_df, api_df], ignore_index=True)
        return combined_df
    else:
        print(api_data["error"])
        return postgres_df

# Inicializando a aplicação Dash com controle de rotas
app = dash.Dash(__name__)
app.title = "Dashboard Finacap"
app.config.suppress_callback_exceptions = True

df = fetch_data()
df['cliente_ativo'] = df['cliente_ativo'].str.strip().str.capitalize()
df['perfil_risco_ips'] = pd.to_numeric(df['perfil_risco_ips'], errors='coerce')

# Gráficos
fig_pie = px.pie(df, names="suitability_cliente", values="patrimonio", title="Distribuição de Patrimônio por Suitability")
fig_bar = px.bar(df, x="nome_cliente", y="patrimonio", title="Patrimônio por Cliente")

# Sidebar com links para navegação
sidebar = html.Div(
    [
        html.Img(src="/assets/logo_finacap.png", className="logo"),
        html.H2("Dashboard Finacap", className="title"),
        html.Hr(),
        dcc.Link("Clientes Ativos", href="/clientes-ativos", className="menu-item"),
        dcc.Link("Clientes", href="/clientes", className="menu-item"),
        dcc.Link("Patrimônio Total", href="/patrimonio-total", className="menu-item"),
        dcc.Link("Revisões Pendentes", href="/revisoes-pendentes", className="menu-item"),
        dcc.Link("Relatório Gerencial Carteiras", href="/relatorio-gerencial", className="menu-item"),  # Nova aba
        dcc.Link("Configurações", href="/configuracoes", className="menu-item"),
        dcc.Link("Sair", href="/sair", className="menu-item"),
        html.Button("Atualizar Dados", id="update-data-btn", className="update-button"),
    ],
    className="sidebar",
)

# Layout da Página de Clientes Ativos
clientes_ativos_page = html.Div(
    [
        html.H3("Clientes Ativos", className="table-title"),
        html.Div(
            [
                html.Div([ 
                    html.H3(f"{df['cliente_ativo'].value_counts().get('Sim', 0)}"),
                    html.P("Clientes Ativos")
                ], className="card"),
                html.Div([ 
                    html.H3(f"R$ {df['patrimonio'].sum():,.2f}"),
                    html.P("Patrimônio Total")
                ], className="card"),
                html.Div([ 
                    html.H3(f"{len(df[df['perfil_risco_ips'] > 4])}"),
                    html.P("Revisões Pendentes")
                ], className="card"),
                html.Div([ 
                    html.H3(f"{df['perfil_risco_ips'].mean():.1f}"),
                    html.P("Exposição CP Média")
                ], className="card"),
            ],
            className="cards-container",
        ),
        html.Div(
            [
                html.Div([dcc.Graph(figure=fig_pie)], className="graph"),
                html.Div([dcc.Graph(figure=fig_bar)], className="graph"),
            ],
            className="graphs-container",
        ),
    ]
)

# Layout da Página de Clientes com a Tabela e Barra de Busca
tabela_clientes_page = html.Div(
    [
        html.H3("Tabela de Clientes", className="table-title"),
        dcc.Input(
            id="search-bar",
            type="text",
            placeholder="Digite para buscar...",
            style={"marginBottom": "10px", "width": "100%", "padding": "10px", "fontSize": "16px"}
        ),
        dt.DataTable(
            id="clientes-table",
            columns=[{"name": col, "id": col} for col in df.columns],
            data=df.to_dict("records"),
            style_table={"overflowX": "auto", "overflowY": "scroll", "maxHeight": "500px"},
            style_header={
                "backgroundColor": "#1b51b1",
                "color": "white",
                "fontWeight": "bold",
                "textAlign": "center",
            },
            style_cell={"textAlign": "center", "padding": "10px"},
            style_data={"border": "1px solid #cbd6e2"}
        ),
    ],
    className="table-container",
)

# Layout da Página de Relatório Gerencial Carteiras
relatorio_gerencial_page = html.Div(
    [
        html.H3("Relatório Gerencial Carteiras", className="table-title"),
        dt.DataTable(
            id="relatorio-table",
            columns=[
                {"name": "Carteira", "id": "carteira"},
                {"name": "Ativo", "id": "ativo"},
                {"name": "Descrição", "id": "descricao"},
                {"name": "Saldo Bruto", "id": "saldo_bruto"},
            ],
            # Dados simulados
            data=[
                {"carteira": "FINACAP009", "ativo": "04.899.128/0001-90", "descricao": "Sul América Excellence FI RF Créd Priv", "saldo_bruto": "44.519,63"},
                {"carteira": "FINACAP009", "ativo": "05.964.067/0001-60", "descricao": "Finacap Mauritstad FIA", "saldo_bruto": "191.654,39"},
                {"carteira": "FINACAP009", "ativo": "29.562.673/0001-57", "descricao": "BTG Pactual Digital Tesouro Selic Simples FI RF", "saldo_bruto": "18.757,83"},
            ],
            style_table={"overflowX": "auto", "overflowY": "scroll", "maxHeight": "500px"},
            style_header={
                "backgroundColor": "#1b51b1",
                "color": "white",
                "fontWeight": "bold",
                "textAlign": "center",
            },
            style_cell={"textAlign": "center", "padding": "10px"},
            style_data={"border": "1px solid #cbd6e2"}
        ),
    ],
    className="table-container",
)

# Layouts para as outras páginas
patrimonio_total_page = html.Div([html.H3("Patrimônio Total"), dcc.Graph(figure=fig_pie)])
revisoes_pendentes_page = html.Div([html.H3("Revisões Pendentes")])
configuracoes_page = html.Div([html.H3("Configurações")])
logout_page = html.Div([html.H3("Você saiu do sistema.")])

# Layout principal e controle de rotas
app.layout = html.Div([ 
    dcc.Location(id="url", refresh=False),
    sidebar,
    html.Div(id="page-content", className="content"),
])

# Callback para controle de rotas
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def display_page(pathname):
    if pathname in ["/clientes-ativos", "/"]:
        return clientes_ativos_page
    elif pathname == "/clientes":
        return tabela_clientes_page
    elif pathname == "/patrimonio-total":
        return patrimonio_total_page
    elif pathname == "/revisoes-pendentes":
        return revisoes_pendentes_page
    elif pathname == "/relatorio-gerencial":
        return relatorio_gerencial_page
    elif pathname == "/configuracoes":
        return configuracoes_page
    elif pathname == "/sair":
        return logout_page
    else:
        return html.Div([html.H3("Página não encontrada!!")])

# Callback para buscar e atualizar a tabela dinamicamente
@app.callback(
    Output("clientes-table", "data"),
    [Input("search-bar", "value")]
)
def update_clientes_table(search_value):
    if not search_value:
        return df.to_dict("records")
    filtered_df = df[df.apply(lambda row: row.astype(str).str.contains(search_value, case=False).any(), axis=1)]
    return filtered_df.to_dict("records")

if __name__ == "__main__":
    app.run_server(debug=True)
