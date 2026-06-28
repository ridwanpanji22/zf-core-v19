import numpy as np

def predict_decay(zf_scores_30d: list[float], psi_totals_30d: list[float]) -> float:
    """Predict price decay direction (Decay_t) over next 10 days.

    Calculates slope of regression line over past 30 days of metrics
    and projects the decay scale.
    """
    if not zf_scores_30d or not psi_totals_30d:
        return 0.0

    length = min(len(zf_scores_30d), len(psi_totals_30d))
    if length < 5: # Not enough datapoints
        return 0.0

    y1 = np.array(zf_scores_30d[-length:])
    y2 = np.array(psi_totals_30d[-length:])

    # Multi-dimensional composite value to regress
    y = (y1 * 0.6) + (y2 * 0.4)
    x = np.arange(length)

    # Perform linear fit
    slope, intercept = np.polyfit(x, y, 1)

    # Proportional projection: positive slope implies fragility decay (downwards price movement)
    # negative slope implies stabilizing (potential recovery/growth)
    projected_change = -slope * 10.0 # 10 days extrapolation
    return round(projected_change, 2)
