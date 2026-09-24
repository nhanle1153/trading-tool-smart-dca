"""TD-0400 — chiến lược rổ funding chéo `RoFunding` của ứng viên `IQ-0003` (`DR-D0-IQ0003`).

Ba tầng kiểm:
  1. Tầng THUẦN `tool_d.ro_funding` — chỉ số tổng funding 72h (mã chốt 4h và 8h so được), điều kiện đủ lịch sử, chia
     nhóm tất định, không nhìn trước (dòng `date > t` không đổi kết quả).
  2. Danh sách khoá (`DR-BIEN-THE-01` §3): mọi `resolve("tier_*…")` trong chiến lược TRÙNG KHÍT khối
     `DR-BIEN-THE-01:KHOA` của `DR-D0-IQ0003` — đọc khoá không khai là mở lại lối tinh chỉnh ngầm.
  3. Backtest THẬT (Freqtrade trong Docker) trên dữ liệu TỔNG HỢP 8 mã, dựng qua đúng `dung_moi_truong()` của bộ chạy
     (kể cả file phủ lệnh thị trường): nhãn thoát chỉ thuộc lớp `CAN_RO_THEO_LICH`, rổ trung tính (mỗi lần cân rổ số
     lệnh Long mở = số lệnh Short mở), đòn bẩy sàn 2 / phơi nhiễm 1, vào lệnh đúng 00:00 UTC, đổi nhóm thì đảo chiều trong cùng nến, stop
     thảm hoạ nổ đúng mã có cú giật giá, không exception nào bị Freqtrade nuốt.

⚠️ Phạm vi bằng chứng: dữ liệu TỔNG HỢP — chứng minh máy nối đúng luật đã đăng ký, KHÔNG nói gì về lợi thế.
"""

from __future__ import annotations

import ast
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from tool_d.ledger.bien_the import doc_khoa_bien_the
from tool_d.ro_funding import (
    RoFundingError,
    chi_so_funding,
    chia_nhom,
    la_moc_can_ro,
    nhom_tai,
    notional_moi_vi_the,
    so_k,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CHIEN_LUOC = REPO_ROOT / "user_data" / "strategies" / "RoFunding.py"
UTC = timezone.utc
T = datetime(2025, 1, 10, 0, 0, tzinfo=UTC)


def _funding(bat_dau: datetime, buoc_gio: int, gia_tri: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.date_range(bat_dau, periods=len(gia_tri), freq=f"{buoc_gio}h", tz="UTC"),
        "funding_rate": gia_tri,
    })


class TestChiSo:
    def test_tong_trong_72h_ma_8h_va_4h_so_duoc(self) -> None:
        """Cùng mức trả 0,0003/ngày: mã 8h chốt 0,0001 × 3 kỳ/ngày, mã 4h chốt 0,00005 × 6 kỳ/ngày ⇒ cùng chỉ số."""
        # 5 ngày tới ĐÚNG `t`: 8h ⇒ 16 kỳ, 4h ⇒ 31 kỳ (kỳ chốt tại `t` thuộc cửa sổ).
        ma_8h = _funding(T - timedelta(days=5), 8, [0.0001] * 16)
        ma_4h = _funding(T - timedelta(days=5), 4, [0.00005] * 31)
        a = chi_so_funding(ma_8h, T, cua_so_gio=72)
        b = chi_so_funding(ma_4h, T, cua_so_gio=72)
        assert a == pytest.approx(0.0009) and b == pytest.approx(0.0009)

    def test_cua_so_nua_mo_trai_dong_phai(self) -> None:
        """`(t − 72h, t]`: kỳ chốt đúng tại `t` được tính, kỳ đúng tại `t − 72h` thì không."""
        # mốc: t-80 (1), t-72 (10, bị loại — biên trái mở), t-64…t-16 (0), t-8 (100), t (1000, được tính)
        df = _funding(T - timedelta(hours=80), 8, [1.0, 10.0, 0, 0, 0, 0, 0, 0, 0, 100.0, 1000.0])
        assert chi_so_funding(df, T, cua_so_gio=72) == pytest.approx(1100.0)

    def test_chua_du_lich_su_thi_none_khong_phai_0(self) -> None:
        df = _funding(T - timedelta(hours=64), 8, [0.001] * 9)
        assert chi_so_funding(df, T, cua_so_gio=72) is None

    def test_dong_tuong_lai_khong_doi_ket_qua(self) -> None:
        """Chống nhìn trước: nối một kỳ chốt khổng lồ SAU `t` — chỉ số tại `t` đứng yên."""
        df = _funding(T - timedelta(days=4), 8, [0.0001] * 13)
        tuong_lai = pd.concat([df, _funding(T + timedelta(hours=8), 8, [9.9])], ignore_index=True)
        assert chi_so_funding(tuong_lai, T, cua_so_gio=72) == chi_so_funding(df, T, cua_so_gio=72)

    def test_nan_trong_cua_so_thi_tu_choi(self) -> None:
        df = _funding(T - timedelta(days=4), 8, [0.0001] * 12 + [math.nan])
        with pytest.raises(RoFundingError, match="NaN"):
            chi_so_funding(df, T, cua_so_gio=72)


