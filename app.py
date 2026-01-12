import os
import json
from dotenv import load_dotenv
import dash
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Carrega variáveis do arquivo .env se ele existir (uso local)
load_dotenv()

import logging
from flask import jsonify

# Configure structured logging via LOG_LEVEL env var
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s [%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('tibiatracker')
logger.debug("Environment loaded, LOG_LEVEL=%s", LOG_LEVEL)

# --- CONFIGURAÇÃO GOOGLE SHEETS ---
def carregar_dados_google_sheets():
    # Use a single space-separated scope string to avoid type-checker warnings
    scope = "https://spreadsheets.google.com/feeds https://www.googleapis.com/auth/drive"

    # Try credential path first (useful for .env to point to a file)
    creds = None
    creds_path = os.getenv("GOOGLE_CREDENTIALS_JSON_PATH")
    env_creds = os.getenv("GOOGLE_CREDENTIALS")

    if creds_path:
        try:
            # allow user to set a path like 'credenciais.json' or an absolute path
            if os.path.exists(creds_path):
                creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
            else:
                # try expanding user and retry
                creds_path_expanded = os.path.expanduser(creds_path)
                if os.path.exists(creds_path_expanded):
                    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path_expanded, scope)
                else:
                    logger.warning("GOOGLE_CREDENTIALS_JSON_PATH was set but file not found: %s", creds_path)
        except Exception as e:
            logger.exception("Erro ao carregar credenciais do caminho %s", creds_path)

    # Next, try JSON stored directly in the environment variable (supports escaped \n)
    if creds is None and env_creds:
        try:
            info = json.loads(env_creds)
        except Exception:
            # try to fix common formatting issues: strip quotes and unescape newlines
            s = env_creds.strip()
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                s = s[1:-1]
            s = s.replace('\\n', '\n')
            try:
                info = json.loads(s)
            except Exception as e:
                logger.exception("Invalid GOOGLE_CREDENTIALS JSON in environment (attempted to unescape)); raw length=%d", len(env_creds) if env_creds else 0)
                raise ValueError("GOOGLE_CREDENTIALS env var is set but not valid JSON or improperly escaped") from e
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        logger.debug("Loaded credentials from environment for client_email=%s", info.get('client_email'))

    # Fallback to local file
    if creds is None:
        if os.path.exists('credenciais.json'):
            creds = ServiceAccountCredentials.from_json_keyfile_name('credenciais.json', scope)
        else:
            raise FileNotFoundError("Google credentials not provided. Set GOOGLE_CREDENTIALS (JSON string), GOOGLE_CREDENTIALS_JSON_PATH (path to file), or provide 'credenciais.json' in the project root.")

    client = gspread.authorize(creds)
    logger.debug("gspread client authorized with provided credentials")

    # Support multiple env var names for spreadsheet id
    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID") or os.getenv("SPREADSHEET_ID") or "1sFde6uvz0UdR1Vd1KJ7kflxqZd_-ydJuphesMMOLyMA"
    try:
        sh = client.open_by_key(spreadsheet_id)
    except Exception as e:
        # Try to extract the service account email to provide a helpful hint
        client_email = None
        try:
            if creds_path and os.path.exists(creds_path):
                with open(creds_path, 'r', encoding='utf-8') as f:
                    j = json.load(f)
                    client_email = j.get('client_email')
            elif env_creds:
                try:
                    j = json.loads(env_creds)
                except Exception:
                    s = env_creds.strip()
                    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                        s = s[1:-1]
                    s = s.replace('\\n', '\n')
                    j = json.loads(s)
                client_email = j.get('client_email')
        except Exception:
            client_email = None
        logger.error("Spreadsheet not accessible (HTTP 404 or not found). Check that GOOGLE_SPREADSHEET_ID is correct and that the spreadsheet is shared with the service account (email: %s)", client_email or 'service-account@example.com')
        raise ValueError(
            f"Spreadsheet not accessible (HTTP 404 or not found). Check that GOOGLE_SPREADSHEET_ID is correct and that the spreadsheet is shared with the service account (email: {client_email or 'service-account@example.com'})."
        ) from e

    worksheet = sh.worksheet(os.getenv("GOOGLE_WORKSHEET_NAME", "EXP/DIA"))

    dados = worksheet.get_all_records()
    return pd.DataFrame(dados)

