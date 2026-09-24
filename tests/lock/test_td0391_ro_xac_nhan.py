"""TD-0391 (`DR-XAC-NHAN-01` §9) — rổ `XAC_NHAN` tại ngày CHỌN.

Khoá năm thứ:
1. Bộ đọc kho NGÀY `doc_quote_volume_1d_ngay` fail-closed (ngày chưa đóng không gọi mạng, 404 là dữ kiện, lệch ngày /
   nhiều hàng là lỗi) — cùng khuôn bộ đọc kho tháng.
2. `mo_rong_khoang` chỉ nối đời sống mã còn sống ở tháng cuối nguồn, không nối mã có `moc_ngung`, từ chối khi mốc quá xa.
3. `doc_volume_cho_moc`: tháng mốc đọc kho NGÀY, tháng khác đọc kho THÁNG.
4. E7 `--ro-xac-nhan`: mốc đọc từ sổ ý tưởng, đòi hiện vật đối chiếu KHÍT, từ chối ghi đè; `ro_cho_tap("XAC_NHAN")` đọc
   được file sinh ra.
5. Hai đường (E7 và kịch bản logic `TD-0231`) chạy trên CÙNG một bộ dữ liệu giả phải ra CÙNG một rổ.
"""

from __future__ import annotations

import importlib.util
import io
import json
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from tool_d.api_client.binance_public import KhoLuuTruError, NenThangKhongCoError, doc_quote_volume_1d_ngay
from tool_d.measurement.gitinfo import GitInfo
from tool_d.pool_giai_doan import RoGiaiDoanError, ro_cho_tap
from tool_d.pool_xac_nhan import RoXacNhanError, doc_volume_cho_moc, lan_chon, mo_rong_khoang

REPO = Path(__file__).resolve().parents[2]
MOC = date(2026, 9, 10)
SELECTED_AT = "2026-09-10T14:07:20Z"
SLOT = "IQ-0099"
SAN = 15_000_000.0
TUOI = 180
MS_MOC = int(datetime(2026, 9, 10, tzinfo=timezone.utc).timestamp() * 1000)


def _nap(ten: str, duong: Path):
    spec = importlib.util.spec_from_file_location(ten, duong)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E7 = _nap("build_pool_td0391", REPO / "entrypoints" / "build_pool.py")


# ─── 1. Bộ đọc kho NGÀY ─────────────────────────────────────────────────────


