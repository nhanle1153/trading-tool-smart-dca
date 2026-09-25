"""TD-0419 — script tạo thư mục phiên IDEA/CHỌN sạch (`tool_d.ops.phien_sach`, `scripts/tao_phien_sach.py`).

Thứ phải đúng:
  • trích spec theo MỐC TIÊU ĐỀ, mốc thiếu/trùng ⇒ từ chối;
  • hàng chờ RÚT GỌN chỉ giữ trường đối chiếu trùng — bài học `MT-77`: bản đầy đủ lẫn số đo Tool D;
  • dò `mau_cam` có răng TRÊN DỮ LIỆU THẬT: sổ ý tưởng đầy đủ của repo phải bị bắt, bản rút gọn phải sạch;
  • dính vi phạm ⇒ KHÔNG ghi gì ở đích; đích đã tồn tại ⇒ từ chối; file khai mà thiếu ⇒ từ chối.
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from tool_d.ops.phien_sach import (
    PhienSachError,
    do_vi_pham,
    doc_cau_hinh,
    dung_noi_dung,
    rut_gon_hang_cho,
    tao_phien_sach,
    trich_doan,
)

REPO = Path(__file__).resolve().parents[2]
TIEU_CHI = "docs/decisions/DR-Q4-2026-tieu-chi-chon-y-tuong.md"
NGAY = date(2026, 9, 25)


class TestTrichDoan:
    VB = "a\n## A. mot\nx\ny\n## B. hai\nz"

    def test_trich_dung_doan(self) -> None:
        assert trich_doan(self.VB, "## A.", "## B.") == "## A. mot\nx\ny"

    @pytest.mark.parametrize("bat_dau, ket_thuc", [("## C.", "## B."), ("## A.", "## C."), ("## B.", "## A.")])
    def test_moc_thieu_hoac_sai_thu_tu_thi_tu_choi(self, bat_dau: str, ket_thuc: str) -> None:
        with pytest.raises(PhienSachError, match="mốc tiêu đề"):
            trich_doan(self.VB, bat_dau, ket_thuc)

    def test_moc_trung_thi_tu_choi(self) -> None:
        with pytest.raises(PhienSachError):
            trich_doan(self.VB + "\n## A. lap", "## A.", "## B.")


class TestHangChoRutGon:
    def test_chi_giu_truong_khai(self) -> None:
        dong = json.dumps({"idea_id": "IQ-9", "mechanism": "m", "explore_evidence": "n_giao 22", "so_bien_the": 2})
        ra = json.loads(rut_gon_hang_cho(dong + "\n", ["idea_id", "mechanism", "who_pays"]))
        assert ra == {"idea_id": "IQ-9", "mechanism": "m", "who_pays": None}


class TestDoViPham:
    MAU = doc_cau_hinh(REPO)["mau_cam"]

    @pytest.mark.parametrize("dong", [
        "đã tiêu D-0023", "n_giao = 22", "63,6 lệnh/năm", "expectancy: -0.22", "dsr_adj_exp", "can_duoi âm",
        "mean_r ≥ 0,10", "time_stop_ratio 0.43%", "docs/du-lieu-do/td0193-lenh-nam-explore.json", "KTC95",
        "+0,081%/ngày", "theo DR-ZA-01", "DR-HUONG-01 §3", "DR-PHAN-QUYET-01", "DR-KET-CUC-IQ0003-01",
        "DR-TAI-THIET-KE-01", "DR-D0-IQ0003", "DR-D4-19",
    ])
    def test_moi_mau_bat_duoc_dau_hieu_so_lieu(self, dong: str) -> None:
        assert do_vi_pham("x.md", dong, self.MAU), dong

    @pytest.mark.parametrize("dong", [
        "CẤM đọc `docs/du-lieu-do/**`", "khai `data_source: TOOL_D_RESULTS`", "rào DSR", "`retest_forbidden`",
        "mean-reversion", "DR-IQ-01A", "DR-Q4-2026",
    ])
    def test_chu_thuong_trong_mau_khong_bi_bat_nham(self, dong: str) -> None:
        assert not do_vi_pham("x.md", dong, self.MAU), dong


class TestTrenDuLieuThat:
    def test_so_y_tuong_day_du_cua_repo_BI_BAT_ban_rut_gon_SACH(self) -> None:
        """Có răng trên đúng vụ rò `MT-77`: dòng IQ-0001 bản đầy đủ mang số đo Tool D."""
        cau_hinh = doc_cau_hinh(REPO)
        day_du = (REPO / "registry/idea_queue.jsonl").read_text(encoding="utf-8")
        assert do_vi_pham("idea_queue.jsonl", day_du, cau_hinh["mau_cam"])
        rut_gon = rut_gon_hang_cho(day_du, cau_hinh["hang_cho"]["giu_truong"])
        assert not do_vi_pham("rut_gon", rut_gon, cau_hinh["mau_cam"])

    def test_noi_dung_dung_tu_repo_that_sach_va_mau_da_dien(self) -> None:
        cau_hinh = doc_cau_hinh(REPO)
        nd = dung_noi_dung(REPO, cau_hinh, tieu_chi=TIEU_CHI, dich=Path("C:/tmp/phien"), ngay=NGAY)
        assert {"README.md", "LOI-MO-DAU.md", "idea_queue-rut-gon.jsonl", "spec-trich-dr009-explore-idea-queue.md",
                "DR-Q4-2026-tieu-chi-chon-y-tuong.md", "mau-don-y-tuong.yaml"} <= set(nd)
        for ten, vb in nd.items():
            assert not do_vi_pham(ten, vb, cau_hinh["mau_cam"]), ten
        for ten in ("README.md", "LOI-MO-DAU.md"):
            assert "{ngay}" not in nd[ten] and "{tieu_chi}" not in nd[ten] and "{thu_muc_windows}" not in nd[ten]
        assert "## 📋 DR-009" in nd["spec-trich-dr009-explore-idea-queue.md"]


def _repo_gia(tmp_path: Path, *, chen_so_lieu: bool = False) -> Path:
    repo = tmp_path / "repo"
    for rel in ["docs/phien-sach/cau-hinh.json", "docs/phien-sach/README-mau.md", "docs/phien-sach/LOI-MO-DAU-mau.md",
                "tool-d-smart-dca.md", "registry/idea_queue.jsonl", TIEU_CHI,
                *doc_cau_hinh(REPO)["file_chep"]]:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, repo / rel)
    if chen_so_lieu:
        p = repo / "docs/decisions/DR-IQ-02-so-y-tuong-nhat-ky-su-kien.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nlỡ chép: mean +0,081%/ngày (D-0024)\n", encoding="utf-8")
    return repo


class TestTaoPhienSach:
    def test_tao_duoc_thu_muc_day_du(self, tmp_path: Path) -> None:
        dich, vp = tao_phien_sach(_repo_gia(tmp_path), tieu_chi=TIEU_CHI, dich=tmp_path / "sach", ngay=NGAY)
        assert vp == [] and (dich / "README.md").is_file() and (dich / "idea_queue-rut-gon.jsonl").is_file()

    def test_dinh_so_lieu_thi_dung_va_khong_ghi_gi(self, tmp_path: Path) -> None:
        dich, vp = tao_phien_sach(_repo_gia(tmp_path, chen_so_lieu=True), tieu_chi=TIEU_CHI, dich=tmp_path / "sach",
                                  ngay=NGAY)
        assert vp and {v.file for v in vp} == {"DR-IQ-02-so-y-tuong-nhat-ky-su-kien.md"}
        assert not dich.exists()

    def test_dich_da_ton_tai_thi_tu_choi(self, tmp_path: Path) -> None:
        (tmp_path / "sach").mkdir()
        with pytest.raises(PhienSachError, match="đã tồn tại"):
            tao_phien_sach(_repo_gia(tmp_path), tieu_chi=TIEU_CHI, dich=tmp_path / "sach", ngay=NGAY)

    def test_file_tieu_chi_thieu_thi_tu_choi(self, tmp_path: Path) -> None:
        with pytest.raises(PhienSachError, match="không có"):
            tao_phien_sach(_repo_gia(tmp_path), tieu_chi="docs/decisions/DR-Q9-2099.md", dich=tmp_path / "sach",
                           ngay=NGAY)
