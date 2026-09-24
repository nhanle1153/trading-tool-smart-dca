"""TD-0389 (`DR-XAC-NHAN-01` §6, §7) — bộ đo lớp xác nhận: hạng sổ `XAC` ngoài `N`, tập `XAC_NHAN`, hai chế độ E1.

Trước việc này: `tran_von.py` (TD-0382/0387) kiểm một hiện vật mà KHÔNG đường nào sinh ra được. Nay:
- dòng ĐẾM = CTRL *đo mô tả* đúng `["so_lenh"]` trên `XAC_NHAN`; dòng TÍNH = `XAC`, đứng ngoài `N`, trần 1/slot;
- cửa ghi `XAC` thi hành Q2 bằng máy: cửa sổ của dòng TÍNH phải bằng cửa sổ của dòng ĐẾM ĐẦU TIÊN đạt n ≥ 30;
- E1 ghi hiện vật đúng khoá `tran_von` đòi — ca nối hai đầu ở `TestHienVatNoiHaiDau`.

Repo git THẬT trong `tmp_path` (khuôn `test_td0378`): `reserve()` tính vân tay lần chạy bằng git.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from tool_d.bo_chay.yeu_cau import BoChayError
from tool_d.config.loader import load_tool_d_config
from tool_d.config.tran_von import ly_do_chua_xac_nhan
from tool_d.ledger.audit_checks import check_td0119_so_bien_the_khong_vuot_khai
from tool_d.ledger.registry import (
    CtrlClaimError,
    ThietKeChuaKiemError,
    TrialLedger,
    XacClaimError,
)
from tool_d.ledger.timerange import TimerangeViolationError, bien_xac_nhan
from tool_d.pool_giai_doan import RoGiaiDoanError, ro_cho_tap

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "entrypoints"))
import run_backtest as e1  # noqa: E402

SLOT = "IQ-0003"
NGAY_CHON = "2026-10-01T10:00:00Z"
CFG_HASH = "c" * 64
PROVENANCE = {
    "params_source": "yaml",
    "params_effective": {},
    "git_sha": "a" * 40,
    "reproducible_from_sha": False,
    "data_hashes": {"BTC_USDT-1h.feather": "d" * 64},
    "cache_mode": "none",
    "guard_passed": True,
}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=repo, check=True,
                   capture_output=True)


def _ghi_jsonl(p: Path, dong: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(d) + "\n" for d in dong), encoding="utf-8")


def _y_tuong(*, voided: bool = False, so_bien_the: int | None = None) -> list[dict]:
    dong = [{"idea_id": SLOT, "status": "QUEUED", "selected_at": None},
            {"idea_id": SLOT, "status": "SELECTED", "selected_at": NGAY_CHON, "so_bien_the": so_bien_the}]
    if voided:
        dong.append({"idea_id": SLOT, "status": "VOIDED", "selected_at": NGAY_CHON})
    return dong


def _cham(cfg_hash: str = CFG_HASH) -> dict:
    return {"accessed_at": "2026-12-01T00:00:00Z", "reason": "D9.5", "config_hash": cfg_hash,
            "seal_path": "lockbox/lockbox_seal_1.json", "seal_file_hash": "e" * 64}


def _dung_repo(tmp_path: Path, *, y_tuong: list[dict] | None = None, cham: list[dict] | None = None) -> Path:
    r = tmp_path / "repo"
    (r / "config").mkdir(parents=True)
    shutil.copy(REPO / "config" / "tool_d_config.yaml", r / "config" / "tool_d_config.yaml")
    _ghi_jsonl(r / "registry" / "idea_queue.jsonl", _y_tuong() if y_tuong is None else y_tuong)
    if cham is None or cham:
        _ghi_jsonl(r / "lockbox" / "lockbox_access.log", [_cham()] if cham is None else cham)
    _git(r, "init", "-q")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "seed")
    return r


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _dung_repo(tmp_path)


def _cua_so(che_do: str, tu: str = "2026-10-01", den: str = "2026-12-20") -> dict:
    return {"che_do": che_do, "tu": tu, "den": den}


def _kw(**doi) -> dict:
    k = {
        "n_dang_ky": 114, "budget_line": "XAC", "hypothesis_slot": SLOT, "direction": "LONG",
        "dataset": "XAC_NHAN", "param_under_test": "xac_nhan_cua_so", "param_value": _cua_so("TINH"),
        "params_frozen_hash": CFG_HASH, "config_hash": CFG_HASH, "code_commit": "a" * 40,
        "provenance": PROVENANCE, "contribution": 1,
    }
    k.update(doi)
    return k


def _dem(so: TrialLedger, n: int, **cua_so) -> str:
    """Một lượt ĐẾM đã CONSUMED với `n` lệnh."""
    tid = so.reserve(**_kw(budget_line="CTRL", param_value=_cua_so("DEM", **cua_so), ctrl_mo_ta_whitelist=["so_lenh"]))
    so.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
    so.consume(tid, outcome={"expectancy": None, "sharpe": None, "n_trades": n, "max_single_loss_ratio": None},
               verdict="INCONCLUSIVE")
    return tid


def _so(tmp_path: Path, repo: Path) -> tuple[TrialLedger, Path]:
    p = tmp_path / "reg.jsonl"
    return TrialLedger(p, repo_dir=repo), p


def _so_dong(p: Path) -> int:
    return sum(1 for d in p.read_text(encoding="utf-8").splitlines() if d.strip()) if p.exists() else 0


class TestNgoaiNVaDuongHopLe:
    def test_dem_roi_tinh_ghi_duoc_va_khong_vao_N(self, tmp_path: Path, repo: Path) -> None:
        so, _ = _so(tmp_path, repo)
        _dem(so, 30)
        tid = so.reserve(**_kw())
        so.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        so.consume(tid, outcome={"expectancy": 0.12, "sharpe": None, "n_trades": 30, "max_single_loss_ratio": None},
                   verdict="INCONCLUSIVE")
        assert so.n_used() == 0 and so.n_reserved() == 0, "XAC/CTRL phải đứng NGOÀI N (điều kiện dừng DR §6)"

    def test_xac_da_REFUNDED_khong_tinh_tran(self, tmp_path: Path, repo: Path) -> None:
        """§7 Q7: máy hỏng TRƯỚC niêm phong ⇒ hoàn lại ⇒ được ghi lại."""
        so, _ = _so(tmp_path, repo)
        _dem(so, 30)
        tid = so.reserve(**_kw())
        so.refund(tid, cause_machine="freqtrade_backtesting_exit_2")
        assert so.reserve(**_kw())

    def test_tinh_phai_dung_cua_so_cua_lan_dem_DAU_TIEN_dat_nguong(self, tmp_path: Path, repo: Path) -> None:
        """§6 Q2 bằng máy: không được chờ thêm sau khi đã đếm đủ."""
        so, _ = _so(tmp_path, repo)
        _dem(so, 12, den="2026-11-01")
        _dem(so, 31, den="2026-12-20")
        _dem(so, 45, den="2027-01-10")
        with pytest.raises(XacClaimError, match="khác cửa sổ của lần ĐẾM đầu tiên"):
            so.reserve(**_kw(param_value=_cua_so("TINH", den="2027-01-10")))
        assert so.reserve(**_kw(param_value=_cua_so("TINH", den="2026-12-20")))


class TestTuChoiTaiCuaXac:
    @pytest.mark.parametrize(
        ("chuan_bi", "doi", "khop"),
        [
            ("khong_dem", {}, "chưa có dòng ĐẾM CONSUMED nào đạt n ≥ 30"),
            ("dem_29", {}, "chưa có dòng ĐẾM CONSUMED nào đạt n ≥ 30"),
            ("dem_30", {"config_hash": "f" * 64, "params_frozen_hash": "f" * 64}, "không phải cấu hình đã chạm lockbox"),
            ("dem_30", {"param_value": _cua_so("DEM")}, "che_do 'TINH'"),
            ("dem_30", {"dataset": "CALIB"}, "chỉ chạy trên tập XAC_NHAN"),
            ("dem_30", {"param_under_test": "zss_threshold"}, "xac_nhan_cua_so"),
            ("xac_da_co", {}, "trần 1/slot"),
        ],
    )
    def test_tu_choi_va_so_khong_doi(self, tmp_path: Path, repo: Path, chuan_bi: str, doi: dict, khop: str) -> None:
        so, p = _so(tmp_path, repo)
        if chuan_bi == "dem_29":
            _dem(so, 29)
        elif chuan_bi in ("dem_30", "xac_da_co"):
            _dem(so, 30)
        if chuan_bi == "xac_da_co":
            tid = so.reserve(**_kw())
            so.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        truoc = _so_dong(p)
        with pytest.raises(XacClaimError, match=khop):
            so.reserve(**_kw(**doi))
        assert _so_dong(p) == truoc

    def test_lan_chon_da_huy(self, tmp_path: Path) -> None:
        repo = _dung_repo(tmp_path, y_tuong=_y_tuong(voided=True))
        so, _ = _so(tmp_path, repo)
        with pytest.raises(XacClaimError, match="không có lần CHỌN còn hiệu lực"):
            so.reserve(**_kw())

    def test_chua_cham_lockbox(self, tmp_path: Path) -> None:
        repo = _dung_repo(tmp_path, cham=[])
        so, _ = _so(tmp_path, repo)
        with pytest.raises(XacClaimError, match="chưa có lần chạm lockbox nào"):
            so.reserve(**_kw())

    def test_cua_so_bat_dau_truoc_ngay_chon(self, tmp_path: Path, repo: Path) -> None:
        so, _ = _so(tmp_path, repo)
        _dem(so, 30, tu="2026-09-20")
        with pytest.raises(XacClaimError, match="trước ngày CHỌN"):
            so.reserve(**_kw(param_value=_cua_so("TINH", tu="2026-09-20")))


class TestTapXacNhanChiNhanHaiLoaiDong:
    @pytest.mark.parametrize("dong", ["B0", "B1", "B2", "B3"])
    def test_dong_ngan_sach_khac_bi_tu_choi(self, tmp_path: Path, repo: Path, dong: str) -> None:
        so, p = _so(tmp_path, repo)
        with pytest.raises(XacClaimError, match="chỉ nhận dòng ĐẾM"):
            so.reserve(**_kw(budget_line=dong, param_value=_cua_so("TINH")))
        assert _so_dong(p) == 0

    @pytest.mark.parametrize(
        ("ds", "che_do"),
        [(["so_lenh", "lenh_moi_nam"], "DEM"), (["lenh_moi_nam"], "DEM"), (["so_lenh"], "TINH")],
    )
    def test_dem_chi_la_CTRL_so_lenh(self, tmp_path: Path, repo: Path, ds: list[str], che_do: str) -> None:
        so, p = _so(tmp_path, repo)
        with pytest.raises(XacClaimError, match="đúng ctrl_mo_ta_whitelist"):
            so.reserve(**_kw(budget_line="CTRL", param_value=_cua_so(che_do), ctrl_mo_ta_whitelist=ds))
        assert _so_dong(p) == 0

    def test_dem_khong_khai_mo_ta_van_bi_cua_ctrl_chan(self, tmp_path: Path, repo: Path) -> None:
        so, _ = _so(tmp_path, repo)
        with pytest.raises((XacClaimError, CtrlClaimError)):
            so.reserve(**_kw(budget_line="CTRL", param_value=_cua_so("DEM")))


class TestKhongMoDuongTatChoSuatB:
    def test_dong_dem_cua_slot_khong_mien_cua_thiet_ke(self, tmp_path: Path, repo: Path) -> None:
        """TD-0375: trước TD-0389 "slot đã có dòng" tính cả CTRL ⇒ một dòng ĐẾM mở đường tắt cho suất B."""
        so, _ = _so(tmp_path, repo)
        _dem(so, 5)
        with pytest.raises(ThietKeChuaKiemError):
            so.reserve(**_kw(budget_line="B3", dataset="CALIB", param_under_test="zss_threshold", param_value=0.5))


class TestTD0119bChiDemDongVaoN:
    def test_ctrl_va_xac_khong_la_bien_the(self, tmp_path: Path) -> None:
        repo = _dung_repo(tmp_path, y_tuong=_y_tuong(so_bien_the=1))
        so, p = _so(tmp_path, repo)
        tid = so.reserve(**_kw(budget_line="B0", dataset="N/A", param_under_test="pool", param_value=1,
                                config_hash="n/a", params_frozen_hash="n/a"))
        so.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        _dem(so, 30)
        x = so.reserve(**_kw())
        so.seal(x, seal_path=f"runs/{x}/metrics.seal")
        kq = check_td0119_so_bien_the_khong_vuot_khai(repo / "registry" / "idea_queue.jsonl", p)
        assert kq.ok, kq.evidence


class TestBienXacNhan:
    def _cfg(self):
        return load_tool_d_config(REPO / "config" / "tool_d_config.yaml")

    def test_bien_la_ngay_chon_toi_ngay_do(self, repo: Path) -> None:
        b = bien_xac_nhan(self._cfg(), SLOT, ngay_do=date(2026, 12, 20), repo_dir=repo, hom_nay=date(2026, 12, 21))
        assert (b.name, b.start, b.end) == ("XAC_NHAN", date(2026, 10, 1), date(2026, 12, 20))

    @pytest.mark.parametrize("ngay_do", [date(2026, 10, 1), date(2026, 9, 30), date(2026, 12, 22)])
    def test_ngay_do_sai_bi_tu_choi(self, repo: Path, ngay_do: date) -> None:
        with pytest.raises(TimerangeViolationError, match="Ngày đo"):
            bien_xac_nhan(self._cfg(), SLOT, ngay_do=ngay_do, repo_dir=repo, hom_nay=date(2026, 12, 21))

    def test_ngay_chon_khong_sau_T3(self, tmp_path: Path) -> None:
        dong = _y_tuong()
        dong[1]["selected_at"] = "2026-09-06T08:00:00Z"
        repo = _dung_repo(tmp_path, y_tuong=dong)
        with pytest.raises(TimerangeViolationError, match="không nằm SAU T3"):
            bien_xac_nhan(self._cfg(), SLOT, ngay_do=date(2026, 12, 20), repo_dir=repo, hom_nay=date(2026, 12, 21))

    def test_ro_chua_co_thi_tu_choi(self, tmp_path: Path) -> None:
        """§7 Q5: rổ tại ngày CHỌN hoãn (TD-0391) ⇒ E1 dừng ở rổ, không rơi về rổ khác."""
        with pytest.raises(RoGiaiDoanError, match="pool_xac_nhan.yaml"):
            ro_cho_tap("XAC_NHAN", repo_dir=tmp_path)


class TestE1KeHoach:
    def _args(self, *extra: str):
        args, _ = e1.build_parser().parse_known_args(
            ["--tap", "XAC_NHAN", "--hypothesis-slot", SLOT, "--den", "2026-12-20", *extra]
        )
        return args

    @pytest.mark.parametrize(
        ("extra", "khop"),
        [
            ((), "cần --che-do"),
            (("--che-do", "DEM", "--budget-line", "XAC"), "đi với --budget-line CTRL"),
            (("--che-do", "TINH", "--budget-line", "CTRL"), "đi với --budget-line XAC"),
            (("--che-do", "DEM", "--param-under-test", "x"), "KHÔNG nhận --param-under-test"),
            (("--che-do", "TINH", "--direction", "SHORT"), "chỉ nhận LONG"),
        ],
    )
    def test_ke_hoach_sai_bi_tu_choi(self, extra: tuple[str, ...], khop: str) -> None:
        with pytest.raises(BoChayError, match=khop):
            e1._kiem_ke_hoach_xac_nhan(self._args(*extra), load_tool_d_config(REPO / "config" / "tool_d_config.yaml"))

    def test_che_do_khong_co_mac_dinh(self) -> None:
        assert self._args().che_do is None
        assert e1.DONG_THEO_CHE_DO == {"DEM": "CTRL", "TINH": "XAC"}

    def test_tinh_khi_hien_vat_da_co_bi_tu_choi(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "docs" / "du-lieu-do").mkdir(parents=True)
        (tmp_path / "docs" / "du-lieu-do" / "xac-nhan-sau-t3.json").write_text("{}", encoding="utf-8")
        with pytest.raises(BoChayError, match="chỉ đo MỘT lần"):
            e1._kiem_ke_hoach_xac_nhan(self._args("--che-do", "TINH"),
                                      load_tool_d_config(REPO / "config" / "tool_d_config.yaml"))

    def test_lenh_da_dong_bo_force_exit(self) -> None:
        lenh = ({"exit_reason": "trailing_stop_loss"}, {"exit_reason": "force_exit"}, {"exit_reason": "roi"})
        assert [t["exit_reason"] for t in e1._lenh_da_dong(lenh)] == ["trailing_stop_loss", "roi"]


class TestHienVatNoiHaiDau:
    def test_hien_vat_E1_ghi_ra_duoc_tran_von_nhan(self, tmp_path: Path, monkeypatch) -> None:
        """Hai đầu của lớp xác nhận: thứ E1 ghi ra phải là thứ `tran_von` chấp nhận — không lệch tên khoá."""
        repo = _dung_repo(tmp_path)
        monkeypatch.chdir(repo)
        cfg = load_tool_d_config(repo / "config" / "tool_d_config.yaml")
        duong = e1._ghi_hien_vat_xac_nhan(cfg, slot=SLOT, tu=date(2026, 10, 1), den=date(2026, 12, 20), n_lenh=30,
                                         mean_r=0.12, config_sha256=CFG_HASH, trial_id="D-0099")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "hien vat")
        assert ly_do_chua_xac_nhan(cfg.tier_c, repo) == []
        with pytest.raises(FileExistsError):
            e1._ghi_hien_vat_xac_nhan(cfg, slot=SLOT, tu=date(2026, 10, 1), den=date(2026, 12, 20), n_lenh=30,
                                     mean_r=0.5, config_sha256=CFG_HASH, trial_id="D-0100")
        assert json.loads(duong.read_text(encoding="utf-8"))["gia_tri"] == 0.12
