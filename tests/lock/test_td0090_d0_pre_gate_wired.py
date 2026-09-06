"""TD-0090 — cổng D0-PRE (§N2, spec dòng 4464) phải NỐI VÀO việc thật, không
nằm trong tài liệu. Cùng tinh thần L-Z34: một lệnh kiểm không bao giờ kích
hoạt là trang trí.

Hai lớp kiểm:
  1. AST — `require_d0_pre_complete()` có mặt trong `main()` của E1/E2/E3
     (vô điều kiện, ngay sau guard) và của E8 (nhánh backfill thật).
  2. Hành vi — trỏ `runtime_state.json` sang file KHÔNG có khoá
     `d0_pre_complete` → hàm trả đúng `EXIT_D0_PRE_GATE_CLOSED`, và trỏ
     sang file thật của repo (cổng đã hoàn tất, TD-0086) → trả `None`.

🔴 E7 CHƯA nối: nhánh chạm dữ liệu của nó (H1-D point-in-time) chưa tồn
tại, sẽ nối ở TD-0096. Test dưới đây khoá luôn giả định đó để nếu ai viết
nhánh H1-D mà quên gác cổng thì có chỗ bắt (xem
`test_e7_chua_noi_cong_va_phai_noi_o_td0096`).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tool_d.gates.d0_pre import (
    EXIT_D0_PRE_GATE_CLOSED,
    DEFAULT_RUNTIME_STATE_PATH,
    is_d0_pre_complete,
    require_d0_pre_complete,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINTS_GATED_ALWAYS = ("run_backtest.py", "run_wfo.py", "run_ablation.py")
ENTRYPOINT_GATED_ON_BRANCH = "backfill_data.py"


def _main_calls(entrypoint_file: str) -> list[str]:
    tree = ast.parse((REPO_ROOT / "entrypoints" / entrypoint_file).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            calls: list[str] = []
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    f = sub.func
                    if isinstance(f, ast.Name):
                        calls.append(f.id)
                    elif isinstance(f, ast.Attribute):
                        calls.append(f.attr)
            return calls
    raise AssertionError(f"{entrypoint_file}: không tìm thấy main()")


class TestCongNoiVaoMain:
    @pytest.mark.parametrize("f", ENTRYPOINTS_GATED_ALWAYS)
    def test_e1_e2_e3_goi_cong_trong_main(self, f: str) -> None:
        assert "require_d0_pre_complete" in _main_calls(f), f"{f}: main() không gác cổng D0-PRE"

    @pytest.mark.parametrize("f", ENTRYPOINTS_GATED_ALWAYS)
    def test_cong_dung_ngay_sau_guard_truoc_moi_viec_ton_thoi_gian(self, f: str) -> None:
        # N5: guard trước; cổng D0-PRE ngay sau — TRƯỚC audit/seal-verify/cache,
        # vì không được làm bất cứ việc tốn thời gian nào khi còn chưa được phép.
        calls = _main_calls(f)
        assert calls.index("measurement_guard") < calls.index("require_d0_pre_complete")
        for sau in ("run_audit", "verify_all_seals"):
            assert calls.index("require_d0_pre_complete") < calls.index(sau), (
                f"{f}: cổng D0-PRE phải đứng trước {sau}"
            )

    def test_e8_gac_nhanh_backfill_that(self) -> None:
        assert "require_d0_pre_complete" in _main_calls(ENTRYPOINT_GATED_ON_BRANCH)

    def test_e8_van_cho_probe_coverage_chay_truoc_cong(self) -> None:
        # MT-02: đo metadata KHÔNG phải "chạm dữ liệu" — TD-0080 đã chạy
        # đúng như vậy khi cổng chưa hoàn tất. Nhánh probe phải nằm TRƯỚC
        # lệnh gác trong mã nguồn.
        text = (REPO_ROOT / "entrypoints" / ENTRYPOINT_GATED_ON_BRANCH).read_text(encoding="utf-8")
        assert text.index("args.probe_coverage") < text.index("require_d0_pre_complete(ENTRYPOINT)")

    def test_e7_chua_noi_cong_va_phai_noi_o_td0096(self) -> None:
        # Khoá giả định hiện tại: E7 chưa có nhánh chạm dữ liệu nào. Khi
        # TD-0096 viết `pairlist_point_in_time`, test này đỏ — lúc đó nối
        # cổng vào nhánh đó rồi chuyển test sang khẳng định ngược lại.
        text = (REPO_ROOT / "entrypoints" / "build_pool.py").read_text(encoding="utf-8")
        assert "pairlist_point_in_time" not in text, (
            "E7 đã có nhánh chạm dữ liệu point-in-time — phải gác cổng D0-PRE cho nhánh đó (TD-0096)"
        )


class TestHanhViCong:
    def test_thieu_khoa_thi_tra_ma_thoat_90(self, tmp_path: Path) -> None:
        state = tmp_path / "runtime_state.json"
        state.write_text('{"khong_co_khoa_can_thiet": true}', encoding="utf-8")
        assert require_d0_pre_complete("E1", state) == EXIT_D0_PRE_GATE_CLOSED

    def test_file_khong_ton_tai_thi_tu_choi(self, tmp_path: Path) -> None:
        assert require_d0_pre_complete("E1", tmp_path / "khong_ton_tai.json") == EXIT_D0_PRE_GATE_CLOSED

    def test_json_hong_thi_tu_choi_khong_crash(self, tmp_path: Path) -> None:
        state = tmp_path / "runtime_state.json"
        state.write_text("{ hỏng json", encoding="utf-8")
        assert require_d0_pre_complete("E1", state) == EXIT_D0_PRE_GATE_CLOSED

    def test_khoa_la_chuoi_true_khong_duoc_tinh_la_dat(self, tmp_path: Path) -> None:
        # Fail-closed: chỉ đúng boolean True mới qua, "true"/1 thì không.
        state = tmp_path / "runtime_state.json"
        state.write_text('{"d0_pre_complete": "true"}', encoding="utf-8")
        assert require_d0_pre_complete("E1", state) == EXIT_D0_PRE_GATE_CLOSED

    def test_cong_that_cua_repo_da_hoan_tat_thi_cho_di_tiep(self) -> None:
        # TD-0086 đã đóng cổng thật — nếu test này đỏ nghĩa là
        # registry/runtime_state.json bị xoá/sửa, không phải lỗi code.
        assert is_d0_pre_complete(REPO_ROOT / DEFAULT_RUNTIME_STATE_PATH) is True
        assert require_d0_pre_complete("E1", REPO_ROOT / DEFAULT_RUNTIME_STATE_PATH) is None
