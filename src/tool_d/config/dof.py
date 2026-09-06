"""Kế toán bậc tự do (DOF) — DR-010, canh bởi L-Z29 (spec dòng 3918-3925).

Ba vế của L-Z29:
    (a) |tier_frozen non-underscore| == số bản ghi registry có frozen_rationale
        — CHƯA kiểm được ở D0-PRE (chưa có bản ghi registry thật, registry
        rỗng). `dof_report()` trả `None` cho vế này, không phải False —
        khác "chưa đo được" với "sai" (đúng tinh thần Measured, §0d.6).
    (b) DOF_gốc == Σ(v5 các dòng "rows") + Σ(v5_dung_ra các dòng "bo_sot")
        VÀ |tier_b| == Σ(dof_v6 của rows + bo_sot)
    (c) N_ĐĂNG_KÝ == 4 + 3×|tier_b|×2 + |arm B2|×2 + 20

Lệch bất kỳ vế nào (trừ (a), chưa đo được) → RAISE, CHẶN CHẠY — không
cảnh báo suông (spec dòng 3918: "Lệch → chặn chạy").
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from tool_d.config.loader import DEFAULT_CONFIG_PATH, load_tool_d_config, tunable_param_names

DEFAULT_DOF_INVENTORY_PATH = Path("config/dof_inventory.yaml")

# 9 cấu hình của D0.9 ablation (§10.1, arm: Z0,Z1,Z2,Z3,Z3b,Z0-T0,Z0-T1,Z0-V1,Z0-S1)
# — hằng số CỐ ĐỊNH của spec, không phải tham số tune được, không đọc từ YAML.
ARM_B2_COUNT = 9


class DofMismatchError(RuntimeError):
    """Kế toán DOF lệch — CHẶN CHẠY, không phải cảnh báo suông (L-Z29)."""


@dataclass(frozen=True)
class DofReport:
    dof_goc_declared: int
    dof_goc_from_v5_sum: int
    tier_b_declared_count: int  # từ tool_d_config.yaml thật (tunable_param_names)
    tier_b_from_table_sum: int  # từ tổng cột dof_v6 trong dof_inventory.yaml
    n_dang_ky_computed: int

    @property
    def dof_goc_ok(self) -> bool:
        return self.dof_goc_declared == self.dof_goc_from_v5_sum

    @property
    def tier_b_ok(self) -> bool:
        return self.tier_b_declared_count == self.tier_b_from_table_sum

    def render(self) -> str:
        lines = [
            f"DOF_gốc khai báo: {self.dof_goc_declared}",
            f"DOF_gốc tính từ tổng v5 (26 dòng + bỏ sót): {self.dof_goc_from_v5_sum}"
            f"  {'✅' if self.dof_goc_ok else '❌ LỆCH'}",
            f"tier_b thật trong tool_d_config.yaml: {self.tier_b_declared_count}",
            f"tier_b tính từ tổng dof_v6 trong bảng: {self.tier_b_from_table_sum}"
            f"  {'✅' if self.tier_b_ok else '❌ LỆCH'}",
            f"N_ĐĂNG_KÝ tính từ công thức L-Z29(c): {self.n_dang_ky_computed}",
        ]
        return "\n".join(lines)


def load_dof_inventory(path: Path = DEFAULT_DOF_INVENTORY_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dof_report(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    inventory_path: Path = DEFAULT_DOF_INVENTORY_PATH,
) -> DofReport:
    """Tính báo cáo đối chiếu — KHÔNG raise, chỉ trả số liệu. Dùng
    `assert_dof_or_block()` để biến lệch thành lỗi chặn chạy.
    """
    cfg = load_tool_d_config(config_path)
    inv = load_dof_inventory(inventory_path)

    v5_main = sum(r["v5"] for r in inv["rows"])
    v5_bo_sot = sum(r["v5_dung_ra"] for r in inv["bo_sot"])
    dof_goc_from_v5_sum = v5_main + v5_bo_sot

    dof_v6_main = sum(r["dof_v6"] for r in inv["rows"])
    dof_v6_bo_sot = sum(r["dof_v6"] for r in inv["bo_sot"])
    tier_b_from_table_sum = dof_v6_main + dof_v6_bo_sot

    tier_b_declared_count = len(tunable_param_names(cfg))

    n_dang_ky_computed = 4 + 3 * tier_b_declared_count * 2 + ARM_B2_COUNT * 2 + 20

    return DofReport(
        dof_goc_declared=inv["dof_goc"],
        dof_goc_from_v5_sum=dof_goc_from_v5_sum,
        tier_b_declared_count=tier_b_declared_count,
        tier_b_from_table_sum=tier_b_from_table_sum,
        n_dang_ky_computed=n_dang_ky_computed,
    )


def assert_dof_or_block(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    inventory_path: Path = DEFAULT_DOF_INVENTORY_PATH,
) -> DofReport:
    """Raise `DofMismatchError` nếu (b) không khớp. Gọi TRƯỚC khi commit
    N_ĐĂNG_KÝ (TD-0032, spec dòng 4424: "L-Z29 PASS trước khi commit").
    """
    report = dof_report(config_path=config_path, inventory_path=inventory_path)
    if not report.dof_goc_ok:
        raise DofMismatchError(
            f"DOF_gốc khai báo ({report.dof_goc_declared}) != tổng v5 tính "
            f"được ({report.dof_goc_from_v5_sum}) — kiểm lại config/dof_inventory.yaml"
        )
    if not report.tier_b_ok:
        raise DofMismatchError(
            f"|tier_b| thật ({report.tier_b_declared_count}) != tổng dof_v6 "
            f"trong bảng ({report.tier_b_from_table_sum}) — tool_d_config.yaml "
            "và dof_inventory.yaml đang LỆCH NHAU"
        )
    return report


def main() -> int:  # pragma: no cover — CLI, verify thủ công qua TASKS.md
    import sys

    if "--check" not in sys.argv:
        print("Dùng: python -m tool_d.config.dof --check")
        return 2
    try:
        report = assert_dof_or_block()
    except DofMismatchError as exc:
        print(f"❌ {exc}")
        return 1
    print(report.render())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
