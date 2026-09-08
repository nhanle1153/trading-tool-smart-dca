"""TD-0166 — `close_d3_5_gate()` (E6 `--close-d3-5-gate`).

Kế thừa toàn bộ ba bài học của lần đóng cổng D3 (08/09/2026): tự chạy
pytest THẬT, kiểm cây làm việc, chạy RIÊNG từng file test cốt lõi.

🔴 **Điểm khác biệt lớn nhất, và là thứ bộ test này canh chặt nhất:** cổng
D3.5 gọi `kiem_cong_d35()` — CHÍNH cái máy mà E3 dùng để TỪ CHỐI chạy
ablation. Điều kiện đóng cổng và điều kiện cho phép chạy ablation vì thế
là **MỘT**, không phải hai danh sách song song sẽ trôi lệch nhau. Nếu
chúng tách đôi thì sẽ có lúc "cổng D3.5 đã đóng" mà E3 vẫn từ chối chạy —
và không ai biết bên nào đúng.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

import trial_ledger_audit  # noqa: E402
from trial_ledger_audit import (  # noqa: E402
    DUONG_DAN_TEST_D3_5,
    EXIT_GATE_ALREADY_CLOSED,
    EXIT_GATE_AUDIT_DIRTY,
    close_d3_5_gate,
)

PASS_CMD = [sys.executable, "-c", "print('1100 passed in 300.0s')"]
FAIL_CMD = [sys.executable, "-c", "print('1 failed, 1099 passed'); import sys; sys.exit(1)"]
D35_PASS = [sys.executable, "-c", "import sys; print('14 passed in 3.0s')", "--"]
D35_FAIL = [sys.executable, "-c", "import sys; print('2 failed, 12 passed'); sys.exit(1)", "--"]
D35_RONG = [sys.executable, "-c", "import sys; print('no tests ran in 0.01s')", "--"]


@pytest.fixture(autouse=True)
def _moi_truong_sach(monkeypatch):
    """Cố định môi trường: cây sạch, `kiem_cong_d35()` PASS.

    Bắt buộc phải cố định, cùng lý do như bộ test cổng D3: repo này có
    nhiều phiên cùng sửa một thư mục đĩa, nên nếu không ghim thì các ca
    đường-thành-công sẽ đỏ/xanh theo việc phiên khác có đang gõ dở hay
    không — tức bộ test đo MÔI TRƯỜNG chứ không đo code.
    """
    from tool_d.measurement.gitinfo import GitInfo

    monkeypatch.setattr(
        trial_ledger_audit, "get_git_info", lambda _: GitInfo(sha="b" * 40, is_clean=True)
    )
    monkeypatch.setattr(trial_ledger_audit, "_thay_doi_anh_huong_phep_do", lambda _: [])
    monkeypatch.setattr(
        trial_ledger_audit, "is_d0_pre_complete", lambda: True, raising=False
    )
    import tool_d.dr015.cong_d35 as cong

    monkeypatch.setattr(
        cong, "kiem_cong_d35", lambda **kw: {"LONG": {"gia_tri": 0.1612, "trang_thai": "ok"}}
    )


def _empty_ledger_kwargs(tmp_path: Path) -> dict:
    reg = tmp_path / "reg.jsonl"
    reg.touch()
    iq = tmp_path / "iq.jsonl"
    iq.touch()
    return {"registry_path": reg, "idea_queue_path": iq}


def _state(tmp_path: Path, **khoa) -> Path:
    p = tmp_path / "runtime_state.json"
    mac_dinh = {
        "d0_pre_complete": True, "d1_complete": True,
        "d2_complete": True, "d3_complete": True,
    }
    mac_dinh.update(khoa)
    p.write_text(json.dumps(mac_dinh), encoding="utf-8")
    return p


def _goi(sp: Path, tmp_path: Path, *, d35=D35_PASS, suite=PASS_CMD):
    return close_d3_5_gate(
        runtime_state_path=sp,
        pytest_cmd=suite,
        pytest_d35_cmd=d35,
        **_empty_ledger_kwargs(tmp_path),
    )


class TestThuTuBonCong:
    @pytest.mark.parametrize("khoa", ["d1_complete", "d2_complete", "d3_complete"])
    def test_cong_truoc_chua_dong_thi_tu_choi(self, tmp_path: Path, khoa: str) -> None:
        sp = _state(tmp_path, **{khoa: False})
        before = sp.read_text(encoding="utf-8")
        exit_code, text = _goi(sp, tmp_path)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and khoa in text
        assert sp.read_text(encoding="utf-8") == before

    def test_d0_pre_chua_dong_thi_tu_choi(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: False)
        exit_code, text = _goi(_state(tmp_path), tmp_path)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and "D0-PRE chưa đóng" in text


class TestDungChungMayVoiE3:
    """🔴 Điều kiện đóng cổng và điều kiện chạy ablation phải là MỘT."""

    def test_kiem_cong_d35_TU_CHOI_thi_cong_cung_tu_choi(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        import tool_d.dr015.cong_d35 as cong

        def _no(**kw):
            raise cong.CongD35ChuaDongError("Δ_R chưa commit")

        monkeypatch.setattr(cong, "kiem_cong_d35", _no)
        sp = _state(tmp_path)
        before = sp.read_text(encoding="utf-8")
        exit_code, text = _goi(sp, tmp_path)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and "chưa commit" in text
        assert sp.read_text(encoding="utf-8") == before

    def test_cong_goi_dung_ham_cua_E3_khong_tu_viet_ban_thu_hai(self) -> None:
        import inspect

        src = inspect.getsource(close_d3_5_gate)
        assert "kiem_cong_d35" in src
        # và KHÔNG tự dựng lại danh sách artifact
        assert "dr015-buoc1-delta-r.json" not in src

    def test_delta_r_niem_phong_duoc_GHI_VAO_file_trang_thai(self, tmp_path: Path) -> None:
        """Ghi lại chính con số đã dùng — để sau này truy được ablation
        chạy với Δ_R nào, không phải đoán từ ngày tháng."""
        sp = _state(tmp_path)
        _goi(sp, tmp_path)
        d = json.loads(sp.read_text(encoding="utf-8"))
        assert d["d3_5_delta_r_niem_phong"]["LONG"] == pytest.approx(0.1612)


class TestDongCongThanhCong:
    def test_ghi_du_khoa_va_exit_0(self, tmp_path: Path) -> None:
        sp = _state(tmp_path)
        exit_code, _ = _goi(sp, tmp_path)
        assert exit_code == 0
        d = json.loads(sp.read_text(encoding="utf-8"))
        assert d["d3_5_complete"] is True and d["d3_5_cay_sach"] is True
        assert len(d["d3_5_git_sha"]) == 40
        for k in ("d0_pre_complete", "d1_complete", "d2_complete", "d3_complete"):
            assert d[k] is True  # không phá khoá cổng nào trước đó

    def test_evidence_liet_ke_du_NAM_file_va_nhan_do_duoc(self, tmp_path: Path) -> None:
        sp = _state(tmp_path)
        _goi(sp, tmp_path)
        ev = json.loads(sp.read_text(encoding="utf-8"))["d3_5_evidence"]
        for k in ("full_suite", "test_khoa_d3_5", "cong_d35_kiem_cong", "trial_ledger_audit"):
            assert ev[k]["nguon"] == "do-duoc"
        for duong_dan in DUONG_DAN_TEST_D3_5:
            assert duong_dan in ev["test_khoa_d3_5"]["noi_dung"]

    def test_han_che_noi_du_BON_dieu(self, tmp_path: Path) -> None:
        """Cổng D3.5 dễ bị đọc quá tay nhất trong bốn cổng: nó có con số
        p_nf = 0 trông rất sạch. Bốn hạn chế phải nằm trong file, dưới
        nhãn `nguoi-khai`."""
        sp = _state(tmp_path)
        _goi(sp, tmp_path)
        hc = json.loads(sp.read_text(encoding="utf-8"))["d3_5_han_che"]
        assert hc["nguon"] == "nguoi-khai"
        n = hc["noi_dung"]
        assert "GIÁN TIẾP" in n and "testnet" in n          # (1) cách đo
        assert "hàng đợi" in n and "MỘT PHẦN" in n          # (1) ba thứ không thấy
        assert "LONG-only" in n and "unreadable" in n       # (2) chỉ một hướng
        assert "TƯƠNG ĐƯƠNG" in n and "1,04" in n           # (3) Bước 3
        assert "ĐÃ CẤP" in n                                # (4) tập đo


class TestTuChoiKhiBangChungKhongDU:
    def test_suite_that_bai_thi_khong_ghi(self, tmp_path: Path) -> None:
        sp = _state(tmp_path)
        before = sp.read_text(encoding="utf-8")
        exit_code, text = _goi(sp, tmp_path, suite=FAIL_CMD)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and "suite pytest CHƯA sạch" in text
        assert sp.read_text(encoding="utf-8") == before

    def test_test_khoa_that_bai_thi_khong_ghi(self, tmp_path: Path) -> None:
        sp = _state(tmp_path)
        before = sp.read_text(encoding="utf-8")
        exit_code, text = _goi(sp, tmp_path, d35=D35_FAIL)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and "cốt lõi CHƯA xanh" in text
        assert sp.read_text(encoding="utf-8") == before

    def test_exit_0_nhung_0_ca_thi_tu_choi(self, tmp_path: Path) -> None:
        sp = _state(tmp_path)
        exit_code, text = _goi(sp, tmp_path, d35=D35_RONG)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and "PASS RỖNG" in text

    def test_cay_ban_thi_tu_choi_TRUOC_khi_chay_suite(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            trial_ledger_audit,
            "_thay_doi_anh_huong_phep_do",
            lambda _: ["[M] src/tool_d/dr015/buoc1_lech_tranche.py"],
        )
        goi: list[list[str]] = []
        that = trial_ledger_audit.subprocess.run
        monkeypatch.setattr(
            trial_ledger_audit.subprocess,
            "run",
            lambda cmd, **kw: (goi.append(list(cmd)), that(cmd, **kw))[1],
        )
        sp = _state(tmp_path)
        exit_code, text = _goi(sp, tmp_path)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and "ẢNH HƯỞNG PHÉP ĐO" in text
        assert [c for c in goi if "pytest" in " ".join(c)] == []

    def test_da_dong_roi_thi_tu_choi_ghi_de(self, tmp_path: Path) -> None:
        sp = _state(tmp_path, d3_5_complete=True)
        before = sp.read_text(encoding="utf-8")
        exit_code, _ = _goi(sp, tmp_path)
        assert exit_code == EXIT_GATE_ALREADY_CLOSED
        assert sp.read_text(encoding="utf-8") == before


class TestMoiFileChayRieng:
    def test_moi_file_mot_luot_khong_gop(self, tmp_path: Path, monkeypatch) -> None:
        """Gộp năm file vào MỘT lượt thì một file bị xoá vẫn cho tổng > 0
        nhờ bốn file kia — cổng vẫn đóng trong khi một phép kiểm cốt lõi
        đã biến mất (bài học TD-0117)."""
        goi: list[list[str]] = []
        that = trial_ledger_audit.subprocess.run
        monkeypatch.setattr(
            trial_ledger_audit.subprocess,
            "run",
            lambda cmd, **kw: (goi.append(list(cmd)), that(cmd, **kw))[1],
        )
        _goi(_state(tmp_path), tmp_path)
        chay_test = [c for c in goi if "git" not in c[0]]
        assert len(chay_test) == 1 + len(DUONG_DAN_TEST_D3_5)
        for duong_dan in DUONG_DAN_TEST_D3_5:
            assert sum(1 for c in chay_test if duong_dan in c) == 1

    def test_nam_file_deu_CO_THAT_va_phu_du_bon_thanh_phan(self) -> None:
        """Hằng số trỏ sai đường dẫn sẽ luôn cho 0 ca và làm cổng không
        bao giờ đóng được — nhưng chỉ lộ ra lúc chạy thật."""
        assert len(DUONG_DAN_TEST_D3_5) == 5
        for duong_dan in DUONG_DAN_TEST_D3_5:
            assert (REPO_ROOT / duong_dan).is_file(), duong_dan
        gop = " ".join(DUONG_DAN_TEST_D3_5)
        for phan in ("buoc1", "td0162", "td0163", "lz58", "lz56"):
            assert phan in gop
