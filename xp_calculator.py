# xp_calculator.py
def cumulative_exp_closed(level: int) -> int:
    """Calcula XP acumulada até um nível usando fórmula fechada."""
    if level <= 1:
        return 0
    m = level - 1
    sum_k2 = m * (m + 1) * (2 * m + 1) // 6
    sum_k = m * (m + 1) // 2
    return 50 * sum_k2 - 150 * sum_k + 200 * m


def find_level_for_exp(total_exp: int) -> int:
    """Encontra o nível atual com base na XP total."""
    low, high = 1, 2500
    while low < high:
        mid = (low + high + 1) // 2
        if cumulative_exp_closed(mid) <= total_exp:
            low = mid
        else:
            high = mid - 1
    return low