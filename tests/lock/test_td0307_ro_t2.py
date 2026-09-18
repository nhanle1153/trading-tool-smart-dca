"""TD-0307 (`DR-LOCKBOX-01`) — rổ `T2` cho LOCKBOX: đời sống đo thật, đối chiếu BẤT ĐỐI XỨNG.

Ba thứ được khoá:
1. `dung_ro_tai_moc()` dùng mốc ngừng giao dịch ĐO THẬT khi có (`MT-59`: kho kéo đời sống mã chết
   tới tháng lớn nhất và gán `delisted_at = None`), và fail-closed khi mã lọt rổ mà đời sống chỉ là
   cận trên. Dữ liệu cũ (`TD-0230`, không mang khoá mới) đi nhánh cũ ⇒ rổ `t0`/`t1` tái lập được.
2. Bộ sinh E7 ở mốc `t2` KHÔNG đòi khít `td0231` (số đó tính bằng chính hàm sai): phần chỉ có ở lần
   tính mới phải RỖNG, phần chỉ có ở `td0231` phải nằm trong danh sách mã chết trước `T2`.
3. 🔴 `ro_cho_tap("LOCKBOX")` VẪN từ chối khi `config/pool_t2.yaml` đã có — nó là cửa chặn duy nhất
   giữa lõi bộ chạy (Khối 27) và dữ liệu chỉ được chạm một lần.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import yaml

from tool_d.api_client.binance_public import NenThangKhongCoError
from tool_d.measurement.gitinfo import GitInfo
from tool_d.pool_giai_doan import RO_THEO_TAP, RoGiaiDoanError, ro_cho_tap
from tool_d.pool_t1 import dung_ro_tai_moc

REPO = Path(__file__).resolve().parents[2]
T2 = date(2026, 1, 29)
SAN = 15_000_000.0
TUOI = 180


def _nap_e7():
    spec = importlib.util.spec_from_file_location("build_pool_td0307", REPO / "entrypoints" / "build_pool.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E7 = _nap_e7()


def _vol(bang: dict[str, float]):
    def doc(sym: str, nam: int, thang: int):
        if (nam, thang) == (T2.year, T2.month):
            return {T2: bang[sym]}
        raise NenThangKhongCoError("không cần tháng khác")

    return doc


def _dung(khoang: dict, vol: dict[str, float]):
    return dung_ro_tai_moc(T2, khoang, doc_volume_thang=_vol(vol), age_floor_days=TUOI, volume_floor_usdt=SAN)


class TestMocNgungThatVaoDuongSanXuat:
    def test_moc_ngung_truoc_T2_bi_loai_du_thang_cuoi_bang_thang_lon_nhat(self) -> None:
        """Đúng hình MT-59: nhánh cũ thấy `thang_cuoi` = tháng lớn nhất ⇒ `delisted_at = None` ⇒ cho qua.
        Volume cố ý ĐỦ ngưỡng để tách riêng tác dụng của mốc ngừng (khỏi dựa vào 'volume 0 loại giúp')."""
        khoang = {
            "SONGUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08"},
            "CHETUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "moc_ngung": "2025-12-01T09:00:00+00:00"},
        }
        kq = _dung(khoang, {"SONGUSDT": SAN * 2, "CHETUSDT": SAN * 2})
        assert "CHETUSDT" not in kq.pool_dung
        assert "SONGUSDT" in kq.pool_dung

    def test_moc_ngung_SAU_T2_van_vao_ro(self) -> None:
        """Mã chết GIỮA [T2,T3] còn sống tại T2 ⇒ vào rổ (DR-LOCKBOX-01 Q7: giữ + cắt tại mốc)."""
        khoang = {"TONUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-06", "moc_ngung": "2026-06-23T09:00:00+00:00"}}
        assert _dung(khoang, {"TONUSDT": SAN * 2}).pool_dung == ("TONUSDT",)

    def test_du_lieu_cu_khong_moc_ngung_di_nhanh_cu(self) -> None:
        """Hồi quy cho t0/t1: không có khoá mới thì hành vi y như trước (thang_cuoi max ⇒ không huỷ)."""
        khoang = {"AUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08"}}
        assert _dung(khoang, {"AUSDT": SAN * 2}).pool_dung == ("AUSDT",)


class TestFailClosedDoiSongChuaDo:
    def test_ma_lot_ro_ma_chi_la_can_tren_thi_TU_CHOI(self) -> None:
        khoang = {
            "DOUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "do_that"},
            "CANUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "can_tren_td0230"},
        }
        with pytest.raises(ValueError, match="CHƯA đo thật"):
            _dung(khoang, {"DOUSDT": SAN * 2, "CANUSDT": SAN * 2})

    def test_ma_can_tren_TRUOT_tieu_chi_thi_khong_sao(self) -> None:
        """Cận trên chỉ nguy khi mã LỌT rổ; trượt volume thì đời sống của nó không ảnh hưởng rổ."""
        khoang = {
            "DOUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "do_that"},
            "CANUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "can_tren_td0230"},
        }
        assert _dung(khoang, {"DOUSDT": SAN * 2, "CANUSDT": SAN / 2}).pool_dung == ("DOUSDT",)


# ─── Bộ sinh E7 ở mốc t2 ────────────────────────────────────────────────────

KHOANG_T2 = {
    "AUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "do_that"},
    "BUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "do_that"},
    "EXPLUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "do_that"},
    "LOWUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "can_tren_td0230"},
}
VOL_T2 = {"AUSDT": SAN * 3, "BUSDT": SAN * 2, "EXPLUSDT": SAN * 2, "LOWUSDT": SAN / 2}
DU_T2 = ["AUSDT", "BUSDT", "EXPLUSDT"]


def _repo(tmp_path: Path, *, td0231_t2: list[str], chet_truoc: list[str] = ()) -> Path:
    (tmp_path / "config").mkdir()
    shutil.copy(REPO / "config" / "tool_d_config.yaml", tmp_path / "config" / "tool_d_config.yaml")
    dl = tmp_path / "docs" / "du-lieu-do"
    dl.mkdir(parents=True)
    (dl / "td0230-lech-song-sot-pool.json").write_text(json.dumps({"khoang_ton_tai": {}}), encoding="utf-8")
    (dl / "td0306-khoang-ton-tai-that.json").write_text(
        json.dumps({"khoang_ton_tai": KHOANG_T2, "mt59_lech_pool_dung_tai_t2": list(chet_truoc)}), encoding="utf-8"
    )
    (dl / "td0231-pool-point-in-time.json").write_text(
        json.dumps({"moc": {"t2": T2.isoformat()}, "pool_dung_tai_t2": {"danh_sach": td0231_t2}}), encoding="utf-8"
    )
    ex = tmp_path / "user_data" / "data" / "explore" / "futures"
    ex.mkdir(parents=True)
    (ex / "EXPL_USDT_USDT-1h-futures.feather").write_bytes(b"")
    return tmp_path


def _chay(repo: Path, *, ghi: bool = True) -> int:
    return E7.sinh_ro_tai_moc(
        moc_ten="t2",
        ghi=ghi,
        repo_dir=repo,
        doc_volume_thang=_vol(VOL_T2),
        lay_exchange_info=lambda: {"symbols": []},
        thay_doi_chua_commit=lambda _: [],
        bay_gio=lambda: datetime(2026, 9, 18, tzinfo=timezone.utc),
        lay_git_info=lambda _: GitInfo(sha="c" * 40, is_clean=True),
    )


def _doc(repo: Path) -> dict:
    return yaml.safe_load((repo / "config" / "pool_t2.yaml").read_text(encoding="utf-8"))


class TestBoSinhT2:
    def test_khop_thi_ghi_pool_t2_nguon_td0306_kieu_bat_doi_xung(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, td0231_t2=DU_T2)
        assert _chay(repo) == 0
        ro = _doc(repo)
        assert ro["moc_t2"] == T2.isoformat()
        assert ro["trading"] == ["AUSDT", "BUSDT"]
        assert ro["loai"]["explore_da_dung"] == ["EXPLUSDT"]
        xx = ro["xuat_xu"]
        assert xx["nguon_khoang_ton_tai"]["file"].endswith("td0306-khoang-ton-tai-that.json")
        assert xx["doi_chieu_td0231"]["kieu"] == "bat_doi_xung"

    def test_chi_co_o_lan_tinh_moi_thi_TU_CHOI(self, tmp_path: Path) -> None:
        """Vế (a): sửa MT-59 chỉ thu hẹp rổ — xuất hiện mã MỚI là có thứ khác đã đổi."""
        repo = _repo(tmp_path, td0231_t2=["AUSDT", "BUSDT"])  # EXPLUSDT chỉ có ở lần tính mới
        assert _chay(repo) == E7.EXIT_RO_T1_LECH_TD0231
        assert not (repo / "config" / "pool_t2.yaml").exists()

    def test_chi_co_o_td0231_ma_la_ma_chet_truoc_T2_thi_CHAP_NHAN_va_ghi_lai(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, td0231_t2=DU_T2 + ["DEADUSDT"], chet_truoc=["DEADUSDT"])
        assert _chay(repo) == 0
        assert _doc(repo)["xuat_xu"]["doi_chieu_td0231"]["chi_co_o_td0231_giai_thich_bang_chet_truoc_t2"] == ["DEADUSDT"]

    def test_chi_co_o_td0231_KHONG_giai_thich_duoc_thi_TU_CHOI(self, tmp_path: Path) -> None:
        """Vế (b): lệch mà không nằm trong danh sách chết trước T2 ⇒ dừng."""
        repo = _repo(tmp_path, td0231_t2=DU_T2 + ["LAUSDT"], chet_truoc=["DEADUSDT"])
        assert _chay(repo) == E7.EXIT_RO_T1_LECH_TD0231
        assert not (repo / "config" / "pool_t2.yaml").exists()

    def test_t0_t1_van_doc_td0230_khong_phai_td0306(self) -> None:
        assert E7.NGUON_KHOANG_THEO_MOC["t0"] == E7.NGUON_TD0230
        assert E7.NGUON_KHOANG_THEO_MOC["t1"] == E7.NGUON_TD0230
        assert E7.NGUON_KHOANG_THEO_MOC["t2"] == E7.NGUON_TD0306


class TestLockboxVanBiChanDuRoT2DaCo:
    def test_ro_cho_tap_LOCKBOX_van_tu_choi_khi_pool_t2_ton_tai(self, tmp_path: Path) -> None:
        """🔴 An toàn: rổ T2 có rồi cũng KHÔNG mở đường cho bộ chạy vào lockbox."""
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "pool_t2.yaml").write_text(
            yaml.dump({"moc_t2": T2.isoformat(), "trading": ["AUSDT"]}), encoding="utf-8"
        )
        with pytest.raises(RoGiaiDoanError):
            ro_cho_tap("LOCKBOX", repo_dir=tmp_path)

    def test_bang_ro_theo_tap_khong_co_LOCKBOX(self) -> None:
        assert "LOCKBOX" not in RO_THEO_TAP