class TestChiaNhom:
    def test_k_theo_cong_thuc(self) -> None:
        assert [so_k(n, ty_le_k=0.2, k_toi_thieu=3) for n in (6, 14, 15, 107, 143)] == [3, 3, 3, 21, 28]

    def test_short_la_cao_nhat_long_la_thap_nhat_hoa_theo_ten(self) -> None:
        chi_so = {"A": 5.0, "B": 5.0, "C": 4.0, "D": 3.0, "E": 1.0, "F": 1.0, "G": 0.0}
        n = chia_nhom(chi_so, T, ty_le_k=0.2, k_toi_thieu=3, so_coin_toi_thieu=6)
        assert n.k == 3 and n.short == {"A", "B", "C"} and n.long == {"E", "F", "G"}

    def test_duoi_so_coin_toi_thieu_thi_khong_nhom_nao(self) -> None:
        n = chia_nhom({m: float(i) for i, m in enumerate("ABCDE")}, T, ty_le_k=0.2, k_toi_thieu=3, so_coin_toi_thieu=6)
        assert n.k == 0 and not n.short and not n.long and n.nhom_cua("A") is None

    def test_hai_chan_chong_nhau_thi_tu_choi(self) -> None:
        with pytest.raises(RoFundingError, match="chồng nhau"):
            chia_nhom({m: float(i) for i, m in enumerate("ABCDE")}, T, ty_le_k=0.2, k_toi_thieu=3, so_coin_toi_thieu=5)

    def test_nhom_tai_loai_btc_eth_va_ma_khong_co_mat(self) -> None:
        ma = ["BTC", "ETH", "A", "B", "C", "D", "E", "F", "G"]
        funding = {m: _funding(T - timedelta(days=4), 8, [0.0001 * (i + 1)] * 13) for i, m in enumerate(ma)}
        n = nhom_tai(funding, set(ma) - {"G"}, T, cua_so_gio=72, ty_le_k=0.2, k_toi_thieu=3, so_coin_toi_thieu=6)
        assert n.so_ma_du_dieu_kien == 6
        assert not ({"BTC", "ETH", "G"} & (n.short | n.long))

    def test_moc_can_ro_va_notional(self) -> None:
        assert la_moc_can_ro(T, gio_utc=0) and not la_moc_can_ro(T + timedelta(minutes=5), gio_utc=0)
        assert notional_moi_vi_the(1200.0, 3) == pytest.approx(200.0)
        with pytest.raises(RoFundingError):
            notional_moi_vi_the(1200.0, 0)


class TestKhoaDayDu:
    def test_khoa_doc_trung_khit_khoa_khai(self) -> None:
        cay = ast.parse(CHIEN_LUOC.read_text(encoding="utf-8"))
        doc = {
            n.args[1].value
            for n in ast.walk(cay)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "resolve"
            and len(n.args) == 2
            and isinstance(n.args[1], ast.Constant)
        }
        tat_ca_resolve = [
            n for n in ast.walk(cay) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "resolve"
        ]
        assert len(tat_ca_resolve) == len(doc), "mọi lời gọi resolve() phải mang khoá HẰNG (đọc được bằng máy)"
        assert doc == set(doc_khoa_bien_the("IQ-0003", repo_dir=REPO_ROOT))

    def test_khong_doc_env_khong_parameter(self) -> None:
        van_ban = CHIEN_LUOC.read_text(encoding="utf-8")
        assert "os.environ" not in van_ban and "getenv" not in van_ban
        assert "Parameter(" not in van_ban


# ── Backtest THẬT trên dữ liệu tổng hợp ────────────────────────────
MA = ["LTC", "XRP", "ADA", "DOGE", "LINK", "DOT", "AVAX", "ATOM"]
BAT_DAU = datetime(2025, 1, 1, tzinfo=UTC)
SO_NGAY = 16
NGAY_DAO = 8  # từ ngày này thứ hạng funding đảo ngược
MA_GIAT = "ATOM"  # funding cao nhất nửa đầu ⇒ chân SHORT; giá giật +35% ngày 5 ⇒ stop thảm hoạ
NGAY_GIAT = 5
VON_TEST = 3000.0
TIMERANGE = "20250101-20250117"


