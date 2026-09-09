"""🔒 TD-0193 / DR-D4-08 — §3.3b (xác nhận entry) phải ĐƯỢC GỌI trên đường
chiến lược THẬT, đúng chiều thời gian, và phản thực B không được chạm tập lệnh.

Bài học TD-0188/TD-0192 áp nguyên văn: `entry_confirmation.py` có test khoá
riêng (L-Z6, TD-0193 chặng 1) và vẫn KHÔNG được gọi trên đường sản xuất suốt
hai ngày (MT-21, `Z0 ≡ Z0-V1` 83/83 lệnh). File này canh ĐƯỜNG DÂY NỐI.

════ Bốn lớp ════

(1) **Backtest THẬT** (fixture `kq_san_xuat` của TD-0187): mọi lệnh mang
    `ec`/`wb`/`lc` trong `enter_tag` (L-Z6: *"mọi tranche 1 đã khớp đều có
    entry_confirmation không rỗng"*), và dấu vết `XAC_NHAN_3_3B` có trong log.
(2) **Z0 ≠ Z0-V1 trên cùng dữ liệu** — gọi đúng `_xac_nhan_3_3b` của chiến
    lược với công tắc (c) bật/tắt, trên một chuỗi 1H mà nến xác nhận có
    volume YẾU: Z0 bỏ lượt, Z0-V1 vào. Không dựng lại phép tính.
(3) **Đối chứng ÂM lookahead** (khuôn TD-0170, mặt cắt `populate`): cắt cả
    hai khung tại C−1 ⇒ KHÔNG tín hiệu; cắt tại C ⇒ CÓ, và tag GIỐNG HỆT bản
    đầy đủ. Kèm phép phá cô lập: bản chép của chiến lược bắt đầu quét từ giờ
    MỞ của nến 4H j (lỗi của script MT-22) phải làm ca cắt-tại-C−1 ĐỎ.
(4) **Phản thực B chỉ ghi**: (a) AST — hai cột phản thực chỉ xuất hiện trong
    `_xac_nhan_3_3b`/`_ghi_cot_3_3b`; (b) hành vi — xoá sạch hai cột đó rồi
    chạy `populate_entry_trend` ⇒ `enter_long` không đổi một hàng.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import talib

REPO_ROOT = Path(__file__).resolve().parents[2]
NGUON_CHIEN_LUOC = REPO_ROOT / "user_data/strategies/ZoneAbsorption.py"

_spec = importlib.util.spec_from_file_location(
    "td0187", REPO_ROOT / "tests" / "lock" / "test_td0187_dinh_co_lenh_backtest_that.py"
)
_td0187 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_td0187)  # type: ignore[union-attr]
_chay, _lenh_vao, _lenh_du_ba_tranche = _td0187._chay, _td0187._lenh_vao, _td0187._lenh_du_ba_tranche
SAN_XUAT, CAP = _td0187.SAN_XUAT, _td0187.CAP
PAIR = CAP.replace("_USDT_USDT", "/USDT:USDT")


def _import_chien_luoc():
    if str(REPO_ROOT / "user_data/strategies") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "user_data/strategies"))
    spec = importlib.util.spec_from_file_location("ZoneAbsorption", NGUON_CHIEN_LUOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)  # type: ignore[union-attr]
    return m


def _chien_luoc(mod=None):
    mod = mod or _import_chien_luoc()
    return mod.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})


# ── dữ liệu: đúng bộ sinh của TD-0187, dựng thành hai khung như backtest nạp ──

@pytest.fixture(scope="module")
def khung() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows4 = _td0187._bars_4h_co_trend()
    rows1 = _td0187._rows1_tu_rows4(rows4)
    bat_dau = _td0187._moc_bat_dau(len(rows1))
    df1 = pd.DataFrame(rows1, columns=["open", "high", "low", "close", "volume"])
    df1.insert(0, "date", pd.date_range(bat_dau, periods=len(rows1), freq="1h", tz="UTC"))
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    df4 = df1.set_index("date").resample("4h").agg(agg).reset_index()
    return df1, df4


def _chi_bao_1h(df1: pd.DataFrame) -> pd.DataFrame:
    """Đúng ba cột 1H mà `populate_indicators` tính trước khi gọi `_xac_nhan_3_3b`."""
    d = df1.copy()
    d["atr_1h"] = talib.ATR(d["high"], d["low"], d["close"], timeperiod=14)
    d["rsi_1h"] = talib.RSI(d["close"], timeperiod=14)
    d["volume_ma_1h"] = d["volume"].rolling(20).mean()
    return d


def _xac_nhan(s, df1: pd.DataFrame, df4: pd.DataFrame) -> pd.DataFrame:
    d = _chi_bao_1h(df1)
    inf4 = s._tinh_zone_4h(df4.copy())
    s._xac_nhan_3_3b(d, inf4, PAIR)
    return d


@pytest.fixture(scope="module")
def tmp_module(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("td0193")


@pytest.fixture(scope="module")
def kq_san_xuat(tmp_module) -> dict:
    return _chay(tmp_module, SAN_XUAT)


# ═══════════════════════════════════════════════════════════════════════
class TestTrenBacktestThat:
    def test_moi_lenh_mang_entry_confirmation_khong_rong(self, kq_san_xuat) -> None:
        """L-Z6 — trên lệnh THẬT, không phải trên hàm."""
        assert kq_san_xuat["trades"], "0 lệnh — bộ sinh không cho tín hiệu nào (xem NEN_1H_CHAM_P1)"
        for t in kq_san_xuat["trades"]:
            d = json.loads(t["enter_tag"])
            assert d["ec"] in ("ac", "b"), d
            assert isinstance(d["wb"], int) and 0 <= d["wb"] <= 2, d
            assert isinstance(d["lc"], int) and d["lc"] >= 0, d
            assert len(t["enter_tag"]) <= 255, "order tag Binance giới hạn 255 ký tự"

    def test_lenh_mau_xac_nhan_qua_a_VA_c_ngay_nen_cham(self, kq_san_xuat) -> None:
        """Bộ sinh cố ý cho C = nến chạm (NEN_1H_CHAM_P1[2]) — nếu ra `b` hay
        `wb > 0` thì đường nối đang đọc nến khác nến thiết kế."""
        d = json.loads(_lenh_du_ba_tranche(kq_san_xuat)["enter_tag"])
        assert d["ec"] == "ac" and d["wb"] == 0, d
        assert d["lc"] == 1, "A xác nhận ở lượt 1 thì B phải trùng A (lc == 1)"

    def test_p1_la_p1_order_cua_3_5(self, kq_san_xuat) -> None:
        """§3.5: p1_order = min(zone_high, close(C)). Với bộ sinh, close(C) = 96,5 >
        zone_high ⇒ p1 == zone_high, và giá khớp thật ≤ p1 (L-Z50)."""
        t = _lenh_du_ba_tranche(kq_san_xuat)
        d = json.loads(t["enter_tag"])
        assert d["p1"] == pytest.approx(d["zh"], rel=1e-9)
        assert float(_lenh_vao(t)[0]["safe_price"]) <= d["p1"] + 1e-6

    def test_dau_vet_XAC_NHAN_3_3B_tren_duong_chay(self, kq_san_xuat) -> None:
        log = kq_san_xuat["_log"]
        assert "XAC_NHAN_3_3B" in log, "không có dấu vết — hàm tồn tại nhưng không được gọi (TD-0168)"


# ═══════════════════════════════════════════════════════════════════════
class TestZ0KhacZ0V1TrenChienLuocThat:
    def test_volume_yeu_Z0_bo_luot_Z0_V1_vao(self, khung) -> None:
        df1, df4 = khung
        rows4 = _td0187._bars_4h_co_trend()
        k = _td0187._i_cham_p1(rows4) * 4 + 2  # nến C của bộ sinh (NEN_1H_CHAM_P1[2])
        yeu = df1.copy()
        yeu.loc[k, "volume"] = 100.0  # < MA20 ≈ 240 ⇒ (c) loại, (a) vẫn đúng
        s0 = _chien_luoc(); s0._arm, s0._bat_dieu_kien_c = "Z0", True
        s1 = _chien_luoc(); s1._arm, s1._bat_dieu_kien_c = "Z0-V1", False
        d0, d1 = _xac_nhan(s0, yeu, df4), _xac_nhan(s1, yeu, df4)
        assert not d0["xac_nhan_3_3b"].iloc[k], "Z0 phải BỎ LƯỢT tại nến này khi volume yếu"
        assert d1["xac_nhan_3_3b"].iloc[k], "Z0-V1 (tắt (c)) phải xác nhận qua (a)"
        # Tiêu chí thật (TASKS.md TD-0193 (1)): TẬP TÍN HIỆU khác nhau — Z0 có
        # thể vẫn vào ở một nến khác trong cửa sổ (vd qua (b)), nhưng không
        # được TRÙNG KHỚP với Z0-V1 như 83/83 lệnh của MT-21.
        tap0 = set(np.flatnonzero(d0["xac_nhan_3_3b"].to_numpy()).tolist())
        tap1 = set(np.flatnonzero(d1["xac_nhan_3_3b"].to_numpy()).tolist())
        assert tap0 != tap1, f"Z0 và Z0-V1 cho CÙNG tập tín hiệu {tap0} — công tắc (c) chưa nối (MT-21)"
        assert json.loads(d1["ke_hoach_json_3_3b"].iloc[k])["ec"] == "ac"

    def test_C_khong_som_hon_luc_nen_4h_j_dong(self, khung) -> None:
        """DR-D4-08 §3 #3 — mọi C phải ≥ nến 1H đầu tiên SAU khi nến 4H xác
        nhận zone ĐÓNG. Bộ sinh không có lần chạm nào bên trong nến j, nên
        ca này canh bằng THỜI GIAN chứ không bằng số tín hiệu."""
        df1, df4 = khung
        s = _chien_luoc()
        inf4 = s._tinh_zone_4h(df4.copy())
        d = _xac_nhan(s, df1, df4)
        dong_cua_j = {inf4["date"].iloc[j] + pd.Timedelta(hours=4) for j in np.flatnonzero(inf4["zone_valid"].to_numpy())}
        assert dong_cua_j
        for c in np.flatnonzero(d["xac_nhan_3_3b"].to_numpy()):
            assert any(d["date"].iloc[c] >= m for m in dong_cua_j), (d["date"].iloc[c], dong_cua_j)

    def test_AST_moc_quet_la_gio_DONG_nen_4h_j(self) -> None:
        """Script đo MT-22 bắt đầu từ giờ MỞ của j (`ts_j`) — sản xuất phải dùng
        mốc ĐÓNG (`dong_cua4`). Canh bằng chuỗi nguồn vì fixture không phân biệt được."""
        src = NGUON_CHIEN_LUOC.read_text(encoding="utf-8")
        assert "k_start = int(np.searchsorted(ngay1, dong_cua4[j]))" in src
        assert "searchsorted(ngay1, ngay4[j])" not in src

    def test_cong_tac_doc_tu_arm_qua_bang_cua_entry_confirmation(self) -> None:
        from tool_d.entry_confirmation import bat_dieu_kien_c_cua_arm

        s = _chien_luoc()
        assert s._bat_dieu_kien_c is bat_dieu_kien_c_cua_arm(s._arm)


# ═══════════════════════════════════════════════════════════════════════
class TestDoiChungAmLookahead:
    """Tín hiệu tại C chỉ được phụ thuộc dữ liệu ≤ C — trên CẢ HAI khung."""

    @staticmethod
    def _cat(df1, df4, k: int):
        """Đúng thứ live nhìn thấy khi nến 1H k vừa ĐÓNG: 1H ≤ k, 4H đã đóng ≤ close(k)."""
        moc = df1["date"].iloc[k] + pd.Timedelta(hours=1)
        return df1.iloc[: k + 1].reset_index(drop=True), df4[df4["date"] + pd.Timedelta(hours=4) <= moc].reset_index(drop=True)

    def test_cat_tai_C_tru_1_khong_tin_hieu_cat_tai_C_co(self, khung) -> None:
        df1, df4 = khung
        s = _chien_luoc()
        day_du = _xac_nhan(s, df1, df4)
        cac_c = np.flatnonzero(day_du["xac_nhan_3_3b"].to_numpy())
        assert len(cac_c) >= 1, "bản đầy đủ không có C nào — đối chứng thường trực lẽ ra đã bắt"
        c = int(cac_c[0])

        d1, d4 = self._cat(df1, df4, c - 1)
        truoc = _xac_nhan(_chien_luoc(), d1, d4)
        assert not truoc["xac_nhan_3_3b"].any(), "cắt tại C−1 mà vẫn có tín hiệu ⇒ đọc nến tương lai"

        d1, d4 = self._cat(df1, df4, c)
        tai = _xac_nhan(_chien_luoc(), d1, d4)
        assert tai["xac_nhan_3_3b"].iloc[c], "cắt tại C mà mất tín hiệu ⇒ tín hiệu phụ thuộc dữ liệu SAU C"
        assert tai["ke_hoach_json_3_3b"].iloc[c] == day_du["ke_hoach_json_3_3b"].iloc[c], "tag tại C đổi theo dữ liệu tương lai"

    def test_pha_that_ghi_tin_hieu_som_mot_nen_phai_do(self, khung, tmp_path) -> None:
        """Bản chép chiến lược ghi tín hiệu tại C−1 (dạng tối giản của lookahead:
        tín hiệu đứng TRƯỚC dữ liệu biện minh cho nó) — cắt tại C của bản hỏng
        thì tín hiệu BIẾN MẤT ⇒ lớp canh có răng. KHÔNG sửa file sản xuất.
        📌 Phép phá "quét từ giờ MỞ nến j" (lỗi script MT-22) KHÔNG cắn trên bộ
        sinh này (không có lần chạm nào bên trong j) — canh riêng bằng AST."""
        src = NGUON_CHIEN_LUOC.read_text(encoding="utf-8")
        goc = "xac_nhan[c] = True"
        assert src.count(goc) == 1, "dòng ghi tín hiệu đã đổi — cập nhật phép phá"
        hong = src.replace(goc, "xac_nhan[c - 1] = True")
        p = tmp_path / "ZoneAbsorptionHong.py"
        p.write_text(hong.replace("class ZoneAbsorption(", "class ZoneAbsorptionHong(").replace(
            "ZoneAbsorption(IStrategy)", "ZoneAbsorptionHong(IStrategy)"), encoding="utf-8")
        spec = importlib.util.spec_from_file_location("ZoneAbsorptionHong", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)  # type: ignore[union-attr]
        s = m.ZoneAbsorptionHong(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})

        df1, df4 = khung
        day_du = _xac_nhan(s, df1, df4)
        cac_c = np.flatnonzero(day_du["xac_nhan_3_3b"].to_numpy())
        assert len(cac_c) >= 1
        c_hong = int(cac_c[0])
        # bản hỏng thấy C SỚM hơn bản đúng (đọc nến bên trong j) — và tại mốc
        # đó zone CHƯA xác nhận nên khung 4H cắt đúng KHÔNG có zone ⇒ mất tín hiệu.
        c_dung = int(np.flatnonzero(_xac_nhan(_chien_luoc(), df1, df4)["xac_nhan_3_3b"].to_numpy())[0])
        assert c_hong < c_dung, (c_hong, c_dung)
        d1, d4 = self._cat(df1, df4, c_hong)
        assert not _xac_nhan(m.ZoneAbsorptionHong(config={"stake_currency": "USDT", "exchange": {"name": "binance"}}), d1, d4)["xac_nhan_3_3b"].any(), (
            "bản hỏng vẫn có tín hiệu khi cắt tại C của nó ⇒ phép phá không phá được gì, "
            "đối chứng âm không có răng"
        )


# ═══════════════════════════════════════════════════════════════════════
class TestPhanThucBChiGhi:
    COT = ("xac_nhan_phan_thuc_b", "lan_cham_phan_thuc")

    def test_AST_hai_cot_phan_thuc_khong_duoc_doc_ngoai_ham_ghi(self) -> None:
        cay = ast.parse(NGUON_CHIEN_LUOC.read_text(encoding="utf-8"))
        cls = next(n for n in cay.body if isinstance(n, ast.ClassDef) and n.name == "ZoneAbsorption")
        cho_phep = {"_xac_nhan_3_3b", "_ghi_cot_3_3b"}
        for fn in (n for n in cls.body if isinstance(n, ast.FunctionDef)):
            if fn.name in cho_phep:
                continue
            chuoi = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
            assert not (chuoi & set(self.COT)), f"{fn.name} đọc cột phản thực {chuoi & set(self.COT)} — B phải CHỈ ghi"

    def test_xoa_hai_cot_phan_thuc_tap_lenh_khong_doi(self, khung) -> None:
        df1, df4 = khung
        s = _chien_luoc()
        d = _xac_nhan(s, df1, df4)
        # `populate_entry_trend` cần các cột `_4h`/`_1d` — ghép như populate_indicators.
        from freqtrade.strategy import merge_informative_pair

        inf4 = s._tinh_zone_4h(df4.copy())
        d = merge_informative_pair(d, inf4, "1h", "4h", ffill=True)
        df1d = df1.set_index("date").resample("1D").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).reset_index()
        inf1d = s._tinh_trend_1d(df1d)
        d = merge_informative_pair(d, inf1d[["date", "adx", "trend_dir_1d", "tuoi_trend_1d"]], "1h", "1d", ffill=True)

        co = s.populate_entry_trend(d.copy(), {"pair": PAIR})
        tat = d.copy()
        for c in self.COT:
            tat[c] = False if c == "xac_nhan_phan_thuc_b" else 0
        khong = s.populate_entry_trend(tat, {"pair": PAIR})
        assert "enter_long" in co.columns and co["enter_long"].fillna(0).sum() >= 1, "không có tín hiệu nào để so"
        pd.testing.assert_series_equal(co["enter_long"].fillna(0), khong["enter_long"].fillna(0), check_names=False)


# ═══════════════════════════════════════════════════════════════════════
class TestAST_TinHieuChiDiQuaMotCua:
    def test_populate_entry_trend_khong_con_doc_zone_valid(self) -> None:
        """Bản trước đặt `enter_long` theo `zone_valid_4h` (khối 4 nến sau j).
        Còn đọc nó là còn một đường vào lệnh KHÔNG qua §3.3b."""
        cay = ast.parse(NGUON_CHIEN_LUOC.read_text(encoding="utf-8"))
        cls = next(n for n in cay.body if isinstance(n, ast.ClassDef) and n.name == "ZoneAbsorption")
        fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "populate_entry_trend")
        chuoi = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        assert not any("zone_valid" in c for c in chuoi), chuoi
        assert "xac_nhan_3_3b" in chuoi and "ke_hoach_json_3_3b" in chuoi

    def test_quet_xac_nhan_zone_DUOC_GOI_trong_populate_indicators_path(self) -> None:
        cay = ast.parse(NGUON_CHIEN_LUOC.read_text(encoding="utf-8"))
        goi = {n.func.id for n in ast.walk(cay) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "quet_xac_nhan_zone" in goi
        assert "tim_xac_nhan_entry" not in goi, "chiến lược phải đi qua vòng quét cả vòng đời zone, không gọi lẻ"


class TestDoiChungThuongTrucCoRang:
    def test_bo_nen_xac_nhan_thi_bo_sinh_RAISE(self) -> None:
        rows4 = _td0187._bars_4h_co_trend()
        rows1_cu = [x for bar in rows4 for x in _td0187._chia_nho(bar, 4)]  # bản chia cũ: không rejection
        with pytest.raises(AssertionError, match="XANH-VÔ-NGHĨA"):
            _td0187._khang_dinh_bo_sinh_co_nen_xac_nhan_3_3b(rows4, rows1_cu)
        _td0187._khang_dinh_bo_sinh_co_nen_xac_nhan_3_3b(rows4, _td0187._rows1_tu_rows4(rows4))
