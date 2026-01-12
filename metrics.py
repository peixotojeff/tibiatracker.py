# metrics.py
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Any

from xp_calculator import cumulative_exp_closed


def calculate_all_metrics(df: pd.DataFrame, level_target: int = 1000) -> Dict[str, Any]:
    """
    Calcula todas as métricas do dashboard a partir do DataFrame de XP.
    Retorna um dicionário com todos os valores necessários para layout e gráficos.
    """
    if df.empty:
        raise ValueError("DataFrame vazio")

    # XP consolidada e nível real
    xp_consolidada = df["Experience"].iloc[-1]
    level_real = find_level_for_exp_safe(int(xp_consolidada))
    xp_objetivo = cumulative_exp_closed(level_target)
    xp_faltante = max(0, xp_objetivo - xp_consolidada)

    # Médias
    positive_hunts = df[df["daily_exp"] > 0]["daily_exp"]
    media_geral = float(positive_hunts.mean()) if not positive_hunts.empty else 0.0
    recent_df = df.tail(30)
    media_recente = float(
        recent_df[recent_df["daily_exp"] > 0]["daily_exp"].mean()
    ) if not recent_df[recent_df["daily_exp"] > 0].empty else media_geral

    # ETA e meta diária
    eta_str, xp_meta_diaria, dias_restantes = "N/A", 0.0, 0
    if media_recente > 0:
        dias_restantes = max(1, int(xp_faltante / media_recente))
        eta_date = datetime.now() + timedelta(days=min(dias_restantes, 18250))
        eta_str = eta_date.strftime("%d/%m/%Y")
        xp_meta_diaria = xp_faltante / dias_restantes

    # Streak (dias consecutivos acima da meta)
    streak_count = 0
    if xp_meta_diaria > 0:
        for val in reversed(df["daily_exp"]):
            if val >= xp_meta_diaria:
                streak_count += 1
            else:
                break

    # Melhor dia
    idx_max = df["daily_exp"].idxmax()
    melhor_dia_xp = float(df.loc[idx_max, "daily_exp"])
    melhor_dia_data = df.loc[idx_max, "create_at"].strftime("%d/%m/%Y")

    # Tendência (comparação média recente vs geral)
    tendencia_status, cor_tendencia = "ESTÁVEL", "info"
    if media_recente > media_geral * 1.05:
        tendencia_status, cor_tendencia = "↑", "success"
    elif media_recente < media_geral * 0.95:
        tendencia_status, cor_tendencia = "↓", "danger"

    # Consistência (% de dias acima da média recente)
    score_consistencia = (
        len(positive_hunts[positive_hunts >= media_recente]) / len(positive_hunts) * 100
        if len(positive_hunts) > 0 else 0.0
    )

    # Desvio padrão
    desvio_padrao = float(positive_hunts.std()) if len(positive_hunts) > 1 else 0.0

    # Streak baixo (dias consecutivos com XP < 10% da meta)
    current_streak_baixo = 0
    if xp_meta_diaria > 0:
        for val in reversed(df["daily_exp"]):
            if val < (xp_meta_diaria * 0.1):
                current_streak_baixo += 1
            else:
                break
    cor_streak_baixo = "danger" if current_streak_baixo > 3 else "success"
    streak_baixo_texto = f"{current_streak_baixo}d" if current_streak_baixo > 0 else "OK"

    # Performance hoje
    xp_hoje = df["daily_exp"].iloc[-1]
    delta_meta = xp_hoje - xp_meta_diaria
    cor_delta = "success" if delta_meta >= 0 else "danger"
    texto_delta = f"{'+' if delta_meta > 0 else ''}{delta_meta / 1e6:.1f}M vs Meta"

    # Histórico de milestones
    historico_milestones = []
    for m in [200, 400, 600, 800, 900, 1000]:
        xp_m = cumulative_exp_closed(m)
        alcancado = df[df["Experience"] >= xp_m]
        if not alcancado.empty:
            data_m = alcancado.iloc[0]["create_at"].strftime("%d/%m/%Y")
            historico_milestones.append((m, data_m, True))
        else:
            historico_milestones.append((m, None, False))

    return {
        # Níveis e XP
        "level_real": level_real,
        "xp_consolidada": xp_consolidada,
        "xp_faltante": xp_faltante,
        "xp_objetivo": xp_objetivo,

        # Médias e ETA
        "media_geral": media_geral,
        "media_recente": media_recente,
        "xp_meta_diaria": xp_meta_diaria,
        "eta_str": eta_str,
        "dias_restantes": dias_restantes,

        # Streaks
        "streak_count": streak_count,
        "current_streak_baixo": current_streak_baixo,
        "streak_baixo_texto": streak_baixo_texto,
        "cor_streak_baixo": cor_streak_baixo,

        # Melhor dia
        "melhor_dia_xp": melhor_dia_xp,
        "melhor_dia_data": melhor_dia_data,

        # Tendência
        "tendencia_status": tendencia_status,
        "cor_tendencia": cor_tendencia,

        # Métricas estatísticas
        "desvio_padrao": desvio_padrao,
        "score_consistencia": score_consistencia,

        # Performance diária
        "texto_delta": texto_delta,
        "cor_delta": cor_delta,

        # Milestones
        "historico_milestones": historico_milestones,

        # DataFrame enriquecido (para gráficos)
        "df_enriched": _add_derived_columns(df, xp_meta_diaria, xp_consolidada)
    }


def _add_derived_columns(df: pd.DataFrame, xp_meta_diaria: float, xp_initial: float) -> pd.DataFrame:
    """Adiciona colunas derivadas ao DataFrame para uso em gráficos."""
    df = df.copy()
    df["MM7"] = df["daily_exp"].rolling(window=7, min_periods=1).mean()
    df["MM30"] = df["daily_exp"].rolling(window=30, min_periods=1).mean()
    df["Meta_SLA"] = xp_meta_diaria
    df["Exp_Projetada"] = xp_initial + (df.reset_index().index * xp_meta_diaria)
    return df


def find_level_for_exp_safe(total_exp: int) -> int:
    """Wrapper seguro para evitar falhas na busca binária."""
    try:
        from xp_calculator import find_level_for_exp
        return find_level_for_exp(total_exp)
    except Exception:
        return 1