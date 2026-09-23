"""TD-0257 — `close_d5_gate()` (E6 `--close-d5-gate`), khuôn `test_close_d4_gate.py`.

Canh:
1. 🔴 Trên BẢN SAO trạng thái thật + sổ thật hôm nay cổng TỪ CHỐI (0 suất `D5_MOC`, `DR-ZA-01` §5) và không chạm
   file thật; kèm lớp canh AST cấm truyền đường dẫn trạng thái thật vào hàm ghi (sự cố 20/09 của cổng D4).
2. Thứ tự cổng: thiếu `d4_complete`, cây bẩn, đã đóng ⇒ 94.
3. Đường thành công trên sổ TẠM (suất B1 dựng qua `reserve()` thật): ghi đủ khoá; chạy lại ⇒ 94.
4. Tiêu chí trượt ⇒ từ chối, không ghi byte nào. Xuất xứ (TD-0369) khớp / lệch.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import trial_ledger_audit  # noqa: E402
from trial_ledger_audit import (  # noqa: E402
    DUONG_DAN_TEST_D5,
    EXIT_GATE_ALREADY_CLOSED,
    EXIT_GATE_AUDIT_DIRTY,
    build_parser,
    close_d5_gate,
)

# Bộ dựng sổ tạm dùng chung với test hàm thuần — một bộ dựng, không hai bản trôi lệch.
from test_td0257_ket_qua_b1_va_tieu_chi_d5 import R_MOC, SoTam, _lenh, _lo_giu_moc, _status_moc  # noqa: E402

PASS_CMD = [sys.executable, "-c", "print('3100 passed in 900.0s')"]
D5_PASS = [sys.executable, "-c", "print('9 passed in 1.0s')", "--"]
SHA_CONG = "c" * 40


@pytest.fixture(autouse=True)
def _moi_truong_sach(monkeypatch):
    from tool_d.ablation import khoa_do
    from tool_d.measurement.gitinfo import GitInfo

    monkeypatch.setattr(trial_ledger_audit, "get_git_info", lambda _: GitInfo(sha=SHA_CONG, is_clean=True))
    monkeypatch.setattr(trial_ledger_audit, "_thay_doi_anh_huong_phep_do", lambda _: [])
    monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True, raising=False)
    monkeypatch.setattr(khoa_do, "D5_DO_TAM_DUNG", False)  # để dựng suất B1 trong sổ TẠM


def _state(tmp_path: Path, **khoa) -> Path:
    # Tên RIÊNG: `SoTam` ghi `runtime_state.json` của cửa B1 vào cùng `tmp_path` — trùng tên là ghi đè nhau.
    p = tmp_path / "runtime_state_cong.json"
    s = {f"d{k}_complete": True for k in ("1", "2", "3", "3_5", "4")}
    s.update(khoa)
    p.write_text(json.dumps(s), encoding="utf-8")
    return p


def _ps(tmp_path: Path, ps: dict | None = None) -> Path:
    p = tmp_path / "param_status.yaml"
    p.write_text(yaml.safe_dump({"params": ps or _status_moc()}, allow_unicode=True), encoding="utf-8")
    return p


def _goi(sp: Path, so: SoTam, tmp_path: Path, ps: dict | None = None):
    (tmp_path / "iq.jsonl").touch()
    return close_d5_gate(
        runtime_state_path=sp, repo_dir=REPO_ROOT, runs_dir=so.runs, registry_path=so.reg,
        param_status_path=_ps(tmp_path, ps), pytest_cmd=PASS_CMD, pytest_d5_cmd=D5_PASS,
        idea_queue_path=tmp_path / "iq.jsonl",
    )


class TestTrangThaiThatHomNay:
    def test_ban_sao_trang_thai_that_TU_CHOI_va_khong_cham_file_that(self, tmp_path, monkeypatch) -> None:
        from tool_d.ablation import khoa_do

        monkeypatch.setattr(khoa_do, "D5_DO_TAM_DUNG", True)
        that = REPO_ROOT / "registry" / "runtime_state.json"
        so_that = REPO_ROOT / "registry" / "trial_registry.jsonl"
        truoc, truoc_so = that.read_bytes(), so_that.read_bytes()
        ban_sao = tmp_path / "runtime_state.json"
        ban_sao.write_bytes(truoc)
        ma, text = close_d5_gate(
            runtime_state_path=ban_sao, repo_dir=REPO_ROOT, runs_dir=REPO_ROOT / "runs",
            registry_path=so_that, param_status_path=REPO_ROOT / "config" / "param_status.yaml",
            pytest_cmd=PASS_CMD, pytest_d5_cmd=D5_PASS,
        )
        assert ma == EXIT_GATE_AUDIT_DIRTY and "D5_MOC" in text, text
        assert that.read_bytes() == truoc and so_that.read_bytes() == truoc_so

    def test_khong_ca_nao_truyen_duong_dan_that_vao_ham_dong_cong(self) -> None:
        nguon = Path(__file__).read_text(encoding="utf-8")
        vi_pham = []
        for n in ast.walk(ast.parse(nguon)):
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "close_d5_gate":
                for kw in n.keywords:
                    doan = ast.get_source_segment(nguon, kw.value) or ""
                    if kw.arg == "runtime_state_path" and "REPO_ROOT" in doan:
                        vi_pham.append(n.lineno)
        assert vi_pham == [], f"dòng {vi_pham}: truyền đường dẫn trạng thái THẬT vào hàm ghi"


class TestThuTuCong:
    def test_thieu_d4_complete(self, tmp_path) -> None:
        ma, text = _goi(_state(tmp_path, d4_complete=False), SoTam(tmp_path), tmp_path)
        assert ma == EXIT_GATE_AUDIT_DIRTY and "d4_complete" in text

    def test_da_dong_thi_94(self, tmp_path) -> None:
        assert _goi(_state(tmp_path, d5_complete=True), SoTam(tmp_path), tmp_path)[0] == EXIT_GATE_ALREADY_CLOSED

    def test_cay_ban_thi_tu_choi(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "_thay_doi_anh_huong_phep_do", lambda _: ["M src/x.py"])
        ma, text = _goi(_state(tmp_path), SoTam(tmp_path), tmp_path)
        assert ma == EXIT_GATE_AUDIT_DIRTY and "ẢNH HƯỞNG PHÉP ĐO" in text


class TestTieuChi:
    def test_so_rong_tu_choi_khong_ghi_byte(self, tmp_path) -> None:
        sp = _state(tmp_path)
        truoc = sp.read_bytes()
        ma, text = _goi(sp, SoTam(tmp_path), tmp_path)
        assert ma == EXIT_GATE_AUDIT_DIRTY and "D5_MOC" in text and sp.read_bytes() == truoc

    def test_param_status_lech_quyet_dinh_thi_tu_choi(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        _lo_giu_moc(so)
        ps = _status_moc()
        ps["zss_threshold"] = {"status": "TUNED", "value": 0.6}
        ma, text = _goi(_state(tmp_path), so, tmp_path, ps)
        assert ma == EXIT_GATE_AUDIT_DIRTY and "zss_threshold" in text


class TestDuongThanhCong:
    def test_dong_ghi_khoa_roi_chay_lai_94(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        _lo_giu_moc(so)
        sp = _state(tmp_path)
        ma, text = _goi(sp, so, tmp_path)
        assert ma == 0, text
        s = json.loads(sp.read_text(encoding="utf-8"))
        assert s["d5_complete"] is True and s["d5_huong"] == "LONG" and s["d5_git_sha"] == SHA_CONG
        ev = s["d5_evidence"]
        for k in ("full_suite", "test_khoa_d5", "tieu_chi_dr_d5_01", "quyet_dinh_tinh_lai", "xac_nhan_ghep",
                  "gia_tri_cuoi", "trial_ledger_audit", "xuat_xu_ban_ghi"):
            assert ev[k]["nguon"] == "do-duoc", k
        assert f"{len(R_MOC)} lệnh" in ev["tieu_chi_dr_d5_01"]["noi_dung"]
        assert s["d5_han_che"]["nguon"] == "nguoi-khai" and "CHỈ LONG" in s["d5_han_che"]["noi_dung"]
        assert _goi(sp, so, tmp_path)[0] == EXIT_GATE_ALREADY_CLOSED

    def test_xuat_xu_LECH_khi_suat_do_tren_ma_khac(self, tmp_path) -> None:
        so = SoTam(tmp_path)  # SoTam ghi git_sha = "a"*40, cổng chứng nhận "c"*40
        _lo_giu_moc(so)
        sp = _state(tmp_path)
        assert _goi(sp, so, tmp_path)[0] == 0
        noi_dung = json.loads(sp.read_text(encoding="utf-8"))["d5_evidence"]["xuat_xu_ban_ghi"]["noi_dung"]
        assert "LỆCH" in noi_dung

    def test_xuat_xu_KHOP_khi_cung_ma(self, tmp_path, monkeypatch) -> None:
        from tool_d.measurement.gitinfo import GitInfo

        monkeypatch.setattr(trial_ledger_audit, "get_git_info", lambda _: GitInfo(sha="a" * 40, is_clean=True))
        so = SoTam(tmp_path)
        _lo_giu_moc(so)
        sp = _state(tmp_path)
        assert _goi(sp, so, tmp_path)[0] == 0
        noi_dung = json.loads(sp.read_text(encoding="utf-8"))["d5_evidence"]["xuat_xu_ban_ghi"]["noi_dung"]
        assert "KHỚP" in noi_dung

    def test_doi_tham_so_ghi_gia_tri_cuoi(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        so.them("D5_MOC", None, _lenh(R_MOC))
        for ten, ts in so_tham_so_tru("buf_sl_atr"):
            for v in ts.thu:
                so.them(ten, v, _lenh(R_MOC))
        so.them("buf_sl_atr", 0.3, _lenh(R_MOC))
        so.them("buf_sl_atr", 0.5, _lenh([r + 1.0 for r in R_MOC]))
        so.them("D5_XAC_NHAN", {"buf_sl_atr": 0.5}, _lenh([r + 1.0 for r in R_MOC]))
        ps = _status_moc()
        ps["buf_sl_atr"] = {"status": "TUNED", "value": 0.5}
        sp = _state(tmp_path)
        ma, text = _goi(sp, so, tmp_path, ps)
        assert ma == 0, text
        assert json.loads(sp.read_text(encoding="utf-8"))["d5_evidence"]["gia_tri_cuoi"]["noi_dung"]["buf_sl_atr"] == 0.5


def so_tham_so_tru(bo: str):
    from test_td0257_ket_qua_b1_va_tieu_chi_d5 import BANG

    return [(k, v) for k, v in BANG.tham_so.items() if k != bo]


class TestNoiVaoE6:
    def test_co_close_d5_gate(self) -> None:
        assert build_parser().parse_args(["--close-d5-gate"]).close_d5_gate is True

    def test_file_test_cot_loi_ton_tai(self) -> None:
        for p in DUONG_DAN_TEST_D5:
            assert (REPO_ROOT / p).is_file(), p
