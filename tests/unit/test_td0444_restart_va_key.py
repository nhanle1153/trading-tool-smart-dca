"""TD-0444 (`DR-CONG-AN-TOAN-01` §3.1(b)) — phần CHUNG mọi chiến lược của bộ kiểm sự cố `TD-0272`.

(A) Thiếu key, tổng quát: MỌI module `ops/` có `main()` phải được xếp loại tiền thật / không tiền — module mới chưa xếp
    loại ⇒ đỏ (buộc người thêm phải quyết). Tiến trình tiền thật gọi `validate_credentials_for_live()` trong `main()`;
    bộ khởi chạy bot tiền thật (`execvp`) qua chốt cờ đỏ `ly_do_khong_bat_tien_that()` TRƯỚC `execvp`.
(B) Khởi động lại giữa chừng, qua `main()` THẬT của Risk Supervisor (mạng giả lập): đỉnh equity, cờ đỏ thanh lý và cờ đỏ
    ABORT đều sống qua lần chạy sau. Phần riêng từng chiến lược (kế hoạch cỡ lệnh kiểu `TD-0237`) là mục bắt buộc của DR
    thiết kế D0 (`DR-CONG-AN-TOAN-01` §3.4), không ở đây."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from tool_d.ops import risk_supervisor_daemon as d
from tool_d.ops.risk_supervisor_daemon import ly_do_khong_bat_tien_that
from tool_d.risk_supervisor import TEN_FILE_DD_STATE, TrangThaiBreaker

REPO_ROOT = Path(__file__).resolve().parents[2]
THU_MUC_OPS = REPO_ROOT / "src/tool_d/ops"

#: Xếp loại có chủ ý. Thêm module `ops/` có `main()` ⇒ PHẢI thêm vào đúng một tập (test dưới đỏ cho tới khi làm).
OPS_TIEN_THAT = {"live_d10.py", "risk_supervisor_daemon.py"}
OPS_KHONG_TIEN = {
    "dry_run.py",  # ví giấy của Freqtrade
    "ghi_nap_rut.py",  # chỉ ghi sổ đỉnh cục bộ
    "heartbeat_watchdog.py",  # chỉ đọc heartbeat + gửi Telegram
}


def _main(path: Path) -> ast.FunctionDef | None:
    cay = ast.parse(path.read_text(encoding="utf-8"))
    return next((n for n in cay.body if isinstance(n, ast.FunctionDef) and n.name == "main"), None)


def _ten_goi(ham: ast.FunctionDef) -> list[str]:
    """Tên các lời gọi theo THỨ TỰ NGUỒN — `ast.walk` duyệt theo chiều rộng, dùng thẳng thứ tự đó để so trước/sau là sai."""
    goi = [
        n for n in ast.walk(ham) if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))
    ]
    goi.sort(key=lambda n: (n.lineno, n.col_offset))
    return [n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in goi]


class TestAKeyTongQuat:
    def test_moi_module_ops_co_main_deu_da_xep_loai(self) -> None:
        co_main = {p.name for p in THU_MUC_OPS.glob("*.py") if _main(p) is not None}
        assert not OPS_TIEN_THAT & OPS_KHONG_TIEN
        assert co_main == OPS_TIEN_THAT | OPS_KHONG_TIEN, (
            f"module ops/ có main() chưa xếp loại: {sorted(co_main - OPS_TIEN_THAT - OPS_KHONG_TIEN)} · "
            f"xếp loại thừa: {sorted((OPS_TIEN_THAT | OPS_KHONG_TIEN) - co_main)}"
        )

    @pytest.mark.parametrize("ten", sorted(OPS_TIEN_THAT))
    def test_tien_that_goi_kiem_key_trong_main(self, ten: str) -> None:
        assert "validate_credentials_for_live" in _ten_goi(_main(THU_MUC_OPS / ten))

    @pytest.mark.parametrize("ten", sorted(OPS_TIEN_THAT))
    def test_bo_khoi_chay_bot_tien_that_qua_chot_co_do_truoc_execvp(self, ten: str) -> None:
        goi = _ten_goi(_main(THU_MUC_OPS / ten))
        if "execvp" not in goi:
            pytest.skip(f"{ten} không khởi chạy bot (không execvp)")
        assert goi.index("ly_do_khong_bat_tien_that") < goi.index("execvp")
        assert goi.index("validate_credentials_for_live") < goi.index("execvp")


# ─────────────────────────── (B) qua main() thật ───────────────────────────


@pytest.fixture
def mang_gia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Thay MỌI lời gọi mạng của `main()` bằng bản ghi; phần còn lại (đọc/lưu trạng thái, đỉnh, dd_state, cờ tài khoản,
    L-Z44 trên `tool_d_config.yaml` thật) chạy nguyên."""
    goi: list[str] = []
    tk = {"equity": 1000.0, "force_orders": []}
    monkeypatch.setenv(d.ENV_FT_USERNAME, "u")
    monkeypatch.setenv(d.ENV_FT_PASSWORD, "p")
    monkeypatch.setattr(d, "validate_credentials_for_live", lambda: ("k", "s"))
    monkeypatch.setattr(d, "get_account_info", lambda **_: {"totalMarginBalance": tk["equity"]})
    monkeypatch.setattr(d, "get_position_risk", lambda **_: [])
    monkeypatch.setattr(d, "get_force_orders", lambda **_: list(tk["force_orders"]))
    monkeypatch.setattr(d, "trang_thai_breaker_hien_tai", TrangThaiBreaker)
    for ten in ("dung_bot", "tam_ngung_mo_lenh", "mo_lai_bot"):
        monkeypatch.setattr(d, ten, lambda *_a, _t=ten, **_k: goi.append(_t) or {})
    monkeypatch.setattr(d, "doc_so_lenh_dong", lambda *_a, **_k: 0)
    monkeypatch.setattr(d, "doc_so_vi_the_mo", lambda *_a, **_k: 0)
    monkeypatch.setattr(d, "DUONG_DAN_CO_DO_TAI_KHOAN", tmp_path / "co_do_tai_khoan.json")
    state = tmp_path / "live" / "state.json"

    def chay() -> int:
        return d.main(["--runmode", "live", "--state-path", str(state), "--max-iterations", "1", "--chu-ky-s", "0"])

    return chay, tk, goi, state