# --- LÓGICA DE XP ---
def cumulative_exp_closed(level):
    if level <= 1: return 0
    m = level - 1
    sum_k2 = m * (m + 1) * (2 * m + 1) // 6
    sum_k = m * (m + 1) // 2
    return 50 * sum_k2 - 150 * sum_k + 200 * m

def find_level_for_exp(total_exp):
    low, high = 1, 2500
    while low < high:
        mid = (low + high + 1) // 2
        if cumulative_exp_closed(mid) <= total_exp: low = mid
        else: high = mid - 1
    return low

# --- INICIALIZAÇÃO DE VARIÁVEIS ---
level_estimado = 1000
level_real, media_geral, media_recente, dias_restantes, xp_meta_diaria = 0, 0, 0, 0, 0
xp_faltante = 0
eta_str, tendencia_status, cor_tendencia = "N/A", "Aguardando...", "secondary"
streak_count, melhor_dia_xp, melhor_dia_data = 0, 0, "N/A"
texto_delta, cor_delta = "N/A", "secondary"
df = pd.DataFrame()
pivot = pd.DataFrame()
historico_milestones = []
fig_roadmap = go.Figure()
desvio_padrao, score_consistencia = 0, 0.0
current_streak_baixo, streak_baixo_texto, cor_streak_baixo = 0, "OK", "secondary"
fig_moving_avg = go.Figure()
fig_dia_semana = go.Figure()
fig_heatmap = go.Figure()
fig_cenarios = go.Figure()

