"""🔒 TD-0255 (`DR-TRIEN-KHAI-01`) — E1 chạy được suất calibration B1 (`DR-D5-01`).

Ba thứ được khoá:
1. **Sổ và lượt chạy là MỘT cấu hình** (bài học `MT-23`). Với B1 phần phủ SUY từ `--param-under-test`/
   `--param-value`; `--ghi-de` bị từ chối. Kiểm qua `dung_moi_truong()` THẬT: giá trị đã khai chính là giá trị
   đọc ra từ cấu hình phủ (đường đọc `tier_b` → chiến lược đã khoá riêng ở TD-0195).
2. **Arm của D5 là `Z0-T1`** lấy từ bảng ứng viên của DR, không phải `"Z3"` đang nằm trong YAML.
3. **Bảng R theo từng lệnh** — đầu vào của `chon_gia_tri` (TD-0254): ghi → đọc lại đúng, trùng khoá thì từ chối.
"""

from __future__ import annotations

import ast
import json
import sys
from argparse import Namespace
from datetime import datetime
from pathlib import Path

import pytest

from tool_d.bo_chay.moi_truong import dung_moi_truong
from tool_d.bo_chay.yeu_cau import BoChayError
from tool_d.calibration.bang_r import BangRError, doc_bang_r, ghi_bang_r
from tool_d.calibration.ghi_de_b1 import KHOA_ARM, ghi_de_cho_b1
from tool_d.calibration.ung_vien import PARAM_MOC, PARAM_XAC_NHAN, UngVienError, doc_bang_ung_vien
from tool_d.config.loader import resolve
from tool_d.wfo.lenh import LenhWFO

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))
import run_backtest  # noqa: E402

BANG = doc_bang_ung_vien(REPO_ROOT / "docs/decisions/DR-D5-01-pham-vi-ung-vien-luat-chon-calibration.md")


class TestGhiDeSuyTuSo:
    def test_moc_chi_co_arm_cua_DR(self) -> None:
        assert ghi_de_cho_b1(PARAM_MOC, None, BANG) == {KHOA_ARM: "Z0-T1"}

    def test_moc_mang_gia_tri_bi_tu_choi(self) -> None:
        with pytest.raises(UngVienError):
            ghi_de_cho_b1(PARAM_MOC, 0.4, BANG)

    @pytest.mark.parametrize("ten", sorted(BANG.tham_so))
    def test_moi_tham_so_calibrate_vao_dung_tier_b(self, ten: str) -> None:
        v = BANG.tham_so[ten].thu[0]
        assert ghi_de_cho_b1(ten, v, BANG) == {KHOA_ARM: "Z0-T1", f"tier_b.{ten}": v}

    def test_xac_nhan_ghep_nhieu_khoa(self) -> None:
        gd = ghi_de_cho_b1(PARAM_XAC_NHAN, {"zss_threshold": 0.4, "buf_sl_atr": 0.5}, BANG)
        assert gd == {KHOA_ARM: "Z0-T1", "tier_b.zss_threshold": 0.4, "tier_b.buf_sl_atr": 0.5}

    def test_tham_so_FROZEN_ngoai_DR_bi_tu_choi(self) -> None:
        with pytest.raises(UngVienError):
            ghi_de_cho_b1("dg4_bars_1h", 6, BANG)  # FROZEN theo DR-D5-01 §2.2

    @pytest.mark.parametrize("ten", sorted(BANG.tham_so))
    def test_gia_tri_khai_la_gia_tri_cau_hinh_phu_doc_ra(self, ten: str, tmp_path) -> None:
        """Đường THẬT: phần phủ → `dung_moi_truong()` → YAML phủ → `resolve()`."""
        v = BANG.tham_so[ten].thu[-1]
        mt = dung_moi_truong(
            repo_dir=REPO_ROOT, goc=tmp_path, ghi_de=ghi_de_cho_b1(ten, v, BANG), ma_trong_ro=("BTCUSDT",)
        )
        assert resolve(mt.cfg_phu, f"tier_b.{ten}") == v
        assert resolve(mt.cfg_phu, KHOA_ARM) == "Z0-T1"


def _args(**kw) -> Namespace:
    goc = dict(budget_line="B1", ghi_de=[], param_under_test=None, param_value=None)
    goc.update(kw)
    return Namespace(**goc)


