# app.py
import os
import logging
from flask import jsonify

import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc

from data_loader import load_sheet_data
from metrics import calculate_all_metrics
from figures import (
    create_roadmap_figure,
    create_moving_avg_figure,
    create_heatmap_figure,
    create_weekday_bar_figure,
    create_eta_scenarios_figure,
    create_adherence_figure,
    create_delivery_curve_figure,
    # --- NOVOS GRÁFICOS ---
    create_progress_timeline,
    create_daily_efficiency,
    create_activity_calendar,
    create_performance_trend,
    create_xp_distribution
)
from layout import (
    create_top_indicators,
    create_advanced_metrics,
    create_milestone_list,
    create_health_effort_row,
    create_curves_row
)

# Configuração de logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("tibiatracker")

# Inicialização do app Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

# Health check para Render
@server.route("/health")
def health():
    return jsonify(status="ok")

# Layout base com intervalo de atualização
app.layout = dbc.Container([
    dcc.Interval(id="refresh-interval", interval=15 * 60 * 1000, n_intervals=0),  # 15 minutos
    html.Div(id="content")
], fluid=True)


@callback(Output("content", "children"), Input("refresh-interval", "n_intervals"))
def render_dashboard(_):
    try:
        # Carregar e processar dados
        df = load_sheet_data()
        metrics = calculate_all_metrics(df, level_target=1000)
        enriched_df = metrics["df_enriched"]

        # === Layout: Indicadores ===
        top_row = create_top_indicators(
            level_real=metrics["level_real"],
            eta_str=metrics["eta_str"],
            streak_count=metrics["streak_count"],
            melhor_dia_xp=metrics["melhor_dia_xp"],
            melhor_dia_data=metrics["melhor_dia_data"],
            tendencia_status=metrics["tendencia_status"],
            cor_tendencia=metrics["cor_tendencia"]
        )

        metrics_row = create_advanced_metrics(
            desvio_padrao=metrics["desvio_padrao"],
            media_recente=metrics["media_recente"],
            score_consistencia=metrics["score_consistencia"],
            streak_baixo_texto=metrics["streak_baixo_texto"],
            cor_streak_baixo=metrics["cor_streak_baixo"]
        )

        # === Gráficos principais ===
        fig_roadmap = create_roadmap_figure(metrics["level_real"])
        fig_moving = create_moving_avg_figure(enriched_df)
        fig_heatmap = create_heatmap_figure(enriched_df)
        fig_weekday = create_weekday_bar_figure(enriched_df)
        fig_eta = create_eta_scenarios_figure(
            metrics["xp_faltante"],
            metrics["media_geral"],
            metrics["media_recente"],
            metrics["melhor_dia_xp"]
        )
        fig_adherence = create_adherence_figure(enriched_df, metrics["xp_meta_diaria"])
        fig_delivery = create_delivery_curve_figure(enriched_df)

        # === NOVOS GRÁFICOS PROFISSIONAIS ===
        fig_timeline = create_progress_timeline(enriched_df)
        fig_efficiency = create_daily_efficiency(enriched_df, metrics["xp_meta_diaria"])
        fig_calendar = create_activity_calendar(enriched_df)
        fig_trend = create_performance_trend(enriched_df)
        fig_distribution = create_xp_distribution(enriched_df)

        # === Componentes compostos ===
        milestone_list = create_milestone_list(metrics["historico_milestones"])
        health_effort_row = create_health_effort_row(
            metrics["texto_delta"],
            metrics["cor_delta"],
            metrics["xp_faltante"],
            metrics["melhor_dia_xp"]
        )
        curves_row = create_curves_row(fig_adherence, fig_delivery)

        # === Montagem final do layout ===
        return dbc.Container([
            html.H1("PROJETO ELDER DRUID 1000", className="text-center my-4 text-warning"),

            # Indicadores principais
            top_row,
            metrics_row,

            # Roadmap + Progresso com Marcos
            dbc.Row([
                dbc.Col(dbc.Card([dbc.CardHeader("ROADMAP DE PROGRESSO"), dbc.CardBody(dcc.Graph(figure=fig_roadmap, config={'displayModeBar': False}))]))],
            className="mb-4"),

            dbc.Row([
                dbc.Col(dbc.Card([dbc.CardHeader("Intensidade de Hunts (Heatmap Semanal)"), dbc.CardBody(dcc.Graph(figure=fig_heatmap))])),
            ], className="mb-4"),

            # XP Diário + Eficiência
            dbc.Row([
                dbc.Col(dbc.Card([dbc.CardHeader("XP DIÁRIO + MÉDIAS MÓVEIS"), dbc.CardBody(dcc.Graph(figure=fig_moving))]), width=12, md=7),
                dbc.Col(dbc.Card([dbc.CardHeader("Eficiência Diária (% da Meta)"), dbc.CardBody(dcc.Graph(figure=fig_efficiency))]), width=12, md=5),
            ], className="mb-4"),

            # Calendário + Distribuição
            dbc.Row([
                # dbc.Col(dbc.Card([dbc.CardHeader("Calendário de Atividade"), dbc.CardBody(dcc.Graph(figure=fig_calendar))]), width=12, md=7),
                dbc.Col(dbc.Card([dbc.CardHeader("Distribuição de XP Diária"), dbc.CardBody(dcc.Graph(figure=fig_distribution))]), width=12, md=12),
            ], className="mb-4"),

            # Tendência + Heatmap
            dbc.Row([
                dbc.Col(dbc.Card([dbc.CardHeader("Tendência de Desempenho"), dbc.CardBody(dcc.Graph(figure=fig_trend))]), width=12, md=6),
                dbc.Col(dbc.Card([dbc.CardHeader("Progresso com Marcos-Chave"), dbc.CardBody(dcc.Graph(figure=fig_timeline))]), width=12, md=6),
            ], className="mb-4"),

            # Curvas + Dia da Semana
            curves_row,
            dbc.Card([dbc.CardHeader("Média XP por Dia da Semana"), dbc.CardBody(dcc.Graph(figure=fig_weekday))], className="mb-4"),

            # Cenários ETA + Saúde/Esfôrço
            dbc.Row(
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader("ANÁLISE DE CENÁRIOS (ETA)"),
                        dbc.CardBody(dcc.Graph(figure=fig_eta))
                    ]),
                    width=12
                ),
                className="mb-4"
            ),
            health_effort_row,

            # Histórico de Marcos
            dbc.Card([dbc.CardHeader("HISTÓRICO DE MARCOS ATINGIDOS"), dbc.CardBody(milestone_list)], className="mb-4")
        ], fluid=True)

    except Exception as e:
        logger.exception("Erro ao renderizar o dashboard")
        return dbc.Container([
            dbc.Alert(f"⚠️ Erro ao carregar os dados: {str(e)}", color="danger", className="mt-5 text-center")
        ], fluid=True)


# Execução local
if __name__ == "__main__":
    app.run(debug=True)