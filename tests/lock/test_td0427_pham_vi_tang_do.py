"""TD-0427 (`MT-71`, luật chung chủ dự án duyệt 26/09/2026) — hàm tầng ĐO dùng ở tầng QUYẾT ĐỊNH phải FAIL-CLOSED.

`MT-71`: `ablation/thanh_ly.liq_buffer_ke_hoach()` là Long-only theo `DR-D4-17`, nhưng phạm vi ấy nằm trong DR, không
trong chữ ký. `TD-0364` tái dùng nó ở tầng quyết định ⇒ **mọi lệnh Short bị từ chối im lặng** (11 ca đo được). Luật
chung: mọi hàm thuộc `tool_d.ablation` / `tool_d.measurement` mà tầng quyết định (`user_data/strategies/`,
`src/tool_d/ops/`) chạm tới phải KHAI phạm vi, và gọi ngoài phạm vi phải ra lỗi ĐỌC ĐƯỢC — không trả rỗng/0/`False`.

Ba lớp:

- `quet_vuot_ranh()` — bao đóng import **bắc cầu**: ca gốc của `MT-71` đi GIÁN TIẾP
  (`ZoneAbsorption` → `tool_d.cong_thanh_ly` → `ablation.thanh_ly`), một phép quét import trực tiếp bỏ sót đúng ca
  đã sinh ra luật này. `TestMayQuetCoRang` chứng minh điều đó trên cây giả trong `tmp_path`.
- `KHAI_PHAM_VI` — mỗi HÀM vượt ranh một dòng, ba loại:
  `NEM_LOI` (ca trỏ tới phải có `pytest.raises`) · `NGUOI_GOI_TU_CHOI` (hàm trả `None` = `unreadable` theo N6, người
  gọi ở tầng quyết định từ chối — ca trỏ tới kiểm lời từ chối đó) · `TOAN_CUC` (không có giả định phạm vi, kèm lý do).
  Hằng số, kiểu, lớp lỗi KHÔNG vào danh sách: chúng không thể "từ chối im lặng".
- `TestLiqBufferNgoaiPhamVi` — lấp khoảng hở đo được khi dựng test này: `liq_buffer_ke_hoach()` có năm nhánh
  `raise ThanhLyError`, nhưng tới 26/09/2026 KHÔNG ca nào trong `tests/` kiểm hàm ném lỗi khi bị gọi ngoài phạm vi
  (chỉ tầng cổng `xet_cong_l_z3` được kiểm).

Thêm một hàm đo vào đường quyết định ⇒ test đỏ tới khi khai phạm vi ở đây. Đó là chủ đích: khai là một việc có ý thức.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from tool_d.ablation.thanh_ly import ThanhLyError, liq_buffer_ke_hoach

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Tầng ĐO — nơi hàm có thể mang giả định phạm vi chỉ nằm trong DR.
TANG_DO = ("tool_d.ablation", "tool_d.measurement")
#: Tầng QUYẾT ĐỊNH — thứ chạy trong bot / bộ khởi động vận hành.
GOC_QUYET_DINH = ("user_data/strategies", "src/tool_d/ops")

NEM_LOI = "NEM_LOI"
NGUOI_GOI_TU_CHOI = "NGUOI_GOI_TU_CHOI"
TOAN_CUC = "TOAN_CUC"


@dataclass(frozen=True)
class KhaiPhamVi:
    pham_vi: str
    loai: str
    ca_ngoai_pham_vi: str = ""  # node id pytest; rỗng ⇔ TOAN_CUC
    ly_do: str = ""  # bắt buộc với TOAN_CUC


_F = "tests/lock/test_td0427_pham_vi_tang_do.py::TestLiqBufferNgoaiPhamVi"

KHAI_PHAM_VI: dict[str, KhaiPhamVi] = {
    "tool_d.ablation.thanh_ly.liq_buffer_ke_hoach": KhaiPhamVi(
        pham_vi="LONG và SHORT (`la_short`); `sl` đúng phía `p_avg_plan`; trọng số tổng 1; giá/khối lượng/đòn bẩy "
        "dương; chiều SHORT cần `TinhLiq` nhận `la_short`",
        loai=NEM_LOI,
        ca_ngoai_pham_vi=f"{_F}::test_sl_sai_phia_thi_NEM_LOI",
    ),
    "tool_d.ablation.thanh_ly.ham_tu_exchange": KhaiPhamVi(
        pham_vi="`Exchange` Freqtrade đang chạy; cặp ngoài bảng bậc đòn bẩy ⇒ `None` (`unreadable`, N6), không phải số",
        loai=NGUOI_GOI_TU_CHOI,
        ca_ngoai_pham_vi="tests/lock/test_td0364_cong_lz3_vao_lenh.py::TestTangThuan::"
        "test_ba_ca_khong_tinh_duoc_deu_TU_CHOI",
    ),
    "tool_d.measurement.gitinfo.kiem_cay_khop_head": KhaiPhamVi(
        pham_vi="thư mục là repo git đọc được",
        loai=NEM_LOI,
        ca_ngoai_pham_vi="tests/unit/test_td0425_cay_khop_head.py::TestKiemCayKhopHead::"
        "test_khong_phai_repo_git_thi_FAIL_CLOSED",
    ),
    "tool_d.measurement.gitinfo.bam_thay_doi_chua_commit": KhaiPhamVi(
        pham_vi="thư mục là repo git đọc được",
        loai=NEM_LOI,
        ca_ngoai_pham_vi="tests/lock/test_td0380_van_tay_lan_chay.py::TestCuaGhiTuTinhVanTay::"
        "test_git_loi_thi_TU_CHOI_va_so_khong_doi_dong_nao",
    ),
    "tool_d.measurement.provenance.build_provenance": KhaiPhamVi(
        pham_vi="thư mục là repo git đọc được",
        loai=NEM_LOI,
        ca_ngoai_pham_vi="tests/lock/test_lz40_provenance.py::TestBuildProvenance::"
        "test_khong_phai_git_repo_thi_raise_khong_tra_UNKNOWN",
    ),
    "tool_d.measurement.provenance.doc_runtime_image_digest": KhaiPhamVi(
        pham_vi="chạy trong ảnh Docker của dự án, `docker/Dockerfile` ghim đúng một digest",
        loai=NEM_LOI,
        ca_ngoai_pham_vi="tests/lock/test_td0229_khoa_xuat_xu_thu_8.py::TestBoSinhFailClosed::"
        "test_ngoai_docker_thi_tu_choi",
    ),
    "tool_d.measurement.provenance.van_tay_lan_chay": KhaiPhamVi(
        pham_vi="mọi đầu vào",
        loai=TOAN_CUC,
        ly_do="băm thuần năm yếu tố; không có nhánh nào trả rỗng — khối xuất xứ sai hình dạng để schema ở cửa ghi "
        "sổ báo lỗi (`TrialLedger._append`)",
    ),
    "tool_d.measurement.hashing.sha256_of": KhaiPhamVi(
        pham_vi="mọi đường dẫn",
        loai=TOAN_CUC,
        ly_do="không phụ thuộc chiều/sàn/giai đoạn; lỗi đọc ⇒ hằng `MISSING` đã khai trong `hashing.py` (không phải "
        "rỗng hay số cũ) — người gọi thấy được, không lẫn với một băm thật",
    ),
}


# ─────────────────────────────── máy quét ───────────────────────────────


def _file_module(goc: Path, mod: str) -> Path | None:
    p = goc / "src" / Path(*mod.split("."))
    if p.with_suffix(".py").is_file():
        return p.with_suffix(".py")
    if (p / "__init__.py").is_file():
        return p / "__init__.py"
    return None


def _ten_module_cua(goc: Path, f: Path) -> str | None:
    try:
        rel = f.relative_to(goc / "src")
    except ValueError:
        return None
    phan = list(rel.with_suffix("").parts)
    if phan[-1] == "__init__":
        phan.pop()
    return ".".join(phan)


def _giai_tuong_doi(goc: Path, f: Path, n: ast.ImportFrom) -> str | None:
    if n.level == 0:
        return n.module
    ten = _ten_module_cua(goc, f)
    if ten is None:
        return None
    goi = ten.split(".") if f.name == "__init__.py" else ten.split(".")[:-1]
    goi = goi[: len(goi) - (n.level - 1)]
    return ".".join(goi + ([n.module] if n.module else []))


def quet_vuot_ranh(goc: Path) -> dict[str, set[str]]:
    """`{"<module>.<tên>": {file tầng quyết định/trung gian nơi import}}` cho mọi ký hiệu tầng ĐO chạm tới được
    BẮC CẦU từ `GOC_QUYET_DINH`. Import trong thân hàm (import lười) cũng tính. `from tool_d.ablation import khoa_do`
    (import cả module) ⇒ tính từng thuộc tính `khoa_do.<x>` mà file đó dùng."""
    goc_files = sorted(f for d in GOC_QUYET_DINH for f in (goc / d).glob("*.py"))
    da_xem: set[Path] = set()
    ngan_xep = list(goc_files)
    vuot: dict[str, set[str]] = {}
    while ngan_xep:
        f = ngan_xep.pop()
        if f in da_xem:
            continue
        da_xem.add(f)
        cay = ast.parse(f.read_text(encoding="utf-8"))
        noi = f.relative_to(goc).as_posix()
        for n in ast.walk(cay):
            if isinstance(n, ast.ImportFrom):
                mod = _giai_tuong_doi(goc, f, n)
                if not mod or not mod.startswith("tool_d"):
                    continue
                for a in n.names:
                    con = f"{mod}.{a.name}"
                    if mod.startswith(TANG_DO):
                        if _file_module(goc, con):  # import cả MODULE tầng đo ⇒ thuộc tính được dùng
                            ten_cuc_bo = a.asname or a.name
                            for m in ast.walk(cay):
                                if (isinstance(m, ast.Attribute) and isinstance(m.value, ast.Name)
                                        and m.value.id == ten_cuc_bo):
                                    vuot.setdefault(f"{con}.{m.attr}", set()).add(noi)
                        else:
                            vuot.setdefault(con, set()).add(noi)
                        continue
                    for dich in (_file_module(goc, con), _file_module(goc, mod)):
                        if dich:
                            ngan_xep.append(dich)
            elif isinstance(n, ast.Import):
                for a in n.names:
                    if a.name.startswith(TANG_DO):
                        vuot.setdefault(a.name, set()).add(noi)
                    elif a.name.startswith("tool_d") and (dich := _file_module(goc, a.name)):
                        ngan_xep.append(dich)
    return vuot


def la_ham(goc: Path, ky_hieu: str) -> bool:
    """`True` ⇔ ký hiệu là HÀM định nghĩa ở cấp cao nhất của module. Không phân loại được ⇒ raise (fail-closed)."""
    mod, ten = ky_hieu.rsplit(".", 1)
    f = _file_module(goc, mod)
    if f is None:
        raise AssertionError(f"{ky_hieu}: không tìm thấy module {mod}")
    for n in ast.parse(f.read_text(encoding="utf-8")).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == ten:
            return True
        if isinstance(n, ast.ClassDef) and n.name == ten:
            return False
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == ten for t in n.targets):
            return False
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == ten:
            return False
    raise AssertionError(f"{ky_hieu}: không phân loại được (không phải def/class/gán cấp cao nhất) — khai tay")


def ham_vuot_ranh(goc: Path) -> dict[str, set[str]]:
    return {k: v for k, v in quet_vuot_ranh(goc).items() if la_ham(goc, k)}


def _tim_ham_test(node_id: str) -> ast.FunctionDef:
    duong, *ten = node_id.split("[", 1)[0].split("::")
    f = REPO_ROOT / duong
    assert f.is_file(), f"{node_id}: không có file {duong}"
    than: list[ast.stmt] = ast.parse(f.read_text(encoding="utf-8")).body
    for i, phan in enumerate(ten):
        loai = ast.FunctionDef if i == len(ten) - 1 else ast.ClassDef
        nut = next((n for n in than if isinstance(n, loai) and n.name == phan), None)
        assert nut is not None, f"{node_id}: không có {phan} trong {duong}"
        than = nut.body
    return nut  # type: ignore[return-value]


def _co_pytest_raises(ham: ast.FunctionDef) -> bool:
    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "raises"
        and isinstance(n.func.value, ast.Name) and n.func.value.id == "pytest"
        for n in ast.walk(ham)
    )


# ─────────────────────────────── luật trên repo thật ───────────────────────────────


class TestLuatMT71TrenRepo:
    def test_moi_ham_do_toi_duoc_tu_tang_quyet_dinh_deu_da_KHAI(self) -> None:
        thuc = ham_vuot_ranh(REPO_ROOT)
        chua_khai = {k: sorted(v) for k, v in thuc.items() if k not in KHAI_PHAM_VI}
        assert not chua_khai, (
            "Hàm tầng ĐO chạm tới được từ tầng QUYẾT ĐỊNH mà CHƯA khai phạm vi (MT-71) — thêm vào KHAI_PHAM_VI kèm "
            f"ca gọi ngoài phạm vi: {chua_khai}"
        )

    def test_khong_khai_thua(self) -> None:
        """Dòng khai không còn đường nào chạm tới là dòng lỗi thời — đúng cơ chế trôi của `MT-46`."""
        thua = sorted(set(KHAI_PHAM_VI) - set(ham_vuot_ranh(REPO_ROOT)))
        assert not thua, f"KHAI_PHAM_VI có dòng không còn đường quyết định nào chạm tới: {thua}"

    @pytest.mark.parametrize("ky_hieu", sorted(KHAI_PHAM_VI))
    def test_dong_khai_dung_hinh(self, ky_hieu: str) -> None:
        k = KHAI_PHAM_VI[ky_hieu]
        assert k.pham_vi.strip(), ky_hieu
        assert k.loai in (NEM_LOI, NGUOI_GOI_TU_CHOI, TOAN_CUC), ky_hieu
        if k.loai == TOAN_CUC:
            assert k.ly_do.strip() and not k.ca_ngoai_pham_vi, f"{ky_hieu}: TOAN_CUC cần lý do, không cần ca"
            return
        ham = _tim_ham_test(k.ca_ngoai_pham_vi)
        if k.loai == NEM_LOI:
            assert _co_pytest_raises(ham), f"{ky_hieu}: ca {k.ca_ngoai_pham_vi} không có `pytest.raises`"
        else:
            assert any(isinstance(n, ast.Assert) for n in ast.walk(ham)), f"{ky_hieu}: ca không khẳng định gì"

    def test_ca_goc_MT_71_nam_trong_tap_quet(self) -> None:
        """Neo: nếu máy quét mất khả năng đi bắc cầu, ca sinh ra luật này sẽ rơi khỏi tập quét."""
        thuc = ham_vuot_ranh(REPO_ROOT)
        assert "tool_d.ablation.thanh_ly.liq_buffer_ke_hoach" in thuc
        assert "src/tool_d/cong_thanh_ly.py" in thuc["tool_d.ablation.thanh_ly.liq_buffer_ke_hoach"]


# ─────────────────────────────── máy quét có răng ───────────────────────────────


def _cay_gia(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, noi_dung in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(noi_dung, encoding="utf-8")
    for d in GOC_QUYET_DINH:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


_DO = {"src/tool_d/ablation/do_moi.py": "HANG = 1\nclass Kieu: ...\ndef ham_do(x):\n    return x\n"}


class TestMayQuetCoRang:
    def test_bat_import_TRUC_TIEP(self, tmp_path: Path) -> None:
        goc = _cay_gia(tmp_path, {**_DO, "user_data/strategies/S.py": "from tool_d.ablation.do_moi import ham_do\n"})
        assert set(ham_vuot_ranh(goc)) == {"tool_d.ablation.do_moi.ham_do"}

    def test_bat_import_BAC_CAU_qua_module_trung_gian(self, tmp_path: Path) -> None:
        """Hình dạng đúng của ca `MT-71`: chiến lược → module trung gian → hàm tầng đo."""
        goc = _cay_gia(tmp_path, {
            **_DO,
            "src/tool_d/cong.py": "from tool_d.ablation.do_moi import ham_do\n",
            "user_data/strategies/S.py": "from tool_d.cong import x\n",
        })
        assert ham_vuot_ranh(goc) == {"tool_d.ablation.do_moi.ham_do": {"src/tool_d/cong.py"}}

    def test_bat_import_LUOI_trong_than_ham(self, tmp_path: Path) -> None:
        goc = _cay_gia(tmp_path, {
            **_DO, "src/tool_d/ops/b.py": "def f():\n    from tool_d.ablation.do_moi import ham_do\n",
        })
        assert set(ham_vuot_ranh(goc)) == {"tool_d.ablation.do_moi.ham_do"}

    def test_bat_thuoc_tinh_khi_import_ca_module(self, tmp_path: Path) -> None:
        goc = _cay_gia(tmp_path, {
            **_DO, "src/tool_d/ops/b.py": "from tool_d.ablation import do_moi\ny = do_moi.ham_do(1) + do_moi.HANG\n",
        })
        assert set(ham_vuot_ranh(goc)) == {"tool_d.ablation.do_moi.ham_do"}

    def test_hang_va_kieu_KHONG_tinh_la_ham(self, tmp_path: Path) -> None:
        goc = _cay_gia(tmp_path, {**_DO, "user_data/strategies/S.py": "from tool_d.ablation.do_moi import HANG, Kieu\n"})
        assert set(quet_vuot_ranh(goc)) == {"tool_d.ablation.do_moi.HANG", "tool_d.ablation.do_moi.Kieu"}
        assert ham_vuot_ranh(goc) == {}

    def test_module_khong_ai_o_tang_quyet_dinh_goi_thi_KHONG_tinh(self, tmp_path: Path) -> None:
        goc = _cay_gia(tmp_path, {**_DO, "src/tool_d/ablation/chay_lo.py": "from tool_d.ablation.do_moi import ham_do\n"})
        assert ham_vuot_ranh(goc) == {}

    def test_ky_hieu_khong_phan_loai_duoc_thi_FAIL_CLOSED(self, tmp_path: Path) -> None:
        goc = _cay_gia(tmp_path, {**_DO, "user_data/strategies/S.py": "from tool_d.ablation.do_moi import khong_co\n"})
        with pytest.raises(AssertionError, match="không phân loại được"):
            ham_vuot_ranh(goc)


# ─────────────────────── lấp khoảng hở: liq_buffer_ke_hoach ngoài phạm vi ───────────────────────

P = (100.0, 98.0, 96.0)
W = (0.5, 0.3, 0.2)


def _tinh_6(pair, open_rate, amount, stake, leverage, la_short=False):
    return 130.0 if la_short else 66.0


def _goi(**kw):
    goc = dict(pair="LTC/USDT:USDT", p=P, sl=90.0, w=W, n_full=300.0, don_bay=5.0, liquidation_buffer=0.05,
               tinh_liq=_tinh_6)
    return liq_buffer_ke_hoach(**{**goc, **kw})


class TestLiqBufferNgoaiPhamVi:
    def test_trong_pham_vi_ca_hai_chieu_ra_so(self) -> None:
        """Đối chứng: ca ngoài phạm vi đỏ vì phạm vi, không vì vật dựng hỏng."""
        assert _goi().ty_so > 0
        assert _goi(sl=110.0, la_short=True).ty_so > 0

    @pytest.mark.parametrize("sl,la_short", [(99.5, False), (120.0, False), (95.0, True), (98.0, True)])
    def test_sl_sai_phia_thi_NEM_LOI(self, sl: float, la_short: bool) -> None:
        with pytest.raises(ThanhLyError, match="sai phía"):
            _goi(sl=sl, la_short=la_short)

    def test_chieu_SHORT_voi_ham_5_doi_so_thi_NEM_ThanhLyError_khong_phai_TypeError(self) -> None:
        """Cửa hở thứ hai của `MT-71`: `TypeError` mà ai đó bắt `Exception` quanh lời gọi = từ chối im lặng."""
        def tinh_5(pair, open_rate, amount, stake, leverage):
            return 130.0

        with pytest.raises(ThanhLyError, match="la_short"):
            _goi(sl=110.0, la_short=True, tinh_liq=tinh_5)

    @pytest.mark.parametrize(
        "kw,khop",
        [
            ({"w": (0.5, 0.3)}, "trọng số"),
            ({"w": (0.5, 0.3, 0.3)}, "tổng trọng số"),
            ({"n_full": 0.0}, "phải dương"),
            ({"don_bay": -1.0}, "phải dương"),
            ({"p": (100.0, 0.0, 96.0)}, "phải dương"),
        ],
    )
    def test_ke_hoach_sai_hinh_thi_NEM_LOI(self, kw: dict, khop: str) -> None:
        with pytest.raises(ThanhLyError, match=khop):
            _goi(**kw)
