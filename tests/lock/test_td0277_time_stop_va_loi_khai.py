"""🔒 TD-0277 (MT-46, chủ dự án chốt 18/09/2026) — hai chốt:

1. Dải TIME_STOP 5–25% là tiêu chí CHẶN của Nhánh 1, cả hai biên (spec
   :4277-4278 + :4290). Trước đó `TIME_STOP_RATIO_BAND` có đúng một lần xuất
   hiện toàn repo — tại dòng định nghĩa.
2. Lời khai FROZEN phải KHỚP ĐĨA (`check_td0277_loi_khai_frozen_khop_dia`):
   rà 18/09 thấy 3/12 lời khai sai cùng một cơ chế — *"chưa có đường chạy nào
   chạm tới"* hết đúng khi code nối vào sau.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest
import yaml

from tool_d.gates.cscv import KetQuaPBO
from tool_d.gates.d9_gate import TIEU_CHI_KHAI, danh_gia_cong_d9
from tool_d.gates.dsr import N_DANG_KY
from tool_d.gates.ket_cuc import KetCuc
from tool_d.gates.thresholds import (
    DSR_ADJ_EXPECTANCY_MIN,
    TIME_STOP_RATIO_BAND,
    Verdict,
    best_known_result_for_test,
    evaluate_branch1,
)
from tool_d.ledger.audit_checks import (
    DEFAULT_PARAM_STATUS_PATH,
    check_td0277_loi_khai_frozen_khop_dia,
    dem_cho_doc_tier_b,
)
from tool_d.measurement.tri_state import Measured

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))
from trial_ledger_audit import run_audit  # noqa: E402

STATUS_THAT = REPO_ROOT / DEFAULT_PARAM_STATUS_PATH


# ═══════════════════════════ 1. TIME_STOP ═══════════════════════════
def _metrics_dat(**sua: float) -> dict[str, float]:
    m = best_known_result_for_test()
    m["dsr_adjusted_expectancy"] = DSR_ADJ_EXPECTANCY_MIN + 0.01
    m.update(sua)
    return m


class TestTimeStopChanCaHaiBien:
    def test_dai_dung_chu_spec(self) -> None:
        assert TIME_STOP_RATIO_BAND == (0.05, 0.25)

    @pytest.mark.parametrize("ty_le", [0.05, 0.10, 0.25])
    def test_trong_dai_ke_ca_bien_thi_pass(self, ty_le: float) -> None:
        assert evaluate_branch1(_metrics_dat(time_stop_ratio=ty_le), pbo_chan=True).verdict is Verdict.PASS

    @pytest.mark.parametrize("ty_le", [0.0, 0.049, 0.251, 0.30])
    def test_ngoai_dai_thi_fail_dung_mot_tieu_chi(self, ty_le: float) -> None:
        """0.0 chính là con số `Z0-T1` đo được (td0246) — hệ quả biết trước, khai trong MT-46."""
        r = evaluate_branch1(_metrics_dat(time_stop_ratio=ty_le), pbo_chan=True)
        assert r.verdict is Verdict.FAIL and r.failed_criteria == ("time_stop_ratio",)

    def test_thieu_khoa_thi_fail_khong_pass_ngam(self) -> None:
        m = _metrics_dat()
        del m["time_stop_ratio"]
        assert evaluate_branch1(m, pbo_chan=True).failed_criteria == ("time_stop_ratio",)

    def test_nan_thi_fail(self) -> None:
        r = evaluate_branch1(_metrics_dat(time_stop_ratio=math.nan), pbo_chan=True)
        assert r.failed_criteria == ("time_stop_ratio",)

    def test_d4_cung_chan_khong_chi_d9(self) -> None:
        """Khác PBO (D4 chỉ ghi): TIME_STOP chặn ở mọi nơi gọi."""
        r = evaluate_branch1(_metrics_dat(time_stop_ratio=0.0), pbo_chan=False)
        assert r.failed_criteria == ("time_stop_ratio",)


def _goi_d9(ts: Measured[float]):
    chi_so = {
        "liq_buffer_ratio_mean": Measured.ok(20.0),
        "max_single_trade_loss_over_risk_budget": Measured.ok(1.0),
        "skewness_diff_vs_z1": Measured.ok(0.0),
        "trades_per_year": Measured.ok(300.0),
        "tp_fallback_ratio": Measured.ok(0.1),
        "time_stop_ratio": ts,
    }
    pbo = KetQuaPBO(
        pbo=Measured.ok(0.2), so_cau_hinh_dau_vao=4, so_cau_hinh_phan_biet=4, cau_hinh_gop_trung=(),
        so_to_hop=70, so_to_hop_doc_duoc=70, to_hop=(),
    )
    return danh_gia_cong_d9(
        r_trien_khai_test=[1.0 + (0.1 if i % 2 else -0.1) for i in range(100)],
        n_trials=N_DANG_KY, chi_so=chi_so, ket_qua_pbo=pbo,
    )


class TestCongD9KhaiTimeStop:
    def test_tieu_chi_nam_trong_danh_sach_khai(self) -> None:
        assert "time_stop_ratio" in TIEU_CHI_KHAI

    def test_chua_do_thi_inconclusive_khong_phai_fail_gia(self) -> None:
        kq = _goi_d9(Measured.pending("chưa có lệnh đoạn test"))
        assert kq.ket_cuc is KetCuc.INCONCLUSIVE and kq.chua_do == ("time_stop_ratio",)
        assert kq.khong_dat == ()

    def test_do_duoc_0_thi_fail(self) -> None:
        kq = _goi_d9(Measured.ok(0.0))
        assert kq.ket_cuc is KetCuc.FAIL and kq.khong_dat == ("time_stop_ratio",)

    def test_trong_dai_thi_pass(self) -> None:
        assert _goi_d9(Measured.ok(0.10)).ket_cuc is KetCuc.PASS


# ═══════════════════════ 2. Lời khai khớp đĩa ═══════════════════════
class TestFileSanXuatThat:
    def test_file_that_dat(self) -> None:
        r = check_td0277_loi_khai_frozen_khop_dia(STATUS_THAT, REPO_ROOT)
        assert r.ok, r.evidence

    def test_ba_loi_khai_sai_cu_nay_khai_co_nguoi_doc(self) -> None:
        """Ba tham số MT-46 bắt sai phải mang `doc_boi_san_xuat: true` — và đĩa phải đồng ý."""
        doc = yaml.safe_load(STATUS_THAT.read_text(encoding="utf-8"))["params"]
        cho_doc, _ = dem_cho_doc_tier_b(REPO_ROOT)
        for ten in ("dg7_funding_frac", "tp1_haircut_pct", "mult_corr_thresholds"):
            assert doc[ten]["doc_boi_san_xuat"] is True
            assert cho_doc.get(ten), ten

    def test_khong_co_ghep_ten_khoa_dong(self) -> None:
        _, dong = dem_cho_doc_tier_b(REPO_ROOT)
        assert dong == []

    def test_co_rang_lat_dg7_ve_loi_khai_cu_thi_do(self, tmp_path: Path) -> None:
        """Tái hiện đúng lời khai cũ của dg7 (*"chưa có đường chạy nào chạm tới"*) trên code THẬT."""
        doc = yaml.safe_load(STATUS_THAT.read_text(encoding="utf-8"))
        doc["params"]["dg7_funding_frac"]["doc_boi_san_xuat"] = False
        st = tmp_path / "param_status.yaml"
        st.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
        r = check_td0277_loi_khai_frozen_khop_dia(st, REPO_ROOT)
        assert r.is_fail and "dg7_funding_frac" in r.evidence and "ZoneAbsorption.py" in r.evidence


def _goc_gia(tmp_path: Path, code: str) -> Path:
    goc = tmp_path / "repo"
    (goc / "src/tool_d").mkdir(parents=True)
    (goc / "user_data/strategies").mkdir(parents=True)
    (goc / "src/tool_d/mod.py").write_text(code, encoding="utf-8")
    (goc / "ghi_chu.md").write_text("a\nb\nc\n", encoding="utf-8")
    return goc


CODE_CHUAN = (
    '"""Module mẫu. Docstring nhắc "tier_b.b" — không phải chỗ đọc."""\n'
    "# chú thích nhắc \"tier_b.b\" — không nằm trong AST\n"
    "def f(cfg):\n"
    '    return resolve(cfg, "tier_b.a")\n'
)


def _status(tmp_path: Path, **muc: dict) -> Path:
    goc_muc = {
        "a": {"status": "FROZEN", "frozen_rationale": "x", "doc_boi_san_xuat": True,
              "bang_chung": ["src/tool_d/mod.py:4"]},
        "b": {"status": "FROZEN", "frozen_rationale": "x", "doc_boi_san_xuat": False,
              "bang_chung": ["ghi_chu.md:2"]},
    }
    for ten, sua in muc.items():
        goc_muc[ten] = {**goc_muc[ten], **sua} if sua is not None else None
    goc_muc = {k: v for k, v in goc_muc.items() if v is not None}
    p = tmp_path / "status.yaml"
    p.write_text(yaml.safe_dump({"params": goc_muc}, allow_unicode=True), encoding="utf-8")
    return p


class TestCaDungTay:
    def test_khop_thi_dat_va_docstring_chu_thich_khong_tinh(self, tmp_path: Path) -> None:
        goc = _goc_gia(tmp_path, CODE_CHUAN)
        r = check_td0277_loi_khai_frozen_khop_dia(_status(tmp_path), goc)
        assert r.ok, r.evidence
        assert "1 có code sản xuất đọc, 1 không (b)" in r.evidence

    def test_khai_khong_doc_ma_co_doc_thi_do(self, tmp_path: Path) -> None:
        """Hình dạng lỗi lỗi thời: code nối vào sau, lời khai `false` còn nguyên."""
        goc = _goc_gia(tmp_path, CODE_CHUAN)
        r = check_td0277_loi_khai_frozen_khop_dia(_status(tmp_path, a={"doc_boi_san_xuat": False}), goc)
        assert r.is_fail and "a: khai doc_boi_san_xuat=False nhưng đĩa có 1 chỗ đọc" in r.evidence

    def test_khai_co_doc_ma_khong_ai_doc_thi_do(self, tmp_path: Path) -> None:
        goc = _goc_gia(tmp_path, CODE_CHUAN)
        r = check_td0277_loi_khai_frozen_khop_dia(_status(tmp_path, b={"doc_boi_san_xuat": True}), goc)
        assert r.is_fail and "b: khai doc_boi_san_xuat=True nhưng đĩa có 0 chỗ đọc" in r.evidence

    @pytest.mark.parametrize("xau", [None, "true", 1])
    def test_doc_boi_phai_la_bool(self, tmp_path: Path, xau) -> None:
        goc = _goc_gia(tmp_path, CODE_CHUAN)
        r = check_td0277_loi_khai_frozen_khop_dia(_status(tmp_path, a={"doc_boi_san_xuat": xau}), goc)
        assert r.is_fail and "a: thiếu doc_boi_san_xuat" in r.evidence

    @pytest.mark.parametrize(
        ("bc", "chu"),
        [
            ([], "không rỗng"),
            (None, "không rỗng"),
            (["khong_co.py:1"], "file không tồn tại"),
            (["ghi_chu.md:4"], "file chỉ có 3 dòng"),
            (["ghi_chu.md:0"], "không đúng dạng"),
            (["ghi_chu.md"], "không đúng dạng"),
        ],
    )
    def test_bang_chung_hong_thi_do(self, tmp_path: Path, bc, chu: str) -> None:
        goc = _goc_gia(tmp_path, CODE_CHUAN)
        r = check_td0277_loi_khai_frozen_khop_dia(_status(tmp_path, b={"bang_chung": bc}), goc)
        assert r.is_fail and chu in r.evidence

    @pytest.mark.parametrize(
        "dong_dong",
        ['    return resolve(cfg, f"tier_b.{ten}")\n', '    return resolve(cfg, "tier_b." + ten)\n'],
    )
    def test_ghep_ten_khoa_dong_thi_do(self, tmp_path: Path, dong_dong: str) -> None:
        """Phép đếm mù với tên ghép động ⇒ fail-closed, không coi là 'không ai đọc'."""
        goc = _goc_gia(tmp_path, CODE_CHUAN + "def g(cfg, ten):\n" + dong_dong)
        r = check_td0277_loi_khai_frozen_khop_dia(_status(tmp_path), goc)
        assert r.is_fail and "động" in r.evidence

    def test_thong_diep_loi_bat_dau_bang_tier_b_khong_phai_doc_dong(self, tmp_path: Path) -> None:
        """Hình dạng thật ở `config/loader.py`: chuỗi ghép ngầm `"tier_b.x phải là null …" f"{v!r}"`.
        Lần chạy đầu của phép kiểm này báo nhầm nó là chỗ ghép tên khoá động."""
        code = CODE_CHUAN + 'def h(v):\n    raise ValueError("tier_b._x phải là null. Nhận: " f"{v!r}")\n'
        r = check_td0277_loi_khai_frozen_khop_dia(_status(tmp_path), _goc_gia(tmp_path, code))
        assert r.ok, r.evidence

    def test_chien_luoc_trong_user_data_cung_tinh(self, tmp_path: Path) -> None:
        goc = _goc_gia(tmp_path, CODE_CHUAN)
        (goc / "user_data/strategies/S.py").write_text('X = "tier_b.b"\n', encoding="utf-8")
        r = check_td0277_loi_khai_frozen_khop_dia(_status(tmp_path), goc)
        assert r.is_fail and "user_data/strategies/S.py:1" in r.evidence

    def test_chi_soi_frozen(self, tmp_path: Path) -> None:
        goc = _goc_gia(tmp_path, CODE_CHUAN)
        st = _status(tmp_path, b={"status": "TUNED", "doc_boi_san_xuat": None, "bang_chung": None})
        assert check_td0277_loi_khai_frozen_khop_dia(st, goc).ok

    def test_thieu_file_status_thi_do(self, tmp_path: Path) -> None:
        r = check_td0277_loi_khai_frozen_khop_dia(tmp_path / "khong_co.yaml", tmp_path)
        assert r.is_fail


class TestNoiVaoE6:
    def test_run_audit_goi_phep_kiem(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        iq = tmp_path / "iq.jsonl"
        reg.touch()
        iq.touch()
        _, text = run_audit(registry_path=reg, idea_queue_path=iq)
        assert "TD-0277: ✅ đạt" in text, text