# --- PROCESSAMENTO DOS DADOS (GOOGLE SHEETS) ---
try:
    df = carregar_dados_google_sheets()
    df['create_at'] = pd.to_datetime(df['create_at'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['create_at', 'Experience']).sort_values('create_at')
    
    if not df.empty:
        df['Experience'] = pd.to_numeric(df['Experience'], errors='coerce')
        df['daily_exp'] = df['Experience'].diff().fillna(0)
        df.loc[df['daily_exp'] < 0, 'daily_exp'] = 0

        xp_consolidada = df['Experience'].iloc[-1]
        level_real = find_level_for_exp(xp_consolidada)
        logger.info("Loaded spreadsheet data: rows=%d, xp_consolidada=%s, level_real=%s, media_recente=%s", len(df), xp_consolidada, level_real, media_recente)
        
        # Médias e ETA
        positive_hunts = df[df['daily_exp'] > 0]['daily_exp']
        media_geral = positive_hunts.mean() if not positive_hunts.empty else 0
        recent_df = df.tail(30)
        media_recente = recent_df[recent_df['daily_exp'] > 0]['daily_exp'].mean() if not recent_df[recent_df['daily_exp'] > 0].empty else media_geral
        
        # --- Desvio e Consistência ---
        desvio_padrao = positive_hunts.std() if len(positive_hunts) > 1 else 0
        score_consistencia = (len(positive_hunts[positive_hunts >= media_recente]) / len(positive_hunts) * 100) if len(positive_hunts) > 0 else 0

        xp_objetivo = cumulative_exp_closed(level_estimado)
        xp_faltante = xp_objetivo - xp_consolidada
        
        if media_recente > 0:
            dias_restantes = int(xp_faltante / media_recente)
            dias_restantes_capped = min(max(dias_restantes, 1), 18250)
            eta_str = (datetime.now() + timedelta(days=dias_restantes_capped)).strftime("%d/%m/%Y")
            xp_meta_diaria = xp_faltante / dias_restantes_capped

        # Streak e Recorde
        streak_count = 0
        for val in df['daily_exp'].iloc[::-1]:
            if val >= xp_meta_diaria and xp_meta_diaria > 0: 
                streak_count += 1
            else: 
                break
        
        idx_max = df['daily_exp'].idxmax()
        melhor_dia_xp = df.loc[idx_max, 'daily_exp']
        melhor_dia_data = df.loc[idx_max, 'create_at'].strftime("%d/%m/%Y")

        # Performance Hoje vs Meta
        xp_hoje = df['daily_exp'].iloc[-1]
        delta_meta = xp_hoje - xp_meta_diaria
        cor_delta = "success" if delta_meta >= 0 else "danger"
        texto_delta = f"{'+' if delta_meta > 0 else ''}{delta_meta/1e6:.1f}M vs Meta"

        # Projeção
        df['Exp_Projetada'] = df['Experience'].iloc[0] + (df.reset_index().index * xp_meta_diaria)
        df['Meta_SLA'] = xp_meta_diaria
        
        # --- Médias Móveis ---
        df['MM7'] = df['daily_exp'].rolling(window=7, min_periods=1).mean()
        df['MM30'] = df['daily_exp'].rolling(window=30, min_periods=1).mean()

        # Roadmap e Histórico
        fig_roadmap.add_trace(go.Bar(x=[level_estimado], y=["Progresso"], orientation='h', marker_color="#333", showlegend=False))
        fig_roadmap.add_trace(go.Bar(x=[level_real], y=["Progresso"], orientation='h', marker_color="#E6BC53", name="Atual"))
        
        for m in [200, 400, 600, 800, 900, 1000]:
            fig_roadmap.add_vline(x=m, line_width=2, line_dash="dash", line_color="white")
            xp_m = cumulative_exp_closed(m)
            alcancado = df[df['Experience'] >= xp_m]
            if not alcancado.empty:
                data_m = alcancado.iloc[0]['create_at'].strftime("%d/%m/%Y")
                historico_milestones.append(html.Li(f"Level {m} atingido em: {data_m}", className="text-success"))
            else:
                historico_milestones.append(html.Li(f"Level {m}: Ainda não alcançado", className="text-muted"))

        fig_roadmap.update_layout(showlegend=False, barmode='overlay', height=80, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(range=[0, 1000]), yaxis=dict(showticklabels=False), font_color="white")

        # Tendência
        if media_recente > media_geral * 1.05: tendencia_status, cor_tendencia = "↑", "success"
        elif media_recente < media_geral * 0.95: tendencia_status, cor_tendencia = "↓", "danger"
        else: tendencia_status, cor_tendencia = "ESTÁVEL", "info"
        
        # --- Análise de Risco / Streak Baixo ---
        df['abaixo_meta'] = df['daily_exp'] < (xp_meta_diaria * 0.1)
        rev_baixo = df['abaixo_meta'].iloc[::-1]
        current_streak_baixo = int(rev_baixo.groupby((~rev_baixo).cumsum()).cumsum().iloc[0])
        cor_streak_baixo = "danger" if current_streak_baixo > 3 else "success"
        streak_baixo_texto = f"{current_streak_baixo}d" if current_streak_baixo > 0 else "OK"

        # Heatmap
        df_heatmap = df.copy()
        df_heatmap['Semana'] = "S" + df_heatmap['create_at'].dt.strftime('%V')
        df_heatmap['Dia'] = df_heatmap['create_at'].dt.day_name().map({'Monday':'Seg','Tuesday':'Ter','Wednesday':'Qua','Thursday':'Qui','Friday':'Sex','Saturday':'Sab','Sunday':'Dom'})
        pivot = df_heatmap.pivot_table(index='Dia', columns='Semana', values='daily_exp', aggfunc='sum', fill_value=0).reindex(['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'])
        
       # --- Gráfico Heatmap ---
        fig_heatmap = px.imshow(pivot / 1e6, color_continuous_scale='blues')
        fig_heatmap.update_layout(
            template='plotly_dark', 
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
            coloraxis_colorbar=dict(title="Soma XP (M)")
        )
        
        # --- Média por Dia da Semana ---
        dias_order = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
        media_dia_semana = df_heatmap.groupby('Dia')['daily_exp'].mean().reindex(dias_order).fillna(0) / 1e6
        fig_dia_semana = px.bar(
            x=media_dia_semana.values,
            y=media_dia_semana.index,
            orientation='h',
            # text=[f"{v:.1f}" for v in media_dia_semana.values],
            color=media_dia_semana.values,
            color_continuous_scale='blues',
            title="Média XP por Dia da Semana (milhões)"
        )
        fig_dia_semana.update_traces(textposition='auto')
        fig_dia_semana.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis_autorange="reversed",
            coloraxis_showscale=False,
            showlegend=False,
            xaxis_title="Média (M)",
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(0,0,0,0.5)" # Fundo semi-transparente para não cobrir as linhas
            )
        )
        
        # --- Gráfico Médias Móveis ---
        fig_moving_avg = go.Figure([
            go.Scatter(x=df['create_at'], y=df['daily_exp']/1e6, mode='lines+markers', name="Diário", 
                       line=dict(color='#17a2b8'), marker=dict(size=4)),
            go.Scatter(x=df['create_at'], y=df['MM7']/1e6, name="MM 7 dias", line=dict(color='#ffc107', width=3)),
            go.Scatter(x=df['create_at'], y=df['MM30']/1e6, name="MM 30 dias", line=dict(color='#dc3545', width=3))
        ])
        fig_moving_avg.update_layout(
            title="XP Diário + Médias Móveis",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Data",
            yaxis_title="XP (milhões)",
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)")
        )
        
        # --- NOVOS CENÁRIOS DE ETA (corrigido: usa dias_limitados no X) ---
        cenarios = {
            "Média Geral": media_geral,
            "Média Recente (30d)": media_recente,
            "Ritmo Recorde": melhor_dia_xp
        }
        
        nomes_cenarios = []
        datas_cenarios = []
        dias_cenarios = []

        for nome, media in cenarios.items():
            if media > 0:
                dias = int(xp_faltante / media)
                dias_limitados = min(max(dias, 1), 3650) 
                data_prevista = (datetime.now() + timedelta(days=dias_limitados))
                
                nomes_cenarios.append(nome)
                datas_cenarios.append(data_prevista.strftime("%d/%m/%Y"))
                dias_cenarios.append(dias_limitados)  # CORRIGIDO: era 'dias'

        fig_cenarios = go.Figure(go.Bar(
            x=dias_cenarios,
            y=nomes_cenarios,
            orientation='h',
            text=[f"{d} dias ({dt})" for d, dt in zip(dias_cenarios, datas_cenarios)],
            marker_color=["#e1edf7", "#0b2d69", '#a7cde2']
        ))
        fig_cenarios.update_traces(textposition='auto')

        fig_cenarios.update_layout(
            title="Previsão de Conclusão por Cenário",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Dias Restantes",
            yaxis=dict(autorange="reversed")
        )

