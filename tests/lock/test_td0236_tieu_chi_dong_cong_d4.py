"""🔒 TD-0236 / `DR-D4-11` — cổng D4 đóng bằng HIỆN VẬT, không đếm trial.

`MT-38`: khoá `d4_complete` đòi *"đếm được **đúng 18** trial `B2` CONSUMED"*
(`back-end-note.md:80`) trong khi `DR-D4-01:15` cấp **9**. Nhưng con số chỉ
là lớp nông nhất. Lý do thật để đổi hẳn tiêu chí nằm ở `DR-D4-10:211-213`:

    Cổng đếm N dòng `B2` CONSUMED sẽ PASS KỂ CẢ KHI toàn bộ N suất đó đều
    là loại MÔ TẢ và `Z0-T1` — cấu hình DUY NHẤT D4 còn phán quyết được —
    chưa từng chạy.

File này khoá cả hai chiều của phát biểu đó:

  (A) Bộ hiện vật ĐẦY ĐỦ thì cổng cho qua — chốt không quá chặt tới mức
      không bao giờ thoả được (bài học cổng D3: *"một chốt không bao giờ
      thoả được thì tệ hơn không có chốt"*, vì lúc gỡ thì gỡ luôn phần đúng).
  (B) 🔴 Thiếu đúng `Z0-T1` thì cổng TỪ CHỐI, **dù mọi arm mô tả đã đủ và
      kế toán trial khớp hoàn hảo** — đây là ca mà một cổng đếm trial sẽ cho
      qua, và là toàn bộ lý do `DR-D4-11` tồn tại.

  (C) `TestKhongCoHangSoDemTrial` ghim chính QUYẾT ĐỊNH: module không được
      chứa hằng số `18` hay `9`. Đây là ca duy nhất trong file **nêu đích
      danh `DR-D4-11`** — theo khuôn `TD-0171`, con số bị ghim đúng MỘT chỗ
      và chỗ đó phải nhắc tới quyết định, để đổi ý thì buộc phải sửa một
      dòng có tên DR chứ không phải một hằng số vô danh.

⚠️ PHẠM VI: file này canh *tiêu chí*, không canh `close_d4_gate()` — hàm đó
là việc của `TD-0186` và nó phải GỌI `kiem_tieu_chi_dong_d4()` chứ không
khai lại luật (bài học cổng D3.5: hai danh sách song song sẽ trôi lệch).
"""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from tool_d.gates.arm_record import ARM_MUA_PHAN_QUYET, ARM_NHOM_C, CHI_SO_BAT_BUOC, build_arm_record
from tool_d.gates.d4_gate import D4GateError, kiem_tieu_chi_dong_d4
from tool_d.measurement.provenance import Provenance
from tool_d.measurement.tri_state import Measured

REPO_ROOT = Path(__file__).resolve().parents[2]
FILE_D4_GATE = REPO_ROOT / "src" / "tool_d" / "gates" / "d4_gate.py"

DIGEST = "sha256:" + "a" * 64
CUA_SO_TEST = [
    (date(2025, 9, 4), date(2025, 10, 23)),
    (date(2025, 10, 23), date(2025, 12, 11)),
    (date(2025, 12, 11), date(2026, 1, 29)),
]
CUA_SO_TOAN = (date(2025, 6, 12), date(2026, 1, 29))
LENH_THEO_THANG = {
    "2025-06": 12, "2025-07": 30, "2025-08": 28, "2025-09": 31,
    "2025-10": 27, "2025-11": 26, "2025-12": 29, "2026-01": 23,
}
#: Đúng con số của artifact đã niêm phong (`dr015-luot-khop-tranche.json`) —
#: Δ_R đo trên HAI cặp trong khi arm chạy 102 mã. `TD-0234`/`MT-37` chốt
#: KHÔNG đặt sàn số mã, chỉ BẮT KHAI; nên bộ này phải HỢP LỆ.
DELTA_R_PHAM_VI = {"so_ma": 2, "so_fill": 91, "dataset": "CALIB", "chien_luoc": "ZoneAbsorptionMinimal"}

HAN_CHE_DU = (
    "D4 chỉ chạy hướng LONG. D4 KHÔNG phán quyết câu DCA — theo DR-D4-10 "
    "§2.4 câu đó đi Idea Queue, mặc định Z0 single-entry."
)


def _prov() -> Provenance:
    return Provenance(
        params_source="yaml",
        params_effective={"zss_threshold": 0.5},
        git_sha="deadbeef",
        reproducible_from_sha=True,
        data_hashes={"x": "sha256:" + "0" * 64},
        cache_mode="none",
        guard_passed=True,
        runtime_image_digest=DIGEST,
    )


