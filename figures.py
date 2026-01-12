# figures.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from scipy import stats
from xp_calculator import cumulative_exp_closed
from datetime import datetime, timedelta


def create_roadmap_figure(level_real: int, level_target: int = 1000) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[level_target], y=["Progresso"], orientation='h', marker_color="#333", showlegend=False))
    fig.add_trace(go.Bar(x=[level_real], y=["Progresso"], orientation='h', marker_color="#E6BC53", name="Atual"))
    for m in [200, 400, 600, 800, 900, 1000]:
        fig.add_vline(x=m, line_dash="dash", line_color="white")
    fig.update_layout(
        showlegend=False, barmode='overlay', height=80,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(range=[0, 1000]),
        yaxis=dict(showticklabels=False),
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
        legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(0,0,0,0.5)" # Fundo semi-transparente para não cobrir as linhas
            )
    )
    return fig


def create_delivery_curve_figure(df: pd.DataFrame) -> go.Figure:
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
        legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(0,0,0,0.5)" # Fundo semi-transparente para não cobrir as linhas
            )
    )
    return fig


# === GRÁFICOS PROFISSIONAIS ADICIONAIS ===

def create_progress_timeline(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['create_at'],
        y=df['Experience'] / 1e9,
        mode='lines+markers',
        name='XP Acumulada',
        line=dict(color='#E6BC53', width=3),
        marker=dict(size=4)
    ))

    milestones = [200, 400, 600, 800, 900, 1000]
    for level in milestones:
        xp_target = cumulative_exp_closed(level)
        reached = df[df['Experience'] >= xp_target]
        if not reached.empty:
            row = reached.iloc[0]
            fig.add_annotation(
                x=row['create_at'],
                y=xp_target / 1e9,
                text=f"L{level}",
                showarrow=True,
                arrowhead=2,
                ax=0, ay=-20,
                font=dict(color="white", size=10),
                bgcolor="rgba(0,0,0,0.6)",
                bordercolor="#E6BC53"
            )

    fig.update_layout(
        title="Progresso Acumulado com Marcos-Chave",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Data",
        yaxis_title="XP Total (Bilhões)",
        hovermode="x unified"
    )
    return fig


def create_daily_efficiency(df: pd.DataFrame, xp_meta_diaria: float) -> go.Figure:
    if xp_meta_diaria <= 0:
        return go.Figure()

    df_eff = df.copy()
    df_eff['efficiency'] = (df_eff['daily_exp'] / xp_meta_diaria) * 100
    df_eff['color'] = df_eff['efficiency'].apply(lambda x: 'red' if x < 50 else 'orange' if x < 100 else 'green')

    fig = go.Figure(go.Bar(
        x=df_eff['create_at'],
        y=df_eff['efficiency'],
        marker_color=df_eff['color'],
        customdata=df_eff['daily_exp'] / 1e6,
        hovertemplate="Data: %{x}<br>Eficiência: %{y:.1f}%<br>XP: %{custom.1f}M<extra></extra>"
    ))

    fig.add_hline(y=100, line_dash="dash", line_color="white", annotation_text="Meta")
    fig.add_hline(y=50, line_dash="dot", line_color="red", annotation_text="Risco")

    fig.update_layout(
        title="Eficiência Diária (% da Meta)",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Data",
        yaxis_title="% da Meta Diária",
        showlegend=False
    )
    return fig


def create_activity_calendar(df: pd.DataFrame) -> go.Figure:
    df_cal = df[['create_at', 'daily_exp']].copy()
    df_cal['date'] = df_cal['create_at'].dt.date
    df_cal = df_cal.groupby('date')['daily_exp'].sum().reset_index()
    df_cal['xp_m'] = df_cal['daily_exp'] / 1e6

    start = df_cal['date'].min()
    end = df_cal['date'].max()
    date_range = pd.date_range(start=start, end=end, freq='D')
    calendar_df = pd.DataFrame({'date': date_range})
    calendar_df['date'] = calendar_df['date'].dt.date
    calendar_df = calendar_df.merge(df_cal[['date', 'xp_m']], on='date', how='left')
    calendar_df['xp_m'] = calendar_df['xp_m'].fillna(0)

    calendar_df['week'] = pd.to_datetime(calendar_df['date']).dt.isocalendar().week
    calendar_df['weekday'] = pd.to_datetime(calendar_df['date']).dt.weekday

    pivot = calendar_df.pivot(index='weekday', columns='week', values='xp_m')
    pivot = pivot.reindex(index=[0, 1, 2, 3, 4, 5, 6])

    fig = px.imshow(
        pivot,
        labels=dict(x="Semana", y="Dia da Semana", color="XP (M)"),
        color_continuous_scale='greens',
        aspect="auto"
    )
    fig.update_yaxes(tickvals=[0,1,2,3,4,5,6], ticktext=["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"])
    fig.update_layout(
        title="Calendário de Atividade (XP Diária em Milhões)",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(0,0,0,0.5)" # Fundo semi-transparente para não cobrir as linhas
            )
    )
    return fig


def create_performance_trend(df: pd.DataFrame) -> go.Figure:
    df_trend = df[['create_at', 'daily_exp']].copy()
    df_trend['days_since_start'] = (df_trend['create_at'] - df_trend['create_at'].min()).dt.days
    df_trend = df_trend[df_trend['daily_exp'] > 0]

    if len(df_trend) < 2:
        return go.Figure()

    slope, intercept, r_value, p_value, std_err = stats.linregress(
        df_trend['days_since_start'], df_trend['daily_exp']
    )

    df_trend['trend'] = intercept + slope * df_trend['days_since_start']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_trend['create_at'],
        y=df_trend['daily_exp'] / 1e6,
        mode='markers',
        name='XP Diário',
        marker=dict(color='#17a2b8', size=4)
    ))
    fig.add_trace(go.Scatter(
        x=df_trend['create_at'],
        y=df_trend['trend'] / 1e6,
        mode='lines',
        name=f'Tendência (R²={r_value**2:.2f})',
        line=dict(color='orange', width=2)
    ))

    fig.update_layout(
        title="Tendência de Desempenho (Regressão Linear)",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Data",
        yaxis_title="XP Diário (M)",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    return fig


def create_xp_distribution(df: pd.DataFrame) -> go.Figure:
    daily_xp = df[df['daily_exp'] > 0]['daily_exp'] / 1e6

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=daily_xp,
        nbinsx=30,
        name='Frequência',
        marker_color='rgba(230, 188, 83, 0.6)',
        opacity=0.75
    ))
    fig.add_trace(go.Box(
        y=daily_xp,
        name='Distribuição',
        boxpoints='outliers',
        jitter=0.3,
        marker_color='#dc3545',
        showlegend=False
    ))

    fig.update_layout(
        title="Distribuição de XP Diária (Milhões)",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis_title="XP por Dia (M)",
        yaxis_title="Frequência / Distribuição",
        barmode='overlay'
    )
    return fig