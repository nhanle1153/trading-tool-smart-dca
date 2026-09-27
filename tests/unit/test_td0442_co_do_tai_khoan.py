"""TD-0442 (`DR-CONG-AN-TOAN-01` §3.1(d)) — thanh lý / cấm IP (418) ⇒ dừng MỌI bot cùng tài khoản sàn + cờ đỏ chặn mọi
bộ khởi chạy tiền thật.

API điều khiển mỗi bot chỉ nghe localhost trong mạng riêng của nó (`DR-D11-03` §2.1) ⇒ một Supervisor không với tới bot
khác. Cơ chế: mỗi bot live một Supervisor; cờ đỏ CẤP TÀI KHOẢN là một file chung trên đĩa. Test dựng hai Supervisor giả
dùng chung một file cờ, qua đúng `chay_mot_vong_giam_sat` sản xuất."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path

from tool_d.ops import risk_supervisor_daemon as d
from tool_d.ops.risk_supervisor_daemon import chay_mot_vong_giam_sat, ly_do_khong_bat_tien_that
from tool_d.risk_supervisor import (
    TrangThaiBenVung,
    TrangThaiBreaker,
    doc_co_do_tai_khoan,
    ghi_co_do_tai_khoan,
    luu_trang_thai,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
T0 = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


def _sach() -> TrangThaiBenVung:
    return TrangThaiBenVung(breaker=TrangThaiBreaker())


def _khong_duoc_goi(*_a, **_k):
    raise AssertionError("không được gọi sàn khi đã có cờ đỏ tài khoản")


def _vong(co: Path, nhat_ky: list[str], ten: str, *, force_orders=(), breaker=None, doc_mang=True):
    """Một vòng của Supervisor `ten`, nối đúng hai hàm cờ tài khoản như `main()` nối cho runmode live."""
    return chay_mot_vong_giam_sat(
        _sach(),
        now=T0,
        doc_account_fn=(lambda: {}) if doc_mang else _khong_duoc_goi,
        doc_position_fn=(lambda: []) if doc_mang else _khong_duoc_goi,
        doc_force_orders_fn=(lambda: list(force_orders)) if doc_mang else _khong_duoc_goi,
        doc_breaker_hien_tai_fn=(lambda: breaker or TrangThaiBreaker()) if doc_mang else _khong_duoc_goi,
        tu_thoi_diem_ms=1000,
        dung_bot_fn=lambda: nhat_ky.append(f"stop:{ten}") or {},
        doc_co_do_tai_khoan_fn=lambda: doc_co_do_tai_khoan(co),
        ghi_co_do_tai_khoan_fn=lambda ly_do: (nhat_ky.append(f"co:{ten}"),
                                              ghi_co_do_tai_khoan(co, ly_do=ly_do, nguon=ten, now=T0)),
    )


class TestFileCo:
    def test_chua_co_la_none(self, tmp_path: Path) -> None:
        assert doc_co_do_tai_khoan(tmp_path / "co.json") is None

    def test_giu_ban_dau_khong_ghi_de(self, tmp_path: Path) -> None:
        co = tmp_path / "co.json"
        ghi_co_do_tai_khoan(co, ly_do="LIQUIDATED", nguon="a", now=T0)
        ghi_co_do_tai_khoan(co, ly_do="BINANCE_418_DUNG_HAN", nguon="b", now=T0)
        assert "LIQUIDATED" in doc_co_do_tai_khoan(co) and json.loads(co.read_text(encoding="utf-8"))["nguon"] == "a"

    def test_file_hong_van_la_co_do(self, tmp_path: Path) -> None:
        co = tmp_path / "co.json"
        co.write_text("{dở", encoding="utf-8")
        assert "vẫn coi là CỜ ĐỎ" in doc_co_do_tai_khoan(co)


class TestHaiBotCungTaiKhoan:
    def test_thanh_ly_o_bot_a_thi_ca_hai_bot_nhan_stop(self, tmp_path: Path) -> None:
        co, nhat_ky = tmp_path / "co.json", []
        _, dung_a = _vong(co, nhat_ky, "A", force_orders=[{"time": 5000}])
        _, dung_b = _vong(co, nhat_ky, "B", doc_mang=False)  # B không cần tự thấy thanh lý, không gọi sàn
        assert dung_a and dung_b
        assert nhat_ky == ["co:A", "stop:A", "stop:B"]  # GHI cờ TRƯỚC khi /stop
        assert "LIQUIDATED" in doc_co_do_tai_khoan(co)

    def test_418_o_bot_a_thi_bot_b_cung_dung(self, tmp_path: Path) -> None:
        co, nhat_ky = tmp_path / "co.json", []
        _vong(co, nhat_ky, "A", breaker=TrangThaiBreaker(dung_han=True))
        _vong(co, nhat_ky, "B", doc_mang=False)
        assert nhat_ky == ["co:A", "stop:A", "stop:B"] and "418" in doc_co_do_tai_khoan(co)

    def test_khong_su_co_thi_khong_ai_dung_khong_ghi_co(self, tmp_path: Path) -> None:
        co, nhat_ky = tmp_path / "co.json", []
        _, dung = _vong(co, nhat_ky, "A")
        assert dung is False and nhat_ky == [] and not co.exists()

    def test_khong_noi_ham_co_thi_hanh_vi_cu_giu_nguyen(self) -> None:
        """Dry-run (ví giấy) không nối hai hàm cờ tài khoản ⇒ đúng hành vi trước TD-0442."""
        nhat_ky: list[str] = []
        _, dung = chay_mot_vong_giam_sat(
            _sach(), now=T0, doc_account_fn=lambda: {}, doc_position_fn=lambda: [],
            doc_force_orders_fn=lambda: [{"time": 5000}], doc_breaker_hien_tai_fn=TrangThaiBreaker,
            tu_thoi_diem_ms=1000, dung_bot_fn=lambda: nhat_ky.append("stop") or {},
        )
        assert dung and nhat_ky == ["stop"]


class TestBoKhoiChayTuChoi:
    def test_sach_thi_duoc_bat(self, tmp_path: Path) -> None:
        assert ly_do_khong_bat_tien_that(duong_trang_thai=tmp_path / "s.json",
                                         duong_co_do_tai_khoan=tmp_path / "co.json") is None

    def test_co_do_tai_khoan_thi_tu_choi(self, tmp_path: Path) -> None:
        co = tmp_path / "co.json"
        ghi_co_do_tai_khoan(co, ly_do="LIQUIDATED", nguon="A", now=T0)
        ly_do = ly_do_khong_bat_tien_that(duong_trang_thai=tmp_path / "s.json", duong_co_do_tai_khoan=co)
        assert ly_do and "TÀI KHOẢN" in ly_do

    def test_supervisor_live_giu_co_do_thi_tu_choi(self, tmp_path: Path) -> None:
        s = tmp_path / "s.json"
        luu_trang_thai(TrangThaiBenVung(breaker=TrangThaiBreaker(), la_thanh_ly=True), s)
        assert "cờ đỏ" in ly_do_khong_bat_tien_that(duong_trang_thai=s, duong_co_do_tai_khoan=tmp_path / "co.json")

    def test_trang_thai_hong_thi_tu_choi(self, tmp_path: Path) -> None:
        s = tmp_path / "s.json"
        s.write_text("{hỏng", encoding="utf-8")
        assert "che cờ đỏ" in ly_do_khong_bat_tien_that(duong_trang_thai=s, duong_co_do_tai_khoan=tmp_path / "co.json")

    def test_duong_mac_dinh_la_mot_file_chung_cho_moi_supervisor_live(self) -> None:
        assert d.DUONG_DAN_CO_DO_TAI_KHOAN == Path("runs/risk_supervisor/live/co_do_tai_khoan.json")


def _main(path: Path) -> ast.FunctionDef:
    cay = ast.parse(path.read_text(encoding="utf-8"))
    return next(n for n in cay.body if isinstance(n, ast.FunctionDef) and n.name == "main")


def _ten_goi(ham: ast.FunctionDef) -> list[str]:
    return [
        n.func.id if isinstance(n.func, ast.Name) else n.func.attr
        for n in ast.walk(ham)
        if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))
    ]


class TestNoiDay:
    def test_live_d10_main_kiem_co_do_truoc_moi_buoc_mang(self) -> None:
        goi = _ten_goi(_main(REPO_ROOT / "src/tool_d/ops/live_d10.py"))
        i = goi.index("ly_do_khong_bat_tien_that")
        for sau in ("kiem_cay_khop_head", "kiem_truoc_khi_bat", "get_exchange_info", "execvp"):
            assert goi.index(sau) > i, f"{sau} chạy TRƯỚC chốt cờ đỏ"

    def test_daemon_main_noi_hai_ham_co_tai_khoan(self) -> None:
        ham = _main(REPO_ROOT / "src/tool_d/ops/risk_supervisor_daemon.py")
        khoa = {
            k.arg
            for n in ast.walk(ham)
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "chay_mot_vong_giam_sat"
            for k in n.keywords
        }
        assert {"doc_co_do_tai_khoan_fn", "ghi_co_do_tai_khoan_fn"} <= khoa

    def test_chot_co_do_khong_nam_trong_try(self) -> None:
        """Nuốt lỗi đọc quanh chốt = bật tiền thật trên một cờ đỏ bị che."""
        for n in ast.walk(_main(REPO_ROOT / "src/tool_d/ops/live_d10.py")):
            if isinstance(n, ast.Try):
                trong_try = {
                    getattr(c.func, "id", None) for s in n.body for c in ast.walk(s) if isinstance(c, ast.Call)
                }
                assert "ly_do_khong_bat_tien_that" not in trong_try