def _ban_ghi(*, arm: str = "Z0-T1", ket_cuc: str = "PASS", **kw: Any) -> dict[str, Any]:
    return build_arm_record(
        arm=arm,
        huong="LONG",
        n_toan_cua_so=206,
        n_chi_test=131,
        cua_so_toan_bo=CUA_SO_TOAN,
        cua_so_chi_test=CUA_SO_TEST,
        lenh_theo_thang=LENH_THEO_THANG,
        so_ma_da_chay=102,
        delta_r_pham_vi=dict(DELTA_R_PHAM_VI),
        chi_so={ten: Measured.ok(0.25) for ten in sorted(CHI_SO_BAT_BUOC)},
        ket_cuc=Measured.ok(ket_cuc),
        provenance=_prov(),
        trial_id="D-0006",
        **kw,
    )


def _bo_day_du() -> list[dict[str, Any]]:
    """Một arm phán quyết (`Z0-T1`) + mọi arm mô tả, mỗi arm một bản ghi."""
    ban = [_ban_ghi(arm="Z0-T1")]
    ban += [_ban_ghi(arm=a, ket_cuc="INCONCLUSIVE") for a in sorted(ARM_NHOM_C)]
    return ban


def _goi(ban_ghi: list[dict[str, Any]], **ghi_de: Any) -> list[str]:
    tham_so: dict[str, Any] = {
        "ban_ghi_arm": ban_ghi,
        "so_dong_b2_consumed": len(ban_ghi),
        "d4_huong": "LONG",
        "d4_han_che": HAN_CHE_DU,
    }
    tham_so.update(ghi_de)
    return kiem_tieu_chi_dong_d4(**tham_so)


class TestBoHienVatDayDuThiChoQua:
    """(A) — chốt phải THOẢ ĐƯỢC, nếu không sớm muộn nó bị gỡ."""

    def test_du_hien_vat_thi_khong_con_ly_do_tu_choi(self) -> None:
        assert _goi(_bo_day_du()) == []

    def test_ket_cuc_INCONCLUSIVE_cua_Z0_T1_VAN_dong_duoc_cong(self) -> None:
        """Cổng chứng nhận *"đã phán quyết"*, KHÔNG phải *"đã thắng"*.

        `DR-D4-09` §2.2 tách "đo được, không đạt" (FAIL) khỏi "không đo được"
        (INCONCLUSIVE) vì hai thứ dẫn tới hành động trái ngược. Một cổng chỉ
        chấp nhận PASS sẽ biến INCONCLUSIVE thành "chưa chạy xong", tức mời
        người ta chạy lại tới khi ra số đẹp — đúng thứ ngân sách trial tồn
        tại để chặn.
        """
        ban = _bo_day_du()
        ban[0] = _ban_ghi(arm="Z0-T1", ket_cuc="INCONCLUSIVE")
        assert _goi(ban) == []


class TestThieuArmPhanQuyetThiTuChoi:
    """(B) 🔴 — ca mà một cổng ĐẾM TRIAL sẽ cho qua. Lý do DR-D4-11 tồn tại."""

    def test_chi_co_arm_MO_TA_va_ke_toan_KHOP_van_bi_TU_CHOI(self) -> None:
        ban = [_ban_ghi(arm=a, ket_cuc="INCONCLUSIVE") for a in sorted(ARM_NHOM_C)]
        loi = _goi(ban)  # so_dong_b2_consumed == len(ban) ⇒ kế toán KHỚP
        assert loi, "cổng cho qua một bộ hiện vật KHÔNG có arm phán quyết nào"
        assert any("Z0-T1" in m for m in loi), loi

    def test_Z0_T1_mang_co_mo_ta_thi_TU_CHOI(self) -> None:
        """Có mặt là chưa đủ — nó phải mang đúng cờ `phan_quyet`."""
        ban = _bo_day_du()
        ban[0] = dict(ban[0], pham_vi_phan_quyet="mo_ta")
        loi = _goi(ban)
        assert loi, "cổng cho qua Z0-T1 mang cờ mo_ta"

    def test_Z0_T1_thieu_ket_cuc_thi_TU_CHOI(self) -> None:
        ban = _bo_day_du()
        ban[0] = dict(ban[0], ket_cuc={"status": "pending", "reason": "chưa chạy"})
        loi = _goi(ban)
        assert loi, "cổng cho qua Z0-T1 không có kết cục đọc được"


