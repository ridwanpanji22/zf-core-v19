import math
from dataclasses import dataclass

@dataclass
class ZFScoreResult:
    score: float
    status: str
    mode: str

def min_max_scale(val: float, min_val: float, max_val: float) -> float:
    if math.isnan(val) or math.isinf(val):
        return 0.0
    if max_val - min_val <= 0:
        return 0.0
    scaled = (val - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, scaled))

def calculate_zf_score(
    d_res: float,
    oi_ratio: float,
    fr_divergence: float,
    liq_density: float,
    book_imbalance: float,
    historicals: dict = None
) -> ZFScoreResult:
    """Calculate ZF-Score (0-1) representing asset fragility.

    Input components are scaled against 30-day min-max historicals.
    If historicals are not provided, default bounds are assumed.
    """
    if not historicals:
        # Default fallback bounds
        historicals = {
            "d_res": (0.0, 10.0),
            "oi_ratio": (0.0, 1.0),
            "fr_divergence": (0.0, 5.0),
            "liq_density": (0.0, 0.1),
            "book_imbalance": (0.0, 5.0)
        }

    # Normalize inputs
    s_drift = min_max_scale(d_res, *historicals["d_res"])
    s_oi = min_max_scale(oi_ratio, *historicals["oi_ratio"])
    s_fr = min_max_scale(fr_divergence, *historicals["fr_divergence"])
    s_liq = min_max_scale(liq_density, *historicals["liq_density"])
    s_book = min_max_scale(book_imbalance, *historicals["book_imbalance"])

    # Component weights
    w_drift = 0.30
    w_oi = 0.25
    w_fr = 0.20
    w_liq = 0.15
    w_book = 0.10

    score = (
        (s_drift * w_drift) +
        (s_oi * w_oi) +
        (s_fr * w_fr) +
        (s_liq * w_liq) +
        (s_book * w_book)
    )
    score = round(max(0.0, min(1.0, score)), 4)

    # Classify
    if score < 0.60:
        status = "normal"
        mode = "heartbeat"
    elif score < 0.80:
        status = "perlu_perhatian"
        mode = "deep_analysis"
    elif score < 0.85:
        status = "kritis"
        mode = "deep_analysis"
    elif score < 0.99:
        status = "disintegrasi"
        mode = "deep_analysis"
    else:
        status = "force_exit"
        mode = "deep_analysis"

    return ZFScoreResult(score=score, status=status, mode=mode)
