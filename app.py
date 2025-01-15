import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# Inicializando a aplicação Dash
app = dash.Dash(__name__)

# Simulando um dataset para o Dashboard com as colunas indicadas
df = pd.DataFrame({
    "Código Finacap": [1001, 1002, 1003, 1004],
    "CLIENTE ATIVO": ["Sim", "Não", "Sim", "Sim"],
    "Nome do Cliente": ["João Silva", "Maria Oliveira", "Carlos Santos", "Ana Souza"],
    "Gestor": ["Gestor A", "Gestor B", "Gestor A", "Gestor C"],
    "Suitability Cliente": ["Conservador", "Moderado", "Agressivo", "Moderado"],
    "Perfil de Risco (IPS)": [3, 5, 7, 4],
    "TIPO IPS": ["Fundo", "Ação", "Fundo", "CDB"],
    "Patrimônio": [150000, 200000, 300000, 100000]
})

# Gráficos para representar os dados
fig_pie = px.pie(df, names="Suitability Cliente", values="Patrimônio", title="Distribuição de Patrimônio por Suitability")
fig_bar = px.bar(df, x="Nome do Cliente", y="Patrimônio", title="Patrimônio por Cliente")

# Layout do Dashboard com CSS externo aplicado
app.layout = html.Div([
    # Sidebar com a logo e estilos atualizados
    html.Div([
        html.Img(src='/assets/logo_finacap.png', className='logo'),
        html.H2("Dashboard Finacap", className="title"),
        html.Hr(),
        html.P("Clientes Ativos", className="menu-item"),
        html.P("Patrimônio Total", className="menu-item"),
        html.P("Revisões Pendentes", className="menu-item"),
        html.P("Configurações", className="menu-item"),
        html.P("Sair", className="menu-item"),
    ], className="sidebar"),

    # Conteúdo principal com CSS
    html.Div([
        # Cards com Métricas
        html.Div([
            html.Div([
                html.H3(f"{df['CLIENTE ATIVO'].value_counts()['Sim']}"),
                html.P("Clientes Ativos")
            ], className="card"),

            html.Div([
                html.H3(f"R$ {df['Patrimônio'].sum():,.2f}"),
                html.P("Patrimônio Total")
            ], className="card"),

            html.Div([
                html.H3(f"{len(df[df['Perfil de Risco (IPS)'] > 4])}"),
                html.P("Revisões Pendentes")
            ], className="card"),

            html.Div([
                html.H3(f"{df['Perfil de Risco (IPS)'].mean():.1f}"),
                html.P("Exposição CP Média")
            ], className="card")
        ], className="cards-container"),

        # Gráficos
        html.Div([
            html.Div([dcc.Graph(figure=fig_pie)], className="graph"),
            html.Div([dcc.Graph(figure=fig_bar)], className="graph")
        ], className="graphs-container"),

        # Tabela de Clientes
        html.Div([
            html.H3("Tabela de Clientes", className="table-title"),
            html.Table([
                html.Tr([html.Th(col, className="table-header") for col in df.columns]),
                *[html.Tr([html.Td(df.iloc[i][col], className="table-data") for col in df.columns]) for i in range(len(df))]
            ], className="table")
        ], className="table-container")
    ], className="content")
])

# Executando o servidor
if __name__ == "__main__":
    app.run_server(debug=True)
