"""TD-0436 (`DR-TANG-CHAN-01` §4 điều 4) — mọi chiến lược LÊN TIỀN phải nối bậc 5% qua `tang_chan.mult_dd_tu_supervisor`.

Vì sao: tới 26/09/2026 thang sụt vốn chỉ sống trong `ZoneAbsorption`; `RoFunding` — ứng viên từng sắp lên tiền — không có
tầng nào. Phần CỨNG (HALT/ABORT) nay ở Supervisor cho mọi chiến lược; phần MỀM (nửa cỡ) chỉ chiến lược làm được, nên cần máy
canh: một chiến lược mới được đưa vào bộ khởi động mà quên nối thì test đỏ.

"Lên tiền" = tên chiến lược mà CHÍNH các bộ khởi động chạy dài khai (`ops/dry_run.TEN_CHIEN_LUOC`,
`ops/live_d10.CHIEN_LUOC_HOP_LE`) — không liệt kê tay, để thêm một chiến lược vào bộ khởi động là tự vào vùng canh.
Điều kiện: `custom_stake_amount` của lớp (hoặc lớp cha trong cùng thư mục) gọi — trực tiếp hoặc qua một phương thức cùng lớp
— tới `mult_dd_tu_supervisor`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tool_d.ops import dry_run, live_d10

REPO_ROOT = Path(__file__).resolve().parents[2]
THU_MUC_CHIEN_LUOC = REPO_ROOT / "user_data/strategies"
HAM_DOC = "mult_dd_tu_supervisor"

#: Miễn TƯỜNG MINH, có lý do. Thêm một dòng ở đây là quyết định có ý thức — ghi vào commit và DR.
MIEN: dict[str, str] = {
    "CtrlD10": "công cụ PHỤ đo hạ tầng lệnh D10 (`DR-D10-02` §6), cỡ lệnh = sàn tối thiểu cố định ⇒ nửa cỡ rơi dưới sàn; "
    "HALT/ABORT vẫn chặn nó qua Supervisor (`/stopentry` chặn cả bơm thêm — `freqtradebot.py:801`, `/stop`)",
}


def chien_luoc_len_tien() -> set[str]:
    return {dry_run.TEN_CHIEN_LUOC, *live_d10.CHIEN_LUOC_HOP_LE}


def _lop(ten: str, goc: Path = THU_MUC_CHIEN_LUOC) -> ast.ClassDef:
    cay = ast.parse((goc / f"{ten}.py").read_text(encoding="utf-8"))
    return next(n for n in cay.body if isinstance(n, ast.ClassDef) and n.name == ten)


def _goi_trong(ham: ast.FunctionDef) -> set[str]:
    ten: set[str] = set()
    for n in ast.walk(ham):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                ten.add(n.func.id)
            elif isinstance(n.func, ast.Attribute):
                ten.add(n.func.attr)
    return ten


def co_noi_tang_chan(ten: str, goc: Path = THU_MUC_CHIEN_LUOC) -> bool:
    """`custom_stake_amount` (tìm từ lớp này lên các lớp cha CÙNG thư mục) chạm tới `HAM_DOC`, bắc cầu qua phương thức
    cùng lớp. Lớp cha ngoài thư mục (IStrategy) không tính."""
    chuoi: list[ast.ClassDef] = []
    hien = ten
    while (goc / f"{hien}.py").is_file():
        lop = _lop(hien, goc)
        chuoi.append(lop)
        cha = [b.id for b in lop.bases if isinstance(b, ast.Name)]
        if not cha:
            break
        hien = cha[0]
    phuong_thuc: dict[str, ast.FunctionDef] = {}
    for lop in reversed(chuoi):  # lớp con ghi đè lớp cha
        for n in lop.body:
            if isinstance(n, ast.FunctionDef):
                phuong_thuc[n.name] = n
    if "custom_stake_amount" not in phuong_thuc:
        return False
    da_xem: set[str] = set()
    ngan_xep = ["custom_stake_amount"]
    while ngan_xep:
        ten_ham = ngan_xep.pop()
        if ten_ham in da_xem or ten_ham not in phuong_thuc:
            continue
        da_xem.add(ten_ham)
        goi = _goi_trong(phuong_thuc[ten_ham])
        if HAM_DOC in goi:
            return True
        ngan_xep.extend(goi & set(phuong_thuc))
    return False


class TestMoiChienLuocLenTienNoiTangChan:
    def test_vung_canh_khong_rong_va_gom_hai_chien_luoc_that(self) -> None:
        assert {"ZoneAbsorption", "RoFundingD10"} <= chien_luoc_len_tien()

    @pytest.mark.parametrize("ten", sorted(chien_luoc_len_tien()))
    def test_chien_luoc_noi_tang_chan_hoac_mien_co_ly_do(self, ten: str) -> None:
        if ten in MIEN:
            assert MIEN[ten].strip(), ten
            return
        assert co_noi_tang_chan(ten), (
            f"{ten} được bộ khởi động chạy dài nhưng `custom_stake_amount` KHÔNG chạm tới `{HAM_DOC}` — thiếu bậc 5% của "
            "thang sụt vốn (DR-TANG-CHAN-01 §4). Nối qua `tool_d.tang_chan`, hoặc miễn TƯỜNG MINH có lý do."
        )

    def test_khong_mien_thua(self) -> None:
        assert set(MIEN) <= chien_luoc_len_tien(), "dòng miễn cho chiến lược không còn được bộ khởi động nào chạy"


class TestMayCanhCoRang:
    def _ghi(self, goc: Path, ten: str, than: str) -> None:
        (goc / f"{ten}.py").write_text(than, encoding="utf-8")

    def test_goi_truc_tiep_thi_dat(self, tmp_path) -> None:
        self._ghi(tmp_path, "A", "class A(IStrategy):\n    def custom_stake_amount(self):\n"
                                 "        return mult_dd_tu_supervisor('live')\n")
        assert co_noi_tang_chan("A", tmp_path)

    def test_goi_bac_cau_qua_phuong_thuc_cung_lop_thi_dat(self, tmp_path) -> None:
        self._ghi(tmp_path, "A", "class A(IStrategy):\n    def _m(self):\n        return mult_dd_tu_supervisor('live')\n"
                                 "    def custom_stake_amount(self):\n        return self._m() * 2\n")
        assert co_noi_tang_chan("A", tmp_path)

    def test_lop_con_ke_thua_tu_lop_cha_cung_thu_muc(self, tmp_path) -> None:
        self._ghi(tmp_path, "Cha", "class Cha(IStrategy):\n    def custom_stake_amount(self):\n"
                                   "        return mult_dd_tu_supervisor('live')\n")
        self._ghi(tmp_path, "Con", "class Con(Cha):\n    def khac(self):\n        return 1\n")
        assert co_noi_tang_chan("Con", tmp_path)

    def test_lop_con_ghi_de_ma_quen_thi_DO(self, tmp_path) -> None:
        self._ghi(tmp_path, "Cha", "class Cha(IStrategy):\n    def custom_stake_amount(self):\n"
                                   "        return mult_dd_tu_supervisor('live')\n")
        self._ghi(tmp_path, "Con", "class Con(Cha):\n    def custom_stake_amount(self):\n        return 5.0\n")
        assert not co_noi_tang_chan("Con", tmp_path)

    def test_khong_co_custom_stake_amount_thi_DO(self, tmp_path) -> None:
        self._ghi(tmp_path, "A", "class A(IStrategy):\n    def _m(self):\n        return mult_dd_tu_supervisor('live')\n")
        assert not co_noi_tang_chan("A", tmp_path)
