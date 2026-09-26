"""TD-0437 (§12c.5 bước 2–4, `DR-TANG-CHAN-01`) — mở lại sau HALT theo THỜI GIAN LỊCH, không theo kết quả.

Spec bác phương án "mở lại khi dd hồi ≤ 5%" vì deadlock (HALT ⇒ không lệnh mới ⇒ dd đứng yên). Cơ chế chốt: đủ CẢ BA —
(a) hết vị thế · (b) qua 2 × `max_hold_bars` kể từ lúc hết · (c) người vận hành ghi xác nhận — thì `/start`, mở lại ở
NỬA cỡ (`NUA_CO`) tới khi dd ≤ soft; trong `NUA_CO` KHÔNG HALT lại (dd lúc mở lại vẫn > halt), chỉ còn ABORT > abort.
"""

from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tool_d.api_client.freqtrade_control import FreqtradeControlError, doc_so_vi_the_mo, mo_lai_bot
from tool_d.ops.risk_supervisor_daemon import NoiMoLai, chay_mot_vong_giam_sat, co_xac_nhan_mo_lai
from tool_d.risk_supervisor import (
    ABORT,
    BINH_THUONG,
    HALT,
    NUA_CO,
    RiskSupervisorError,
    TrangThaiBenVung,
    TrangThaiBreaker,
    dieu_kien_mo_lai,
    doc_trang_thai,
    luu_trang_thai,
    quyet_dinh_tang_chan,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
T0 = datetime(2026, 9, 27, 0, 0, 0, tzinfo=timezone.utc)
CHO = timedelta(hours=4 * 2 * 24)  # 2 × max_hold_bars_4h (24) × 4 h = 8 ngày


class TestNuaCoThuan:
    @pytest.mark.parametrize("dd,muc", [(9.0, NUA_CO), (19.9, NUA_CO), (5.01, NUA_CO), (5.0, BINH_THUONG),
                                        (0.0, BINH_THUONG), (20.01, ABORT), (None, NUA_CO)])
    def test_chuyen_muc_tu_NUA_CO(self, dd, muc) -> None:
        assert quyet_dinh_tang_chan(NUA_CO, dd_pct=dd) == muc

    def test_NUA_CO_KHONG_HALT_lai_du_dd_tren_8(self) -> None:
        """Deadlock spec đã bác: mở lại lúc dd còn > 8% mà HALT lại ngay thì không bao giờ ra khỏi HALT."""
        assert quyet_dinh_tang_chan(NUA_CO, dd_pct=12.0) == NUA_CO


class TestDieuKienMoLai:
    def _dk(self, **kw):
        goc = dict(so_vi_the_mo=0, luc_het_vi_the=T0, now=T0 + CHO, cho_toi_thieu=CHO, co_xac_nhan=True)
        return dieu_kien_mo_lai(**{**goc, **kw})

    def test_du_ca_ba_thi_rong(self) -> None:
        assert self._dk() == []

    @pytest.mark.parametrize(
        "kw,dau",
        [({"so_vi_the_mo": 2}, "(a)"), ({"so_vi_the_mo": None}, "(a)"), ({"luc_het_vi_the": None}, "(b)"),
         ({"now": T0 + CHO - timedelta(seconds=1)}, "(b)"), ({"co_xac_nhan": False}, "(c)")],
    )
    def test_thieu_tung_dieu_kien(self, kw, dau) -> None:
        thieu = self._dk(**kw)
        assert len(thieu) == 1 and thieu[0].startswith(dau)


class TestMocGioBenVung:
    def test_ghi_doc_lai(self, tmp_path) -> None:
        p = tmp_path / "state.json"
        luu_trang_thai(TrangThaiBenVung(breaker=TrangThaiBreaker(), muc_tang_chan=HALT, luc_halt=T0,
                                        luc_het_vi_the=T0 + timedelta(hours=3)), p)
        d = doc_trang_thai(p)
        assert (d.luc_halt, d.luc_het_vi_the) == (T0, T0 + timedelta(hours=3))

    def test_file_cu_khong_co_khoa(self, tmp_path) -> None:
        p = tmp_path / "state.json"
        luu_trang_thai(TrangThaiBenVung(breaker=TrangThaiBreaker()), p)
        tho = json.loads(p.read_text(encoding="utf-8"))
        del tho["luc_halt"], tho["luc_het_vi_the"]
        p.write_text(json.dumps(tho), encoding="utf-8")
        assert doc_trang_thai(p).luc_halt is None

    def test_moc_khong_mui_gio_thi_raise(self, tmp_path) -> None:
        p = tmp_path / "state.json"
        luu_trang_thai(TrangThaiBenVung(breaker=TrangThaiBreaker()), p)
        tho = json.loads(p.read_text(encoding="utf-8"))
        tho["luc_halt"] = "2026-09-27T00:00:00"
        p.write_text(json.dumps(tho), encoding="utf-8")
        with pytest.raises(RiskSupervisorError):
            doc_trang_thai(p)


class _San:
    """Mô phỏng bot: số vị thế mở, có xác nhận chưa, ghi thứ tự mọi lời gọi điều khiển."""

    def __init__(self) -> None:
        self.so_mo = 2
        self.xac_nhan = False
        self.loi_start: Exception | None = None
        self.goi: list[str] = []

    def mo_lai(self) -> NoiMoLai:
        def start():
            self.goi.append("start")
            if self.loi_start is not None:
                raise self.loi_start
            return {"status": "starting trader ..."}

        return NoiMoLai(doc_so_vi_the_mo_fn=lambda: self.so_mo, mo_lai_fn=start,
                        co_xac_nhan_fn=lambda _luc: self.xac_nhan, cho_toi_thieu=CHO)

    def vong(self, tt: TrangThaiBenVung, *, dd: float | None, now: datetime):
        return chay_mot_vong_giam_sat(
            tt, now=now, doc_account_fn=lambda: {}, doc_position_fn=lambda: [], doc_force_orders_fn=lambda: [],
            doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(), tu_thoi_diem_ms=1000,
            dung_bot_fn=lambda: self.goi.append("stop"), tinh_dd_fn=lambda _a: dd,
            tam_ngung_fn=lambda: self.goi.append("stopentry"), ghi_abort_fn=lambda: self.goi.append("su_kien"),
            luu_truoc_fn=lambda _t: None, mo_lai=self.mo_lai(),
        )


class TestKichBanMoLai:
    def test_HALT_cho_het_vi_the_cho_du_gio_xac_nhan_roi_moi_mo_lai_NUA_CO(self) -> None:
        san = _San()
        tt = TrangThaiBenVung(breaker=TrangThaiBreaker())
        tt, _ = san.vong(tt, dd=9.0, now=T0)
        assert tt.muc_tang_chan == HALT and tt.luc_halt == T0 and tt.luc_het_vi_the is None
        san.so_mo = 0
        t1 = T0 + timedelta(hours=5)
        tt, _ = san.vong(tt, dd=9.0, now=t1)
        assert tt.luc_het_vi_the == t1, "mốc hết vị thế = vòng ĐẦU TIÊN thấy 0"
        tt, _ = san.vong(tt, dd=9.0, now=t1 + CHO)
        assert tt.muc_tang_chan == HALT, "đủ (a)(b) nhưng chưa (c) ⇒ chưa mở"
        san.xac_nhan = True
        tt, dung = san.vong(tt, dd=9.0, now=t1 + CHO - timedelta(seconds=1))
        assert tt.muc_tang_chan == HALT, "(b) thiếu một giây ⇒ chưa mở"
        san.goi.clear()
        tt, dung = san.vong(tt, dd=9.0, now=t1 + CHO)
        assert (tt.muc_tang_chan, dung, san.goi) == (NUA_CO, False, ["start"])
        assert tt.luc_halt is None and tt.luc_het_vi_the is None

    def test_vi_the_xuat_hien_lai_thi_dong_ho_cho_lam_lai(self) -> None:
        san = _San()
        tt, _ = san.vong(TrangThaiBenVung(breaker=TrangThaiBreaker()), dd=9.0, now=T0)
        san.so_mo = 0
        tt, _ = san.vong(tt, dd=9.0, now=T0 + timedelta(hours=1))
        san.so_mo = 1
        tt, _ = san.vong(tt, dd=9.0, now=T0 + timedelta(hours=2))
        assert tt.luc_het_vi_the is None

    def test_trong_NUA_CO_dd_tren_8_khong_stopentry_hoi_ve_5_thi_binh_thuong(self) -> None:
        san = _San()
        tt = TrangThaiBenVung(breaker=TrangThaiBreaker(), muc_tang_chan=NUA_CO)
        tt, dung = san.vong(tt, dd=12.0, now=T0)
        assert (tt.muc_tang_chan, dung, san.goi) == (NUA_CO, False, [])
        tt, _ = san.vong(tt, dd=4.0, now=T0)
        assert tt.muc_tang_chan == BINH_THUONG

    def test_trong_NUA_CO_vuot_20_thi_ABORT(self) -> None:
        san = _San()
        tt, dung = san.vong(TrangThaiBenVung(breaker=TrangThaiBreaker(), muc_tang_chan=NUA_CO), dd=21.0, now=T0)
        assert tt.muc_tang_chan == ABORT and dung is True and san.goi == ["stop", "su_kien"]

    def test_start_loi_thi_giu_HALT_va_van_stopentry(self) -> None:
        san = _San()
        san.so_mo, san.xac_nhan = 0, True
        san.loi_start = FreqtradeControlError("mô phỏng: /start lỗi")
        tt = TrangThaiBenVung(breaker=TrangThaiBreaker(), muc_tang_chan=HALT, luc_halt=T0, luc_het_vi_the=T0)
        tt, dung = san.vong(tt, dd=9.0, now=T0 + CHO)
        assert (tt.muc_tang_chan, dung, san.goi) == (HALT, False, ["start", "stopentry"])

    def test_co_do_KHONG_BAO_GIO_start(self) -> None:
        san = _San()
        san.so_mo, san.xac_nhan = 0, True
        tt = TrangThaiBenVung(breaker=TrangThaiBreaker(), muc_tang_chan=HALT, luc_halt=T0, luc_het_vi_the=T0,
                              leo_thang_dung=True)
        _, dung = san.vong(tt, dd=9.0, now=T0 + CHO)
        assert dung is True and san.goi == []

    def test_thieu_bo_mo_lai_thi_khong_bao_gio_tu_mo(self) -> None:
        goi: list[str] = []
        tt = TrangThaiBenVung(breaker=TrangThaiBreaker(), muc_tang_chan=HALT, luc_halt=T0, luc_het_vi_the=T0)
        tt, _ = chay_mot_vong_giam_sat(
            tt, now=T0 + CHO * 10, doc_account_fn=lambda: {}, doc_position_fn=lambda: [],
            doc_force_orders_fn=lambda: [], doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(), tu_thoi_diem_ms=1000,
            dung_bot_fn=lambda: goi.append("stop"), tinh_dd_fn=lambda _a: 9.0,
            tam_ngung_fn=lambda: goi.append("stopentry"), ghi_abort_fn=lambda: None, luu_truoc_fn=lambda _t: None,
        )
        assert tt.muc_tang_chan == HALT and goi == ["stopentry"]

    def test_main_noi_bo_mo_lai(self) -> None:
        cay = ast.parse((REPO_ROOT / "src/tool_d/ops/risk_supervisor_daemon.py").read_text(encoding="utf-8"))
        main = next(n for n in cay.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        goi = [n for n in ast.walk(main) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "chay_mot_vong_giam_sat"]
        assert len(goi) == 1 and "mo_lai" in {k.arg for k in goi[0].keywords}


class TestDongXacNhan:
    @pytest.mark.parametrize(
        "noi_dung,runmode,ket_qua",
        [("x\nXAC_NHAN_MO_LAI_HALT dry_run 2026-09-27\n", "dry_run", True),
         ("XAC_NHAN_MO_LAI_HALT dry_run 2026-09-28\n", "dry_run", True),
         ("XAC_NHAN_MO_LAI_HALT dry_run 2026-09-26\n", "dry_run", False),  # trước ngày HALT
         ("XAC_NHAN_MO_LAI_HALT live 2026-09-27\n", "dry_run", False),  # sai runmode
         ("  XAC_NHAN_MO_LAI_HALT dry_run 2026-09-27  \n", "dry_run", True),
         ("- XAC_NHAN_MO_LAI_HALT dry_run 2026-09-27\n", "dry_run", False),  # phải là dòng riêng
         ("XAC_NHAN_MO_LAI_HALT dry_run 2026-13-40\n", "dry_run", False)],
    )
    def test_nhan_dien(self, tmp_path, noi_dung, runmode, ket_qua) -> None:
        p = tmp_path / "research-log.md"
        p.write_text(noi_dung, encoding="utf-8")
        assert co_xac_nhan_mo_lai(p, runmode=runmode, luc_halt=T0 + timedelta(hours=10)) is ket_qua

    def test_thieu_file_thi_chua_xac_nhan(self, tmp_path) -> None:
        assert co_xac_nhan_mo_lai(tmp_path / "khong_co.md", runmode="live", luc_halt=T0) is False


def _resp(payload) -> MagicMock:
    r = MagicMock()
    r.read.return_value = json.dumps(payload).encode("utf-8")
    r.__enter__.return_value = r
    return r


class TestApiMoi:
    def test_mo_lai_bot_POST_start(self) -> None:
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as m:
            m.return_value = _resp({"status": "starting trader ..."})
            mo_lai_bot("http://127.0.0.1:8081", username="u", password="p")
        req = m.call_args[0][0]
        assert req.full_url.endswith("/api/v1/start") and req.get_method() == "POST"

    def test_doc_so_vi_the_mo_GET_status(self) -> None:
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as m:
            m.return_value = _resp([{"trade_id": 1}, {"trade_id": 2}])
            assert doc_so_vi_the_mo("http://127.0.0.1:8081", username="u", password="p") == 2
        req = m.call_args[0][0]
        assert req.full_url.endswith("/api/v1/status") and req.get_method() == "GET"

    def test_status_khong_phai_danh_sach_thi_raise(self) -> None:
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as m:
            m.return_value = _resp({"error": "x"})
            with pytest.raises(FreqtradeControlError):
                doc_so_vi_the_mo("http://127.0.0.1:8081", username="u", password="p")
