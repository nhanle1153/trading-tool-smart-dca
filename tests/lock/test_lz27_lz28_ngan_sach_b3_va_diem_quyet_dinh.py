"""TD-0127 — L-Z27 (trần B3 + cấm tăng bằng tay) và L-Z28 (đổi tham số
phải rơi ĐÚNG vào điểm quyết định).

Spec §12d.4 dòng 4871-4874:
  L-Z27 — B3 ≤ 20 tại mọi thời điểm; B3 chỉ tăng theo công thức
          floor(lệnh_mới / 25), không tăng bằng tay
  L-Z28 — Không có thay đổi tham số nào xảy ra giữa hai điểm quyết định
          (trừ DR-012 Hạng 1 — sửa lỗi)

🔑 PHẠM VI (chủ dự án chốt 07/09/2026): Tool D **chưa chạy lệnh live nào**,
mà cả hai luật đều đo bằng SỐ LỆNH ĐÃ ĐÓNG (§12c.1: điểm quyết định = mỗi
100 lệnh đóng; §12c.2: +1 trial / 25 lệnh). Nên đợt này làm phần đo được:

  • L-Z27 làm được TRỌN VẸN ngay, và phần mạnh nhất không phải phép kiểm
    mà là **làm cho "tăng bằng tay" KHÔNG BIỂU DIỄN ĐƯỢC**: API sổ trial
    không còn nhận một con số ngân sách nào từ người gọi, chỉ nhận SỐ LỆNH
    rồi tự áp công thức. Cùng thủ pháp `luan_diem` của TD-0125: câu không
    trích được số thì không viết ra được.
  • L-Z28 chỉ kiểm được phần "có chứng minh được hợp lệ không". Chưa có
    đánh số điểm quyết định → một đề xuất đã APPLIED mà không chứng minh
    được là **BÁO ĐỎ**, không phải im lặng cho qua (fail-closed).

🔎 DR-012 Hạng 1 (ngoại lệ của L-Z28) KHÔNG cần trường khai nào: §12c.4
định nghĩa Hạng 1 là *"code không làm đúng như spec mô tả"* — đó là LỖI,
sửa tự do 0 trial, **không phải đổi tham số**, nên nó không bao giờ đi vào
`param_change_proposals.jsonl` (sổ này dành cho Hạng 2). Ngoại lệ tự nó đã
nằm ngoài phạm vi sổ; bịa thêm một ô "đây là sửa lỗi" chỉ tạo đúng cái cửa
mà L-Z28 sinh ra để đóng.
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

from tool_d.ledger import budget as _budget
from tool_d.ledger.audit_checks import (
    check_lz27_tran_b3,
    check_lz28_doi_tham_so_dung_diem_quyet_dinh,
)
from tool_d.ledger.registry import TrialLedger

B3_TRAN = 20


def _prov() -> dict:
    return {
        "params_source": "yaml",
        "params_effective": {},
        "git_sha": "a" * 40,
        "reproducible_from_sha": True,
        "data_hashes": {},
        "cache_mode": "none",
        "guard_passed": True,
    }


def _kw(**overrides) -> dict:
    kwargs = dict(
        n_dang_ky=114,
        budget_line="B3",
        hypothesis_slot="A-03",
        direction="LONG",
        dataset="CALIB",
        param_under_test="zss_threshold",
        param_value=0.55,
        params_frozen_hash="fh",
        config_hash="ch",
        code_commit="abc123",
        provenance=_prov(),
        contribution=1,
    )
    kwargs.update(overrides)
    return kwargs


# ── L-Z27 phần 1: công thức tái sinh ─────────────────────────────────


class TestCongThucTaiSinh:
    @pytest.mark.parametrize(
        "so_lenh, mong_doi",
        [
            (0, 0),  # chưa có lệnh nào → không có ngân sách mới
            (24, 0),  # chưa đủ 25 → vẫn 0, floor chứ không làm tròn
            (25, 1),
            (99, 3),  # floor(99/25)
            (100, 4),  # đúng "mỗi điểm quyết định có 4 trial" (§12c.2)
            (500, B3_TRAN),  # chạm trần
            (10_000, B3_TRAN),  # 🔒 trần TÍCH LUỸ: không để dành 3 năm rồi tiêu một lúc
        ],
    )
    def test_floor_25_va_chan_tran_20(self, so_lenh: int, mong_doi: int) -> None:
        assert _budget.b3_tai_sinh(so_lenh) == mong_doi

    def test_so_lenh_am_bi_tu_choi(self) -> None:
        """Số lệnh âm là vô nghĩa — thà nổ còn hơn sinh ngân sách lạ."""
        with pytest.raises(ValueError):
            _budget.b3_tai_sinh(-1)


# ── L-Z27 phần 2: KHÔNG CÓ ĐƯỜNG tăng bằng tay ───────────────────────


class TestKhongTheTangBangTay:
    """Phần mạnh nhất của L-Z27 — kiểm bằng AST/chữ ký, không phải bằng
    một phép kiểm chạy lúc audit. Một phép kiểm có thể bị bỏ qua; một
    tham số KHÔNG TỒN TẠI thì không ai truyền vào được."""

    @pytest.mark.parametrize("ten_ham", ["available", "reserve"])
    def test_api_so_trial_khong_nhan_so_ngan_sach_nao(self, ten_ham: str) -> None:
        tham_so = set(inspect.signature(getattr(TrialLedger, ten_ham)).parameters)

        assert "n_tai_sinh" not in tham_so, (
            f"TrialLedger.{ten_ham}() vẫn nhận `n_tai_sinh` — đó chính là "
            "đường 'tăng B3 bằng tay' mà L-Z27 cấm (spec dòng 4956)"
        )
        assert "so_lenh_da_dong" in tham_so, (
            f"TrialLedger.{ten_ham}() phải nhận SỐ LỆNH rồi tự áp công thức, "
            "không nhận thẳng một con số ngân sách"
        )

    def test_khong_file_nguon_nao_tu_cong_them_vao_b3(self) -> None:
        """Quét AST: không nơi nào trong `src/` gọi `b3_tai_sinh` với một
        hằng số — nghĩa là ngân sách luôn suy từ số lệnh thật, không ai
        viết thẳng `b3_tai_sinh(500)` để mở trần."""
        goc = Path(__file__).resolve().parents[2] / "src"
        vi_pham: list[str] = []
        for f in goc.rglob("*.py"):
            cay = ast.parse(f.read_text(encoding="utf-8"))
            for node in ast.walk(cay):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "b3_tai_sinh"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                ):
                    vi_pham.append(f"{f.name}:{node.lineno}")
        assert not vi_pham, f"b3_tai_sinh() bị gọi với hằng số tại {vi_pham}"


# ── L-Z27 phần 3: phép kiểm lúc audit ────────────────────────────────


class TestPhepKiemTranB3:
    def test_so_rong_thi_chua_do_duoc(self, tmp_path: Path) -> None:
        kq = check_lz27_tran_b3(tmp_path / "reg.jsonl")

        assert kq.code == "L-Z27"
        assert not kq.measured.is_ok()

    def test_b3_trong_tran_thi_dat(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)
        for _ in range(3):
            ledger.seal(ledger.reserve(**_kw()), seal_path="runs/td/metrics.seal")

        assert check_lz27_tran_b3(reg).ok

    def test_b3_vuot_tran_thi_bao_do(self, tmp_path: Path) -> None:
        """Chưa có lệnh live → tái sinh = 0 → trần vẫn đúng 20."""
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)
        for _ in range(B3_TRAN + 1):
            ledger.seal(ledger.reserve(**_kw(n_dang_ky=200)), seal_path="runs/td/metrics.seal")

        assert check_lz27_tran_b3(reg).is_fail

    def test_dong_khong_phai_b3_khong_bi_dem_vao_tran(self, tmp_path: Path) -> None:
        """Trần B3 áp lên pool tái sinh, không áp lên B1/B2 (spec 3488)."""
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)
        for _ in range(B3_TRAN + 5):
            ledger.seal(
                ledger.reserve(**_kw(budget_line="B1", n_dang_ky=200)), seal_path="runs/td/metrics.seal"
            )

        assert check_lz27_tran_b3(reg).ok

    def test_co_lenh_live_thi_tran_noi_theo_dung_cong_thuc(self, tmp_path: Path) -> None:
        """25 lệnh đóng → trần thành 21, dòng thứ 21 hết vi phạm."""
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)
        for _ in range(B3_TRAN + 1):
            ledger.seal(ledger.reserve(**_kw(n_dang_ky=200)), seal_path="runs/td/metrics.seal")

        assert check_lz27_tran_b3(reg).is_fail
        assert check_lz27_tran_b3(reg, so_lenh_da_dong=25).ok


# ── L-Z28 ────────────────────────────────────────────────────────────


def _de_xuat(**overrides) -> dict:
    e = {
        "de_xuat_id": "PC-0001",
        "created_at": "2026-09-07T10:00:00Z",
        "source": "HUMAN",
        "bao_cao_path": "reports/x.md",
        "bao_cao_hash": "0" * 64,
        "nguon_kich_hoat": "HEALTH",
        "tham_so_tro_toi": "tier_b.buf_sl_atr_mult",
        "cap_tham_so": "B",
        "tu_khai_hang": 2,
        "luan_diem": [],
        "gia_tri_hien_tai": 1.0,
        "gia_tri_de_xuat": 1.2,
        "trial_id": None,
        "status": "PROPOSED",
    }
    e.update(overrides)
    return e


def _ghi(path: Path, *dong: dict) -> Path:
    path.write_text(
        "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in dong), encoding="utf-8"
    )
    return path


class TestLz28DiemQuyetDinh:
    def test_so_rong_thi_chua_do_duoc(self, tmp_path: Path) -> None:
        kq = check_lz28_doi_tham_so_dung_diem_quyet_dinh(tmp_path / "pc.jsonl")

        assert kq.code == "L-Z28"
        assert not kq.measured.is_ok()

    def test_chi_co_de_xuat_chua_ap_dung_thi_chua_do_duoc(self, tmp_path: Path) -> None:
        """PROPOSED chưa đổi gì cả — chưa có gì để kiểm, KHÔNG phải 'đạt'."""
        so = _ghi(tmp_path / "pc.jsonl", _de_xuat(status="PROPOSED"))

        assert not check_lz28_doi_tham_so_dung_diem_quyet_dinh(so).measured.is_ok()

    def test_da_ap_dung_ma_khong_chung_minh_duoc_thi_bao_do(self, tmp_path: Path) -> None:
        """🔴 Chốt của chủ dự án: không chứng minh được hợp lệ = BÁO ĐỎ.
        Im lặng cho qua ở đây nghĩa là tham số đã đổi thật trên tiền thật
        mà không ai kiểm được nó có đúng lúc không."""
        so = _ghi(tmp_path / "pc.jsonl", _de_xuat(status="APPLIED", trial_id="D-0001"))

        kq = check_lz28_doi_tham_so_dung_diem_quyet_dinh(so)

        assert kq.is_fail
        assert not kq.ok

    def test_da_ap_dung_va_dung_diem_quyet_dinh_thi_dat(self, tmp_path: Path) -> None:
        """100 lệnh đóng = điểm quyết định #1 (§12c.1)."""
        so = _ghi(tmp_path / "pc.jsonl", _de_xuat(status="APPLIED", trial_id="D-0001"))

        assert check_lz28_doi_tham_so_dung_diem_quyet_dinh(so, so_lenh_da_dong=100).ok

    def test_da_ap_dung_giua_hai_diem_quyet_dinh_thi_bao_do(self, tmp_path: Path) -> None:
        """137 lệnh: điểm quyết định gần nhất là 100, còn 37 lệnh nữa mới
        tới điểm kế. Đổi tham số lúc này là đổi GIỮA hai điểm — đúng thứ
        L-Z28 cấm (spec dòng 4952)."""
        so = _ghi(tmp_path / "pc.jsonl", _de_xuat(status="APPLIED", trial_id="D-0001"))

        assert check_lz28_doi_tham_so_dung_diem_quyet_dinh(so, so_lenh_da_dong=137).is_fail

    def test_chua_toi_diem_quyet_dinh_dau_tien_thi_bao_do(self, tmp_path: Path) -> None:
        """Dưới 100 lệnh thì chưa có điểm quyết định nào — không được đổi."""
        so = _ghi(tmp_path / "pc.jsonl", _de_xuat(status="APPLIED", trial_id="D-0001"))

        assert check_lz28_doi_tham_so_dung_diem_quyet_dinh(so, so_lenh_da_dong=99).is_fail
