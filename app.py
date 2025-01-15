import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import dash.dash_table as dt
import pandas as pd
import psycopg2

# Função para obter os dados do banco de dados PostgreSQL
def fetch_data():
    # Conexão ao banco de dados PostgreSQL
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="postgres",
        host="localhost",
        port="5432"
    )

    # Consulta SQL para obter os dados da tabela 'clientes'
    query = """
    SELECT codigo_finacap, cliente_ativo, nome_cliente, gestor, suitability_cliente,
           perfil_risco_ips, tipo_ips, patrimonio
    FROM clientes;
    """

    # Carregando os dados na tabela 'clientes' em um DataFrame
    df = pd.read_sql(query, conn)

    # Fechar a conexão com o banco de dados
    conn.close()

    return df


# Inicializando a aplicação Dash com controle de rotas
app = dash.Dash(__name__)
app.title = "Dashboard Finacap"
app.config.suppress_callback_exceptions = True

# Carregar os dados do banco de dados
df = fetch_data()

# Corrigir valores e evitar erro de KeyError
df['cliente_ativo'] = df['cliente_ativo'].str.strip().str.capitalize()

# Converter a coluna 'perfil_risco_ips' para valores numéricos
df['perfil_risco_ips'] = pd.to_numeric(df['perfil_risco_ips'], errors='coerce')

# Gráficos

# PL Atual: Gráfico de Pizza
fig_pie = px.pie(df, names="suitability_cliente", values="patrimonio", title="Distribuição de Patrimônio por Suitability")

# Clientes: Gráfico de Barras
fig_bar = px.bar(df, x="nome_cliente", y="patrimonio", title="Patrimônio por Cliente")

# Sidebar com links para navegação
sidebar = html.Div(
    [
        html.Img(src="/assets/logo_finacap.png", className="logo"),
        html.H2("Dashboard Finacap", className="title"),
        html.Hr(),
        dcc.Link("Clientes Ativos", href="/clientes-ativos", className="menu-item"),
        dcc.Link("Patrimônio Total", href="/patrimonio-total", className="menu-item"),
        dcc.Link("Revisões Pendentes", href="/revisoes-pendentes", className="menu-item"),
        dcc.Link("Configurações", href="/configuracoes", className="menu-item"),
        dcc.Link("Sair", href="/sair", className="menu-item"),
    ],
    className="sidebar",
)

# Layout da Página de Clientes Ativos (com tudo exibido)
clientes_ativos_page = html.Div(
    [
        html.H3("Clientes Ativos", className="table-title"),
        # Cards de Métricas
        html.Div(
            [
                html.Div(
                    [
                        html.H3(f"{df['cliente_ativo'].value_counts().get('Sim', 0)}"),
                        html.P("Clientes Ativos"),
                    ],
                    className="card",
                ),
                html.Div(
                    [
                        html.H3(f"R$ {df['patrimonio'].sum():,.2f}"),
                        html.P("Patrimônio Total"),
                    ],
                    className="card",
                ),
                html.Div(
                    [
                        html.H3(f"{len(df[df['perfil_risco_ips'] > 4])}"),
                        html.P("Revisões Pendentes"),
                    ],
                    className="card",
                ),
                html.Div(
                    [
                        html.H3(f"{df['perfil_risco_ips'].mean():.1f}"),
                        html.P("Exposição CP Média"),
                    ],
                    className="card",
                ),
            ],
            className="cards-container",
        ),
        # Gráficos
        html.Div(
            [
                html.Div([dcc.Graph(figure=fig_pie)], className="graph"),
                html.Div([dcc.Graph(figure=fig_bar)], className="graph"),
            ],
            className="graphs-container",
        ),
        # Tabela de Clientes (Com o CSS do arquivo fornecido)
        html.Div(
            [
                html.H3("Tabela de Clientes", className="table-title"),
                dt.DataTable(
                    id="clientes-table",
                    columns=[{"name": col, "id": col} for col in df.columns],
                    data=df.to_dict("records"),
                    style_table={"overflowX": "auto"},
                    style_header={
                        "backgroundColor": "#1b51b1",
                        "color": "white",
                        "fontWeight": "bold",
                        "textAlign": "center",
                    },
                    style_cell={"textAlign": "center", "padding": "10px"},
                    style_data={"border": "1px solid #cbd6e2"},
                ),
            ],
            className="table-container",
        ),
    ]
)

# Layout da Página de Patrimônio Total
patrimonio_total_page = html.Div(
    [
        html.H3("Patrimônio Total"),
        html.Div(
            [html.H3(f"R$ {df['patrimonio'].sum():,.2f}"), html.P("Patrimônio Total")],
            className="card",
        ),
        dcc.Graph(figure=fig_pie),
    ]
)

# Layout da Página de Revisões Pendentes
revisoes_pendentes_page = html.Div(
    [
        html.H3("Revisões Pendentes"),
        html.Div(
            [
                html.H3(f"{len(df[df['perfil_risco_ips'] > 4])}"),
                html.P("Revisões Pendentes"),
            ],
            className="card",
        ),
    ]
)

# Layout da Página de Configurações
configuracoes_page = html.Div(
    [html.H3("Configurações"), html.P("Ajuste suas configurações aqui.")]
)

# Layout da Página de Logout
logout_page = html.Div(
    [html.H3("Você saiu do sistema."), html.P("Obrigado por usar o Dashboard Finacap.")]
)

# Layout principal que controla as rotas
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        sidebar,
        html.Div(id="page-content", className="content"),
    ]
)


# Callback para controle de navegação
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def display_page(pathname):
    if pathname == "/clientes-ativos" or pathname == "/":
        return clientes_ativos_page
    elif pathname == "/patrimonio-total":
        return patrimonio_total_page
    elif pathname == "/revisoes-pendentes":
        return revisoes_pendentes_page
    elif pathname == "/configuracoes":
        return configuracoes_page
    elif pathname == "/sair":
        return logout_page
    else:
        return html.Div(
            [
                html.H3("Página não encontrada!!"),
                html.P("A página solicitada não existe."),
            ]
        )


# Executando o servidor
if __name__ == "__main__":
    app.run_server(debug=True)
