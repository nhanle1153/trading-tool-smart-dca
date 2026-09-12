"""TD-0232 — bản ghi kết quả ARM phải BẮT KHAI cả hai con số `n` (`MT-36`).

🔴 **Thứ được canh ở đây, nói thẳng:** `n = 206` mà `DR-D4-10` §2.1 dẫn tính
trên **toàn** cửa sổ `[T1,T2]` (231 ngày); ba cửa sổ **test** của sơ đồ fold
chỉ phủ **147/231 ngày**. Hai cách đọc cho `n` = 206 vs ~131 ⇒ thuế nhiễu
`h/√n` lệch **25%**, rào `mean_R` (std 1,25) lệch **0,368 → 0,436**. Mà
`dsr.py:52` nhận `n_trades: int` **không có ngữ nghĩa cửa sổ nào**. Nếu bản
ghi chỉ mang **một** con số `n` thì câu *"n nào"* được trả lời bằng cách vô
tình, và **không phép kiểm nào của dự án nhìn thấy**.

🔑 **Vì sao đối chiếu ĐẦU RA THẬT với schema, không đối chiếu fixture:** schema
đặt `additionalProperties: false`, nên một khoá thêm vào code mà quên thêm vào
schema **không** bị bộ test kiểu-fixture bắt — fixture và schema do cùng một
người sửa cùng lúc nên chúng luôn khớp nhau và **cùng lệch khỏi code**. Nó chỉ
nổ ở lần ghi THẬT đầu tiên. Tiền lệ đã cắn thật: `trial_event.schema.json`,
**735 test xanh vẫn không bắt được** (xem `wfo/fold_record.py` docstring).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from tool_d.gates.arm_record import (
    ARM_MUA_PHAN_QUYET,
    ARM_NHOM_C,
    CHI_SO_BAT_BUOC,
    ArmRecordError,
    build_arm_record,
    pham_vi_theo_arm,
    validate_arm_record,
)
from tool_d.measurement.provenance import Provenance
from tool_d.measurement.tri_state import Measured

REPO_ROOT = Path(__file__).resolve().parents[2]
ARM_RESULT_SCHEMA = json.loads(
    (REPO_ROOT / "registry/schemas/arm_result.schema.json").read_text(encoding="utf-8")
)

DIGEST = "sha256:" + "a" * 64

# Ba cửa sổ test THẬT của sơ đồ fold neo gốc (folds.py:174-185) với
# t1 = 2025-06-12, train 12 tuần, 3 × test 7 tuần.
CUA_SO_TEST = [
    (date(2025, 9, 4), date(2025, 10, 23)),
    (date(2025, 10, 23), date(2025, 12, 11)),
    (date(2025, 12, 11), date(2026, 1, 29)),
]
CUA_SO_TOAN = (date(2025, 6, 12), date(2026, 1, 29))


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


def _chi_so(**ghi_de: Measured[Any]) -> dict[str, Measured[Any]]:
    base = {ten: Measured.ok(0.25) for ten in sorted(CHI_SO_BAT_BUOC)}
    base.update(ghi_de)
    return base


def _ban_ghi(
    *,
    arm: str = "Z0-T1",
    n_phan_quyet: int = 131,
    n_mo_ta: int = 206,
    ket_cuc: Measured[str] | None = None,
    **kw: Any,
) -> dict[str, Any]:
    return build_arm_record(
        arm=arm,
        huong="LONG",
        n_phan_quyet=n_phan_quyet,
        n_mo_ta=n_mo_ta,
        cua_so_phan_quyet=CUA_SO_TEST,
        cua_so_mo_ta=CUA_SO_TOAN,
        chi_so=_chi_so(),
        ket_cuc=ket_cuc if ket_cuc is not None else Measured.ok("PASS"),
        provenance=_prov(),
        trial_id="D-0006",
        **kw,
    )


class TestDauRaThatKhopSchema:
    """🔴 Đối chiếu ĐẦU RA THẬT của `build_arm_record()` với schema."""

    def test_ban_ghi_arm_phan_quyet_khop_schema(self) -> None:
        jsonschema.validate(_ban_ghi(), ARM_RESULT_SCHEMA)

    def test_ban_ghi_arm_mo_ta_khop_schema(self) -> None:
        jsonschema.validate(
            _ban_ghi(arm="Z0", ket_cuc=Measured.ok("INCONCLUSIVE")), ARM_RESULT_SCHEMA
        )

    def test_chi_so_chua_do_duoc_van_khop_schema(self) -> None:
        """`pending`/`unreadable` là trạng thái THẬT, không phải lỗi (N6)."""
        ban = build_arm_record(
            arm="Z1",
            huong="LONG",
            n_phan_quyet=5,
            n_mo_ta=8,
            cua_so_phan_quyet=CUA_SO_TEST,
            cua_so_mo_ta=CUA_SO_TOAN,
            chi_so=_chi_so(dsr_adj=Measured.unreadable("n < 2")),
            ket_cuc=Measured.unreadable("mẫu quá mỏng"),
            provenance=_prov(),
        )
        jsonschema.validate(ban, ARM_RESULT_SCHEMA)


class TestHaiConSoNLaBAT_BUOC:
    """`MT-36` — thiếu một trong hai là bản ghi KHÔNG BIỂU DIỄN ĐƯỢC."""

    @pytest.mark.parametrize("thieu", ["n_phan_quyet", "n_mo_ta"])
    def test_thieu_mot_con_so_n_thi_schema_TU_CHOI(self, thieu: str) -> None:
        ban = _ban_ghi()
        del ban[thieu]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(ban, ARM_RESULT_SCHEMA)

    @pytest.mark.parametrize("thieu", ["n_phan_quyet", "n_mo_ta"])
    def test_thieu_mot_con_so_n_thi_validate_BAO_DO(self, thieu: str) -> None:
        ban = _ban_ghi()
        del ban[thieu]
        assert any(thieu in e for e in validate_arm_record(ban))

    def test_n_phan_quyet_LON_HON_n_mo_ta_thi_BI_TU_CHOI(self) -> None:
        """Đoạn test là TẬP CON của toàn cửa sổ. Vi phạm ⇒ hai con số đến từ
        hai phép đếm khác nhau, và khi đó CẢ HAI đều không đọc được."""
        with pytest.raises(ArmRecordError, match="TẬP CON"):
            _ban_ghi(n_phan_quyet=206, n_mo_ta=131)
        # và validator bắt được cả bản ghi sửa tay
        ban = _ban_ghi()
        ban["n_phan_quyet"], ban["n_mo_ta"] = 206, 131
        assert any("TẬP CON" in e for e in validate_arm_record(ban))

    def test_bang_nhau_thi_HOP_LE(self) -> None:
        """Không cấm — chỉ cấm test > toàn cửa sổ."""
        assert validate_arm_record(_ban_ghi(n_phan_quyet=206, n_mo_ta=206)) == []

    def test_cua_so_phan_quyet_rong_thi_BI_TU_CHOI(self) -> None:
        """`n_phan_quyet` không có nguồn thì nó chỉ là một con số được KHAI."""
        with pytest.raises(ArmRecordError, match="cua_so_phan_quyet rỗng"):
            build_arm_record(
                arm="Z0-T1",
                huong="LONG",
                n_phan_quyet=131,
                n_mo_ta=206,
                cua_so_phan_quyet=[],
                cua_so_mo_ta=CUA_SO_TOAN,
                chi_so=_chi_so(),
                ket_cuc=Measured.ok("PASS"),
                provenance=_prov(),
            )


class TestCoPhamViKhongTuSuyTuN:
    """`DR-D4-10` §8 chặng (a): cờ gán theo §2.1, KHÔNG để bộ đọc tự suy từ `n`."""

    def test_chi_Z0_T1_mua_phan_quyet(self) -> None:
        assert ARM_MUA_PHAN_QUYET == {"Z0-T1"}
        assert pham_vi_theo_arm("Z0-T1") == "phan_quyet"
        for arm in sorted(ARM_NHOM_C | {"Z0-T0"}):
            assert pham_vi_theo_arm(arm) == "mo_ta", arm

    def test_bo_dung_KHONG_NHAN_co_phan_quyet_lam_tham_so(self) -> None:
        """Khuôn `TD-0127`: một tham số không tồn tại thì không ai truyền
        vào được. Khai sai cờ là KHÔNG BIỂU DIỄN ĐƯỢC ở đường này."""
        with pytest.raises(TypeError):
            _ban_ghi(pham_vi_phan_quyet="phan_quyet")  # type: ignore[arg-type]

    def test_arm_nhom_C_khai_phan_quyet_thi_BAO_DO(self) -> None:
        """Đúng thứ `DR-D4-10` §2.2 sinh ra để chặn — nhóm C đã được khai
        INCONCLUSIVE NGAY TẠI DR."""
        ban = _ban_ghi(arm="Z3", ket_cuc=Measured.ok("INCONCLUSIVE"))
        ban["pham_vi_phan_quyet"] = "phan_quyet"
        loi = validate_arm_record(ban)
        assert any("§2.2" in e for e in loi), loi

    def test_Z0_T0_khai_phan_quyet_thi_BAO_DO(self) -> None:
        """`MT-26` (C) hạ `Z0-T0` xuống arm CHẨN ĐOÁN — suất của nó không mua
        một phán quyết Nhánh 1, dù nó có nhiều lệnh nhất (883)."""
        ban = _ban_ghi(arm="Z0-T0", ket_cuc=Measured.ok("INCONCLUSIVE"))
        ban["pham_vi_phan_quyet"] = "phan_quyet"
        assert any("phan_quyet" in e for e in validate_arm_record(ban))

    def test_arm_ngoai_chin_cau_hinh_bi_TU_CHOI(self) -> None:
        with pytest.raises(ArmRecordError, match="Z0-T2"):
            pham_vi_theo_arm("Z0-T2")


class TestKetCucVaChiSo:
    def test_arm_mo_ta_mang_PASS_thi_BI_CHAN_O_CA_HAI_CHO(self) -> None:
        """Suất `mo_ta` không mua một phán quyết — `DR-D4-10` §2.3 cấm đọc
        `DSR_adj` của nhóm C như một phán quyết.

        Kiểm CẢ HAI chiều: bộ dựng tự raise (không dựng nổi), và validator
        bắt được bản ghi đã bị SỬA TAY sau khi dựng — vì sổ trên đĩa sửa tay
        được, cửa ghi không phải đường duy nhất tới file (bài học TD-0124)."""
        with pytest.raises(ArmRecordError, match="KHÔNG mua một phán quyết"):
            _ban_ghi(arm="Z2", ket_cuc=Measured.ok("PASS"))
        ban = _ban_ghi(arm="Z2", ket_cuc=Measured.ok("INCONCLUSIVE"))
        ban["ket_cuc"]["value"] = "PASS"
        assert any("KHÔNG mua một phán quyết" in e for e in validate_arm_record(ban))

    def test_ket_cuc_ngoai_ba_gia_tri_bi_BAO_DO(self) -> None:
        ban = _ban_ghi()
        ban["ket_cuc"] = {"status": "ok", "value": "TAM_ON", "note": None}
        assert any("TAM_ON" in e for e in validate_arm_record(ban))

    @pytest.mark.parametrize("thieu", sorted(CHI_SO_BAT_BUOC))
    def test_thieu_mot_chi_so_bat_buoc_thi_BAO_DO(self, thieu: str) -> None:
        """`DR-D4-09` §2.3: *thiếu một ⇒ bản ghi kết quả không hợp lệ*."""
        ban = _ban_ghi()
        del ban["chi_so"][thieu]
        assert any(thieu in e for e in validate_arm_record(ban))

    def test_chi_so_pending_ma_van_mang_value_thi_BAO_DO(self) -> None:
        ban = _ban_ghi()
        ban["chi_so"]["dsr_adj"] = {"status": "pending", "value": 0.0, "note": None}
        assert any("cấm hiện số cũ" in e for e in validate_arm_record(ban))


class TestXuatXuTamKhoaLaBAT_BUOC:
    """Khác `fold_record.schema.json`: ở đây khoá thứ 8 KHÔNG nhận null. Một
    bản ghi phán quyết D4 mà không truy được ảnh Docker nào sinh ra nó thì
    không đáng tồn tại."""

    def test_digest_null_thi_schema_TU_CHOI(self) -> None:
        ban = _ban_ghi()
        ban["provenance"]["runtime_image_digest"] = None
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(ban, ARM_RESULT_SCHEMA)

    def test_digest_null_thi_validate_BAO_DO(self) -> None:
        ban = _ban_ghi()
        ban["provenance"]["runtime_image_digest"] = None
        assert any("runtime_image_digest" in e for e in validate_arm_record(ban))

    def test_bo_dung_TU_RAISE_khi_thieu_digest(self) -> None:
        prov = Provenance(
            params_source="yaml",
            params_effective={},
            git_sha="deadbeef",
            reproducible_from_sha=True,
            data_hashes={},
            cache_mode="none",
            guard_passed=True,
        )
        with pytest.raises(ArmRecordError, match="runtime_image_digest"):
            build_arm_record(
                arm="Z0-T1",
                huong="LONG",
                n_phan_quyet=131,
                n_mo_ta=206,
                cua_so_phan_quyet=CUA_SO_TEST,
                cua_so_mo_ta=CUA_SO_TOAN,
                chi_so=_chi_so(),
                ket_cuc=Measured.ok("PASS"),
                provenance=prov,
            )


class TestSchemaKhongNhanKhoaLa:
    def test_khoa_la_bi_TU_CHOI(self) -> None:
        """`additionalProperties: false` — thêm khoá vào code mà quên thêm vào
        schema sẽ NỔ ở đây, không phải ở lần ghi thật đầu tiên."""
        ban = _ban_ghi()
        ban["khoa_moi_chua_khai"] = 1
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(ban, ARM_RESULT_SCHEMA)

    def test_dataset_chi_nhan_WFO(self) -> None:
        """`DR-D4-09` §1.1: ablation chạy trên WFO, *không phải toàn bộ
        [T0,T2]*. Danh sách CHO PHÉP một phần tử — nới nó là một quyết định."""
        ban = _ban_ghi()
        ban["dataset"] = "CALIB"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(ban, ARM_RESULT_SCHEMA)
