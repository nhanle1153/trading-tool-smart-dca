"""TD-0299 (`DR-D1-05`) — khoá bảng rổ theo giai đoạn.

Canh ba thứ: (1) CALIB dùng rổ `T0`, WFO dùng rổ `T1` — không đổi chéo; (2) LOCKBOX bị từ chối
cho tới khi `MT-60` giải; (3) `config/pool.yaml` (rổ hôm nay) không bao giờ là rổ backtest.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tool_d import pool_giai_doan as pg
from tool_d.pool_giai_doan import POOL_HOM_NAY, RO_THEO_TAP, RoGiaiDoanError, ro_cho_tap


def _ghi_ro(repo: Path, file_ro: Path, moc: str, trading=("AUSDT", "BUSDT")) -> None:
    duong = repo / file_ro
    duong.parent.mkdir(parents=True, exist_ok=True)
    dong = "\n".join(f"- {s}" for s in trading)
    duong.write_text(f"moc_{moc}: '2025-06-12'\ntrading:\n{dong}\n", encoding="utf-8")


def test_bang_calib_la_t0_wfo_la_t1() -> None:
    assert RO_THEO_TAP["CALIB"][0] == "t0" and RO_THEO_TAP["CALIB"][1] == Path("config/pool_t0.yaml")
    assert RO_THEO_TAP["WFO"][0] == "t1" and RO_THEO_TAP["WFO"][1] == Path("config/pool_t1.yaml")
    assert "LOCKBOX" not in RO_THEO_TAP


def test_khong_tap_nao_tro_vao_pool_yaml() -> None:
    assert all(file_ro != POOL_HOM_NAY for _, file_ro, _ in RO_THEO_TAP.values())


@pytest.mark.parametrize("tap,moc", [("CALIB", "t0"), ("WFO", "t1")])
def test_tra_dung_ro_va_thu_muc(tmp_path: Path, tap: str, moc: str) -> None:
    _, file_ro, thu_muc = RO_THEO_TAP[tap]
    _ghi_ro(tmp_path, file_ro, moc)
    ro = ro_cho_tap(tap, repo_dir=tmp_path)
    assert (ro.moc, ro.file_ro, ro.thu_muc_du_lieu, ro.trading) == (moc, file_ro, thu_muc, ("AUSDT", "BUSDT"))


def test_lockbox_bi_tu_choi_neu_mt60(tmp_path: Path) -> None:
    with pytest.raises(RoGiaiDoanError, match="MT-60"):
        ro_cho_tap("LOCKBOX", repo_dir=tmp_path)


def test_tap_la_bi_tu_choi(tmp_path: Path) -> None:
    with pytest.raises(RoGiaiDoanError):
        ro_cho_tap("EXPLORE", repo_dir=tmp_path)


def test_file_ro_thieu_thi_tu_choi_KHONG_roi_ve_pool_yaml(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / POOL_HOM_NAY).write_text("trading:\n- XUSDT\n", encoding="utf-8")
    with pytest.raises(RoGiaiDoanError):
        ro_cho_tap("CALIB", repo_dir=tmp_path)


def test_file_ro_mang_moc_khac_thi_tu_choi(tmp_path: Path) -> None:
    """Chép nhầm rổ T1 sang tên pool_t0.yaml ⇒ không được nhận làm rổ CALIB."""
    _ghi_ro(tmp_path, RO_THEO_TAP["CALIB"][1], "t1")
    with pytest.raises(RoGiaiDoanError, match="moc_t0"):
        ro_cho_tap("CALIB", repo_dir=tmp_path)


def test_trading_rong_thi_tu_choi(tmp_path: Path) -> None:
    _ghi_ro(tmp_path, RO_THEO_TAP["WFO"][1], "t1", trading=())
    (tmp_path / RO_THEO_TAP["WFO"][1]).write_text("moc_t1: '2025-06-12'\ntrading: []\n", encoding="utf-8")
    with pytest.raises(RoGiaiDoanError):
        ro_cho_tap("WFO", repo_dir=tmp_path)


def test_bang_bi_sua_tro_ve_pool_yaml_thi_tu_choi(tmp_path: Path, monkeypatch) -> None:
    """Kiểm có răng cho chốt canh bảng: ai sửa bảng CALIB về pool.yaml thì hàm phải từ chối."""
    monkeypatch.setitem(pg.RO_THEO_TAP, "CALIB", ("t0", POOL_HOM_NAY, Path("user_data/data/binance/futures")))
    (tmp_path / "config").mkdir()
    (tmp_path / POOL_HOM_NAY).write_text("moc_t0: x\ntrading:\n- XUSDT\n", encoding="utf-8")
    with pytest.raises(RoGiaiDoanError, match="pool.yaml"):
        ro_cho_tap("CALIB", repo_dir=tmp_path)


def test_ro_t1_that_trong_repo_doc_duoc() -> None:
    """Đường sản xuất thật: rổ WFO đã commit (a62540b) phải đi qua được hàm chọn."""
    repo = Path(__file__).resolve().parents[2]
    ro = ro_cho_tap("WFO", repo_dir=repo)
    assert len(ro.trading) == 107
