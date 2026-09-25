"""TD-0335 (`DR-D4-14`) — test khoá cho bộ chạy ablation E3 (`ablation/chay_lo.py` + `run_ablation.py`).

Canh, theo thứ tự quan trọng giảm dần:

1. 🔴 **Khoá đo GHIM `True`** — `DR-IQ-01` §1 + `DR-D4-14` §2.2. Ca này đỏ ⇔ ai đó đã lật
   khoá; sửa nó là nối lại D4-đo và phải đi cùng DR nối lại (`DR-D4-14` §6).
   19/09/2026: ghim `False` theo `DR-D4-19` cho đúng một lô; các ca "khoá bật" ở mục 2 nay tự đặt
   `True` bằng monkeypatch (tiền điều kiện tường minh, câu kiểm không đổi).
2. 🔴 **Khoá bật ⇒ 0 suất, 0 dữ liệu**: `chay_lo()` từ chối ở LỆNH ĐẦU (AST), không dựng môi
   trường, không mở sổ; E3 `--chay` thoát `EXIT_D4_DO_TAM_DUNG` và không tạo `TrialLedger`.
3. 🔴 **Đặt chỗ ĐỦ CẢ LÔ trước arm đầu** (`DR-D4-10` §2.3) — mỗi lần gọi bộ chạy, cả 4 suất đã
   RESERVED; suất đang chạy chưa có con dấu (`L-Z52` trên đường E3).
4. 🔴 **`L-Z53` trên đường E3**: lỗi SAU con dấu ⇒ suất đó CONSUMED (không hoàn trả), các
   arm chưa chạy được hoàn trả; lỗi MÁY trước con dấu ⇒ hoàn trả arm đó + arm chưa chạy.
5. **Chạy THẬT, khoá tắt, trên repo giả + dữ liệu tổng hợp + sổ tạm** — 4 arm đi đủ
   RESERVE→SEAL→CONSUME `B2`, 4 bản ghi hợp lệ + khớp schema.

⚠️ Mọi ca mở khoá đều vá `khoa_do.D4_DO_TAM_DUNG` trong tiến trình test (monkeypatch), trên
repo GIẢ và sổ TẠM. Không ca nào chạm rổ/dữ liệu thật hay `registry/trial_registry.jsonl`.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import shutil
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest

from tool_d.ablation import chay_lo as mod_chay_lo
from tool_d.ablation import khoa_do
from tool_d.ablation.ban_ghi import LO_ARM_D4
from tool_d.ablation.chay_lo import KeHoachLo, KhoaDoError, LoDungError, chay_lo
from tool_d.bo_chay.chay import BacktestHongError
from tool_d.bo_chay.yeu_cau import KetQuaChay
from tool_d.gates.arm_record import validate_arm_record
from tool_d.ledger.registry import TrialLedger, TrialState
from tool_d.measurement.gitinfo import GitInfo
from tool_d.measurement.tri_state import Measured
from tool_d.wfo.folds import Fold

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "registry/schemas/arm_result.schema.json").read_text(encoding="utf-8"))
DIGEST = "sha256:" + "a" * 64
GIT = GitInfo(sha="0" * 40, is_clean=True)
DELTA_R = {"so_ma": 2, "so_fill": 91, "dataset": "CALIB", "chien_luoc": "ZoneAbsorptionMinimal"}
MA = "LTCUSDT"
TU, DEN = date(2025, 3, 15), date(2025, 4, 2)  # = TIMERANGE của fixture td0187
FOLDS = (
    Fold(1, TU, date(2025, 3, 20), date(2025, 3, 20), date(2025, 3, 26)),
    Fold(2, TU, date(2025, 3, 26), date(2025, 3, 26), date(2025, 4, 1)),
)


# ── 1. khoá ghim ─────────────────────────────────────────────────────────────


class TestKhoaGhim:
    def test_khoa_do_dang_BAT(self) -> None:
        # 19/09/2026 — từng ghim `False` theo DR-D4-19 (mở đúng MỘT lô 4 arm, ghi đè DR-IQ-01 §1).
        # 🔄 20/09/2026 (TD-0362, chủ dự án chốt): lô đã chạy xong (D-0019…D-0022 CONSUMED) ⇒ đúng ca mà
        # dòng chú thích cũ hẹn trước — khẳng định trả về `is True`. Đây KHÔNG phải nới chốt: nó siết lại.
        assert khoa_do.D4_DO_TAM_DUNG is True, (
            "Lô DR-D4-20 đã tiêu đủ 4 suất B2 ⇒ khoá đo phải đóng lại (DR-D4-19 §4, vế mà "
            "DR-TRIEN-KHAI-01 §1 GIỮ). Mở lại cần một DR nối lại — DR-D4-14 §2.2/§6."
        )


# ── 2. khoá bật ⇒ 0 suất, 0 dữ liệu ─────────────────────────────────────────


def _than(ham: str, nguon: Path) -> list[ast.stmt]:
    cay = ast.parse(nguon.read_text(encoding="utf-8"))
    f = next(n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef) and n.name == ham)
    than = list(f.body)
    if than and isinstance(than[0], ast.Expr) and isinstance(getattr(than[0], "value", None), ast.Constant):
        than = than[1:]  # bỏ docstring
    return than


class TestKhoaBat:
    def test_tu_choi_la_LENH_DAU_cua_chay_lo(self) -> None:
        dau = _than("chay_lo", REPO / "src/tool_d/ablation/chay_lo.py")[0]
        assert isinstance(dau, ast.Expr) and isinstance(dau.value, ast.Call)
        assert getattr(dau.value.func, "id", None) == "_tu_choi_neu_khoa"

    def test_chay_lo_khong_dung_moi_truong_khong_mo_so(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(khoa_do, "D4_DO_TAM_DUNG", True)  # tiền điều kiện tường minh (DR-D4-19)
        goi: list[str] = []
        monkeypatch.setattr(mod_chay_lo, "dung_moi_truong", lambda **k: goi.append("mt"))
        monkeypatch.setattr(mod_chay_lo, "ro_cho_tap", lambda *a, **k: goi.append("ro"))
        so = tmp_path / "so.jsonl"
        with pytest.raises(KhoaDoError, match="DR-IQ-01"):
            chay_lo(
                KeHoachLo(tu=TU, den_khong_gom=DEN, hypothesis_slot="X"),
                ledger=TrialLedger(path=so), repo_dir=tmp_path, thu_muc_ra=tmp_path / "runs",
                folds=FOLDS, delta_r_pham_vi=DELTA_R, git_info=GIT, runtime_image_digest=DIGEST,
                chay=lambda *a, **k: goi.append("chay"),
            )
        # `TrialLedger(path=…)` tự tạo file rỗng lúc khởi tạo — điều cần là 0 SỰ KIỆN.
        assert goi == [] and so.read_text(encoding="utf-8").strip() == ""

    def test_E3_khoa_dung_truoc_chay_lo_va_main_khong_tu_dat_cho(self) -> None:
        nguon = (REPO / "entrypoints/run_ablation.py").read_text(encoding="utf-8")
        than = nguon.split("def main(")[1]
        assert than.index("if khoa_do.D4_DO_TAM_DUNG") < than.index("chay_lo(")
        assert ".reserve(" not in than, "main() không tự đặt chỗ — mọi đặt chỗ nằm SAU khoá, trong chay_lo()"

    def test_ma_thoat_moi_khong_trung(self) -> None:
        import re

        dung: dict[int, set[str]] = {}
        for f in list((REPO / "entrypoints").glob("*.py")) + list((REPO / "src").rglob("*.py")):
            for ten, so in re.findall(r"^(\w*EXIT\w*) = (\d+)", f.read_text(encoding="utf-8"), re.M):
                dung.setdefault(int(so), set()).add(ten)
        for so in (109, 110, 111, 112):
            assert len(dung.get(so, set())) == 1, f"mã thoát {so} mang nhiều tên: {dung.get(so)}"


def _nap_e3():
    sys.path.insert(0, str(REPO / "entrypoints"))
    spec = importlib.util.spec_from_file_location("run_ablation_td0335", REPO / "entrypoints/run_ablation.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def e3_qua_nam_cong(monkeypatch):
    """E3 với năm cổng cũ vá thành "qua" — ca dưới chỉ hỏi phần TD-0335 sau chúng."""
    e3 = _nap_e3()
    monkeypatch.setattr(e3, "measurement_guard", lambda *a, **k: SimpleNamespace(outcome=None))
    monkeypatch.setattr(e3, "require_d0_pre_complete", lambda *a: None)
    monkeypatch.setattr(e3, "run_audit", lambda *a, **k: (0, ""))
    monkeypatch.setattr(e3, "kiem_cong_d35", lambda *a, **k: None)
    monkeypatch.setattr(e3, "in_va_ma_thoat", lambda *a, **k: None)
    monkeypatch.setattr(e3, "kiem_h17", lambda *a, **k: None)

    def _cam(*a, **k):
        raise AssertionError("TrialLedger bị tạo — khoá đo phải chặn TRƯỚC mọi đặt chỗ")

    monkeypatch.setattr(e3, "TrialLedger", _cam)
    return e3


class TestE3Main:
    def test_khong_co_chay_chi_in_ke_hoach(self, e3_qua_nam_cong) -> None:
        assert e3_qua_nam_cong.main([]) == e3_qua_nam_cong.EXIT_E3_CHUA_XAC_NHAN_CHAY == 109

    def test_chay_khi_khoa_bat_thi_tu_choi(self, e3_qua_nam_cong, capsys, monkeypatch) -> None:
        monkeypatch.setattr(khoa_do, "D4_DO_TAM_DUNG", True)  # tiền điều kiện tường minh (DR-D4-19)
        assert e3_qua_nam_cong.main(["--chay", "--hypothesis-slot", "X"]) == e3_qua_nam_cong.EXIT_D4_DO_TAM_DUNG == 110
        assert "DR-IQ-01" in capsys.readouterr().out

    def test_khoa_dung_truoc_ca_kiem_hypothesis_slot(self, e3_qua_nam_cong, monkeypatch) -> None:
        monkeypatch.setattr(khoa_do, "D4_DO_TAM_DUNG", True)  # tiền điều kiện tường minh (DR-D4-19)
        assert e3_qua_nam_cong.main(["--chay"]) == 110


# ── 3–4. thứ tự đặt chỗ + L-Z52/L-Z53 trên đường E3 (bộ chạy giả) ──────────


@pytest.fixture
def repo_nhe(tmp_path) -> Path:
    """Repo giả tối thiểu: `config/`, rổ T1 giả một mã, thư mục dữ liệu rỗng."""
    goc = tmp_path / "repo"
    shutil.copytree(REPO / "config", goc / "config")
    (goc / "config" / "pool_t1.yaml").write_text(f"moc_t1: '2025-06-12'\ntrading:\n- {MA}\n", encoding="utf-8")
    (goc / "user_data" / "data" / "pool_t1" / "futures").mkdir(parents=True)
    return goc


def _kq_gia(lenh=()) -> KetQuaChay:
    return KetQuaChay(
        tap="WFO", moc_ro="2025-06-12", file_ro=Path("config/pool_t1.yaml"),
        thu_muc_du_lieu=Path("user_data/data/pool_t1/futures"), ma_da_chay=(MA,),
        timerange_yeu_cau="20250315-20250402", observed_start=TU, observed_end=date(2025, 4, 1),
        du_lieu_co_tu=TU, du_lieu_co_den=date(2025, 4, 1), starting_balance=750.0,
        final_balance=750.0, pnl_abs=tuple(0.0 for _ in lenh), lenh=tuple(lenh),
        config_sha256="x", duong_ket_qua=Path("x.zip"), chien_luoc="ZoneAbsorption",
    )


def _goi_lo(repo: Path, so: TrialLedger, chay) -> list:
    return chay_lo(
        KeHoachLo(tu=TU, den_khong_gom=DEN, hypothesis_slot="TD-0335-TEST"),
        ledger=so, repo_dir=repo, thu_muc_ra=repo / "runs", folds=FOLDS,
        delta_r_pham_vi=DELTA_R, git_info=GIT, runtime_image_digest=DIGEST, chay=chay,
    )


def _su_kien(so_path: Path) -> list[dict]:
    return [json.loads(d) for d in so_path.read_text(encoding="utf-8").splitlines() if d.strip()]


class TestThuTuVaLZ52LZ53:
    def test_dat_cho_du_ca_lo_truoc_arm_dau(self, repo_nhe, monkeypatch) -> None:
        monkeypatch.setattr(khoa_do, "D4_DO_TAM_DUNG", False)
        so_path = repo_nhe / "so.jsonl"
        so = TrialLedger(path=so_path)
        thay: list[tuple[int, str, TrialState, bool]] = []

        def chay(yc, *, giay_phep, **k):
            p = so.projections()
            thay.append((len(p), giay_phep.trial_id, p[giay_phep.trial_id].state, p[giay_phep.trial_id].sealed))
            raise BacktestHongError("dừng sau lần gọi đầu để chỉ kiểm thứ tự", returncode=2)

        with pytest.raises(LoDungError):
            _goi_lo(repo_nhe, so, chay)
        so_luot, tid, trang_thai, da_niem = thay[0]
        assert so_luot == len(LO_ARM_D4), "chưa đặt chỗ đủ cả lô trước arm đầu (DR-D4-10 §2.3)"
        assert trang_thai is TrialState.RESERVED and not da_niem  # L-Z52: có đặt chỗ hợp lệ, chưa con dấu
        su = [e["event"] for e in _su_kien(so_path)]
        assert su[: len(LO_ARM_D4)] == ["RESERVE"] * len(LO_ARM_D4)
        assert all(e["budget_line"] == "B2" for e in _su_kien(so_path) if e["event"] == "RESERVE")

    def test_loi_may_truoc_con_dau_hoan_tra_arm_do_va_arm_chua_chay(self, repo_nhe, monkeypatch) -> None:
        monkeypatch.setattr(khoa_do, "D4_DO_TAM_DUNG", False)
        monkeypatch.setattr(mod_chay_lo, "lenh_tu_freqtrade", lambda t, **k: t)
        monkeypatch.setattr(mod_chay_lo, "chi_so_tu_export", lambda **k: {"bat_bien_1_7_ty_so_trung_vi": Measured.unreadable("giả")})
        monkeypatch.setattr(mod_chay_lo, "dung_ban_ghi_arm", lambda **k: {
            "chi_so": {"mean_r": {"status": "ok", "value": 0.1}}, "ket_cuc": {"status": "ok", "value": "INCONCLUSIVE"},
        })
        so = TrialLedger(path=repo_nhe / "so.jsonl")
        dem = {"n": 0}

        def chay(yc, *, giay_phep, **k):
            dem["n"] += 1
            if dem["n"] == 2:
                raise BacktestHongError("rc=3", returncode=3)
            return _kq_gia(lenh=[{"x": 1}])

        with pytest.raises(LoDungError):
            _goi_lo(repo_nhe, so, chay)
        trang = {p.param_value: p.state for p in so.projections().values()}
        assert trang[LO_ARM_D4[0]] is TrialState.CONSUMED
        assert all(trang[a] is TrialState.REFUNDED for a in LO_ARM_D4[1:])

    def test_loi_SAU_con_dau_la_CONSUMED_khong_hoan_tra(self, repo_nhe, monkeypatch) -> None:
        monkeypatch.setattr(khoa_do, "D4_DO_TAM_DUNG", False)
        so = TrialLedger(path=repo_nhe / "so.jsonl")
        # lệnh không có tranche đã khớp ⇒ trich_lenh raise SAU khi đã seal
        with pytest.raises(LoDungError, match="SAU con dấu"):
            _goi_lo(repo_nhe, so, lambda yc, **k: _kq_gia(lenh=[{"pair": "LTC/USDT:USDT", "profit_abs": 1.0, "orders": []}]))
        p = {x.param_value: x for x in so.projections().values()}
        dau = p[LO_ARM_D4[0]]
        assert dau.sealed and dau.state is TrialState.CONSUMED and not dau.refunded
        assert "loi_sau_niem_phong" in json.dumps(_su_kien(repo_nhe / "so.jsonl"))
        assert all(p[a].state is TrialState.REFUNDED for a in LO_ARM_D4[1:])


# ── 5. chạy THẬT, khoá tắt, repo giả ────────────────────────────────────────


def _nap_td0187():
    spec = importlib.util.spec_from_file_location(
        "td0187_e3", REPO / "tests" / "lock" / "test_td0187_dinh_co_lenh_backtest_that.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def lo_that(tmp_path_factory):
    td = _nap_td0187()
    goc = tmp_path_factory.mktemp("td0335") / "repo"
    shutil.copytree(REPO / "config", goc / "config")
    (goc / "config" / "pool_t1.yaml").write_text(f"moc_t1: '2025-06-12'\ntrading:\n- {MA}\n", encoding="utf-8")
    shutil.copytree(REPO / "user_data" / "strategies", goc / "user_data" / "strategies")
    # TD-0402 (`DR-SHORT-02` §3): Short bật ⇒ `L-Z56` chặn mọi lượt E3 khi chưa có Δ_R(SHORT) — đúng thiết kế, có test
    # riêng (`test_lz56_*`). Lô E3 ở đây là máy ablation LONG của ZA ⇒ tắt Short TƯỜNG MINH trong bản sao cấu hình.
    yaml_p = goc / "config" / "tool_d_config.yaml"
    y = yaml_p.read_text(encoding="utf-8")
    assert y.count("enable_short: true") == 1, "YAML không còn đúng một dòng enable_short: true — cập nhật fixture"
    yaml_p.write_text(y.replace("enable_short: true", "enable_short: false"), encoding="utf-8")
    td._sinh_du_lieu(goc / "user_data" / "data" / "pool_t1")
    so_path = goc / "so.jsonl"
    mp = pytest.MonkeyPatch()
    mp.setattr(khoa_do, "D4_DO_TAM_DUNG", False)
    try:
        kq = chay_lo(
            KeHoachLo(tu=TU, den_khong_gom=DEN, hypothesis_slot="TD-0335-TEST", ma_gioi_han=(MA,)),
            ledger=TrialLedger(path=so_path), repo_dir=goc, thu_muc_ra=goc / "runs", folds=FOLDS,
            delta_r_pham_vi=DELTA_R, git_info=GIT, runtime_image_digest=DIGEST,
        )
    finally:
        mp.undo()
    return kq, so_path


class TestLoThat:
    def test_bon_arm_du_ban_ghi_hop_le(self, lo_that) -> None:
        kq, _ = lo_that
        assert [k.arm for k in kq] == list(LO_ARM_D4)
        for k in kq:
            bg = json.loads(k.duong_ban_ghi.read_text(encoding="utf-8"))
            assert validate_arm_record(bg) == [], k.arm
            jsonschema.validate(bg, SCHEMA)
            assert bg["provenance"]["params_effective"]["tier_c.arm_ablation.arm"] == k.arm
            assert bg["pham_vi_phan_quyet"] == ("phan_quyet" if k.arm == "Z0-T1" else "mo_ta")

    def test_so_B2_du_vong_doi(self, lo_that) -> None:
        _, so_path = lo_that
        so = TrialLedger(path=so_path)
        p = so.projections()
        assert len(p) == len(LO_ARM_D4)
        for x in p.values():
            assert x.budget_line == "B2" and x.dataset == "WFO"
            assert x.sealed and x.state is TrialState.CONSUMED
        su = [e["event"] for e in _su_kien(so_path)]
        assert su.index("SEAL") == len(LO_ARM_D4), "SEAL đầu tiên phải đến SAU đủ 4 RESERVE"
