"""Core formula unit tests — verifies ZF-Score, Ψ_total, D_res, and decay predictions."""
import math
from app.core.zf_score import ZFScoreResult, min_max_scale, calculate_zf_score
from app.core.psi_total import calculate_psi_total
from app.core.drift import calculate_drift, calculate_vwap


class TestMinMaxScale:
    def test_within_range(self):
        assert min_max_scale(50, 0, 100) == 0.5

    def test_below_min_clamps(self):
        assert min_max_scale(-10, 0, 100) == 0.0

    def test_above_max_clamps(self):
        assert min_max_scale(200, 0, 100) == 1.0

    def test_zero_range(self):
        assert min_max_scale(5, 5, 5) == 0.0

    def test_nan_input(self):
        assert min_max_scale(float("nan"), 0, 100) == 0.0

    def test_inf_input(self):
        assert min_max_scale(float("inf"), 0, 100) == 0.0


class TestZfScore:
    def test_stable_asset(self):
        result = calculate_zf_score(
            d_res=0.5, oi_ratio=0.01, fr_divergence=0.1,
            liq_density=0.001, book_imbalance=0.1
        )
        assert isinstance(result, ZFScoreResult)
        assert 0.0 <= result.score <= 1.0
        assert result.status in ("normal", "perlu_perhatian", "kritis", "disintegrasi", "force_exit")

    def test_critical_asset(self):
        result = calculate_zf_score(
            d_res=50.0, oi_ratio=5.0, fr_divergence=10.0,
            liq_density=1.0, book_imbalance=10.0
        )
        assert result.score > 0.5

    def test_score_bounded(self):
        result = calculate_zf_score(
            d_res=99999, oi_ratio=99999, fr_divergence=99999,
            liq_density=99999, book_imbalance=99999
        )
        assert 0.0 <= result.score <= 1.0

    def test_heartbeat_mode_threshold(self):
        result = calculate_zf_score(
            d_res=0.1, oi_ratio=0.01, fr_divergence=0.01,
            liq_density=0.001, book_imbalance=0.01
        )
        assert result.mode == "heartbeat"


class TestDrift:
    def test_zero_pure_price(self):
        result = calculate_drift(100.0, 0.0)
        assert result == 0.0

    def test_no_drift(self):
        result = calculate_drift(100.0, 100.0)
        assert result == 0.0

    def test_positive_drift(self):
        # D_res = |110 - 100| / 100 * 100 = 10.0%
        result = calculate_drift(110.0, 100.0)
        assert abs(result - 10.0) < 0.01

    def test_negative_drift(self):
        # D_res = |90 - 100| / 100 * 100 = 10.0%
        result = calculate_drift(90.0, 100.0)
        assert abs(result - 10.0) < 0.01


class TestVwap:
    def test_basic_vwap(self):
        trades = [
            {"price": 100.0, "amount": 10.0},
            {"price": 200.0, "amount": 10.0},
        ]
        vwap = calculate_vwap(trades)
        assert abs(vwap - 150.0) < 0.01

    def test_empty_trades(self):
        vwap = calculate_vwap([])
        assert vwap == 0.0


class TestPsiTotal:
    def test_basic_calculation(self):
        result = calculate_psi_total(
            p_market=100.0,
            p_vwap=99.0,
            delta_oi=1000.0,
            vol_24h=100000.0,
            fr_curr=0.0001,
            fr_avg=0.0001,
            alpha=0.0
        )
        assert result >= 0.0
        assert not math.isnan(result)
        assert not math.isinf(result)

    def test_zero_volume(self):
        result = calculate_psi_total(
            p_market=100.0, p_vwap=99.0,
            delta_oi=1000.0, vol_24h=0.0,
            fr_curr=0.0001, fr_avg=0.0001, alpha=0.0
        )
        assert not math.isnan(result)
