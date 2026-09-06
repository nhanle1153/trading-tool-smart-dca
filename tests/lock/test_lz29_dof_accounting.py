"""L-Z29 🔴 CRITICAL — kế toán bậc tự do tự kiểm (spec dòng 3918-3925, TD-0031/0032).

Ba vế:
    (a) |tier_frozen non-underscore| == số bản ghi registry có frozen_rationale
        — CHƯA kiểm được ở D0-PRE (chưa có bản ghi registry thật). Sẽ thêm
        khi registry hoạt động (Khối 5).
    (b) DOF_gốc == Σ(v5 các dòng) + Σ(v5_dung_ra các dòng bỏ sót)
    (c) N_ĐĂNG_KÝ == 4 + 3×|tier_b|×2 + |arm B2|×2 + 20

File này kiểm (b) và (c) — nguồn: config/dof_inventory.yaml (TD-0031),
xác nhận lại bảng đối chiếu DR-010.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
import yaml

from tool_d.config.dof import (
    ARM_B2_COUNT,
    DofMismatchError,
    assert_dof_or_block,
    dof_report,
)


class TestDofReportTrenDuLieuThat:
    def test_dof_goc_28(self) -> None:
        report = dof_report()
        assert report.dof_goc_declared == 28
        assert report.dof_goc_ok is True

    def test_tier_b_12(self) -> None:
        report = dof_report()
        assert report.tier_b_declared_count == 12
        assert report.tier_b_ok is True

    def test_n_dang_ky_114(self) -> None:
        report = dof_report()
        assert report.n_dang_ky_computed == 114

    def test_cong_thuc_n_dang_ky_dung_cong_thuc_spec(self) -> None:
        # 4 (B0) + 3×12×2 (B1) + 9×2 (B2) + 20 (B3) = 4+72+18+20=114
        report = dof_report()
        assert 4 + 3 * report.tier_b_declared_count * 2 + ARM_B2_COUNT * 2 + 20 == 114

    def test_assert_khong_raise_tren_du_lieu_that(self) -> None:
        assert_dof_or_block()  # không raise = PASS


class TestBoRangCoRang:
    """Cố tình làm hỏng inventory để chứng minh assert_dof_or_block() bắt được."""

    def test_dof_goc_sai_thi_raise(self, tmp_path: Path) -> None:
        inv = yaml.safe_load(Path("config/dof_inventory.yaml").read_text(encoding="utf-8"))
        inv["dof_goc"] = 999  # cố tình sai
        bad_path = tmp_path / "dof_inventory_bad.yaml"
        bad_path.write_text(yaml.dump(inv, allow_unicode=True), encoding="utf-8")

        with pytest.raises(DofMismatchError, match="DOF_gốc"):
            assert_dof_or_block(inventory_path=bad_path)

    def test_thieu_mot_dong_thi_raise(self, tmp_path: Path) -> None:
        inv = yaml.safe_load(Path("config/dof_inventory.yaml").read_text(encoding="utf-8"))
        inv["rows"].pop()  # xoá 1 dòng -> tổng v5 và tổng dof_v6 đều lệch
        bad_path = tmp_path / "dof_inventory_missing_row.yaml"
        bad_path.write_text(yaml.dump(inv, allow_unicode=True), encoding="utf-8")

        with pytest.raises(DofMismatchError):
            assert_dof_or_block(inventory_path=bad_path)

    def test_dof_v6_sai_lech_tier_b_thi_raise(self, tmp_path: Path) -> None:
        inv = yaml.safe_load(Path("config/dof_inventory.yaml").read_text(encoding="utf-8"))
        inv["rows"][0]["dof_v6"] = 1  # bịa thêm 1 tunable không có thật trong YAML
        bad_path = tmp_path / "dof_inventory_extra_tunable.yaml"
        bad_path.write_text(yaml.dump(inv, allow_unicode=True), encoding="utf-8")

        with pytest.raises(DofMismatchError, match="tier_b"):
            assert_dof_or_block(inventory_path=bad_path)
