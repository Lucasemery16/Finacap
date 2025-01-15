import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State

app_auth = dash.Dash(__name__, suppress_callback_exceptions=True)
app_auth.title = "Autenticação Finacap"
app_auth.config.suppress_callback_exceptions = True

# Token definido
TOKEN_CORRETO = "#Finacap@"

# Layout da tela de autenticação com classe CSS
auth_layout = html.Div([
    html.Div([
        html.Img(src='/assets/logo_finacap.png', className='logo'),
        
        # Campo de input para o token
        dcc.Input(
            id="token-input", 
            type="password", 
            placeholder="Token...", 
            className="input-field"
        ),
        
        # Botão para alternar entre mostrar e esconder a senha
        html.Button(
            html.I(className="fa fa-eye"),  # Ícone de olho para mostrar/esconder a senha
            id="toggle-password", 
            n_clicks=0, 
            className="eye-button"
        ),
        
        html.Button("Entrar", id="submit-button", n_clicks=0, className="button"),
        
        # Mensagem de status do token
        html.Div(id="token-status", className="status-message")
    ], className="auth-box")  # auth-box vai estilizar a caixa branca
], className="main-container")  # main-container vai estilizar o fundo

# Define o layout principal como a tela de autenticação
app_auth.layout = html.Div([
    dcc.Location(id="auth-url", refresh=False),
    html.Div(id="auth-page-content", children=auth_layout)
])

# Callback para validar o token
@app_auth.callback(
    Output("token-status", "children"),
    [Input("submit-button", "n_clicks")],
    [State("token-input", "value")]
)
def validar_token(n_clicks, token):
    if n_clicks > 0:
        if token == TOKEN_CORRETO:
            return html.Div("Token correto!", style={'color': 'green'})
        else:
            return html.Div("Tente de novo, senha errada.", style={'color': 'red'})
    return ""

# Callback para alternar a visibilidade da senha
@app_auth.callback(
    Output("token-input", "type"),
    [Input("toggle-password", "n_clicks")],
    [State("token-input", "type")]
)
def toggle_password_visibility(n_clicks, input_type):
    if n_clicks % 2 == 0:
        return "password"  # Senha oculta
    return "text"  # Senha visível

if __name__ == "__main__":
    app_auth.run_server(debug=True)