def _gia_1h(i_ma: int) -> pd.DataFrame:
    so_nen = SO_NGAY * 24 + 24
    idx = pd.date_range(BAT_DAU, periods=so_nen, freq="1h", tz="UTC")
    goc = 100.0 + 10 * i_ma
    dong = [goc * (1 + 0.01 * math.sin((j + 7 * i_ma) / 9)) for j in range(so_nen)]
    rows = []
    for j, c in enumerate(dong):
        o = dong[j - 1] if j else c
        h, l = max(o, c) * 1.002, min(o, c) * 0.998
        if MA[i_ma] == MA_GIAT and idx[j] == BAT_DAU + timedelta(days=NGAY_GIAT, hours=10):
            h = o * 1.35
        rows.append((idx[j], o, h, l, c, 1000.0))
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


def _chia_5m(df1: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in df1.itertuples():
        for k in range(12):
            gia = r.open + (r.close - r.open) * k / 12
            h = r.high if k == 6 else max(gia, gia * 1.0005)
            l = r.low if k == 3 else min(gia, gia * 0.9995)
            rows.append((r.date + timedelta(minutes=5 * k), gia, max(h, gia), min(l, gia), gia, r.volume / 12))
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


def _funding_ma(i_ma: int) -> pd.DataFrame:
    so_ky = SO_NGAY * 3 + 3
    idx = pd.date_range(BAT_DAU, periods=so_ky, freq="8h", tz="UTC")
    gia_tri = [
        (i_ma - 3.5) * 1e-4 if d < BAT_DAU + timedelta(days=NGAY_DAO) else (3.5 - i_ma) * 1e-4 for d in idx
    ]
    return pd.DataFrame({"date": idx, "funding_rate": gia_tri})


def _sinh_du_lieu(thu_muc: Path) -> None:
    thu_muc.mkdir(parents=True, exist_ok=True)
    for i, ma in enumerate(MA):
        df1 = _gia_1h(i)
        ten = f"{ma}_USDT_USDT"
        df1.to_feather(thu_muc / f"{ten}-1h-futures.feather")
        df1.to_feather(thu_muc / f"{ten}-1h-mark.feather")
        _chia_5m(df1).to_feather(thu_muc / f"{ten}-5m-futures.feather")
        _funding_ma(i).to_feather(thu_muc / f"{ten}-1h-funding_rate.feather")


@pytest.fixture(scope="module")
def kq(tmp_path_factory) -> dict:
    """Chạy MỘT backtest thật, dựng môi trường bằng đúng `dung_moi_truong()` của bộ chạy E1."""
    from tool_d.bo_chay.moi_truong import dung_moi_truong

    goc = tmp_path_factory.mktemp("td0400")
    _sinh_du_lieu(goc / "data" / "futures")
    # TD-0404 (`DR-LOCKBOX-04` bổ sung 24/09/2026): có vốn rổ thì phải có trần vốn rổ cùng lúc, không thì loader từ chối.
    # Phủ chỉ đổi khoá lá có tên duy nhất, không với tới `tran_d12: {…}` ⇒ điền trần vào một BẢN SAO `config/` rồi dựng từ đó.
    repo_gia = goc / "repo"
    shutil.copytree(REPO_ROOT / "config", repo_gia / "config")
    yaml_gia = repo_gia / "config" / "tool_d_config.yaml"
    van_ban = yaml_gia.read_text(encoding="utf-8")
    assert van_ban.count("von_ro_usdt: null }") == 1, "không tìm thấy đúng một ô trần vốn rổ trong tran_d12"
    yaml_gia.write_text(van_ban.replace("von_ro_usdt: null }", f"von_ro_usdt: {VON_TEST} }}"), encoding="utf-8")
    mt = dung_moi_truong(
        repo_dir=repo_gia, goc=goc, ghi_de={"tier_a.von_ro_usdt": VON_TEST, "tier_a.enable_short": True},
        ma_trong_ro=[f"{m}USDT" for m in MA], chien_luoc="RoFunding",
    )
    proc = subprocess.run(
        [
            sys.executable, "-m", "freqtrade", "backtesting",
            "--config", str(mt.config_freqtrade), "--datadir", str(goc / "data"), "--userdir", str(mt.userdir),
            "--strategy", "RoFunding", "--strategy-path", str(REPO_ROOT / "user_data" / "strategies"),
            "--timerange", TIMERANGE, "--timeframe-detail", "5m", "--cache", "none", "--export", "trades",
        ],
        capture_output=True, text=True, timeout=900, cwd=goc,
    )
    log = proc.stdout + proc.stderr
    assert proc.returncode == 0, f"backtest thất bại:\n{log[-4000:]}"
    nuot = [d for d in log.splitlines() if "Strategy caused the following exception" in d]
    dong = log.splitlines()
    i_dau = next((i for i, d in enumerate(dong) if "Strategy caused the following exception" in d), 0)
    # Log Freqtrade ngắt dòng theo độ rộng màn hình ⇒ in kèm vài dòng sau để thấy trọn thông điệp.
    assert not nuot, f"{len(nuot)} exception bị Freqtrade nuốt — ngữ cảnh:\n" + "\n".join(dong[i_dau : i_dau + 4])
    from freqtrade.data.btanalysis import load_backtest_stats

    files = sorted((mt.userdir / "backtest_results").glob("backtest-result-*.zip"))
    assert files, "không có file kết quả"
    ket_qua = load_backtest_stats(files[-1])["strategy"]["RoFunding"]
    ket_qua["_cfg_ft"] = json.loads(mt.config_freqtrade.read_text(encoding="utf-8"))
    return ket_qua


def _lenh(kq: dict) -> pd.DataFrame:
    df = pd.DataFrame(kq["trades"])
    assert len(df) > 0, "0 lệnh — mọi khẳng định bên dưới sẽ XANH-VÔ-NGHĨA"
    df["open_date"] = pd.to_datetime(df["open_date"], utc=True)
    df["close_date"] = pd.to_datetime(df["close_date"], utc=True)
    return df


class TestBacktestThat:
    def test_file_phu_lenh_thi_truong_da_ap(self, kq) -> None:
        cfg = kq["_cfg_ft"]
        assert cfg["order_types"]["entry"] == "market" and cfg["order_types"]["exit"] == "market"
        assert cfg["trailing_stop"] is False and cfg["position_adjustment_enable"] is True  # L-Z24 không bị phủ

    def test_nhan_thoat_chi_thuoc_lop_can_ro(self, kq) -> None:
        nhan = set(_lenh(kq)["exit_reason"])
        assert nhan <= {"CAN_RO", "stop_loss", "stoploss_on_exchange", "force_exit"}, nhan
        assert "CAN_RO" in nhan

    def test_stop_tham_hoa_no_dung_ma_giat(self, kq) -> None:
        df = _lenh(kq)
        stop = df[df["exit_reason"].isin(["stop_loss", "stoploss_on_exchange"])]
        assert set(stop["pair"]) == {f"{MA_GIAT}/USDT:USDT"}
        assert stop["is_short"].all()

    def test_vao_lenh_dung_gio_can_ro(self, kq) -> None:
        df = _lenh(kq)
        assert (df["open_date"].dt.hour == 0).all() and (df["open_date"].dt.minute == 0).all()

    def test_don_bay_san_2_phoi_nhiem_1(self, kq) -> None:
        """Đòn bẩy sàn 2 (ký quỹ = nửa notional); notional mỗi vị thế vẫn = vốn / 2k (phơi nhiễm 1x)."""
        df = _lenh(kq)
        assert (df["leverage"] == 2).all()
        dau = df[df["open_date"] == df["open_date"].min()]
        # Freqtrade làm tròn khối lượng theo bước của sàn ⇒ notional lệch vài % tuỳ giá; không bao giờ VƯỢT mục tiêu.
        notional = dau["amount"] * dau["open_rate"]
        assert ((notional <= VON_TEST / 6 * 1.001) & (notional >= VON_TEST / 6 * 0.9)).all(), notional.tolist()

    def test_trung_tinh_moi_lan_can_ro(self, kq) -> None:
        """Lần cân rổ đầu tiên (đủ 72h lịch sử) mở đúng k = 3 Long và 3 Short, cùng notional."""
        df = _lenh(kq)
        dau = df[df["open_date"] == df["open_date"].min()]
        assert dau["open_date"].iloc[0] == pd.Timestamp(BAT_DAU + timedelta(days=3))
        assert (~dau["is_short"]).sum() == 3 and dau["is_short"].sum() == 3
        long_n = (dau["amount"] * dau["open_rate"])[~dau["is_short"]].sum()
        short_n = (dau["amount"] * dau["open_rate"])[dau["is_short"]].sum()
        assert long_n == pytest.approx(short_n, rel=0.1), (long_n, short_n)

    def test_doi_nhom_thi_dao_chieu_trong_cung_nen(self, kq) -> None:
        """Thứ hạng đảo ở ngày 8: mã chân Long nửa đầu (LTC, funding thấp nhất) phải có lệnh Short mở ĐÚNG lúc lệnh
        Long của nó đóng bằng `CAN_RO` (DR §3 điều 5)."""
        df = _lenh(kq)
        ltc = df[df["pair"] == "LTC/USDT:USDT"].sort_values("open_date")
        long_dong = ltc[(~ltc["is_short"]) & (ltc["exit_reason"] == "CAN_RO")]["close_date"]
        short_mo = ltc[ltc["is_short"]]["open_date"]
        assert set(long_dong) & set(short_mo), (list(long_dong), list(short_mo))

    def test_co_funding_that(self, kq) -> None:
        assert (_lenh(kq)["funding_fees"].abs() > 0).any()