def _dd_state(state: Path) -> dict:
    return json.loads((state.parent / TEN_FILE_DD_STATE).read_text(encoding="utf-8"))


class TestBRestartQuaMainThat:
    def test_dinh_equity_song_qua_restart(self, mang_gia) -> None:
        chay, tk, _, state = mang_gia
        assert chay() == 0
        tk["equity"] = 950.0
        assert chay() == 0
        assert _dd_state(state)["dd_pct"] == pytest.approx(5.0)  # đỉnh 1000 giữ nguyên, không đặt lại về 950

    def test_co_do_thanh_ly_song_qua_restart_va_chan_bo_khoi_chay(self, mang_gia, tmp_path: Path) -> None:
        chay, tk, goi, state = mang_gia
        tk["force_orders"] = [{"time": 9_999_999_999_999}]
        assert chay() == d.EXIT_DA_DUNG_VI_CO_DO and goi == ["dung_bot"]
        tk["force_orders"] = []
        assert chay() == d.EXIT_CO_DO_TU_LAN_CHAY_TRUOC and goi == ["dung_bot"]  # không tự gỡ, không gọi gì thêm
        assert _dd_state(state)["co_do"] is True
        assert ly_do_khong_bat_tien_that(duong_trang_thai=state,
                                         duong_co_do_tai_khoan=tmp_path / "co_do_tai_khoan.json") is not None

    def test_abort_song_qua_restart(self, mang_gia, tmp_path: Path) -> None:
        chay, tk, goi, state = mang_gia
        assert chay() == 0
        tk["equity"] = 700.0  # sụt 30% > 20%
        assert chay() == d.EXIT_DA_DUNG_VI_CO_DO and "dung_bot" in goi
        assert chay() == d.EXIT_CO_DO_TU_LAN_CHAY_TRUOC
        assert "cờ đỏ" in ly_do_khong_bat_tien_that(duong_trang_thai=state,
                                                     duong_co_do_tai_khoan=tmp_path / "co_do_tai_khoan.json")
