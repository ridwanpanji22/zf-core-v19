def calculate_drift(p_market: float, p_pure: float) -> float:
    """Calculate Topological Drift (D_res) representation deviation.

    Formula:
    D_res = |P_market - P_pure| / P_pure * 100
    """
    if p_pure <= 0:
        return 0.0
    return round((abs(p_market - p_pure) / p_pure) * 100.0, 2)

def calculate_vwap(trades: list[dict]) -> float:
    """Calculate Volume Weighted Average Price (VWAP) as P_pure proxy.

    trades: list of dict with 'price' (str/float) and 'size' (str/float)
    """
    total_value = 0.0
    total_volume = 0.0
    for trade in trades:
        try:
            p = float(trade.get("price", 0))
            v = float(trade.get("size", 0))
            total_value += p * v
            total_volume += v
        except (ValueError, TypeError):
            continue
    if total_volume <= 0:
        return 0.0
    return total_value / total_volume
