"""TD-0247 / `DR-D1-03` §2 — E7 `build_pool.py --ro-t1`: bộ sinh rổ `T1` có xuất xứ.

Mạng, git và đồng hồ được TIÊM qua tham số `sinh_ro_t1()`; logic đối chiếu,
fail-closed và nội dung file là đường sản xuất thật.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import yaml

from tool_d.api_client.binance_public import KhoLuuTruError, NenThangKhongCoError
from tool_d.measurement.gitinfo import GitInfo

REPO = Path(__file__).resolve().parents[2]
T1 = date(2025, 6, 12)
SAN_VOL = 15_000_000.0


def _nap_e7():
    """`entrypoints/` không nằm trên pythonpath (L-Z36) — nạp theo đường dẫn."""
    spec = importlib.util.spec_from_file_location("build_pool_ro_t1", REPO / "entrypoints" / "build_pool.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E7 = _nap_e7()

# Bốn mã: A/B đủ tiêu chí, EXPL đủ tiêu chí nhưng có dữ liệu EXPLORE, LOW trượt volume.
KHOANG = {
    "AUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08"},
    "BUSDT": {"thang_dau": "2023-02", "thang_cuoi": "2026-08"},
    "EXPLUSDT": {"thang_dau": "2023-03", "thang_cuoi": "2026-08"},
    "LOWUSDT": {"thang_dau": "2023-04", "thang_cuoi": "2026-08"},
}
VOL = {"AUSDT": SAN_VOL * 3, "BUSDT": SAN_VOL * 2, "EXPLUSDT": SAN_VOL * 2, "LOWUSDT": SAN_VOL / 2}
DU_TIEU_CHI = ["AUSDT", "BUSDT", "EXPLUSDT"]


def _repo(tmp_path: Path, *, td0231_danh_sach: list[str] = DU_TIEU_CHI, explore: bool = True) -> Path:
    (tmp_path / "config").mkdir()
    shutil.copy(REPO / "config" / "tool_d_config.yaml", tmp_path / "config" / "tool_d_config.yaml")
    dl = tmp_path / "docs" / "du-lieu-do"
    dl.mkdir(parents=True)
    (dl / "td0230-lech-song-sot-pool.json").write_text(
        json.dumps({"khoang_ton_tai": KHOANG}), encoding="utf-8"
    )
    (dl / "td0231-pool-point-in-time.json").write_text(
        json.dumps({"moc": {"t1": T1.isoformat()}, "pool_dung_tai_t1": {"danh_sach": td0231_danh_sach}}),
        encoding="utf-8",
    )
    if explore:
        ex = tmp_path / "user_data" / "data" / "explore" / "futures"
        ex.mkdir(parents=True)
        (ex / "EXPL_USDT_USDT-1h-futures.feather").write_bytes(b"")
        (ex / "ZZZ_USDT_USDT-1h-futures.feather").write_bytes(b"")
    return tmp_path


def _doc_volume(sym: str, nam: int, thang: int):
    if (nam, thang) != (T1.year, T1.month):
        raise NenThangKhongCoError("không cần tháng khác trong ca này")
    return {T1: VOL[sym]}


def _chay(repo: Path, *, ghi: bool = True, **kw) -> int:
    mac_dinh = dict(
        doc_volume_thang=_doc_volume,
        lay_exchange_info=lambda: {"symbols": [{"symbol": "AUSDT", "contractType": "PERPETUAL"}]},
        thay_doi_chua_commit=lambda _: [],
        bay_gio=lambda: datetime(2026, 9, 17, tzinfo=timezone.utc),
        lay_git_info=lambda _: GitInfo(sha="a" * 40, is_clean=True),
    )
    mac_dinh.update(kw)
    return E7.sinh_ro_t1(ghi=ghi, repo_dir=repo, **mac_dinh)


def _doc_ro(repo: Path) -> dict:
    return yaml.safe_load((repo / "config" / "pool_t1.yaml").read_text(encoding="utf-8"))


def test_ghi_ro_loai_explore_da_dung_va_mang_xuat_xu(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert _chay(repo) == 0
    ro = _doc_ro(repo)
    assert ro["trading"] == ["AUSDT", "BUSDT"]
    assert ro["loai"] == {"explore_da_dung": ["EXPLUSDT"], "tradifi_perpetual": []}
    assert ro["explore_da_dung_chup_luc_sinh"]["danh_sach"] == ["EXPLUSDT", "ZZZUSDT"]
    assert ro["moc_t1"] == "2025-06-12"
    xx = ro["xuat_xu"]
    assert xx["git_sha"] == "a" * 40 and xx["trial"] == 0 and xx["doi_chieu_td0231"]["khit"] is True
    assert len(xx["nguon_khoang_ton_tai"]["sha256"]) == 64


def test_chay_thu_khong_ghi_file(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert _chay(repo, ghi=False) == 0
    assert not (repo / "config" / "pool_t1.yaml").exists()


def test_file_da_ton_tai_thi_TU_CHOI_ghi_de(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    dich = repo / "config" / "pool_t1.yaml"
    dich.write_text("cu: true\n", encoding="utf-8")
    assert _chay(repo) == E7.EXIT_POOL_ALREADY_COMMITTED
    assert dich.read_text(encoding="utf-8") == "cu: true\n"


def test_co_thay_doi_chua_commit_thi_TU_CHOI_ghi(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert _chay(repo, thay_doi_chua_commit=lambda _: ["[M] src/tool_d/pool_t1.py"]) == E7.EXIT_RO_T1_CAY_BAN
    assert not (repo / "config" / "pool_t1.yaml").exists()


def test_KHONG_khit_td0231_thi_TU_CHOI_ghi(tmp_path: Path) -> None:
    """Kiểm có răng cho phép đối chiếu: TD-0231 thiếu một mã ⇒ phải chặn."""
    repo = _repo(tmp_path, td0231_danh_sach=["AUSDT", "BUSDT"])
    assert _chay(repo) == E7.EXIT_RO_T1_LECH_TD0231
    assert not (repo / "config" / "pool_t1.yaml").exists()


def test_thieu_thu_muc_explore_thi_TU_CHOI_khong_coi_la_rong(tmp_path: Path) -> None:
    repo = _repo(tmp_path, explore=False)
    assert _chay(repo) == E7.EXIT_RO_T1_EXPLORE
    assert not (repo / "config" / "pool_t1.yaml").exists()


def test_loi_mang_thi_KHONG_sinh_ro_nua_voi(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    def hong(*_a):
        raise KhoLuuTruError("mạng hỏng")

    assert _chay(repo, doc_volume_thang=hong) == E7.EXIT_FETCH_FAILED
    assert not (repo / "config" / "pool_t1.yaml").exists()


def test_tradifi_bi_loai_va_ghi_ly_do(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    info = {"symbols": [{"symbol": "BUSDT", "contractType": "TRADIFI_PERPETUAL"}]}
    assert _chay(repo, lay_exchange_info=lambda: info) == 0
    ro = _doc_ro(repo)
    assert ro["trading"] == ["AUSDT"] and ro["loai"]["tradifi_perpetual"] == ["BUSDT"]


@pytest.mark.parametrize("co", ["--ro-t1"])
def test_main_goi_guard_truoc_ro_t1(co: str) -> None:
    """Cờ mới đi SAU `measurement_guard()` trong `main()` (N5, L-Z36)."""
    import inspect

    src = inspect.getsource(E7.main)
    assert src.index("measurement_guard(") < src.index("if args.ro_t1:")
