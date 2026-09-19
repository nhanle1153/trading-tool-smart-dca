"""TD-0329 (OQ-14a) — kiểm chính công cụ `tests/tools/mutate_in_memory.py`.

Một công cụ "kiểm có răng" mà bản thân không được kiểm thì có thể im lặng trả xanh cho mọi
thứ. Nên ở đây khoá bốn điều, mỗi điều có ca riêng:

  1. **Phần thuần đúng**: tìm khối duy nhất, từ chối khi khối lệch/lặp/không đổi, giữ thụt
     lề và ký tự xuống dòng (LF lẫn CRLF).
  2. **Nạp bản phá đúng chỗ**: vào `sys.modules` TRƯỚC khi `exec`, từ chối khi module đã
     được nạp (ai đã import bản gốc sẽ không thấy bản phá).
  3. **Công cụ THẬT SỰ đổi hành vi và KHÔNG đổi đĩa**: chạy tiến trình con trên một module
     giả trong `tmp_path` — đối chứng xanh, biến thể đỏ đúng test, sha256 file nguồn giữ nguyên.
  4. **Đặc tả thật khớp mã thật**, và tái lập đúng kết quả của `1be9b88` (phá-thật `TD-0320`):
     M0 xanh; M1 đỏ đúng ca âm `dinh`; M2 đỏ ca `day` + một test Long.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tests" / "tools" / "mutate_in_memory.py"
SPEC_DIR = REPO_ROOT / "tests" / "tools" / "specs"
SPEC_THAT = SPEC_DIR / "td0320_moi_hon.json"
#: Mọi đặc tả thật. `td0330` nghiệm thu test khoá hai chiều: `tests` của nó là CHỈ file
#: `test_td0330…`, nên nghiệm thu chạy Ở ĐÂY (file này) chứ không trong file TD-0330 — đặt trong
#: chính file đó thì tiến trình con sẽ chạy lại chính nó và đệ quy vô hạn.
SPECS_THAT = [SPEC_DIR / "td0320_moi_hon.json", SPEC_DIR / "td0330_khoa_hai_chieu.json"]


def _nap_cong_cu():
    spec = importlib.util.spec_from_file_location("mutate_in_memory_dut", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mutate_in_memory_dut"] = mod  # dataclass tra module qua sys.modules
    spec.loader.exec_module(mod)
    return mod


M = _nap_cong_cu()


def _dac_ta(**kw):
    mac_dinh = dict(
        module="m", file="f.py", khoi_dong=("hon = (", "x > ket", ")"),
        bien_the={"M0": None, "M1": "hon = x < ket"}, tests=(), ky_vong={}, ky_vong_do_gom={},
    )
    mac_dinh.update(kw)
    return M.DacTa(**mac_dinh)


NGUON = (
    "def f(xs):\n"
    "    ket = xs[0]\n"
    "    for x in xs:\n"
    "        hon = (\n"
    "            x > ket\n"
    "        )\n"
    "        if hon:\n"
    "            ket = x\n"
    "    return ket\n"
)


class TestTimKhoi:
    def test_tim_dung_chi_so(self) -> None:
        assert M.tim_khoi(NGUON.splitlines(keepends=True), ("hon = (", "x > ket", ")")) == 3

    def test_khong_thay_thi_loi(self) -> None:
        with pytest.raises(M.DotBienError, match="0 lần"):
            M.tim_khoi(NGUON.splitlines(keepends=True), ("khong_co = (", "x", ")"))

    def test_xuat_hien_hai_lan_thi_loi(self) -> None:
        with pytest.raises(M.DotBienError, match="2 lần"):
            M.tim_khoi((NGUON + NGUON).splitlines(keepends=True), ("hon = (", "x > ket", ")"))

    def test_khoi_lech_dac_ta_thi_loi(self) -> None:
        """Mã nguồn trôi khỏi đặc tả ⇒ lỗi ngay, không phá bừa một khối khác."""
        with pytest.raises(M.DotBienError, match="lệch đặc tả"):
            M.tim_khoi(NGUON.splitlines(keepends=True), ("hon = (", "x >= ket", ")"))

    def test_khoi_vuot_cuoi_file_thi_loi(self) -> None:
        with pytest.raises(M.DotBienError, match="vượt quá"):
            M.tim_khoi(["hon = (\n", "x > ket\n"], ("hon = (", "x > ket", ")"))


class TestDotBien:
    def test_doi_dung_khoi_giu_thut_le_va_phan_con_lai(self) -> None:
        ket = M.dot_bien(NGUON, _dac_ta(), "M1")
        assert "        hon = x < ket\n" in ket
        assert "x > ket" not in ket
        # mọi dòng ngoài khối giữ nguyên
        assert ket.replace("        hon = x < ket\n", "        hon = (\n            x > ket\n        )\n") == NGUON

    def test_giu_ky_tu_xuong_dong_crlf(self) -> None:
        nguon = NGUON.replace("\n", "\r\n")
        ket = M.dot_bien(nguon, _dac_ta(), "M1")
        assert "        hon = x < ket\r\n" in ket
        assert ket.count("\r\n") == ket.count("\n"), "không được lẫn LF trần vào file CRLF"

    def test_doi_chung_tra_nguyen_xi(self) -> None:
        assert M.dot_bien(NGUON, _dac_ta(), "M0") == NGUON

    def test_doi_chung_van_kiem_dac_ta_khop_ma_that(self) -> None:
        """M0 không phá gì, nhưng đặc tả lệch mã thì M0 cũng phải báo — nếu không, `M0` xanh
        chỉ chứng minh không có gì chạy."""
        with pytest.raises(M.DotBienError, match="lệch đặc tả"):
            M.dot_bien(NGUON.replace("x > ket", "x >= ket"), _dac_ta(), "M0")

    def test_bien_the_khong_doi_gi_thi_loi(self) -> None:
        dt = _dac_ta(khoi_dong=("hon = (",), bien_the={"M1": "hon = ("})
        with pytest.raises(M.DotBienError, match="không đổi gì"):
            M.dot_bien(NGUON, dt, "M1")

    def test_ten_bien_the_la_thi_loi(self) -> None:
        with pytest.raises(M.DotBienError, match="không có biến thể"):
            M.dot_bien(NGUON, _dac_ta(), "M9")

    def test_thay_nhieu_dong(self) -> None:
        ket = M.dot_bien(NGUON, _dac_ta(bien_the={"M1": ["hon = False", "pass"]}), "M1")
        assert "        hon = False\n        pass\n" in ket

    def test_ban_pha_van_la_python_hop_le(self) -> None:
        compile(M.dot_bien(NGUON, _dac_ta(), "M1"), "f.py", "exec")


@pytest.fixture
def goi_gia(tmp_path, monkeypatch):
    """Một package tạm để thử `nap_ban_pha`, dọn `sys.modules` sau ca."""
    ten = "td0329_pkg_" + hashlib.sha1(str(tmp_path).encode()).hexdigest()[:8]
    (tmp_path / ten).mkdir()
    (tmp_path / ten / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    yield ten
    for k in [k for k in sys.modules if k == ten or k.startswith(ten + ".")]:
        sys.modules.pop(k, None)


class TestNapBanPha:
    def test_vao_sys_modules_truoc_khi_exec_va_gan_len_goi_cha(self, goi_gia) -> None:
        src = (
            "from __future__ import annotations\n"
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class A:\n"
            "    x: int\n"
            "GIA_TRI = A(3).x\n"
        )
        mod = M.nap_ban_pha(f"{goi_gia}.demo", src, "demo.py")
        assert sys.modules[f"{goi_gia}.demo"] is mod
        assert mod.GIA_TRI == 3
        assert getattr(sys.modules[goi_gia], "demo") is mod

    def test_tu_choi_khi_module_da_duoc_nap(self, goi_gia) -> None:
        goi = __import__(goi_gia)
        (Path(goi.__file__).parent / "demo.py").write_text("X = 1\n", encoding="utf-8")
        __import__(f"{goi_gia}.demo")
        with pytest.raises(M.DotBienError, match="đã được nạp"):
            M.nap_ban_pha(f"{goi_gia}.demo", "X = 2\n", "demo.py")

    def test_exec_loi_thi_don_sys_modules(self, goi_gia) -> None:
        with pytest.raises(ZeroDivisionError):
            M.nap_ban_pha(f"{goi_gia}.hong", "1 / 0\n", "hong.py")
        assert f"{goi_gia}.hong" not in sys.modules


class TestTomTat:
    def test_dang_q(self) -> None:
        dau_ra = "x\nFAILED tests/a.py::T::test_1 - assert 1 == 2\n1 failed, 58 passed in 5.72s\n"
        r = M.tom_tat(dau_ra)
        assert r["do"] == ["tests/a.py::T::test_1"]
        assert r["tom_tat"] == "1 failed, 58 passed"

    def test_dang_co_dau_bang(self) -> None:
        assert M.tom_tat("====== 59 passed in 5.63s ======\n")["tom_tat"] == "59 passed"

    def test_xanh_khong_co_ca_do(self) -> None:
        assert M.tom_tat("59 passed in 5.63s\n")["do"] == []


# ── (3) công cụ THẬT SỰ đổi hành vi và KHÔNG đổi đĩa ─────────────────────────────────

CALC = (
    "def lon_nhat(xs):\n"
    "    ket = xs[0]\n"
    "    for x in xs:\n"
    "        hon = (\n"
    "            x > ket\n"
    "        )\n"
    "        if hon:\n"
    "            ket = x\n"
    "    return ket\n"
)
TEST_DEMO = (
    "from td0329_demo.calc import lon_nhat\n"
    "\n"
    "\n"
    "def test_lon_nhat():\n"
    "    assert lon_nhat([1, 3, 2]) == 3\n"
)


@pytest.fixture
def repo_gia(tmp_path):
    (tmp_path / "src" / "td0329_demo").mkdir(parents=True)
    (tmp_path / "src" / "td0329_demo" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "td0329_demo" / "calc.py").write_text(CALC, encoding="utf-8", newline="")
    (tmp_path / "test_calc.py").write_text(TEST_DEMO, encoding="utf-8")
    return tmp_path


def _ghi_spec(root: Path, **ghi_de) -> Path:
    d = {
        "module": "td0329_demo.calc",
        "file": "src/td0329_demo/calc.py",
        "khoi_dong": ["hon = (", "x > ket", ")"],
        "bien_the": {"M0": None, "M1": "hon = x < ket"},
        "tests": ["test_calc.py"],
    }
    d.update(ghi_de)
    p = root / "spec.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return p


def _chay(root: Path, spec: Path, variant: str, cwd: Path | None = None):
    return subprocess.run(
        [sys.executable, str(TOOL), "--spec", str(spec), "--variant", variant, "--root", str(root)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(cwd or root),
    )


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class TestCongCuThatSuDoiHanhViVaKhongDoiDia:
    def test_doi_chung_M0_xanh(self, repo_gia) -> None:
        kq = _chay(repo_gia, _ghi_spec(repo_gia), "M0")
        assert kq.returncode == 0, kq.stdout + kq.stderr

    def test_M1_do_dung_test_va_that_su_doi_hanh_vi(self, repo_gia) -> None:
        """M0 xanh mà M1 đỏ ⇒ bản phá THẬT SỰ được nạp và làm đổi kết quả (không chỉ đổi chữ)."""
        kq = _chay(repo_gia, _ghi_spec(repo_gia), "M1")
        assert kq.returncode == 1, kq.stdout + kq.stderr
        assert "FAILED test_calc.py::test_lon_nhat" in kq.stdout

    def test_dia_khong_doi_mot_byte(self, repo_gia) -> None:
        nguon = repo_gia / "src" / "td0329_demo" / "calc.py"
        truoc = _sha(nguon)
        _chay(repo_gia, _ghi_spec(repo_gia), "M1")
        assert _sha(nguon) == truoc, "công cụ đã GHI vào file nguồn — vi phạm cam kết cốt lõi"
        assert nguon.read_text(encoding="utf-8") == CALC

    def test_ten_bien_the_la_tra_rc_2_khong_chay_test(self, repo_gia) -> None:
        kq = _chay(repo_gia, _ghi_spec(repo_gia), "M9")
        assert kq.returncode == 2
        assert "LỖI ĐẶC TẢ" in kq.stderr

    def test_dac_ta_lech_ma_that_tra_rc_2(self, repo_gia) -> None:
        spec = _ghi_spec(repo_gia, khoi_dong=["hon = (", "x >= ket", ")"])
        kq = _chay(repo_gia, spec, "M0")
        assert kq.returncode == 2
        assert "lệch đặc tả" in kq.stderr

    def test_all_in_bang_va_khop_du_doan(self, repo_gia) -> None:
        spec = _ghi_spec(
            repo_gia, ky_vong={"M0": "xanh", "M1": "do"},
            ky_vong_do_gom={"M1": ["test_calc.py::test_lon_nhat"]},
        )
        kq = _chay(repo_gia, spec, "all")
        assert kq.returncode == 0, kq.stdout + kq.stderr
        assert "== M0: XANH" in kq.stdout and "== M1: DO" in kq.stdout
        assert "khớp dự đoán" in kq.stdout

    def test_all_bao_lech_khi_du_doan_sai(self, repo_gia) -> None:
        """Dự đoán viết trước mà thực tế khác ⇒ rc 1 và nói rõ — không âm thầm cho qua."""
        spec = _ghi_spec(repo_gia, ky_vong={"M0": "xanh", "M1": "xanh"})
        kq = _chay(repo_gia, spec, "all")
        assert kq.returncode == 1
        assert "LỆCH DỰ ĐOÁN" in kq.stdout and "M1: dự đoán xanh, thực tế do" in kq.stdout

    def test_all_bao_lech_khi_test_phai_do_lai_khong_do(self, repo_gia) -> None:
        spec = _ghi_spec(repo_gia, ky_vong_do_gom={"M1": ["test_calc.py::test_khong_ton_tai"]})
        kq = _chay(repo_gia, spec, "all")
        assert kq.returncode == 1
        assert "PHẢI đỏ mà không đỏ" in kq.stdout


# ── (4) đặc tả THẬT khớp mã THẬT, và tái lập kết quả 1be9b88 ─────────────────────────


@pytest.mark.parametrize("spec", SPECS_THAT, ids=lambda p: p.stem)
class TestDacTaThatKhopMaThat:
    def test_khoi_duy_nhat_va_moi_bien_the_dot_duoc(self, spec) -> None:
        dt = M.DacTa.tu_json(spec)
        nguon = (REPO_ROOT / dt.file).read_text(encoding="utf-8")
        M.tim_khoi(nguon.splitlines(keepends=True), dt.khoi_dong)
        for ten in dt.bien_the:
            compile(M.dot_bien(nguon, dt, ten), dt.file, "exec")

    def test_moi_file_test_trong_dac_ta_ton_tai(self, spec) -> None:
        for t in M.DacTa.tu_json(spec).tests:
            assert (REPO_ROOT / t).is_file(), t

    def test_moi_test_phai_do_deu_ton_tai_trong_tap_tests(self, spec) -> None:
        """`ky_vong_do_gom` trỏ vào một nodeid không có thật thì ca "PHẢI đỏ" không bao giờ
        thoả được — hoặc tệ hơn, bị đọc là đỏ vì lỗi khác. Đòi file của nodeid nằm trong `tests`."""
        dt = M.DacTa.tu_json(spec)
        for ten, ds in dt.ky_vong_do_gom.items():
            for nodeid in ds:
                assert nodeid.split("::")[0] in dt.tests, (ten, nodeid)

    def test_chay_that_khop_du_doan_va_dia_khong_doi(self, spec) -> None:
        """Chạy THẬT mọi biến thể trên mã nguồn thật. Đây cũng là ca canh LONG: nếu ai đó làm yếu
        các test bắt lỗi cực trị cụm, `ky_vong_do_gom` báo LỆCH ở đây và suite đỏ."""
        dt = M.DacTa.tu_json(spec)
        nguon = REPO_ROOT / dt.file
        truoc = _sha(nguon)
        kq = subprocess.run(
            [sys.executable, str(TOOL), "--spec", str(spec), "--variant", "all",
             "--root", str(REPO_ROOT)],
            capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
        )
        assert kq.returncode == 0, kq.stdout + kq.stderr
        assert "== M0: XANH" in kq.stdout
        for ten, mong in dt.ky_vong.items():
            assert f"== {ten}: {mong.upper()}" in kq.stdout, (ten, kq.stdout)
        assert _sha(nguon) == truoc, "công cụ đã đổi file trên đĩa"
