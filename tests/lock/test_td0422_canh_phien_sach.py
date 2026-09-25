"""🔒 TD-0422 — script canh thư mục phiên sạch (`tool_d.ops.canh_phien_sach`, `scripts/canh_phien_sach.py`).

Thứ phải đúng, mỗi thứ chặn một cách hỏng:
  • **Bộ lọc không lọt chữ:** về phiên sạch chỉ có dòng ✅ đầu tiên, hoặc lời 🛑 từ chối — báo cáo kiểm tra sổ in SAU
    dòng ✅ (có thể chứa số Tool D, `DR-009`) không bao giờ được ghi ra; output lạ ⇒ một câu cảnh báo cố định.
  • **Nháp không bị nộp:** chỉ file trong `cho-nop/` đúng tên `don-N.yaml` / `to-chon.yaml`; file đang ghi dở (băm đổi
    giữa hai lần quét) chưa nộp; đã nộp thì không nộp lại (mỗi lần nộp tính vào trần 10 đơn/quý) trừ khi nội dung đổi.
  • **Chọn phải có người gõ `CHON`:** trả lời khác ⇒ không chạy lệnh, sổ không đổi.
  • Thư mục phải là thư mục phiên sạch, và nằm NGOÀI repo.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from tool_d.ops.canh_phien_sach import (
    FILE_KET_QUA,
    KHONG_NHAN_RA,
    CanhPhienSachError,
    Viec,
    doc_da_xu_ly,
    ghi_da_xu_ly,
    kiem_thu_muc,
    lenh_docker,
    loc_ket_qua,
    quet,
    xu_ly,
)

REPO = Path(__file__).resolve().parents[2]
BAO_CAO = "L-Z25 PASS\nTD-0193 expectancy -0.22 mean_r 0.43\n❌ gì đó"


class TestLocKetQua:
    def test_thanh_cong_chi_dong_dau(self) -> None:
        out = f"✅ Đã ghi IQ-0004 vào registry/idea_queue.jsonl.\n{BAO_CAO}\n"
        assert loc_ket_qua(out, 0) == "✅ Đã ghi IQ-0004 vào registry/idea_queue.jsonl."

    def test_thanh_cong_du_audit_ban_van_chi_dong_dau(self) -> None:
        out = f"✅ Đã ghi IQ-0004 SELECTED vào registry/idea_queue.jsonl.\n{BAO_CAO}"
        assert loc_ket_qua(out, 95) == "✅ Đã ghi IQ-0004 SELECTED vào registry/idea_queue.jsonl."

    def test_tu_choi_giu_loi_tu_choi(self) -> None:
        out = "🛑 TỪ CHỐI ghi — sổ KHÔNG bị đụng tới.\nthiếu trường who_pays\n"
        assert loc_ket_qua(out, 96) == out.strip()

    @pytest.mark.parametrize("out, ma", [
        (BAO_CAO, 0), (BAO_CAO, 96), ("", 96), ("", 1), (f"🛑 lạ\n{BAO_CAO}", 1), ("✅ Đã ghi gì đó khác", 0),
    ])
    def test_output_la_thanh_cau_canh_bao_khong_lot_chu(self, out: str, ma: int) -> None:
        kq = loc_ket_qua(out, ma)
        assert kq == KHONG_NHAN_RA.format(ma=ma)
        for cam in ("L-Z", "expectancy", "mean_r", "❌"):
            assert cam not in kq


def _thu_muc(tmp_path: Path) -> Path:
    d = tmp_path / "phien"
    (d / "cho-nop").mkdir(parents=True)
    (d / "README.md").write_text("x", encoding="utf-8")
    (d / "LOI-MO-DAU.md").write_text("x", encoding="utf-8")
    return d


class TestQuet:
    def test_nhap_ngoai_cho_nop_va_ten_la_khong_bi_nop(self, tmp_path: Path) -> None:
        d = _thu_muc(tmp_path)
        (d / "don-1.yaml").write_text("nhap", encoding="utf-8")
        (d / "cho-nop" / "mau-don-y-tuong.yaml").write_text("x", encoding="utf-8")
        (d / "cho-nop" / "don-1.yaml.bak").write_text("x", encoding="utf-8")
        _, bam = quet(d, {}, {})
        viec, _ = quet(d, {}, bam)
        assert viec == [] and bam == {}

    def test_lan_quet_dau_chua_nop_lan_hai_moi_nop(self, tmp_path: Path) -> None:
        d = _thu_muc(tmp_path)
        (d / "cho-nop" / "don-1.yaml").write_text("a", encoding="utf-8")
        viec, bam = quet(d, {}, {})
        assert viec == []
        viec, _ = quet(d, {}, bam)
        assert [v.ten for v in viec] == ["don-1.yaml"]

    def test_dang_ghi_do_chua_nop(self, tmp_path: Path) -> None:
        d = _thu_muc(tmp_path)
        f = d / "cho-nop" / "don-1.yaml"
        f.write_text("a", encoding="utf-8")
        _, bam = quet(d, {}, {})
        f.write_text("ab", encoding="utf-8")
        viec, _ = quet(d, {}, bam)
        assert viec == []

    def test_da_nop_khong_nop_lai_doi_noi_dung_thi_nop(self, tmp_path: Path) -> None:
        d = _thu_muc(tmp_path)
        f = d / "cho-nop" / "don-1.yaml"
        f.write_text("a", encoding="utf-8")
        _, bam = quet(d, {}, {})
        viec, _ = quet(d, {}, bam)
        da = {"don-1.yaml": viec[0].bam}
        assert quet(d, da, bam)[0] == []
        f.write_text("a sua", encoding="utf-8")
        _, bam = quet(d, da, bam)
        assert [v.ten for v in quet(d, da, bam)[0]] == ["don-1.yaml"]

    def test_nop_theo_so_don_chon_sau_cung(self, tmp_path: Path) -> None:
        d = _thu_muc(tmp_path)
        for ten in ("to-chon.yaml", "don-10.yaml", "don-2.yaml"):
            (d / "cho-nop" / ten).write_text(ten, encoding="utf-8")
        _, bam = quet(d, {}, {})
        viec, _ = quet(d, {}, bam)
        assert [v.ten for v in viec] == ["don-2.yaml", "don-10.yaml", "to-chon.yaml"]
        assert [v.la_chon for v in viec] == [False, False, True]

    def test_da_xu_ly_ben_qua_khoi_dong_lai(self, tmp_path: Path) -> None:
        d = _thu_muc(tmp_path)
        ghi_da_xu_ly(d, {"don-1.yaml": "abc"})
        assert doc_da_xu_ly(d) == {"don-1.yaml": "abc"}


class TestXuLy:
    NGAY = staticmethod(lambda: datetime(2026, 9, 25, 10, 0, 0))

    def test_nop_ghi_dong_da_loc_vao_file_ket_qua(self, tmp_path: Path) -> None:
        d = _thu_muc(tmp_path)
        out = f"✅ Đã ghi IQ-0004 vào registry/idea_queue.jsonl.\n{BAO_CAO}"
        kq, da_chay = xu_ly(Viec("don-1.yaml", "h", False), thu_muc=d, chay=lambda v: (out, 0),
                            hoi=lambda s: pytest.fail("nộp không được hỏi"), bay_gio=self.NGAY)
        txt = (d / FILE_KET_QUA).read_text(encoding="utf-8")
        assert da_chay and kq.startswith("✅")
        assert "2026-09-25 10:00:00  don-1.yaml\n✅ Đã ghi IQ-0004" in txt
        for cam in ("L-Z", "expectancy", "mean_r", "❌"):
            assert cam not in txt

    @pytest.mark.parametrize("tra_loi", ["", "y", "Y", "chon", "CHỌN", "yes"])
    def test_chon_khong_go_CHON_thi_khong_chay(self, tmp_path: Path, tra_loi: str) -> None:
        d = _thu_muc(tmp_path)
        kq, da_chay = xu_ly(Viec("to-chon.yaml", "h", True), thu_muc=d,
                            chay=lambda v: pytest.fail("không được chạy lệnh chọn"), hoi=lambda s: tra_loi,
                            bay_gio=self.NGAY)
        assert not da_chay and kq.startswith("⏸")

    def test_chon_go_CHON_thi_chay(self, tmp_path: Path) -> None:
        d = _thu_muc(tmp_path)
        goi: list[Viec] = []

        def chay(v: Viec) -> tuple[str, int]:
            goi.append(v)
            return "✅ Đã ghi IQ-0004 SELECTED vào registry/idea_queue.jsonl.\n", 0

        kq, da_chay = xu_ly(Viec("to-chon.yaml", "h", True), thu_muc=d, chay=chay, hoi=lambda s: " CHON ",
                            bay_gio=self.NGAY)
        assert da_chay and len(goi) == 1 and "SELECTED" in kq


class TestLenhVaThuMuc:
    def test_lenh_nop_va_chon_tro_dung_file_trong_cho_nop(self, tmp_path: Path) -> None:
        nop = lenh_docker(REPO, tmp_path, Viec("don-3.yaml", "h", False))
        chon = lenh_docker(REPO, tmp_path, Viec("to-chon.yaml", "h", True))
        assert nop[-2:] == ["--nop-y-tuong", "/don/cho-nop/don-3.yaml"]
        assert chon[-2:] == ["--chon-y-tuong", "/don/cho-nop/to-chon.yaml"]
        assert f"{tmp_path}:/don:ro" in nop and "entrypoints/trial_ledger_audit.py" in nop

    def test_thu_muc_khong_phai_phien_sach_bi_tu_choi(self, tmp_path: Path) -> None:
        with pytest.raises(CanhPhienSachError, match="không phải"):
            kiem_thu_muc(tmp_path, REPO)

    def test_thu_muc_trong_repo_bi_tu_choi(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        d = _thu_muc(repo)
        with pytest.raises(CanhPhienSachError, match="trong repo"):
            kiem_thu_muc(d, repo)

    def test_thu_muc_hop_le(self, tmp_path: Path) -> None:
        d = _thu_muc(tmp_path)
        assert kiem_thu_muc(d, REPO) == d.resolve()

    def test_mau_loi_mo_dau_huong_dan_bat_script_canh(self) -> None:
        txt = (REPO / "docs/phien-sach/LOI-MO-DAU-mau.md").read_text(encoding="utf-8")
        assert "scripts/canh_phien_sach.py --thu-muc" in txt and "cho-nop" in txt