except Exception as e:
    logger.exception("Erro na conexão/processamento")
    # If the load failed (e.g. 404 or permission issue), provide helpful hint
    try:
        # gspread can include a Response in some exceptions
        if hasattr(e, 'response') and getattr(e, 'response') is not None:
            logger.debug("HTTP response: %s", getattr(e, 'response'))
    except Exception:
        pass

    logger.warning("Using fallback minimal DataFrame due to previous error: %s", str(e))
    # Fallback: create a minimal dataframe so the Dash app can still render
    df = pd.DataFrame([{
        'create_at': pd.to_datetime(datetime.now()),
        'Experience': 0,
        'daily_exp': 0,
        'MM7': 0,
        'MM30': 0,
        'Exp_Projetada': 0,
        'Meta_SLA': 0
    }])

    # Set conservative defaults for derived values used in layout
    xp_consolidada = 0
    level_real = find_level_for_exp(xp_consolidada)
    eta_str = "N/A"
    streak_count = 0
    melhor_dia_xp = 0
    melhor_dia_data = datetime.now().strftime("%d/%m/%Y")
    desvio_padrao = 0
    media_recente = 0
    score_consistencia = 0
    xp_faltante = 0
    xp_meta_diaria = 0
    tendencia_status, cor_tendencia = "N/A", "secondary"

    # Minimal empty figures so layout code can use them safely
    fig_roadmap = go.Figure()
    fig_moving_avg = go.Figure()
    fig_heatmap = go.Figure()
    fig_dia_semana = go.Figure()
    fig_cenarios = go.Figure()

# --- DASH LAYOUT ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

@server.route('/health')
def health():
    try:
        rows = len(df) if isinstance(df, pd.DataFrame) else 0
    except Exception:
        rows = 0
    return jsonify(status='ok', rows=rows)

logger.info("Registered /health endpoint")

