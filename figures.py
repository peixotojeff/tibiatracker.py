# figures.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from xp_calculator import cumulative_exp_closed

def create_roadmap_figure(level_real: int, level_target: int = 1000) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[level_target], y=["Progresso"], orientation='h', marker_color="#333", showlegend=False))
    fig.add_trace(go.Bar(x=[level_real], y=["Progresso"], orientation='h', marker_color="#E6BC53", name="Atual"))
    for m in [200, 400, 600, 800, 900, 1000]:
        fig.add_vline(x=m, line_dash="dash", line_color="white")
    fig.update_layout(
        showlegend=False, barmode='overlay', height=80,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(range=[0, 1000]), yaxis=dict(showticklabels=False),
        font_color="white"
    )
    return fig


def create_moving_avg_figure(df: pd.DataFrame) -> go.Figure:
    df = df.copy()
    df["MM7"] = df["daily_exp"].rolling(window=7, min_periods=1).mean()
    df["MM30"] = df["daily_exp"].rolling(window=30, min_periods=1).mean()

    fig = go.Figure([
        go.Scatter(x=df["create_at"], y=df["daily_exp"]/1e6, mode='lines+markers', name="Diário", line=dict(color='#17a2b8')),
        go.Scatter(x=df["create_at"], y=df["MM7"]/1e6, name="MM 7 dias", line=dict(color='#ffc107', width=3)),
        go.Scatter(x=df["create_at"], y=df["MM30"]/1e6, name="MM 30 dias", line=dict(color='#dc3545', width=3))
    ])
    fig.update_layout(
        title="XP Diário + Médias Móveis",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Data", yaxis_title="XP (milhões)",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)")
    )
    return fig


def create_heatmap_figure(df: pd.DataFrame) -> go.Figure:
    df_heat = df.copy()
    df_heat['Semana'] = "S" + df_heat['create_at'].dt.strftime('%V')
    df_heat['Dia'] = df_heat['create_at'].dt.day_name().map({
        'Monday': 'Seg', 'Tuesday': 'Ter', 'Wednesday': 'Qua',
        'Thursday': 'Qui', 'Friday': 'Sex', 'Saturday': 'Sab', 'Sunday': 'Dom'
    })
    pivot = df_heat.pivot_table(
        index='Dia', columns='Semana', values='daily_exp',
        aggfunc='sum', fill_value=0
    ).reindex(['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'])

    fig = px.imshow(pivot / 1e6, color_continuous_scale='blues')
    fig.update_layout(
        template='plotly_dark', paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False
    )
    return fig


def create_weekday_bar_figure(df: pd.DataFrame) -> go.Figure:
    df_heat = df.copy()
    df_heat['Dia'] = df_heat['create_at'].dt.day_name().map({
        'Monday': 'Seg', 'Tuesday': 'Ter', 'Wednesday': 'Qua',
        'Thursday': 'Qui', 'Friday': 'Sex', 'Saturday': 'Sab', 'Sunday': 'Dom'
    })
    media_dia_semana = df_heat.groupby('Dia')['daily_exp'].mean().reindex(
        ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
    ).fillna(0) / 1e6

    fig = px.bar(
        x=media_dia_semana.values, y=media_dia_semana.index, orientation='h',
        color=media_dia_semana.values, color_continuous_scale='blues'
    )
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        yaxis_autorange="reversed", coloraxis_showscale=False, showlegend=False,
        xaxis_title="Média (M)"
    )
    return fig


def create_eta_scenarios_figure(xp_faltante: float, media_geral: float, media_recente: float, melhor_dia_xp: float) -> go.Figure:
    cenarios = {
        "Média Geral": media_geral,
        "Média Recente (30d)": media_recente,
        "Ritmo Recorde": melhor_dia_xp
    }
    nomes, datas, dias_list = [], [], []
    for nome, media in cenarios.items():
        if media > 0:
            dias = max(1, int(xp_faltante / media))
            dias_lim = min(dias, 3650)
            data_str = (datetime.now() + timedelta(days=dias_lim)).strftime("%d/%m/%Y")
            nomes.append(nome)
            datas.append(data_str)
            dias_list.append(dias_lim)

    fig = go.Figure(go.Bar(
        x=dias_list, y=nomes, orientation='h',
        text=[f"{d} dias ({dt})" for d, dt in zip(dias_list, datas)],
        marker_color=["#e1edf7", "#0b2d69", '#a7cde2']
    ))
    fig.update_traces(textposition='auto')
    fig.update_layout(
        title="Previsão de Conclusão por Cenário",
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Dias Restantes", yaxis=dict(autorange="reversed")
    )
    return fig


def create_adherence_figure(df: pd.DataFrame, xp_meta_diaria: float) -> go.Figure:
    """Gráfico de aderência à meta diária."""
    fig = go.Figure([
        go.Scatter(
            x=df['create_at'],
            y=df['daily_exp'] / 1e6,
            name="Real",
            line=dict(color='#17a2b8')
        ),
        go.Scatter(
            x=df['create_at'],
            y=[xp_meta_diaria / 1e6] * len(df),
            name="Meta Requerida",
            line=dict(dash='dash', color='white')
        )
    ])
    fig.update_layout(
        title="Aderência à Meta Diária",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis_title="XP (M)",
        legend=dict(bgcolor="rgba(0,0,0,0.5)")
    )
    return fig


def create_delivery_curve_figure(df: pd.DataFrame) -> go.Figure:
    """Gráfico de curva de entrega vs plano projetado."""
    fig = go.Figure([
        go.Scatter(
            x=df['create_at'],
            y=df['Experience'] / 1e9,
            name="Acumulado Real",
            fill='tozeroy',
            line=dict(color='#007bff')
        ),
        go.Scatter(
            x=df['create_at'],
            y=df['Exp_Projetada'] / 1e9,
            name="Linha de Meta",
            line=dict(color='orange', dash='dot')
        )
    ])
    fig.update_layout(
        title="Curva de Entrega vs Plano",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis_title="XP Acumulado (B)",
        legend=dict(bgcolor="rgba(0,0,0,0.5)")
    )
    return fig