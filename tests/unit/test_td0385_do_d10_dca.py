"""TD-0385 — bộ đo BA ngưỡng D10 cho lệnh DCA (`ops/do_d10_dca.py`) + ghi kết cục vào dòng D10 (`ops/so_d10.py`, E6
`--d10-do`). Ngưỡng là bản gốc ở `DR-D11-01` §5; test ghim đúng cách đọc, kể cả bẫy `average` của TD-0441.

Tầng thuần: dữ liệu dựng tay. Đường sản xuất: DB SQLite TẠM dựng bằng chính `Trade`/`Order` của Freqtrade, sổ Decision
Log tạm, sổ trial tạm trên repo git tạm — không đụng DB/sổ thật."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from tool_d.ops import do_d10_dca as m
from tool_d.ops.do_d10_dca import (
    NGUONG_GAP_MS_P99,
    DoD10DcaError,
    KetQuaGap,
    LenhDat,
    danh_gia,
    do_d6,
    do_gap_ms,
    do_post_only,
    tranche_da_khop,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
T0 = datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc)


def _l(order_id: str, *, trade_id: int = 1, vai_tro: str = "vao", loai: str | None = "limit",
       tt: str | None = "closed", ke_hoach: float | None = 100.0, tb: float | None = 100.0,
       kl: float | None = 1.0, khop: float | None = 1.0, phut: int = 0) -> LenhDat:
    return LenhDat(trade_id=trade_id, order_id=order_id, vai_tro=vai_tro, loai_lenh=loai, trang_thai=tt,
                   gia_ke_hoach=ke_hoach, gia_khop_tb=tb, khoi_luong=kl, da_khop=khop,
                   moc_khop=(T0 + timedelta(minutes=phut)) if khop else None)


def _gap_du(p99_duoi_nguong: bool = True) -> KetQuaGap:
    return do_gap_ms([1000.0] * 29 + [5000.0 if p99_duoi_nguong else 90_000.0] * 2)


# ───────────────────────────── gap_ms ─────────────────────────────


class TestGapMs:
    def test_p99_noi_suy_tuyen_tinh(self) -> None:
        g = do_gap_ms([float(i) for i in range(1, 101)])
        assert g.n == 100 and g.p99 == pytest.approx(99.01) and g.max == 100.0

    def test_rong_la_chua_co_khong_phai_0(self) -> None:
        assert do_gap_ms([]) == KetQuaGap(n=0, p99=None, max=None)

    @pytest.mark.parametrize("hong", [float("nan"), -1.0, float("inf")])
    def test_so_hong_thi_raise(self, hong: float) -> None:
        with pytest.raises(DoD10DcaError, match="hỏng"):
            do_gap_ms([100.0, hong])


# ───────────────────────────── post-only ─────────────────────────────


class TestPostOnly:
    def test_phan_loai_ba_lo_mu(self) -> None:
        kq = do_post_only([
            _l("ok"),
            _l("tu_choi", tt="expired", khop=0.0),
            _l("mot_phan", tt="canceled", khop=0.4),
            _l("huy", tt="canceled", khop=0.0),
            _l("mo", tt="open", khop=0.0),
            _l("ra", vai_tro="ra"),
            _l("sl", vai_tro="stoploss", loai="stop_market", tt="canceled", khop=0.0),
            _l("hong", khop=None),
        ])
        assert kq.so_lenh_vao_ket_thuc == 4
        assert (kq.san_tu_choi, kq.khop_mot_phan, kq.huy_khong_khop) == (("tu_choi",), ("mot_phan",), ("huy",))
        assert kq.dang_mo == ("mo",) and kq.khong_doc_duoc == ("hong",)


# ───────────────────────────── D6 ─────────────────────────────


class TestD6:
    def test_tranche_theo_moc_khop_khong_theo_thu_tu_dua_vao(self) -> None:
        ds = tranche_da_khop([_l("b", phut=5), _l("a", phut=1), _l("c", tt="canceled", khop=0.0)])
        assert [(i, x.order_id) for i, x in ds] == [(1, "a"), (2, "b")]

    def test_bay_average_lenh_huy_khong_khop_khong_vao_d6(self) -> None:
        """TD-0441: dry-run gán `average = giá đặt` lúc TẠO lệnh — lệnh huỷ `filled = 0` vẫn có average. Không lọc
        `filled > 0` thì D6 đếm một tranche KHÔNG hề khớp như thể khớp đúng giá."""
        kq = do_d6([_l("t1", phut=0), _l("t2", tt="canceled", khop=0.0, tb=100.0, phut=1)], planned_risk=None, delta_r=None)
        assert kq.n_tranche == 0 and kq.lech_bps_max is None

    def test_ctrl_chi_bps_khong_so_delta_r(self) -> None:
        kq = do_d6([_l("t1", phut=0), _l("t2", ke_hoach=100.0, tb=100.05, phut=1)], planned_risk=None, delta_r=0.16)
        assert kq.so_voi_delta_r is False and kq.delta_r is None and kq.thong_ke_r is None
        assert kq.n_tranche == 1 and kq.lech_bps_max == pytest.approx(5.0)
        (ct,) = kq.chi_tiet
        assert set(ct) >= {"fill_price", "p_i", "order_status"}

    def test_tranche_1_khong_tinh(self) -> None:
        kq = do_d6([_l("t1", ke_hoach=100.0, tb=110.0)], planned_risk={1: 10.0}, delta_r=0.16)
        assert kq.n_tranche == 0 and kq.thong_ke_r == 0.0  # chỉ khớp tranche 1 ⇒ lệch 0 THẬT (DR-D35-01 §4)

    def test_che_do_r_duoi_30_lenh_dung_max(self) -> None:
        lenh = []
        for tid in range(1, 4):  # lệch_R = filled·|tb − p| / planned_risk = 1·tid/10
            lenh += [_l(f"{tid}a", trade_id=tid, phut=0), _l(f"{tid}b", trade_id=tid, tb=100.0 + tid, phut=1)]
        kq = do_d6(lenh, planned_risk={1: 10.0, 2: 10.0, 3: 10.0}, delta_r=0.16)
        assert kq.dung_p90 is False and kq.thong_ke_r == pytest.approx(0.3) and kq.n_lenh == 3

    def test_che_do_r_du_30_lenh_dung_p90(self) -> None:
        lenh, pr = [], {}
        for tid in range(1, 31):
            lenh += [_l(f"{tid}a", trade_id=tid, phut=0), _l(f"{tid}b", trade_id=tid, tb=100.0 + tid / 100, phut=1)]
            pr[tid] = 1.0
        kq = do_d6(lenh, planned_risk=pr, delta_r=0.16)
        assert kq.dung_p90 is True and kq.thong_ke_r == pytest.approx(0.271)

    def test_thieu_planned_risk_la_khong_doc_duoc(self) -> None:
        kq = do_d6([_l("a", phut=0), _l("b", tb=101.0, phut=1)], planned_risk={}, delta_r=0.16)
        assert kq.khong_doc_duoc == ("b",) and kq.n_lenh == 0


# ───────────────────────────── phán quyết ─────────────────────────────


def _po_sach():
    return do_post_only([_l("a"), _l("b")])


def _d6_ctrl():
    return do_d6([_l("a", phut=0), _l("b", phut=1)], planned_risk=None, delta_r=None)


class TestDanhGia:
    def test_kept_nhung_ctrl_khong_bao_gio_dat_d12(self) -> None:
        kq = danh_gia(_gap_du(), _po_sach(), _d6_ctrl())
        assert kq.verdict == "KEPT" and kq.dat_dieu_kien_d12 is False
        assert any("KHÔNG so Δ_R" in x for x in kq.ly_do)

    def test_gap_p99_vuot_nguong_thi_rejected(self) -> None:
        kq = danh_gia(_gap_du(p99_duoi_nguong=False), _po_sach(), _d6_ctrl())
        assert kq.gap.p99 > NGUONG_GAP_MS_P99 and kq.verdict == "REJECTED"

    def test_duoi_30_su_kien_thi_inconclusive_khong_thay_bang_max(self) -> None:
        kq = danh_gia(do_gap_ms([90_000.0] * 29), _po_sach(), _d6_ctrl())
        assert kq.verdict == "INCONCLUSIVE" and any("n = 29" in x for x in kq.ly_do)

    def test_bat_ky_lo_mu_post_only_nao_thi_trinh_chu_du_an(self) -> None:
        kq = danh_gia(_gap_du(), do_post_only([_l("a"), _l("b", tt="expired", khop=0.0)]), _d6_ctrl())
        assert kq.verdict == "INCONCLUSIVE" and any("trình chủ dự án" in x for x in kq.ly_do)

    def test_che_do_r_vuot_delta_r_thi_rejected(self) -> None:
        d6 = do_d6([_l("a", phut=0), _l("b", tb=105.0, phut=1)], planned_risk={1: 10.0}, delta_r=0.16)
        kq = danh_gia(_gap_du(), _po_sach(), d6)
        assert d6.thong_ke_r == pytest.approx(0.5) and kq.verdict == "REJECTED" and not kq.dat_dieu_kien_d12

    def test_che_do_r_dat_moi_thu_thi_dat_d12(self) -> None:
        d6 = do_d6([_l("a", phut=0), _l("b", tb=100.5, phut=1)], planned_risk={1: 10.0}, delta_r=0.16)
        kq = danh_gia(_gap_du(), _po_sach(), d6)
        assert kq.verdict == "KEPT" and kq.dat_dieu_kien_d12 is True


class TestHangSo:
    def test_tag_ctrl_khop_chien_luoc(self) -> None:
        spec = importlib.util.spec_from_file_location("CtrlD10", REPO_ROOT / "user_data/strategies/CtrlD10.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        assert mod.TAG_CTRL == m.TAG_CTRL

    def test_delta_r_doc_tu_artifact_niem_phong(self) -> None:
        assert m.doc_delta_r_long(REPO_ROOT) == pytest.approx(0.161206, abs=1e-6)


# ───────────────────────────── đường sản xuất ─────────────────────────────


def _dung_db(duong: Path, *, lenh_vao: list[dict], enter_tag: str = m.TAG_CTRL) -> str:
    from freqtrade.enums import TradingMode
    from freqtrade.persistence import Order, Trade, init_db

    url = f"sqlite:///{duong}"
    init_db(url)
    t = Trade(pair="DOGE/USDT:USDT", stake_amount=10.0, amount=100.0, open_rate=0.1, open_date=T0, is_open=False,
              close_date=T0 + timedelta(hours=1), exchange="binance", fee_open=0.0002, fee_close=0.0002,
              is_short=False, leverage=3.0, trading_mode=TradingMode.FUTURES, enter_tag=enter_tag,
              exit_reason="CTRL_HET_GIO", close_profit_abs=0.0, close_profit=0.0)
    Trade.session.add(t)
    Trade.commit()
    for i, o in enumerate(lenh_vao):
        khop = o["filled"] > 0
        Trade.session.add(Order(
            ft_trade_id=t.id, ft_pair=t.pair, ft_is_open=False, ft_order_side=t.entry_side, ft_amount=o["amount"],
            ft_price=o["ft_price"], order_id=f"V{i}", status=o["status"], order_type="limit", side=t.entry_side,
            price=o["ft_price"], average=o["average"], amount=o["amount"], filled=o["filled"],
            remaining=o["amount"] - o["filled"], order_date=T0 + timedelta(minutes=i),
            order_filled_date=(T0 + timedelta(minutes=i)) if khop else None))
    Trade.session.add(Order(
        ft_trade_id=t.id, ft_pair=t.pair, ft_is_open=False, ft_order_side="stoploss", ft_amount=100.0, ft_price=0.098,
        order_id="SL0", status="canceled", order_type="stop_market", side="sell", price=0.098, amount=100.0,
        filled=0.0, order_date=T0))
    Trade.commit()
    return url


LENH_SACH = [
    {"ft_price": 0.1, "average": 0.1, "amount": 100.0, "filled": 100.0, "status": "closed"},
    {"ft_price": 0.0997, "average": 0.0997, "amount": 100.0, "filled": 100.0, "status": "closed"},
]


def _so_live(duong: Path, gap: list[float], nguon: str = "live") -> Path:
    duong.parent.mkdir(parents=True, exist_ok=True)
    dong = [json.dumps({"loai": "DOI_SL", "nguon": nguon, "gap_ms": g, "sl_order_id_new": f"S{i}"})
            for i, g in enumerate(gap)]
    duong.write_text("\n".join(dong) + "\n", encoding="utf-8")
    return duong


class TestDuongSanXuat:
    def test_db_live_chua_co_thi_pending_va_khong_tao_file(self, tmp_path: Path) -> None:
        db = tmp_path / "live.sqlite"
        with pytest.raises(DoD10DcaError, match="pending"):
            m.doc_lenh_db(f"sqlite:///{db}")
        assert not db.exists()

    def test_trade_khong_phai_ctrl_thi_tu_choi(self, tmp_path: Path) -> None:
        url = _dung_db(tmp_path / "live.sqlite", lenh_vao=LENH_SACH, enter_tag="RO_VAO")
        with pytest.raises(DoD10DcaError, match="không phải lệnh CTRL"):
            m.doc_lenh_db(url)

    def test_chi_dem_doi_sl_nguon_live(self, tmp_path: Path) -> None:
        so = _so_live(tmp_path / "log.jsonl", [100.0, 200.0])
        with so.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"loai": "DOI_SL", "nguon": "dry_run", "gap_ms": 9e9}) + "\n")
        assert m.doc_gap_ms_live(so) == [100.0, 200.0]

    def test_so_hong_thi_raise_khong_tra_rong(self, tmp_path: Path) -> None:
        so = tmp_path / "log.jsonl"
        so.write_text("{hỏng\n", encoding="utf-8")
        with pytest.raises(DoD10DcaError, match="không phải JSON"):
            m.doc_gap_ms_live(so)

    def test_do_tron_db_that(self, tmp_path: Path) -> None:
        lenh = LENH_SACH + [{"ft_price": 0.0994, "average": 0.0994, "amount": 100.0, "filled": 0.0, "status": "canceled"}]
        url = _dung_db(tmp_path / "live.sqlite", lenh_vao=lenh)
        kq = m.do_d10_dca(db_url=url, decision_log=_so_live(tmp_path / "log.jsonl", [1500.0] * 30))
        assert kq.gap.n == 30 and kq.post_only.huy_khong_khop == ("V2",)
        assert kq.d6.n_tranche == 1  # tranche 3 huỷ, average có mà filled = 0 ⇒ không tính
        assert kq.verdict == "INCONCLUSIVE" and kq.dat_dieu_kien_d12 is False


# ───────────────────────────── ghi kết cục vào sổ ─────────────────────────────


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path) -> Path:
    if shutil.which("git") is None:
        pytest.skip("không có git")
    from tool_d.ops.live_d10 import RO_D10

    r = tmp_path / "r"
    for rel in ("config/tool_d_config.yaml", "docker/Dockerfile"):
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / rel, r / rel)
    (r / RO_D10).write_text(yaml.safe_dump({"cap": ["DOGE/USDT:USDT"]}), encoding="utf-8")
    (r / "docs/du-lieu-do").mkdir(parents=True)
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "goc")
    return r


class TestGhiKetCuc:
    def _so(self, repo: Path, tmp_path: Path):
        from tool_d.ledger.registry import TrialLedger
        from tool_d.ops.so_d10 import dat_cho_dong_d10

        so_path = tmp_path / "so.jsonl"
        tid = dat_cho_dong_d10(ledger=TrialLedger(path=so_path, repo_dir=repo), repo_dir=repo)
        return so_path, tid

    def test_seal_roi_consume_hien_vat_du(self, repo: Path, tmp_path: Path) -> None:
        from tool_d.ledger.registry import TrialLedger
        from tool_d.ops.so_d10 import ghi_ket_cuc_d10_dca

        so_path, tid = self._so(repo, tmp_path)
        url = _dung_db(tmp_path / "live.sqlite", lenh_vao=LENH_SACH)
        tra_tid, duong, _ = ghi_ket_cuc_d10_dca(ledger=TrialLedger(path=so_path, repo_dir=repo), db_url=url,
                                                decision_log=_so_live(tmp_path / "log.jsonl", [1500.0] * 30),
                                                repo_dir=repo)
        su_kien = [json.loads(d) for d in so_path.read_text(encoding="utf-8").splitlines() if d.strip()]
        assert tra_tid == tid and [e["event"] for e in su_kien] == ["RESERVE", "SEAL", "CONSUME"]
        assert su_kien[1]["seal_path"] == f"runs/{tid}/metrics.seal" and su_kien[2]["verdict"] == "KEPT"
        assert (repo / su_kien[1]["seal_path"]).read_text(encoding="utf-8") == (repo / duong).read_text(encoding="utf-8")
        hv = json.loads((repo / duong).read_text(encoding="utf-8"))
        assert hv["dat_dieu_kien_d12"] is False and hv["provenance"]["git_sha"]

    def test_con_lenh_vao_mo_thi_tu_choi_so_khong_doi(self, repo: Path, tmp_path: Path) -> None:
        from tool_d.ledger.registry import TrialLedger
        from tool_d.ops.so_d10 import ghi_ket_cuc_d10_dca

        so_path, _ = self._so(repo, tmp_path)
        truoc = so_path.read_text(encoding="utf-8")
        lenh = LENH_SACH + [{"ft_price": 0.0994, "average": 0.0994, "amount": 100.0, "filled": 0.0, "status": "open"}]
        url = _dung_db(tmp_path / "live.sqlite", lenh_vao=lenh)
        with pytest.raises(DoD10DcaError, match="chưa kết thúc"):
            ghi_ket_cuc_d10_dca(ledger=TrialLedger(path=so_path, repo_dir=repo), db_url=url,
                                decision_log=tmp_path / "khong_co.jsonl", repo_dir=repo)
        assert so_path.read_text(encoding="utf-8") == truoc

    def test_khong_co_dong_d10_thi_tu_choi(self, repo: Path, tmp_path: Path) -> None:
        from tool_d.ledger.registry import TrialLedger
        from tool_d.ops.so_d10 import ghi_ket_cuc_d10_dca

        with pytest.raises(ValueError, match="đúng một dòng D10"):
            ghi_ket_cuc_d10_dca(ledger=TrialLedger(path=tmp_path / "so.jsonl", repo_dir=repo),
                                db_url="sqlite:///x", decision_log=tmp_path / "x", repo_dir=repo)
