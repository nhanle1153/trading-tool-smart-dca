"""TD-0347 — `cua_so_tap()`: cửa sổ chạy NỬA MỞ `[start, end)` (`DR-D9-01`), một chỗ tính cho E1, E3 và kịch bản đo.

Canh:
1. Mặc định đúng biên thật đọc từ `tool_d_config.yaml` — WFO `[2025-06-12, 2026-01-29)`, CALIB `[T0, T1)`.
2. 🔴 Cửa sổ cũ `[start, end + 1 ngày)` bị TỪ CHỐI — đó là dạng lỗi đã lấn một ngày qua mốc LOCKBOX (TD-0345 lộ ra).
   Kèm ca chứng minh vì sao phép kiểm cũ không bắt được: `assert_dataset_timerange(observed_end = den − 1)` NHẬN nó.
3. E1 `_cua_so`: mặc định = `cua_so_tap`; `--den` gõ tay vượt mốc cuối tập bị từ chối (trước TD-0347 lọt).
4. AST: E1, E3, kịch bản TD-0345 đều gọi `cua_so_tap`; không file nào còn cộng `timedelta` vào `bien.end`.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from tool_d.config.loader import load_tool_d_config
from tool_d.ledger.timerange import (
    DatasetBoundary,
    TimerangeViolationError,
    assert_dataset_timerange,
    cua_so_tap,
    dataset_boundaries_from_config,
)

REPO = Path(__file__).resolve().parents[2]
NOI_GOI = (
    REPO / "entrypoints" / "run_backtest.py",
    REPO / "entrypoints" / "run_ablation.py",
    REPO / "docs" / "du-lieu-do" / "do_td0345_dem_n_4_arm_ro_t1.py",
)


def _bien() -> dict[str, DatasetBoundary]:
    return dataset_boundaries_from_config(load_tool_d_config(REPO / "config" / "tool_d_config.yaml"))


class TestMacDinh:
    def test_wfo_nua_mo_dung_ngay_that(self) -> None:
        assert cua_so_tap(_bien()["WFO"]) == (date(2025, 6, 12), date(2026, 1, 29))

    def test_calib_nua_mo(self) -> None:
        b = _bien()["CALIB"]
        assert cua_so_tap(b) == (b.start, b.end)
        assert b.end == _bien()["WFO"].start  # cận phải CALIB = cận trái WFO: nửa mở thì không ngày nào thuộc hai tập


class TestTuChoi:
    def test_cua_so_cu_cong_1_ngay_bi_tu_choi(self) -> None:
        b = _bien()["WFO"]
        with pytest.raises(TimerangeViolationError, match="NỬA MỞ"):
            cua_so_tap(b, den=b.end + timedelta(days=1))

    def test_vi_sao_phep_kiem_cu_khong_bat(self) -> None:
        """Ghi lại khoảng hở TD-0347 đóng: biên ĐÓNG của `assert_dataset_timerange` nhận `den = end + 1`."""
        b = _bien()["WFO"]
        den_cu = b.end + timedelta(days=1)
        assert_dataset_timerange(dataset="WFO", observed_start=b.start, observed_end=den_cu - timedelta(days=1), boundary=b)

    @pytest.mark.parametrize(
        "lech",
        [
            {"tu": date(2025, 6, 11)},  # trước biên trái
            {"tu": date(2025, 7, 1), "den": date(2025, 7, 1)},  # cửa sổ rỗng
            {"tu": date(2025, 8, 1), "den": date(2025, 7, 1)},  # ngược
            {"den": date(2026, 9, 6)},  # sâu vào LOCKBOX
        ],
    )
    def test_ngoai_bien(self, lech: dict) -> None:
        with pytest.raises(TimerangeViolationError):
            cua_so_tap(_bien()["WFO"], **lech)

    def test_cua_so_con_ben_trong_hop_le(self) -> None:
        b = _bien()["WFO"]
        assert cua_so_tap(b, tu=date(2025, 7, 1), den=b.end) == (date(2025, 7, 1), b.end)


def _e1():
    sys.path.insert(0, str(REPO / "entrypoints"))
    spec = importlib.util.spec_from_file_location("run_backtest_td0347", REPO / "entrypoints" / "run_backtest.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestE1:
    def test_mac_dinh_la_cua_so_tap(self) -> None:
        b = _bien()["WFO"]
        assert _e1()._cua_so(SimpleNamespace(tu=None, den=None), b) == cua_so_tap(b)

    def test_den_go_tay_vuot_moc_bi_tu_choi(self) -> None:
        b = _bien()["WFO"]
        with pytest.raises(TimerangeViolationError):
            _e1()._cua_so(SimpleNamespace(tu=None, den=(b.end + timedelta(days=1)).isoformat()), b)


def _goi(cay: ast.AST, ten: str) -> int:
    return sum(
        1
        for n in ast.walk(cay)
        if isinstance(n, ast.Call) and (getattr(n.func, "id", None) or getattr(n.func, "attr", None)) == ten
    )


def _cong_vao_bien_end(cay: ast.AST) -> list[int]:
    """Mọi `<x>.end + <...>` — dạng lỗi TD-0347 (`bien.end + timedelta(days=1)`)."""
    return [
        n.lineno
        for n in ast.walk(cay)
        if isinstance(n, ast.BinOp)
        and isinstance(n.op, ast.Add)
        and isinstance(n.left, ast.Attribute)
        and n.left.attr == "end"
    ]


@pytest.mark.parametrize("duong", NOI_GOI, ids=lambda p: p.name)
class TestNoiGoi:
    def test_goi_cua_so_tap(self, duong: Path) -> None:
        assert _goi(ast.parse(duong.read_text(encoding="utf-8")), "cua_so_tap") >= 1

    def test_khong_cong_vao_bien_end(self, duong: Path) -> None:
        assert _cong_vao_bien_end(ast.parse(duong.read_text(encoding="utf-8"))) == []


def test_kiem_co_rang_ast_bat_dang_loi_cu() -> None:
    assert _cong_vao_bien_end(ast.parse("den = bien.end + timedelta(days=1)")) != []
