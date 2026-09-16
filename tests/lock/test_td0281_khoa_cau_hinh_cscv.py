"""🔒 TD-0281 — khoá cấu hình CSCV của D9 (`tier_c.cscv`, `DR-D9-01` §4.5).

Canh ba thứ, đừng gộp:

1. **YAML thật + DR thật khớp nhau** (`TestThat`) — sửa `so_khoi` trong YAML mà
   quên DR, hay sửa khối DR mà quên băm ⇒ đỏ trước khi một tổ hợp nào được tính.
2. **Từng nhánh từ chối có răng** (`TestTuChoi`) — dựng cấu hình/DR hỏng bằng TAY.
   Chỉ test qua file thật thì mọi `raise` xanh mà chưa bao giờ chạy (PASS RỖNG).
3. **Không đụng kế toán `N`** (`TestBatBien`) — `cscv` sống ở `tier_c`, không vào
   `tier_b`; `N = 114`, rào DSR 3,0777 không đổi.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from pathlib import Path
from types import MappingProxyType

import pytest

from tool_d.calibration.ung_vien import bam_chuan_hoa
from tool_d.config.loader import ToolDConfig, load_tool_d_config
from tool_d.gates import cscv_cau_hinh
from tool_d.gates.cscv_cau_hinh import (
    DEFAULT_DR_D9_01_PATH,
    CSCVCauHinhError,
    doc_cau_hinh_cscv,
    doc_khoi_dr,
)
from tool_d.gates.dsr import N_DANG_KY, dsr_hurdle

REPO_ROOT = Path(__file__).resolve().parents[2]
DR_THAT = REPO_ROOT / DEFAULT_DR_D9_01_PATH
CFG_THAT = REPO_ROOT / "config" / "tool_d_config.yaml"


def _cfg(*, cscv: dict | None = None, bo_cscv: bool = False, san: int = 30) -> ToolDConfig:
    tier_c: dict = {
        "data_split": MappingProxyType(
            {"t0": "2024-04-09", "t1": "2025-06-12", "t2": "2026-01-29", "t3": "2026-09-06"}
        ),
        "wfo_folds": MappingProxyType(
            {"so_fold": 3, "train_khoi_tao_tuan": 12, "test_tuan": 7, "san_lenh_moi_fold": san}
        ),
    }
    if not bo_cscv:
        tier_c["cscv"] = MappingProxyType(cscv if cscv is not None else {"so_khoi": 8})
    trong = MappingProxyType({})
    return ToolDConfig(
        tier_a=trong, tier_b=trong, tier_frozen=trong, tier_c=MappingProxyType(tier_c), raw_text="", sha256=""
    )


def _dr_gia(tmp_path: Path, *, sua_khoi=None, sua_bam: str | None = None) -> Path:
    """Chép DR thật, sửa khối JSON (và TÍNH LẠI băm cho khớp) hoặc sửa riêng băm."""
    text = DR_THAT.read_text(encoding="utf-8")
    obj, bam = doc_khoi_dr(DR_THAT)
    if sua_khoi is not None:
        import json

        cu = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        sua_khoi(obj)
        moi = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        assert cu in text
        text = text.replace(cu, moi).replace(bam, bam_chuan_hoa(obj))
    if sua_bam is not None:
        text = text.replace(bam, sua_bam)
    p = tmp_path / "DR-D9-01.md"
    p.write_text(text, encoding="utf-8")
    return p


class TestThat:
    def test_yaml_that_khop_dr_that(self) -> None:
        ch = doc_cau_hinh_cscv(load_tool_d_config(CFG_THAT), dr_path=DR_THAT)
        assert ch.so_khoi == 8
        assert ch.do_dai_khoi == timedelta(hours=693)
        assert ch.san_lenh_moi_nua == 30
        assert ch.pbo_max == 0.5
        assert ch.bam_dr == "7f8c5ff03bd2b8aefa997d8ea9ac382690d13f0b105908c727cd4c1a933260bb"

    def test_moc_khoi_phu_kin_cua_so_wfo(self) -> None:
        ch = doc_cau_hinh_cscv(load_tool_d_config(CFG_THAT), dr_path=DR_THAT)
        moc = ch.moc_khoi()
        assert len(moc) == 9
        assert moc[0] == datetime(2025, 6, 12) and moc[-1] == datetime(2026, 1, 29)
        assert moc[3] == datetime(2025, 9, 6, 15)  # chép từ DR-D9-01 §4.1, không tính lại


class TestTuChoi:
    def test_thieu_khoi_cscv(self) -> None:
        with pytest.raises(CSCVCauHinhError, match="tier_c.cscv"):
            doc_cau_hinh_cscv(_cfg(bo_cscv=True), dr_path=DR_THAT)

    def test_thieu_so_khoi(self) -> None:
        with pytest.raises(CSCVCauHinhError, match="so_khoi"):
            doc_cau_hinh_cscv(_cfg(cscv={}), dr_path=DR_THAT)

    def test_khoa_la(self) -> None:
        with pytest.raises(CSCVCauHinhError, match="ngoài DR-D9-01"):
            doc_cau_hinh_cscv(_cfg(cscv={"so_khoi": 8, "san_lenh": 20}), dr_path=DR_THAT)

    @pytest.mark.parametrize("xau", [0, -8, 8.0, "8", True])
    def test_so_khoi_khong_phai_so_nguyen_duong(self, xau) -> None:
        with pytest.raises(CSCVCauHinhError):
            doc_cau_hinh_cscv(_cfg(cscv={"so_khoi": xau}), dr_path=DR_THAT)

    def test_so_khoi_le(self) -> None:
        with pytest.raises(CSCVCauHinhError, match="chẵn"):
            doc_cau_hinh_cscv(_cfg(cscv={"so_khoi": 7}), dr_path=DR_THAT)

    def test_yaml_lech_dr(self) -> None:
        """16 chẵn, hợp lệ về hình dạng — chỉ sai vì DR niêm phong 8."""
        with pytest.raises(CSCVCauHinhError, match="≠ DR-D9-01"):
            doc_cau_hinh_cscv(_cfg(cscv={"so_khoi": 16}), dr_path=DR_THAT)

    def test_khoi_dr_sua_ma_khong_sua_bam(self, tmp_path: Path) -> None:
        dr = _dr_gia(tmp_path, sua_bam="0" * 64)
        with pytest.raises(CSCVCauHinhError, match="BĂM LỆCH"):
            doc_cau_hinh_cscv(_cfg(), dr_path=dr)

    def test_do_dai_khoi_khong_phu_kin_cua_so(self, tmp_path: Path) -> None:
        """DR sửa khớp băm nhưng 8 × 700 giờ ≠ 5544 giờ — không tự co khối."""
        dr = _dr_gia(tmp_path, sua_khoi=lambda o: o["cscv"].__setitem__("do_dai_khoi_gio", 700))
        with pytest.raises(CSCVCauHinhError, match="không tự co"):
            doc_cau_hinh_cscv(_cfg(), dr_path=dr)

    def test_nguon_san_khac(self, tmp_path: Path) -> None:
        dr = _dr_gia(tmp_path, sua_khoi=lambda o: o["cscv"].__setitem__("san_lenh_moi_nua", "tier_c.cscv.san"))
        with pytest.raises(CSCVCauHinhError, match="nguồn sàn"):
            doc_cau_hinh_cscv(_cfg(), dr_path=dr)

    def test_pbo_max_code_lech_dr(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(cscv_cau_hinh, "PBO_MAX", 0.6)
        with pytest.raises(CSCVCauHinhError, match="PBO_MAX"):
            doc_cau_hinh_cscv(_cfg(), dr_path=DR_THAT)

    def test_san_doc_tu_wfo_folds_khong_go_lai(self) -> None:
        """Đổi sàn ở `wfo_folds` ⇒ cấu hình CSCV đổi theo: chứng minh nó ĐỌC, không chép 30."""
        assert doc_cau_hinh_cscv(_cfg(san=45), dr_path=DR_THAT).san_lenh_moi_nua == 45

    def test_dr_khong_ton_tai(self, tmp_path: Path) -> None:
        with pytest.raises(CSCVCauHinhError, match="không đọc được"):
            doc_cau_hinh_cscv(_cfg(), dr_path=tmp_path / "khong-co.md")


class TestBatBien:
    def test_cscv_khong_nam_trong_tier_b(self) -> None:
        cfg = load_tool_d_config(CFG_THAT)
        assert "cscv" in cfg.tier_c
        assert "cscv" not in cfg.tier_b and "so_khoi" not in cfg.tier_b
        # Khoá mở đầu `_` là ghi chú kế toán, không phải tham số (loader._non_underscore_keys).
        assert len([k for k in cfg.tier_b if not k.startswith("_")]) == 12

    def test_n_va_rao_dsr_khong_doi(self) -> None:
        assert N_DANG_KY == 114
        assert math.isclose(dsr_hurdle(N_DANG_KY), 3.0777, abs_tol=5e-5)