app.layout = dbc.Container([
    html.H1("PROJETO ELDER DRUID 1000", className="text-center my-4 text-warning"),

    # Indicadores Topo (ORIGINAL)
    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("Level Real"), html.H2(level_real, className="text-primary")])]), width=2),
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("Previsão ETA"), html.H4(eta_str, className="text-warning")])]), width=3),
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("🔥 Streak"), html.H2(f"{streak_count} d", className="text-danger")])]), width=2),
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("🏆 Melhor Dia"), html.H3(f"{melhor_dia_xp/1e6:.1f}M"), html.Small(melhor_dia_data)])]), width=2),
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("Performance"), html.H3(tendencia_status, className=f"text-{cor_tendencia}")])]), width=3),
    ], className="mb-4 text-center"),

    # --- Cards Métricas Avançadas ---
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Desvio Padrão"),
                html.H4(f"{desvio_padrao/1e6:.1f}M", className="text-info")
            ])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Média Recente"),
                html.H3(f"{media_recente/1e6:.1f}M", className="text-primary")
            ])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Consistência"),
                html.H4(f"{score_consistencia:.0f}%", className="text-success" if score_consistencia > 60 else "text-warning")
            ])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Streak Ruim"),
                html.H4(streak_baixo_texto, className=f"text-{cor_streak_baixo}")
            ])
        ]), width=3),
    ], className="mb-4 text-center"),

    # Roadmap (ORIGINAL)
    dbc.Card([
        dbc.CardHeader("ROADMAP DE PROGRESSO"),
        dbc.CardBody([dcc.Graph(figure=fig_roadmap, config={'displayModeBar': False})])
    ], className="mb-4"),

    # --- Médias Móveis ---
    dbc.Card([
        dbc.CardHeader("XP DIÁRIO + MÉDIAS MÓVEIS"),
        dbc.CardBody(dcc.Graph(figure=fig_moving_avg, config={'displayModeBar': False}))
    ], className="mb-4"),

    # Heatmap (MELHORADO)
    dbc.Card([
        dbc.CardHeader("INTENSIDADE DE HUNTS (HISTÓRICO ONLINE)"),
        dbc.CardBody(dcc.Graph(figure=fig_heatmap))
    ], className="mb-4"),

    # --- Dia da Semana ---
    dbc.Card([
        dbc.CardHeader("MÉDIA XP POR DIA DA SEMANA"),
        dbc.CardBody(dcc.Graph(figure=fig_dia_semana, config={'displayModeBar': False}))
    ], className="mb-4"),

    # Gráficos de Meta e Curva (MELHORADOS com /1e6 e /1e9)
    dbc.Row([
        dbc.Col(dcc.Graph(figure=go.Figure([
            go.Scatter(x=df['create_at'], y=df['daily_exp']/1e6, name="Real", line=dict(color='#17a2b8')),
            go.Scatter(x=df['create_at'], y=df['Meta_SLA']/1e6, name="Meta Requerida", line=dict(dash='dash', color='white'))
        ]).update_layout(
            title="Aderência à Meta Diária", 
            template="plotly_dark", 
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis_title="XP (M)",
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)")
        )), width=5),
        
        dbc.Col(dcc.Graph(figure=go.Figure([
            go.Scatter(x=df['create_at'], y=df['Experience']/1e9, name="Acumulado Real", fill='tozeroy', line=dict(color='#007bff')),
            go.Scatter(x=df['create_at'], y=df['Exp_Projetada']/1e9, name="Linha de Meta", line=dict(color='orange', dash='dot'))
        ]).update_layout(
            title="Curva de Entrega vs Plano", 
            template="plotly_dark", 
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis_title="XP Acumulado (B)",
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)")
        )), width=7),
    ], className="mb-4"),

    # Status de Saúde e Esforço (ORIGINAL)
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("SAÚDE DO DIA"),
            dbc.CardBody([
                html.H5("Diferença da Meta Hoje", className="card-title"),
                html.P(texto_delta, className=f"text-{cor_delta} h2"),
            ])
        ]), width=6),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("ESFORÇO PARA O FINAL"),
            dbc.CardBody([
                html.H5("Hunts de Recorde Necessárias", className="card-title"),
                html.P(f"~ {int(xp_faltante / melhor_dia_xp) if melhor_dia_xp > 0 else 0} dias", className="text-info h2"),
            ])
        ]), width=6),
    ], className="mb-4 text-center"),

    # Novo Card de Cenários de ETA
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("ANÁLISE DE CENÁRIOS (ETA)"),
            dbc.CardBody([
                dcc.Graph(figure=fig_cenarios, config={'displayModeBar': False})
            ])
        ]), width=12),
    ], className="mb-4"),

    # Histórico de Conquistas (ORIGINAL)
    dbc.Card([
        dbc.CardHeader("HISTÓRICO DE MARCOS ATINGIDOS"),
        dbc.CardBody([html.Ul(historico_milestones)])
    ], className="mb-4")

], fluid=True)

if __name__ == '__main__':
    logger.info("Starting Dash app on http://127.0.0.1:8050/")
    app.run(debug=True)