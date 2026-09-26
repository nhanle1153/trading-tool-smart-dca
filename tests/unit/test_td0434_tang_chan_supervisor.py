"""TD-0434 (`DR-TANG-CHAN-01`, §12c.5) — Risk Supervisor thi hành phần CỨNG của thang sụt vốn cho MỌI chiến lược.

Trước bản này: `HANG_SO_KHAI_LAI` khai 5/8/20 và `L-Z44` kiểm khớp cấu hình, nhưng KHÔNG dòng mã nào dùng chúng để chặn;
thang chỉ sống trong `ZoneAbsorption` (`RoFunding` không có tầng nào) và đo trên lãi/lỗ đã chốt.

Bốn lớp: quyết định THUẦN (`quyet_dinh_tang_chan`) · một vòng giám sát (`chay_mot_vong_giam_sat`, mọi lời gọi mạng tiêm
qua tham số) · mức sụt từ số dư sàn (`dd_tu_account`, qua `equity_peak` + sổ `TD-0426`) · `/stopentry`
(`tam_ngung_mo_lenh`, luật 1 của `api-integration-rules.md` 4.4d). Cộng một ca AST: `main()` phải nối đủ bốn khoá.
"""

from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tool_d.api_client.freqtrade_control import (
    FreqtradeBatLaiBotError,
    FreqtradeControlError,
    doc_so_lenh_dong,
    tam_ngung_mo_lenh,
)
from tool_d.equity_peak import NAP_RUT, SuKienDinh, doc_so_su_kien, duong_dan_so_su_kien, ghi_su_kien
from tool_d.ops.risk_supervisor_daemon import (
    chay_mot_vong_giam_sat,
    dd_tu_account,
    duong_dan_dinh_supervisor,
    ghi_su_kien_abort,
)
from tool_d.risk_supervisor import (
    ABORT,
    BINH_THUONG,
    HALT,
    HANG_SO_KHAI_LAI,
    RiskSupervisorError,
    TrangThaiBenVung,
    TrangThaiBreaker,
    doc_trang_thai,
    luu_trang_thai,
    ap_tran_halt,
    quyet_dinh_tang_chan,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
T0 = datetime(2026, 9, 26, 0, 0, 0, tzinfo=timezone.utc)


def _tt(muc: str = BINH_THUONG, **kw) -> TrangThaiBenVung:
    return TrangThaiBenVung(breaker=TrangThaiBreaker(), muc_tang_chan=muc, **kw)


class TestQuyetDinhThuan:
    def test_dung_hang_so_khai_lai(self) -> None:
        assert (HANG_SO_KHAI_LAI.dd_halt_pct, HANG_SO_KHAI_LAI.dd_abort_pct) == (8.0, 20.0)

    @pytest.mark.parametrize(
        "muc_cu,dd,muc_moi",
        [
            (BINH_THUONG, 0.0, BINH_THUONG),
            (BINH_THUONG, 7.99, BINH_THUONG),
            (BINH_THUONG, 8.0, BINH_THUONG),  # spec: "dd > 8%" — NGẶT
            (BINH_THUONG, 8.01, HALT),
            (BINH_THUONG, 20.0, HALT),
            (BINH_THUONG, 20.01, ABORT),
            (HALT, 20.01, ABORT),
        ],
    )
    def test_thang_8_20_so_sanh_ngat(self, muc_cu: str, dd: float, muc_moi: str) -> None:
        assert quyet_dinh_tang_chan(muc_cu, dd_pct=dd) == muc_moi

    def test_HALT_KHONG_tu_mo_lai_khi_dd_hoi(self) -> None:
        """§12c.5: mở lại theo dd hồi là phương án deadlock spec đã bác — mở lại là việc của TD-0437."""
        assert quyet_dinh_tang_chan(HALT, dd_pct=0.0) == HALT

    @pytest.mark.parametrize("dd", [0.0, None, 9.0, 15.0, 25.0])
    def test_ABORT_khong_tu_go(self, dd) -> None:
        """Gồm dd trong dải HALT (9, 15): phá thật M2 cho thấy chỉ thử 0/None thì một nhánh 'ABORT hạ xuống HALT' lọt."""
        assert quyet_dinh_tang_chan(ABORT, dd_pct=dd) == ABORT

    @pytest.mark.parametrize("muc", [BINH_THUONG, HALT])
    def test_chua_do_duoc_thi_giu_nguyen_khong_bia(self, muc: str) -> None:
        assert quyet_dinh_tang_chan(muc, dd_pct=None) == muc

    @pytest.mark.parametrize("dd", [float("nan"), -0.1])
    def test_dd_rac_thi_raise(self, dd: float) -> None:
        with pytest.raises(RiskSupervisorError):
            quyet_dinh_tang_chan(BINH_THUONG, dd_pct=dd)

    def test_muc_la_thi_raise(self) -> None:
        with pytest.raises(RiskSupervisorError):
            quyet_dinh_tang_chan("PAUSE", dd_pct=1.0)

    @pytest.mark.parametrize(
        "kw,co_do",
        [({}, False), ({"muc_tang_chan": HALT}, False), ({"muc_tang_chan": ABORT}, True),
         ({"leo_thang_dung": True}, True), ({"la_thanh_ly": True}, True)],
    )
    def test_co_do_gop_moi_ly_do(self, kw: dict, co_do: bool) -> None:
        assert TrangThaiBenVung(breaker=TrangThaiBreaker(), **kw).co_do is co_do


class TestTrangThaiBenVung:
    def test_ghi_doc_lai_hai_truong_moi(self, tmp_path) -> None:
        p = tmp_path / "state.json"
        luu_trang_thai(_tt(HALT, leo_thang_dung=True), p)
        doc = doc_trang_thai(p)
        assert (doc.muc_tang_chan, doc.leo_thang_dung) == (HALT, True)

    def test_file_TRUOC_TD_0434_doc_duoc_mac_dinh_binh_thuong(self, tmp_path) -> None:
        p = tmp_path / "state.json"
        luu_trang_thai(_tt(), p)
        tho = json.loads(p.read_text(encoding="utf-8"))
        del tho["muc_tang_chan"], tho["leo_thang_dung"]
        p.write_text(json.dumps(tho), encoding="utf-8")
        doc = doc_trang_thai(p)
        assert (doc.muc_tang_chan, doc.leo_thang_dung) == (BINH_THUONG, False)

    @pytest.mark.parametrize("khoa,gia_tri", [("muc_tang_chan", "halt"), ("leo_thang_dung", "true")])
    def test_khoa_sai_kieu_thi_raise_khong_coi_la_sach(self, tmp_path, khoa: str, gia_tri) -> None:
        p = tmp_path / "state.json"
        luu_trang_thai(_tt(), p)
        tho = json.loads(p.read_text(encoding="utf-8"))
        tho[khoa] = gia_tri
        p.write_text(json.dumps(tho), encoding="utf-8")
        with pytest.raises(RiskSupervisorError):
            doc_trang_thai(p)


class _Ghi:
    """Ghi THỨ TỰ mọi hành động của một vòng — thứ tự là một phần của hợp đồng (ABORT: lưu → /stop → sự kiện)."""

    def __init__(self, *, loi_tam_ngung: Exception | None = None) -> None:
        self.goi: list[str] = []
        self._loi = loi_tam_ngung

    def dung_bot(self):
        self.goi.append("stop")
        return {"status": "stopping trader ..."}

    def tam_ngung(self):
        self.goi.append("stopentry")
        if self._loi is not None:
            raise self._loi
        return {"status": "paused, no more entries will occur from now. Run /start to enable entries."}

    def ghi_abort(self):
        self.goi.append("su_kien_abort")

    def luu(self, t: TrangThaiBenVung):
        self.goi.append(f"luu:{t.muc_tang_chan}:{t.leo_thang_dung}")


def _vong(tt: TrangThaiBenVung, ghi: _Ghi, *, dd: float | None, account=None, force_orders=None, so_lenh=None):
    return chay_mot_vong_giam_sat(
        tt,
        now=T0,
        doc_account_fn=lambda: account if account is not None else {"totalMarginBalance": "1000"},
        doc_position_fn=lambda: [],
        doc_force_orders_fn=lambda: force_orders if force_orders is not None else [],
        doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(),
        tu_thoi_diem_ms=1000,
        dung_bot_fn=ghi.dung_bot,
        tinh_dd_fn=lambda _account: dd,
        tam_ngung_fn=ghi.tam_ngung,
        ghi_abort_fn=ghi.ghi_abort,
        luu_truoc_fn=ghi.luu,
        doc_so_lenh_dong_fn=(lambda: so_lenh) if so_lenh is not None else None,
    )


class TestMotVongGiamSat:
    def test_binh_thuong_khong_goi_gi(self) -> None:
        g = _Ghi()
        tt, dung = _vong(_tt(), g, dd=3.0)
        assert (tt.muc_tang_chan, dung, g.goi) == (BINH_THUONG, False, [])

    def test_vuot_8_thi_HALT_goi_stopentry_bot_van_song(self) -> None:
        g = _Ghi()
        tt, dung = _vong(_tt(), g, dd=9.0)
        assert (tt.muc_tang_chan, dung, g.goi) == (HALT, False, ["stopentry"])

    def test_dang_HALT_goi_lai_stopentry_MOI_VONG(self) -> None:
        """4.4d luật 2: HALT không sống qua restart bot — phải gọi lại mỗi vòng, kể cả khi dd đã hồi."""
        g = _Ghi()
        tt, _ = _vong(_tt(HALT), g, dd=1.0)
        tt, _ = _vong(tt, g, dd=None)
        assert tt.muc_tang_chan == HALT and g.goi == ["stopentry", "stopentry"]

    def test_vuot_20_thi_ABORT_dung_THU_TU_luu_stop_su_kien(self) -> None:
        g = _Ghi()
        tt, dung = _vong(_tt(HALT), g, dd=25.0)
        assert tt.muc_tang_chan == ABORT and tt.co_do and dung is True
        assert g.goi == [f"luu:{ABORT}:False", "stop", "su_kien_abort"]

    def test_ABORT_ma_stop_loi_thi_KHONG_ghi_su_kien_dat_lai_dinh(self) -> None:
        g = _Ghi()

        def stop_loi():
            g.goi.append("stop")
            raise FreqtradeControlError("mô phỏng: không dừng được")

        with pytest.raises(FreqtradeControlError):
            chay_mot_vong_giam_sat(
                _tt(), now=T0, doc_account_fn=lambda: {}, doc_position_fn=lambda: [],
                doc_force_orders_fn=lambda: [], doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(),
                tu_thoi_diem_ms=1000, dung_bot_fn=stop_loi, tinh_dd_fn=lambda _a: 30.0,
                tam_ngung_fn=g.tam_ngung, ghi_abort_fn=g.ghi_abort, luu_truoc_fn=g.luu,
            )
        assert g.goi == [f"luu:{ABORT}:False", "stop"], "sự kiện ABORT không được ghi khi /stop thất bại"

    def test_CO_DO_thi_KHONG_BAO_GIO_goi_stopentry(self) -> None:
        """4.4d luật 1: gọi /stopentry khi bot STOPPED = BẬT LẠI bot."""
        for tt in (_tt(ABORT), _tt(HALT, leo_thang_dung=True), _tt(HALT, la_thanh_ly=True)):
            g = _Ghi()
            tt_moi, dung = _vong(tt, g, dd=12.0)
            assert dung is True and g.goi == [] and tt_moi == tt

    def test_thanh_ly_moi_trong_vong_HALT_thi_stop_khong_stopentry(self) -> None:
        g = _Ghi()
        tt, dung = _vong(_tt(HALT), g, dd=12.0, force_orders=[{"time": 5000}])
        assert dung is True and tt.la_thanh_ly and g.goi == ["stop"]

    @pytest.mark.parametrize(
        "loi", [FreqtradeControlError("hết lượt"), FreqtradeBatLaiBotError("vừa bật lại bot")]
    )
    def test_HALT_khong_thi_hanh_duoc_thi_LEO_THANG_stop_co_do(self, loi) -> None:
        g = _Ghi(loi_tam_ngung=loi)
        tt, dung = _vong(_tt(), g, dd=9.0)
        assert dung is True and tt.leo_thang_dung and tt.co_do
        assert g.goi == ["stopentry", f"luu:{HALT}:True", "stop"]

    def test_account_doc_loi_thi_giu_nguyen_muc_va_van_goi_lai_stopentry(self) -> None:
        g = _Ghi()

        def account_loi():
            raise RiskSupervisorError("mô phỏng: account lỗi")

        tt, dung = chay_mot_vong_giam_sat(
            _tt(HALT), now=T0, doc_account_fn=account_loi, doc_position_fn=lambda: [],
            doc_force_orders_fn=lambda: [], doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(),
            tu_thoi_diem_ms=1000, dung_bot_fn=g.dung_bot,
            tinh_dd_fn=lambda _a: (_ for _ in ()).throw(AssertionError("KHÔNG được gọi khi account lỗi")),
            tam_ngung_fn=g.tam_ngung, ghi_abort_fn=g.ghi_abort, luu_truoc_fn=g.luu,
        )
        assert (tt.muc_tang_chan, dung, g.goi) == (HALT, False, ["stopentry"])


class TestMainGiuCoDoKhiStopLoi:
    def test_nhanh_except_luu_ban_MOI_NHAT_khong_ghi_de_co_do(self) -> None:
        """Nhánh `except FreqtradeControlError` của `main()` phải lưu `da_luu[0]` (bản `luu_truoc_fn` vừa ghi), không
        `trang_thai` đầu vòng — ghi đè sẽ xoá cờ ABORT vừa đặt trước khi /stop thất bại."""
        cay = ast.parse((REPO_ROOT / "src/tool_d/ops/risk_supervisor_daemon.py").read_text(encoding="utf-8"))
        main = next(n for n in cay.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        nhanh = [
            h for n in ast.walk(main) if isinstance(n, ast.Try) for h in n.handlers
            if isinstance(h.type, ast.Name) and h.type.id == "FreqtradeControlError"
        ]
        assert len(nhanh) == 1
        goi_luu = [
            n for n in ast.walk(nhanh[0]) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "luu_trang_thai"
        ]
        assert goi_luu and all(ast.unparse(c.args[0]) == "da_luu[0]" for c in goi_luu)

    def test_main_noi_du_bon_khoa_tang_chan(self) -> None:
        """Bốn khoá mặc định `None` (giữ test cũ của TD-0241 nguyên vẹn) ⇒ phải có máy canh `main()` luôn truyền —
        quên một khoá là tầng chặn tắt im lặng."""
        cay = ast.parse((REPO_ROOT / "src/tool_d/ops/risk_supervisor_daemon.py").read_text(encoding="utf-8"))
        main = next(n for n in cay.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        goi = [
            n for n in ast.walk(main)
            if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "chay_mot_vong_giam_sat"
        ]
        assert len(goi) == 1
        assert {"tinh_dd_fn", "tam_ngung_fn", "ghi_abort_fn", "luu_truoc_fn", "doc_so_lenh_dong_fn"} <= {
            k.arg for k in goi[0].keywords
        }


class TestDdTuAccount:
    def test_dinh_len_roi_sut(self, tmp_path) -> None:
        dinh = duong_dan_dinh_supervisor(tmp_path / "state.json")
        assert dd_tu_account({"totalMarginBalance": "1000"}, duong_dan_dinh=dinh) == 0.0
        assert dd_tu_account({"totalMarginBalance": "1100"}, duong_dan_dinh=dinh) == 0.0
        assert dd_tu_account({"totalMarginBalance": "990"}, duong_dan_dinh=dinh) == pytest.approx(10.0)

    def test_rut_von_co_ghi_so_thi_KHONG_thanh_sut(self, tmp_path) -> None:
        dinh = duong_dan_dinh_supervisor(tmp_path / "state.json")
        dd_tu_account({"totalMarginBalance": "1100"}, duong_dan_dinh=dinh)
        ghi_su_kien(duong_dan_so_su_kien(dinh), SuKienDinh(
            loai=NAP_RUT, stake_currency="USDT", luc_utc="2026-09-26T00:00:00Z", ghi_chu="rút", so_tien=-100.0))
        assert dd_tu_account({"totalMarginBalance": "1000"}, duong_dan_dinh=dinh) == pytest.approx(0.0)

    @pytest.mark.parametrize("account", [{}, {"totalMarginBalance": "abc"}, {"totalMarginBalance": "0"}, None])
    def test_khong_doc_duoc_thi_None_khong_bia(self, tmp_path, account) -> None:
        assert dd_tu_account(account, duong_dan_dinh=duong_dan_dinh_supervisor(tmp_path / "s.json")) is None

    def test_ghi_su_kien_abort_dat_lai_dinh_o_lan_doc_ke_tiep(self, tmp_path) -> None:
        dinh = duong_dan_dinh_supervisor(tmp_path / "state.json")
        dd_tu_account({"totalMarginBalance": "1000"}, duong_dan_dinh=dinh)
        assert dd_tu_account({"totalMarginBalance": "700"}, duong_dan_dinh=dinh) == pytest.approx(30.0)
        ghi_su_kien_abort(dinh, now=T0)
        assert [sk.loai for _, sk in doc_so_su_kien(duong_dan_so_su_kien(dinh))] == [ABORT]
        assert dd_tu_account({"totalMarginBalance": "700"}, duong_dan_dinh=dinh) == 0.0


def _resp(payload: dict) -> MagicMock:
    r = MagicMock()
    r.read.return_value = json.dumps(payload).encode("utf-8")
    r.__enter__.return_value = r
    return r


class TestTamNgungMoLenh:
    def test_goi_dung_duong_va_method(self) -> None:
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as m:
            m.return_value = _resp({"status": "paused, no more entries will occur from now. Run /start to enable entries."})
            tam_ngung_mo_lenh("http://127.0.0.1:8081", username="u", password="p")
        req = m.call_args[0][0]
        assert req.full_url == "http://127.0.0.1:8081/api/v1/stopentry" and req.get_method() == "POST"

    def test_bot_dang_STOPPED_bi_bat_lai_thi_RAISE(self) -> None:
        """4.4d luật 1 / 4.3: chuỗi `rpc.py:1000-1004` = vừa BẬT LẠI bot đã dừng hẳn."""
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as m:
            m.return_value = _resp({"status": "starting bot with trader in paused state, no entries will occur. "
                                              "Run /start to enable entries."})
            with pytest.raises(FreqtradeBatLaiBotError):
                tam_ngung_mo_lenh("http://127.0.0.1:8081", username="u", password="p")


# ═══ TD-0434 chặng 2 — trần "3 HALT / chu kỳ 100 lệnh đóng" (§12c.5 spec:4756, DR-TANG-CHAN-01 §8 (a)) ═══


class TestTranHaltThuan:
    def test_hang_so_khop_spec(self) -> None:
        assert (HANG_SO_KHAI_LAI.tran_halt_so_lan, HANG_SO_KHAI_LAI.chu_ky_lenh_dong) == (3, 100)

    def test_ba_lan_HALT_cung_chu_ky_van_HALT_lan_bon_ABORT(self) -> None:
        moc: tuple = ()
        for so_lenh in (10, 40, 70):
            muc, moc = ap_tran_halt(BINH_THUONG, HALT, moc_halt=moc, so_lenh_dong=so_lenh)
            assert muc == HALT
        muc, moc = ap_tran_halt(BINH_THUONG, HALT, moc_halt=moc, so_lenh_dong=99)
        assert muc == ABORT and moc == (10, 40, 70, 99)

    def test_chu_ky_la_KHOI_CO_DINH_khong_truot(self) -> None:
        """§12c.1: lệnh 99 thuộc chu kỳ 0, lệnh 100 thuộc chu kỳ 1 — ba HALT cũ ở chu kỳ 0 không tính sang chu kỳ 1."""
        muc, moc = ap_tran_halt(BINH_THUONG, HALT, moc_halt=(10, 40, 99), so_lenh_dong=100)
        assert muc == HALT and moc == (10, 40, 99, 100)

    def test_goi_lai_HALT_moi_vong_KHONG_phai_lan_HALT_moi(self) -> None:
        assert ap_tran_halt(HALT, HALT, moc_halt=(1, 2, 3), so_lenh_dong=4) == (HALT, (1, 2, 3))

    def test_khong_phai_HALT_thi_khong_dem(self) -> None:
        assert ap_tran_halt(BINH_THUONG, BINH_THUONG, moc_halt=(1,), so_lenh_dong=5) == (BINH_THUONG, (1,))
        assert ap_tran_halt(BINH_THUONG, ABORT, moc_halt=(1,), so_lenh_dong=5) == (ABORT, (1,))

    def test_khong_doc_duoc_so_lenh_thi_tinh_vao_MOI_chu_ky_phia_an_toan(self) -> None:
        muc, moc = ap_tran_halt(BINH_THUONG, HALT, moc_halt=(5, 250, 480), so_lenh_dong=None)
        assert muc == ABORT and moc == (5, 250, 480, None), "không biết chu kỳ ⇒ đếm mọi lần, ABORT sớm hơn không muộn hơn"
        muc, _ = ap_tran_halt(BINH_THUONG, HALT, moc_halt=(None, None), so_lenh_dong=150)
        assert muc == HALT
        muc, _ = ap_tran_halt(BINH_THUONG, HALT, moc_halt=(None, None, 120), so_lenh_dong=150)
        assert muc == ABORT, "mốc None cũ tính vào cả chu kỳ hiện tại"

    @pytest.mark.parametrize("so_lenh", [-1, 1.5, True, "10"])
    def test_so_lenh_rac_thi_raise(self, so_lenh) -> None:
        with pytest.raises(RiskSupervisorError):
            ap_tran_halt(BINH_THUONG, HALT, moc_halt=(), so_lenh_dong=so_lenh)


class TestTranHaltBenVung:
    def test_ghi_doc_lai_moc_halt_gom_None(self, tmp_path) -> None:
        p = tmp_path / "state.json"
        luu_trang_thai(_tt(HALT, moc_halt=(12, None, 40)), p)
        assert doc_trang_thai(p).moc_halt == (12, None, 40)

    def test_file_TRUOC_chang_2_doc_duoc_moc_rong(self, tmp_path) -> None:
        p = tmp_path / "state.json"
        luu_trang_thai(_tt(), p)
        tho = json.loads(p.read_text(encoding="utf-8"))
        del tho["moc_halt"]
        p.write_text(json.dumps(tho), encoding="utf-8")
        assert doc_trang_thai(p).moc_halt == ()

    @pytest.mark.parametrize("moc", [[-1], [1.5], ["3"], {"a": 1}])
    def test_moc_sai_kieu_thi_raise(self, tmp_path, moc) -> None:
        p = tmp_path / "state.json"
        luu_trang_thai(_tt(), p)
        tho = json.loads(p.read_text(encoding="utf-8"))
        tho["moc_halt"] = moc
        p.write_text(json.dumps(tho), encoding="utf-8")
        with pytest.raises(RiskSupervisorError):
            doc_trang_thai(p)


class TestTranHaltTrongVong:
    def test_moc_halt_SONG_qua_nhieu_vong(self) -> None:
        g = _Ghi()
        tt, _ = _vong(_tt(), g, dd=9.0, so_lenh=42)
        assert tt.moc_halt == (42,)
        tt, _ = _vong(tt, g, dd=9.0, so_lenh=43)
        tt, _ = _vong(tt, g, dd=None)
        assert tt.moc_halt == (42,) and tt.muc_tang_chan == HALT

    def test_thanh_ly_giua_luc_HALT_thi_ho_so_giu_muc_va_moc_halt(self) -> None:
        """Hồi quy (phá thật chặng 2): trước đây nhánh thanh lý dựng lại trạng thái từ HAI trường ⇒ hồ sơ ghi xuống mất
        `muc_tang_chan`/`moc_halt`. Cờ đỏ vẫn bật nên không nguy hiểm, nhưng hồ sơ sai."""
        g = _Ghi()
        tt, dung = _vong(_tt(HALT, moc_halt=(42,)), g, dd=12.0, force_orders=[{"time": 5000}])
        assert dung is True and tt.la_thanh_ly and tt.co_do
        assert (tt.muc_tang_chan, tt.moc_halt) == (HALT, (42,))

    def test_lan_HALT_thu_4_trong_chu_ky_thi_ABORT_dung_thu_tu_khong_stopentry(self) -> None:
        g = _Ghi()
        tt, dung = _vong(_tt(moc_halt=(110, 130, 150)), g, dd=9.0, so_lenh=170)
        assert tt.muc_tang_chan == ABORT and dung is True and tt.moc_halt == (110, 130, 150, 170)
        assert g.goi == [f"luu:{ABORT}:False", "stop", "su_kien_abort"]

    def test_doc_so_lenh_loi_thi_moc_None(self) -> None:
        g = _Ghi()

        def loi():
            raise FreqtradeControlError("mô phỏng: /profit lỗi")

        tt, dung = chay_mot_vong_giam_sat(
            _tt(), now=T0, doc_account_fn=lambda: {}, doc_position_fn=lambda: [],
            doc_force_orders_fn=lambda: [], doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(),
            tu_thoi_diem_ms=1000, dung_bot_fn=g.dung_bot, tinh_dd_fn=lambda _a: 9.0,
            tam_ngung_fn=g.tam_ngung, ghi_abort_fn=g.ghi_abort, luu_truoc_fn=g.luu, doc_so_lenh_dong_fn=loi,
        )
        assert (tt.muc_tang_chan, tt.moc_halt, dung, g.goi) == (HALT, (None,), False, ["stopentry"])


class TestDocSoLenhDong:
    def test_goi_GET_profit_tra_so_nguyen(self) -> None:
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as m:
            m.return_value = _resp({"closed_trade_count": 57, "trade_count": 60})
            assert doc_so_lenh_dong("http://127.0.0.1:8081", username="u", password="p") == 57
        req = m.call_args[0][0]
        assert req.full_url == "http://127.0.0.1:8081/api/v1/profit" and req.get_method() == "GET"

    @pytest.mark.parametrize("payload", [{}, {"closed_trade_count": None}, {"closed_trade_count": -1},
                                         {"closed_trade_count": 1.0}])
    def test_truong_thieu_hoac_rac_thi_RAISE_khong_tra_0(self, payload) -> None:
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as m:
            m.return_value = _resp(payload)
            with pytest.raises(FreqtradeControlError, match="closed_trade_count"):
                doc_so_lenh_dong("http://127.0.0.1:8081", username="u", password="p")
