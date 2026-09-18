"""TD-0313 (`DR-BC-01`) — test khoá cho E1 `run_backtest.py` sau khi nối lõi bộ chạy.

Canh bốn thứ:

1. 🔴 **Thứ tự trong `main()`** — `reserve` < `chay_mot_luot` < `seal` < `consume`,
   và `measurement_guard()` vẫn là lệnh đầu sau parse (N5). Kiểm bằng **AST**, không
   bằng chạy thật: `L-Z52`/`L-Z53` nói về THỨ TỰ, và thứ tự là tính chất của mã.
   (Bài học TD-0312: spy tầng Python không phủ hết đường đọc dữ liệu — pyarrow đọc
   ở tầng C. Nên với câu hỏi "cái gì chạy trước cái gì", AST là đúng dụng cụ.)
2. 🔴 **Không cờ nào có mặc định** — đặc biệt `--budget-line` (`DR-BC-01` §4).
3. 🔴 **Mặc định KHÔNG chạy**: thiếu `--chay` ⇒ thoát mã riêng, **không** đặt chỗ.
4. **Năm cổng cũ còn nguyên** và đúng thứ tự (TD-0016/0018/0057/0072).

⚠️ Không có ca nào ở đây chạy backtest thật trên rổ `pool_t0`/`pool_t1`: một lượt
như thế là "chạm" (`DR-014` §2) ⇒ **1 suất trong 114**, và `DR-IQ-01` §1 đang ⏸.
Đường chạy thật của lõi đã được kiểm ở `test_td0312_loi_bo_chay.py` bằng dữ liệu
tự dựng.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
NGUON = REPO / "entrypoints" / "run_backtest.py"


def _main() -> ast.FunctionDef:
    return next(
        n
        for n in ast.walk(ast.parse(NGUON.read_text(encoding="utf-8")))
        if isinstance(n, ast.FunctionDef) and n.name == "main"
    )


def _dong_goi(ham: ast.FunctionDef, ten: str) -> list[int]:
    """Số dòng của mọi lời gọi tên `ten` (kể cả `x.ten(...)`)."""
    ra = []
    for n in ast.walk(ham):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        goi = getattr(f, "id", None) or getattr(f, "attr", None)
        if goi == ten:
            ra.append(n.lineno)
    return sorted(ra)


class TestThuTuTrongMain:
    def test_guard_van_la_lenh_dau_sau_parse(self) -> None:
        """N5 — gọi TƯỜNG MINH, không decorator. `L-Z36` canh bằng AST vì decorator
        làm phép kiểm phải suy luận và dễ PASS giả."""
        ham = _main()
        assert not ham.decorator_list, "main() bị bọc decorator — N5 cấm"
        goi_guard = _dong_goi(ham, "measurement_guard")
        assert len(goi_guard) == 1
        # Trước guard chỉ được có gán argv + parse tham số, không lời gọi nào khác.
        truoc = [
            n.lineno
            for n in ast.walk(ham)
            if isinstance(n, ast.Call) and n.lineno < goi_guard[0]
        ]
        ten_cho_phep = {"build_parser", "parse_known_args", "list"}
        con_lai = [
            n
            for n in ast.walk(ham)
            if isinstance(n, ast.Call)
            and n.lineno < goi_guard[0]
            and (getattr(n.func, "id", None) or getattr(n.func, "attr", None)) not in ten_cho_phep
        ]
        assert con_lai == [], f"có lời gọi lạ trước measurement_guard ở dòng {truoc}"

    def test_nam_cong_cu_con_nguyen_va_dung_thu_tu(self) -> None:
        """TD-0016/0018/0057/0072 — TD-0313 nối phần mới SAU chúng, không đụng."""
        ham = _main()
        thu_tu = [
            "measurement_guard",
            "require_d0_pre_complete",
            "assert_cache_none",
            "run_audit",
            "kiem_h17",
        ]
        dong = [_dong_goi(ham, t) for t in thu_tu]
        assert all(len(d) == 1 for d in dong), f"mỗi cổng phải xuất hiện đúng 1 lần: {dict(zip(thu_tu, dong))}"
        phang = [d[0] for d in dong]
        assert phang == sorted(phang), f"năm cổng cũ bị đảo thứ tự: {dict(zip(thu_tu, phang))}"

    def test_reserve_truoc_chay_truoc_seal_truoc_consume(self) -> None:
        """🔴 `L-Z52` (đặt chỗ TRƯỚC khi chạm dữ liệu) + `L-Z53` (`seal()` NGAY khi có
        chỉ số đầu, TRƯỚC khi in/ghi kết quả — `registry.py:558-561`).

        Kiểm CÓ RĂNG: hoán vị `reserve` xuống sau `chay_mot_luot` ⇒ ca này đỏ.
        """
        ham = _main()
        moc = {t: _dong_goi(ham, t) for t in ("reserve", "chay_mot_luot", "seal", "consume")}
        assert all(len(v) == 1 for v in moc.values()), f"mỗi lời gọi phải có đúng 1 chỗ: {moc}"
        phang = [moc[t][0] for t in ("reserve", "chay_mot_luot", "seal", "consume")]
        assert phang == sorted(phang), f"sai thứ tự đặt chỗ → chạy → niêm phong → tiêu thụ: {moc}"

    def test_bam_du_lieu_dung_truoc_reserve(self) -> None:
        """`DR-BC-01` §3 — dòng `RESERVE` phải mang `data_hashes` THẬT, nên `hash_many()`
        đứng trước `reserve()`. Ngoại lệ này hẹp đúng một câu: chỉ ĐỌC BYTE ĐỂ BĂM."""
        ham = _main()
        assert _dong_goi(ham, "hash_many")[0] < _dong_goi(ham, "reserve")[0]

    def test_refund_theo_nguyen_nhan_MAY(self) -> None:
        """`DR-014` §3: nguyên nhân do MÁY xác định, không nhận lời khai người vận hành.
        Ở đây nghĩa là chuỗi `cause_machine` phải dựng từ mã thoát / tên exception thật."""
        nguon = NGUON.read_text(encoding="utf-8")
        assert "cause_machine=f\"freqtrade_backtesting_exit_{exc.returncode}\"" in nguon
        assert "cause_machine=f\"bo_chay_tu_choi:{type(exc).__name__}\"" in nguon


class TestKhongCoMacDinh:
    @pytest.mark.parametrize(
        "co", ["--tap", "--budget-line", "--hypothesis-slot", "--param-under-test", "--param-value"]
    )
    def test_co_bat_buoc_khong_co_gia_tri_mac_dinh(self, co: str) -> None:
        """🔴 `--budget-line` là cái quan trọng nhất: một mặc định ở đây nghĩa là người
        gõ lệnh không bao giờ phải nhìn thấy mình đang tiêu dòng ngân sách nào.

        Kiểm CÓ RĂNG: đặt `default="B3"` ⇒ ca này đỏ.
        """
        import sys

        sys.path.insert(0, str(REPO / "entrypoints"))
        from run_backtest import build_parser

        hanh_dong = {a.option_strings[0]: a for a in build_parser()._actions if a.option_strings}
        assert hanh_dong[co].default in (None, []), f"{co} có mặc định {hanh_dong[co].default!r}"

    def test_thieu_co_thi_liet_ke_dung_cai_thieu(self) -> None:
        import sys

        sys.path.insert(0, str(REPO / "entrypoints"))
        from run_backtest import _thieu_co, build_parser

        args, _ = build_parser().parse_known_args(["--tap", "WFO", "--budget-line", "B3"])
        assert _thieu_co(args) == ["--hypothesis-slot", "--param-under-test", "--param-value"]

    def test_tap_chi_nhan_CALIB_va_WFO(self) -> None:
        """LOCKBOX không có cửa chặn RIÊNG ở E1 — `ro_cho_tap()` là cửa duy nhất
        (nó nêu `MT-60`). Nhưng `--tap` vẫn giới hạn ở tập đã dựng được rổ."""
        import sys

        sys.path.insert(0, str(REPO / "entrypoints"))
        from run_backtest import TAP_HOP_LE

        assert TAP_HOP_LE == ("CALIB", "WFO")


class TestMacDinhKhongChay:
    def test_co_chay_la_store_true_va_mac_dinh_False(self) -> None:
        import sys

        sys.path.insert(0, str(REPO / "entrypoints"))
        from run_backtest import build_parser

        args, _ = build_parser().parse_known_args(["--tap", "WFO"])
        assert args.chay is False

    def test_ma_thoat_rieng_khong_tai_dung_97(self) -> None:
        """`run_wfo.py` đã dùng 97 với NGHĨA KHÁC (*"chưa có bộ chạy"*). Giữ nguyên
        con số mà đổi nghĩa là đúng lỗi "một tên hai nghĩa ở hai thời điểm" (TD-0234)."""
        import sys

        sys.path.insert(0, str(REPO / "entrypoints"))
        from run_backtest import EXIT_BACKTEST_HONG, EXIT_BO_CHAY_TU_CHOI, EXIT_CHUA_XAC_NHAN_CHAY
        from run_wfo import EXIT_CHUA_CO_BO_CHAY

        ma = {EXIT_CHUA_XAC_NHAN_CHAY, EXIT_BACKTEST_HONG, EXIT_BO_CHAY_TU_CHOI}
        assert len(ma) == 3, "ba mã thoát mới phải khác nhau"
        assert EXIT_CHUA_CO_BO_CHAY not in ma
        assert all(m > 104 for m in ma), "trùng dải mã thoát đã dùng (tới 104)"

    def test_nhanh_khong_chay_KHONG_goi_reserve(self) -> None:
        """Chốt quan trọng nhất của nhánh mặc định: một cờ gõ nhầm không được tiêu suất.

        Kiểm bằng AST: `reserve()` phải nằm SAU câu `return EXIT_CHUA_XAC_NHAN_CHAY`.
        """
        ham = _main()
        dong_return = [
            n.lineno
            for n in ast.walk(ham)
            if isinstance(n, ast.Return)
            and isinstance(n.value, ast.Name)
            and n.value.id == "EXIT_CHUA_XAC_NHAN_CHAY"
        ]
        assert len(dong_return) == 1, "phải có đúng một chỗ thoát cho nhánh chưa xác nhận"
        assert dong_return[0] < _dong_goi(ham, "reserve")[0], (
            "nhánh `--chay` chưa bật vẫn đi qua reserve() — một cờ gõ nhầm sẽ tiêu 1 suất"
        )


class TestKhongThemEntrypointThuChin:
    def test_van_dung_8_file(self) -> None:
        """`L-Z36` — TD-0313 nối vào E1 sẵn có, KHÔNG thêm file thứ 9."""
        from tool_d.measurement.entrypoint_registry import assert_closed_entrypoint_set

        assert_closed_entrypoint_set(REPO / "entrypoints")
        assert len(list((REPO / "entrypoints").glob("*.py"))) == 8
