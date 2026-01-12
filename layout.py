# layout.py
import dash_bootstrap_components as dbc
from dash import html, dcc


def create_top_indicators(
    level_real: int,
    eta_str: str,
    streak_count: int,
    melhor_dia_xp: float,
    melhor_dia_data: str,
    tendencia_status: str,
    cor_tendencia: str
) -> dbc.Row:
    return dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Level Real"),
            html.H2(level_real, className="text-primary")
        ])), xs=6, md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Previsão ETA"),
            html.H4(eta_str, className="text-warning")
        ])), xs=6, md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("🔥 Streak"),
            html.H2(f"{streak_count} d", className="text-danger")
        ])), xs=6, md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("🏆 Melhor Dia"),
            html.H3(f"{melhor_dia_xp / 1e6:.1f}M"),
            html.Small(melhor_dia_data)
        ])), xs=6, md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Performance"),
            html.H3(tendencia_status, className=f"text-{cor_tendencia}")
        ])), xs=12, md=3),
    ], className="mb-4 text-center")


def create_advanced_metrics(
    desvio_padrao: float,
    media_recente: float,
    score_consistencia: float,
    streak_baixo_texto: str,
    cor_streak_baixo: str
) -> dbc.Row:
    consistencia_class = "text-success" if score_consistencia > 60 else "text-warning"
    
    return dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Desvio Padrão"),
            html.H4(f"{desvio_padrao / 1e6:.1f}M", className="text-info")
        ])), xs=6, md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Média Recente"),
            html.H3(f"{media_recente / 1e6:.1f}M", className="text-primary")
        ])), xs=6, md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Consistência"),
            html.H4(f"{score_consistencia:.0f}%", className=consistencia_class)
        ])), xs=6, md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Streak Ruim"),
            html.H4(streak_baixo_texto, className=f"text-{cor_streak_baixo}")
        ])), xs=6, md=3),
    ], className="mb-4 text-center")


def create_milestone_list(historico_milestones) -> html.Ul:
    items = []
    for level, data, alcanado in historico_milestones:
        if alcanado:
            items.append(html.Li(f"Level {level} atingido em: {data}", className="text-success"))
        else:
            items.append(html.Li(f"Level {level}: Ainda não alcançado", className="text-muted"))
    return html.Ul(items)


def create_health_effort_row(texto_delta: str, cor_delta: str, xp_faltante: float, melhor_dia_xp: float) -> dbc.Row:
    hunts_necessarias = int(xp_faltante / melhor_dia_xp) if melhor_dia_xp > 0 else 0
    return dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("SAÚDE DO DIA"),
            dbc.CardBody([
                html.H5("Diferença da Meta Hoje", className="card-title"),
                html.P(texto_delta, className=f"text-{cor_delta} h2"),
            ])
        ]), xs=12, md=6),
        dbc.Col(dbc.Card([
            dbc.CardHeader("ESFORÇO PARA O FINAL"),
            dbc.CardBody([
                html.H5("Hunts de Recorde Necessárias", className="card-title"),
                html.P(f"~ {hunts_necessarias} dias", className="text-info h2"),
            ])
        ]), xs=12, md=6),
    ], className="mb-4 text-center")


def create_curves_row(fig_adherence, fig_delivery) -> dbc.Row:
    return dbc.Row([
        dbc.Col(dcc.Graph(figure=fig_adherence), xs=12, md=5),
        dbc.Col(dcc.Graph(figure=fig_delivery), xs=12, md=7),
    ], className="mb-4")