class TestKeToanLaQuanHeKhongPhaiHangSo:
    def test_so_b2_lech_so_arm_thi_TU_CHOI(self) -> None:
        ban = _bo_day_du()
        loi = kiem_tieu_chi_dong_d4(
            ban_ghi_arm=ban,
            so_dong_b2_consumed=len(ban) + 1,
            d4_huong="LONG",
            d4_han_che=HAN_CHE_DU,
        )
        assert any("kế toán lệch" in m for m in loi), loi

    @pytest.mark.parametrize("so_arm", [1, 3, 9])
    def test_khop_o_MOI_co_bo_hien_vat(self, so_arm: int) -> None:
        """Quan hệ đúng ở mọi phạm vi D4 — không phải chỉ ở 9 hay 18.

        Bộ chỉ gồm arm mô tả nên vẫn bị từ chối vì thiếu `Z0-T1`; điều ca
        này khẳng định là **không có lý do KẾ TOÁN nào** được sinh ra.
        """
        ban = [_ban_ghi(arm=a, ket_cuc="INCONCLUSIVE") for a in sorted(ARM_NHOM_C)][:so_arm]
        loi = _goi(ban)
        assert not any("kế toán lệch" in m for m in loi), loi


class TestLoiKhaiBatBuoc:
    @pytest.mark.parametrize("huong", [None, "", "long", "CA_HAI"])
    def test_d4_huong_thieu_hoac_sai_thi_TU_CHOI(self, huong: Any) -> None:
        loi = _goi(_bo_day_du(), d4_huong=huong)
        assert any("d4_huong" in m for m in loi), loi

    @pytest.mark.parametrize("han_che", [None, "", "   "])
    def test_thieu_d4_han_che_thi_TU_CHOI(self, han_che: Any) -> None:
        loi = _goi(_bo_day_du(), d4_han_che=han_che)
        assert any("d4_han_che" in m for m in loi), loi

    def test_han_che_khong_nhac_DCA_thi_TU_CHOI(self) -> None:
        loi = _goi(_bo_day_du(), d4_han_che="D4 chỉ chạy hướng LONG.")
        assert any("DCA" in m for m in loi), loi


class TestDauVaoHongThiRAISE:
    """*"Dữ liệu hỏng"* khác hẳn *"cổng chưa đóng được"* — gộp hai thứ là
    cách một lỗi lắp ráp biến thành một kết luận về tiến độ."""

    @pytest.mark.parametrize("xau", ["khong-phai-day", 5, None])
    def test_ban_ghi_arm_sai_kieu(self, xau: Any) -> None:
        with pytest.raises(D4GateError):
            kiem_tieu_chi_dong_d4(
                ban_ghi_arm=xau, so_dong_b2_consumed=0, d4_huong="LONG", d4_han_che=HAN_CHE_DU
            )

    @pytest.mark.parametrize("xau", [-1, "9", True, 1.5])
    def test_so_b2_sai_kieu_hoac_am(self, xau: Any) -> None:
        with pytest.raises(D4GateError):
            kiem_tieu_chi_dong_d4(
                ban_ghi_arm=[], so_dong_b2_consumed=xau, d4_huong="LONG", d4_han_che=HAN_CHE_DU
            )


class TestKhongCoHangSoDemTrial:
    """(C) 🔴 GHIM QUYẾT ĐỊNH — ca DUY NHẤT trong file nêu đích danh `DR-D4-11`.

    `DR-D4-11` §3 chốt: cổng so QUAN HỆ, **không** so với một hằng số. Trả
    tiêu chí về `18` (hay `9`) ⇒ ca này đỏ, và nó là ca đúng để đỏ — người
    sửa buộc phải đọc một dòng có tên quyết định, không phải sửa một hằng số
    vô danh (khuôn `TD-0171`).
    """

    def test_module_khong_chua_hang_so_18_hay_9(self) -> None:
        cay = ast.parse(FILE_D4_GATE.read_text(encoding="utf-8"))
        cam = {9, 18}
        thay = {
            nut.value
            for nut in ast.walk(cay)
            if isinstance(nut, ast.Constant) and isinstance(nut.value, int)
            and not isinstance(nut.value, bool)
            and nut.value in cam
        }
        assert not thay, (
            f"d4_gate.py chứa hằng số {sorted(thay)} — DR-D4-11 §3 chốt cổng so "
            "QUAN HỆ ('số trial B2 đã tiêu khớp số arm đã chạy'), KHÔNG so với "
            "một con số. 18 đã lỗi thời sau 24 giờ; 9 sẽ lỗi thời khi phạm vi D4 "
            "đổi. Nếu thật sự cần một con số, nó phải đi kèm một DR mới."
        )

    def test_arm_mua_phan_quyet_van_la_nguon_su_that(self) -> None:
        """Tiêu chí đọc `ARM_MUA_PHAN_QUYET` của `arm_record`, không chép tên
        arm sang — hai danh sách song song sẽ trôi lệch (MT-03)."""
        nguon = FILE_D4_GATE.read_text(encoding="utf-8")
        assert "ARM_MUA_PHAN_QUYET" in nguon
        assert '"Z0-T1"' not in nguon and "'Z0-T1'" not in nguon, (
            "d4_gate.py ghi cứng tên arm — phải đọc ARM_MUA_PHAN_QUYET"
        )
        assert ARM_MUA_PHAN_QUYET == frozenset({"Z0-T1"})