def _zip(rows: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("X-1d-2026-09-10.csv", "\n".join(rows))
    return buf.getvalue()


def _hang(moc: int, qv: str = "20000000.5") -> str:
    return f"{moc},1,2,0.5,1.5,1000,{moc + 86_399_999},{qv},10,1,1,0"


def _conn(status: int = 200, body: bytes = b"") -> MagicMock:
    conn, resp = MagicMock(), MagicMock()
    resp.status, resp.read.return_value = status, body
    conn.getresponse.return_value = resp
    return conn


def _doc(conn: MagicMock, ngay: date = MOC) -> dict:
    with patch("http.client.HTTPSConnection", return_value=conn):
        return doc_quote_volume_1d_ngay(symbol="AUSDT", ngay=ngay, hom_nay=date(2026, 9, 25))


class TestBoDocKhoNgay:
    def test_mot_hang_dung_ngay_thi_tra_ve_volume(self) -> None:
        conn = _conn(body=_zip([_hang(MS_MOC)]))
        assert _doc(conn) == {MOC: 20000000.5}
        duong = conn.request.call_args[0][1]
        assert duong == "/data/futures/um/daily/klines/AUSDT/1d/AUSDT-1d-2026-09-10.zip"

    def test_moc_micro_giay_va_hang_tieu_de_van_doc_dung(self) -> None:
        tieu_de = "open_time,open,high,low,close,volume,close_time,quote_volume,count,a,b,c"
        assert _doc(_conn(body=_zip([tieu_de, _hang(MS_MOC * 1000)]))) == {MOC: 20000000.5}

    def test_404_la_du_kien(self) -> None:
        with pytest.raises(NenThangKhongCoError):
            _doc(_conn(status=404))

    def test_hang_lech_ngay_thi_TU_CHOI(self) -> None:
        with pytest.raises(KhoLuuTruError, match="không phải 2026-09-10"):
            _doc(_conn(body=_zip([_hang(MS_MOC + 86_400_000)])))

    def test_hai_hang_thi_TU_CHOI(self) -> None:
        """Hai hàng CÙNG ngày: dict chỉ giữ một, nên phải đếm hàng — không để hàng sau đè im lặng."""
        with pytest.raises(KhoLuuTruError, match="2 hàng"):
            _doc(_conn(body=_zip([_hang(MS_MOC), _hang(MS_MOC, "1")])))

    def test_0_hang_thi_TU_CHOI(self) -> None:
        with pytest.raises(KhoLuuTruError, match="0 hàng"):
            _doc(_conn(body=_zip([""])))

    @pytest.mark.parametrize("ngay", [date(2026, 9, 25), date(2026, 9, 26)])
    def test_ngay_chua_dong_thi_khong_goi_mang(self, ngay: date) -> None:
        with patch("http.client.HTTPSConnection") as conn:
            with pytest.raises(ValueError, match="chưa đóng"):
                doc_quote_volume_1d_ngay(symbol="AUSDT", ngay=ngay, hom_nay=date(2026, 9, 25))
        conn.assert_not_called()


# ─── 2–3. Logic thuần ───────────────────────────────────────────────────────

KHOANG = {
    "AUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "do_that"},
    "BUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "do_that"},
    "EXPLUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "do_that"},
    "LOWUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "do_that"},
    "GONEUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "do_that"},
    "CHETUSDT": {
        "thang_dau": "2023-01", "thang_cuoi": "2026-08", "nguon_thang_cuoi": "do_that",
        "moc_ngung": "2026-08-20T09:00:00+00:00",
    },
    "CUUSDT": {"thang_dau": "2022-01", "thang_cuoi": "2025-03", "nguon_thang_cuoi": "do_that"},
}
#: GONEUSDT: còn sống cuối 08 nhưng không có file ngày mốc (rời sàn trong 09) ⇒ 404.
VOL_NGAY = {"AUSDT": SAN * 3, "BUSDT": SAN * 2, "EXPLUSDT": SAN * 2, "LOWUSDT": SAN / 2, "CHETUSDT": SAN * 5}
DU = ["AUSDT", "BUSDT", "EXPLUSDT"]


def _doc_ngay(sym: str, ngay: date) -> dict:
    assert ngay == MOC
    if sym not in VOL_NGAY:
        raise NenThangKhongCoError(f"{sym} không có file ngày")
    return {ngay: VOL_NGAY[sym]}


def _doc_thang(sym: str, nam: int, thang: int) -> dict:
    raise NenThangKhongCoError("không cần tháng khác trong fixture")


class TestMoRongKhoang:
    def test_chi_noi_ma_con_song_cuoi_nguon_khong_moc_ngung(self) -> None:
        ra, noi = mo_rong_khoang(KHOANG, MOC, age_floor_days=TUOI)
        assert noi == ["AUSDT", "BUSDT", "EXPLUSDT", "GONEUSDT", "LOWUSDT"]
        assert ra["AUSDT"]["thang_cuoi"] == "2026-09"
        assert ra["CHETUSDT"]["thang_cuoi"] == "2026-08"  # chết trong tháng cuối nguồn — không nối
        assert ra["CUUSDT"]["thang_cuoi"] == "2025-03"
        assert KHOANG["AUSDT"]["thang_cuoi"] == "2026-08"  # không sửa bản gốc

    def test_moc_trong_nguon_thi_khong_noi(self) -> None:
        _, noi = mo_rong_khoang(KHOANG, date(2026, 8, 15), age_floor_days=TUOI)
        assert noi == []

    def test_moc_qua_xa_nguon_thi_TU_CHOI(self) -> None:
        """Mã niêm yết từ 09/2026 đủ 180 ngày ở 2027-02-28 mà nguồn không biết tới ⇒ không được đoán."""
        with pytest.raises(RoXacNhanError, match="quá xa"):
            mo_rong_khoang(KHOANG, date(2027, 2, 28), age_floor_days=TUOI)
        mo_rong_khoang(KHOANG, date(2027, 2, 27), age_floor_days=TUOI)


class TestDocVolumeChoMoc:
    def test_thang_moc_doc_kho_ngay_thang_khac_doc_kho_thang(self) -> None:
        goi: list[tuple] = []
        doc = doc_volume_cho_moc(
            MOC,
            doc_ngay=lambda s, n: goi.append(("ngay", s, n)) or {n: 1.0},
            doc_thang=lambda s, y, m: goi.append(("thang", s, y, m)) or {},
        )
        doc("AUSDT", 2026, 9)
        doc("AUSDT", 2023, 1)
        assert goi == [("ngay", "AUSDT", MOC), ("thang", "AUSDT", 2023, 1)]


# ─── 4–5. E7 + đường thứ hai trên repo tạm ──────────────────────────────────


def _y_tuong(*, voided: bool = False) -> list[dict]:
    dong = [{"idea_id": SLOT, "status": "QUEUED", "selected_at": None},
            {"idea_id": SLOT, "status": "SELECTED", "selected_at": SELECTED_AT}]
    if voided:
        dong.append({"idea_id": SLOT, "status": "VOIDED", "selected_at": SELECTED_AT})
    return dong


def _repo(tmp_path: Path, *, doi_chieu: list[str] | None = DU, voided: bool = False) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "tool_d_config.yaml").write_text(
        (REPO / "config" / "tool_d_config.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "registry").mkdir()
    (tmp_path / "registry" / "idea_queue.jsonl").write_text(
        "".join(json.dumps(d) + "\n" for d in _y_tuong(voided=voided)), encoding="utf-8"
    )
    dl = tmp_path / "docs" / "du-lieu-do"
    dl.mkdir(parents=True)
    (dl / "td0306-khoang-ton-tai-that.json").write_text(json.dumps({"khoang_ton_tai": KHOANG}), encoding="utf-8")
    if doi_chieu is not None:
        (dl / "td0391-ro-xac-nhan-doi-chieu.json").write_text(
            json.dumps({"moc": MOC.isoformat(), "hypothesis_slot": SLOT, "pool_dung": doi_chieu}), encoding="utf-8"
        )
    ex = tmp_path / "user_data" / "data" / "explore" / "futures"
    ex.mkdir(parents=True)
    (ex / "EXPL_USDT_USDT-1h-futures.feather").write_bytes(b"")
    return tmp_path


def _chay(repo: Path, *, ghi: bool = True, hom_nay: date = date(2026, 9, 25), slot: str = SLOT) -> int:
    return E7.sinh_ro_xac_nhan(
        slot=slot,
        ghi=ghi,
        repo_dir=repo,
        doc_volume_ngay=_doc_ngay,
        doc_volume_thang=_doc_thang,
        lay_exchange_info=lambda: {"symbols": []},
        thay_doi_chua_commit=lambda _: [],
        bay_gio=lambda: datetime.combine(hom_nay, datetime.min.time(), tzinfo=timezone.utc),
        lay_git_info=lambda _: GitInfo(sha="c" * 40, is_clean=True),
    )


def _ro(repo: Path) -> dict:
    return yaml.safe_load((repo / "config" / "pool_xac_nhan.yaml").read_text(encoding="utf-8"))


class TestLanChon:
    def test_ngay_va_selected_at_tu_so_y_tuong(self, tmp_path: Path) -> None:
        assert lan_chon(SLOT, _repo(tmp_path)) == (MOC, SELECTED_AT)

    def test_lan_chon_da_huy_thi_TU_CHOI(self, tmp_path: Path) -> None:
        with pytest.raises(RoXacNhanError, match="không có lần CHỌN"):
            lan_chon(SLOT, _repo(tmp_path, voided=True))


class TestE7RoXacNhan:
    def test_khop_thi_ghi_ro_va_ro_cho_tap_doc_duoc(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        assert _chay(repo) == 0
        ro = _ro(repo)
        assert ro["moc_xac_nhan"] == MOC.isoformat()
        assert ro["hypothesis_slot"] == SLOT and ro["selected_at"] == SELECTED_AT
        assert ro["trading"] == ["AUSDT", "BUSDT"]
        assert ro["loai"]["explore_da_dung"] == ["EXPLUSDT"]
        assert ro["khong_do_duoc"]["kho_404"] == ["GONEUSDT"]
        assert ro["xuat_xu"]["trial"] == 0 and ro["xuat_xu"]["doi_chieu"]["kieu"] == "khit"
        assert ro_cho_tap("XAC_NHAN", repo_dir=repo).trading == ("AUSDT", "BUSDT")

    def test_ma_chet_trong_thang_cuoi_nguon_khong_vao_ro_du_co_volume(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        assert _chay(repo) == 0
        assert "CHETUSDT" not in _ro(repo)["trading"]

    @pytest.mark.parametrize("doi_chieu", [["AUSDT", "BUSDT"], DU + ["LOWUSDT"]])
    def test_lech_doi_chieu_thi_TU_CHOI(self, tmp_path: Path, doi_chieu: list[str]) -> None:
        repo = _repo(tmp_path, doi_chieu=doi_chieu)
        assert _chay(repo) == E7.EXIT_RO_T1_LECH_TD0231
        assert not (repo / "config" / "pool_xac_nhan.yaml").exists()

    def test_thieu_hien_vat_doi_chieu_thi_TU_CHOI(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, doi_chieu=None)
        assert _chay(repo) == E7.EXIT_RO_XAC_NHAN_TU_CHOI
        assert not (repo / "config" / "pool_xac_nhan.yaml").exists()

    def test_khong_co_lan_chon_hieu_luc_thi_TU_CHOI(self, tmp_path: Path) -> None:
        assert _chay(_repo(tmp_path, voided=True)) == E7.EXIT_RO_XAC_NHAN_TU_CHOI

    def test_slot_khac_thi_TU_CHOI(self, tmp_path: Path) -> None:
        assert _chay(_repo(tmp_path), slot="IQ-0098") == E7.EXIT_RO_XAC_NHAN_TU_CHOI

    def test_ngay_chon_chua_dong_thi_TU_CHOI(self, tmp_path: Path) -> None:
        assert _chay(_repo(tmp_path), hom_nay=MOC) == E7.EXIT_RO_XAC_NHAN_TU_CHOI

    def test_khong_ghi_de(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        assert _chay(repo) == 0
        assert _chay(repo) == E7.EXIT_POOL_ALREADY_COMMITTED

    def test_chay_thu_khong_ghi(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        assert _chay(repo, ghi=False) == 0
        assert not (repo / "config" / "pool_xac_nhan.yaml").exists()

    def test_chua_co_ro_thi_ro_cho_tap_tu_choi_va_chi_dung_co(self, tmp_path: Path) -> None:
        with pytest.raises(RoGiaiDoanError, match="--ro-xac-nhan --slot"):
            ro_cho_tap("XAC_NHAN", repo_dir=tmp_path)


class TestHaiDuongKhop:
    def test_duong_TD0231_va_E7_ra_cung_mot_ro(self, tmp_path: Path, monkeypatch) -> None:
        """Chạy THẬT kịch bản đường thứ hai (logic `_dung_mot_moc` của TD-0231) rồi E7 trên cùng dữ liệu giả."""
        repo = _repo(tmp_path, doi_chieu=None)
        kb = _nap("do_td0391_test", REPO / "docs" / "du-lieu-do" / "do_td0391_ro_xac_nhan_doi_chieu.py")
        monkeypatch.setattr(kb, "REPO", repo)
        monkeypatch.setattr(kb, "NGUON_TD0306", repo / "docs" / "du-lieu-do" / "td0306-khoang-ton-tai-that.json")
        monkeypatch.setattr(kb, "KET_QUA", repo / "docs" / "du-lieu-do" / "td0391-ro-xac-nhan-doi-chieu.json")
        monkeypatch.setattr(kb, "doc_quote_volume_1d_ngay", lambda *, symbol, ngay: _doc_ngay(symbol, ngay))
        monkeypatch.setattr(kb, "doc_quote_volume_1d_thang", lambda *, symbol, nam, thang: _doc_thang(symbol, nam, thang))
        monkeypatch.setattr(kb, "get_git_info", lambda _: GitInfo(sha="d" * 40, is_clean=True))
        assert kb.main(["--slot", SLOT, "--ghi"]) == 0
        hv = json.loads((repo / "docs" / "du-lieu-do" / "td0391-ro-xac-nhan-doi-chieu.json").read_text(encoding="utf-8"))
        assert hv["pool_dung"] == DU and hv["moc"] == MOC.isoformat() and hv["trial"] == 0
        assert hv["khong_do_duoc"]["kho_404"] == ["GONEUSDT"]
        assert _chay(repo) == 0
        assert kb.main(["--slot", SLOT, "--ghi"]) == 1  # không ghi đè hiện vật