class TestE1TuChoiLoiKhaiTachRoi:
    def test_B1_co_ghi_de_bi_tu_choi(self) -> None:
        with pytest.raises(BoChayError, match="--ghi-de"):
            run_backtest._ghi_de_cua_luot(
                _args(param_under_test="zss_threshold", param_value="0.4", ghi_de=["tier_b.zss_threshold=0.6"])
            )

    def test_B1_suy_tu_param(self) -> None:
        gd = run_backtest._ghi_de_cua_luot(_args(param_under_test="zss_threshold", param_value="0.4"))
        assert gd == {KHOA_ARM: "Z0-T1", "tier_b.zss_threshold": 0.4}

    def test_B1_moc_param_value_null(self) -> None:
        assert run_backtest._ghi_de_cua_luot(_args(param_under_test=PARAM_MOC, param_value="null")) == {
            KHOA_ARM: "Z0-T1"
        }

    def test_B1_thieu_param_under_test_bi_tu_choi(self) -> None:
        with pytest.raises(BoChayError, match="param-under-test"):
            run_backtest._ghi_de_cua_luot(_args())

    def test_dong_khac_B1_giu_ghi_de_nhu_cu(self) -> None:
        gd = run_backtest._ghi_de_cua_luot(_args(budget_line="B3", ghi_de=["tier_c.arm_ablation.arm=Z0"]))
        assert gd == {KHOA_ARM: "Z0"}


class TestBangR:
    @staticmethod
    def _lenh(pair: str, gio: int, pnl: float) -> LenhWFO:
        return LenhWFO(
            pair=pair, open_date=datetime(2024, 5, 1, gio), close_date=datetime(2024, 5, 2, gio),
            pnl_abs=pnl, rui_ro_da_trien_khai_usdt=2.0, planned_risk_usdt=2.5,
        )

    def test_ghi_doc_lai_dung_hai_thuoc(self, tmp_path) -> None:
        lenhs = [self._lenh("B/USDT:USDT", 3, 1.0), self._lenh("A/USDT:USDT", 1, -2.0)]
        duong = ghi_bang_r(tmp_path, lenhs, trial_id="D-9999")
        assert doc_bang_r(duong) == {
            ("A/USDT:USDT", datetime(2024, 5, 1, 1)): -1.0,
            ("B/USDT:USDT", datetime(2024, 5, 1, 3)): 0.5,
        }
        assert doc_bang_r(duong, thuoc="r_realized")[("A/USDT:USDT", datetime(2024, 5, 1, 1))] == -0.8

    def test_trung_khoa_bi_tu_choi(self, tmp_path) -> None:
        duong = ghi_bang_r(tmp_path, [self._lenh("A/USDT:USDT", 1, 1.0)] * 2, trial_id="D-9999")
        with pytest.raises(BangRError, match="trùng"):
            doc_bang_r(duong)

    def test_so_lenh_lech_bi_tu_choi(self, tmp_path) -> None:
        duong = ghi_bang_r(tmp_path, [self._lenh("A/USDT:USDT", 1, 1.0)], trial_id="D-9999")
        d = json.loads(duong.read_text(encoding="utf-8"))
        d["so_lenh"] = 5
        duong.write_text(json.dumps(d), encoding="utf-8")
        with pytest.raises(BangRError):
            doc_bang_r(duong)

    def test_thuoc_la_bi_tu_choi(self, tmp_path) -> None:
        duong = ghi_bang_r(tmp_path, [self._lenh("A/USDT:USDT", 1, 1.0)], trial_id="D-9999")
        with pytest.raises(BangRError):
            doc_bang_r(duong, thuoc="profit_ratio_khong_ton_tai")


class TestThuTuTrongMain:
    def test_bang_r_ghi_SAU_seal_va_TRUOC_consume(self) -> None:
        nguon = (REPO_ROOT / "entrypoints/run_backtest.py").read_text(encoding="utf-8")
        main = next(n for n in ast.parse(nguon).body if isinstance(n, ast.FunctionDef) and n.name == "main")
        dong: dict[str, list[int]] = {}
        for n in ast.walk(main):
            if isinstance(n, ast.Call):
                f = n.func
                ten = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
                dong.setdefault(ten, []).append(n.lineno)
        assert min(dong["seal"]) < min(dong["ghi_bang_r"]) < max(dong["consume"])
        assert len(dong["consume"]) == 1, "đúng MỘT lời gọi consume (test khoá TD-0313)"
