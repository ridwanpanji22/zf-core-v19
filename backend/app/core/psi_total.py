def calculate_psi_total(
    p_market: float,
    p_vwap: float,
    delta_oi: float,
    vol_24h: float,
    fr_curr: float,
    fr_avg: float,
    alpha: float,
    omega: dict = None
) -> float:
    """Calculate integrated structural tension index (Ψ_total).

    Formula:
    Ψ_total = |P_market - P_vwap| + ω1*(ΔOI/Vol_24h) + ω2*(FR_curr/FR_avg) + ω3*(α)
    """
    if not omega:
        omega = {"w1": 0.35, "w2": 0.40, "w3": 0.25}

    drift = abs(p_market - p_vwap)

    # Prevent ZeroDivisionError
    leverage_tension = (delta_oi / vol_24h) if vol_24h > 0 else 0.0
    sentiment_tension = (fr_curr / fr_avg) if fr_avg != 0 else 0.0

    w1 = omega.get("w1", 0.35)
    w2 = omega.get("w2", 0.40)
    w3 = omega.get("w3", 0.25)

    psi = drift + (w1 * leverage_tension) + (w2 * sentiment_tension) + (w3 * alpha)
    return round(psi, 4)
