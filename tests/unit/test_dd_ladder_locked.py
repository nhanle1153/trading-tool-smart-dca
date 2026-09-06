"""TD-0042 / DR-D0PRE-04 — thang drawdown 5/8/20% là Cấp C, Hạng 0.

Hai điều canh: (1) giá trị YAML khớp DR; (2) `halt` == `daily_loss_budget_pct`
(§12c.5: "một ngày xấu tối đa → HALT tạm" chỉ đúng khi hai số bằng nhau).
Test đỏ = có người đổi Cấp C không qua DR mới, hoặc đổi Tầng A làm gãy ghép cặp.
"""

from __future__ import annotations

from tool_d.config.loader import load_tool_d_config


def test_dd_ladder_khop_dr_d0pre_04() -> None:
    cfg = load_tool_d_config()
    assert dict(cfg.tier_c["dd_ladder_pct"]) == {"soft": 5, "halt": 8, "abort": 20}


def test_halt_bang_daily_loss_budget() -> None:
    cfg = load_tool_d_config()
    assert cfg.tier_c["dd_ladder_pct"]["halt"] == cfg.tier_a["daily_loss_budget_pct"]
