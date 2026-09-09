"""🔴 TD-0189 chặng 2b — chốt lời PHẦN 5 §5.1 NỐI vào `ZoneAbsorption.py`,
đo trên backtest THẬT (không dựng tay — bài học TD-0168/TD-0188).

Ba điều `tests/unit/test_take_profit.py` (chặng 1, hàm THUẦN) KHÔNG chứng
minh được, vì nó không chạy qua Freqtrade:

1. **TP1 thật sự CHỐT 50% qua `adjust_trade_position`** (cơ chế
   `stake_amount` ÂM ⇒ `ExitType.PARTIAL_EXIT`, đọc mã nguồn
   `backtesting.py`/`freqtradebot.py` trước khi viết — N7/rule 6), không
   phải một hàm tồn tại mà đường sản xuất không gọi (bài học TD-0168).
2. **TP2 thật sự đóng NỐT phần còn lại** qua `custom_exit` (trả STRING).
3. **Chốt của chủ dự án (09/09/2026): đã chốt TP1 thì KHÔNG DCA thêm
   nữa** — dù giá sau đó có tụt về đúng mức `p2`/`p3` kế hoạch, tranche
   2/3 KHÔNG được bơm. Bắt được ca này lần đầu khi ĐO (không phải khi
   đoán): dữ liệu `test_td0187` vốn có một nến "vọt lên rồi rơi" ngay
   sau khi tranche 1 khớp, và bản đầu của chặng 2b cho tranche 2/3 khớp
   bình thường SAU KHI TP1 đã chốt — tín hiệu để hỏi chủ dự án, không
   phải một giả định tự chọn.

`TestTP1TP2TrenFixtureChung` dùng LẠI fixture `kq_san_xuat` của
`test_td0187` (cùng cách `test_td0170` đã làm) — dữ liệu đó (sau khi
TD-0189 sửa MỘT nến, xem commit) tự nhiên cho ra đúng chuỗi mua-mua-mua-
rồi-TP1-rồi-TP2. `TestKhongDCASauKhiTP1DaChot` dựng MỘT fixture RIÊNG,
nhỏ, chủ đích tạo lại đúng tình huống "giá vọt lên chốt TP1 xong mới rơi
xuyên qua p2/p3" để khoá điều 3 — vì bản sửa nến ở `test_td0187` đã CỐ Ý
loại bỏ tình huống đó khỏi fixture chung, nên không còn dữ liệu nào ở đó
để khoá lại hành vi "không DCA sau TP1".
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# ── tái dùng bộ sinh/chạy của TD-0187 (cùng cách test_td0170 đã làm) ──────
_spec = importlib.util.spec_from_file_location(
    "td0187", REPO_ROOT / "tests" / "lock" / "test_td0187_dinh_co_lenh_backtest_that.py"
)
_td0187 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_td0187)  # type: ignore[union-attr]

_chay = _td0187._chay
_lenh_vao = _td0187._lenh_vao
_lenh_du_ba_tranche = _td0187._lenh_du_ba_tranche
_chia_nho = _td0187._chia_nho
_ghi_feather = _td0187._ghi_feather
_bars_4h_co_trend = _td0187._bars_4h_co_trend
SAN_XUAT = _td0187.SAN_XUAT

from tool_d.take_profit import TP_SOURCE_NANG, TP_SOURCE_ZONE, TY_LE_CHOT_TP1  # noqa: E402


def _lenh_thoat(trade: dict) -> list[dict]:
    return [o for o in trade.get("orders", []) if o.get("ft_order_side") in ("sell", "short")]


# ═══════════════════════════════════════════════════════════════════════
# Nhóm 1 — dùng lại fixture kq_san_xuat của TD-0187/TD-0194
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def tmp_module(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("td0189")


@pytest.fixture(scope="module")
def kq_san_xuat(tmp_module) -> dict:
    return _chay(tmp_module, SAN_XUAT)


class TestKhongPassRong:
    """Guard trước — mọi khẳng định dưới đây vô nghĩa nếu không có lệnh
    đủ 3 tranche VÀ có TP1 VÀ có TP2 trên cùng một lệnh."""

    def test_co_lenh_du_ba_tranche_va_co_ca_hai_lenh_thoat(self, kq_san_xuat) -> None:
        t = _lenh_du_ba_tranche(kq_san_xuat)
        thoat = _lenh_thoat(t)
        assert len(thoat) == 2, (
            f"cần đúng 2 lệnh thoát (TP1 rồi TP2) trên lệnh đủ 3 tranche, "
            f"thấy {len(thoat)}: {[o.get('ft_order_tag') for o in thoat]}"
        )


class TestTP1ChotDungNuaViThe:
    def test_tp1_la_lenh_thoat_DAU_TIEN_va_mang_tag_dung_nguon(self, kq_san_xuat) -> None:
        t = _lenh_du_ba_tranche(kq_san_xuat)
        thoat = _lenh_thoat(t)
        tp1 = thoat[0]
        assert tp1["ft_order_tag"] in (f"TP1_{TP_SOURCE_ZONE}", f"TP1_{TP_SOURCE_NANG}"), tp1["ft_order_tag"]

    def test_tp1_chot_DUNG_ty_le_TY_LE_CHOT_TP1_theo_AMOUNT(self, kq_san_xuat) -> None:
        """§5.1 — chốt 50% VỊ THẾ, tức 50% `amount` (số coin), không phải
        50% một con số tiền tệ nào khác (cost/stake biến động theo giá)."""
        t = _lenh_du_ba_tranche(kq_san_xuat)
        vao, thoat = _lenh_vao(t), _lenh_thoat(t)
        tong_amount = sum(float(o["amount"]) for o in vao)
        tp1_amount = float(thoat[0]["amount"])
        assert tp1_amount == pytest.approx(TY_LE_CHOT_TP1 * tong_amount, rel=0.01), (
            tp1_amount, TY_LE_CHOT_TP1 * tong_amount,
        )

    def test_tp2_dong_NOT_amount_con_lai(self, kq_san_xuat) -> None:
        t = _lenh_du_ba_tranche(kq_san_xuat)
        vao, thoat = _lenh_vao(t), _lenh_thoat(t)
        tong_amount = sum(float(o["amount"]) for o in vao)
        con_lai = tong_amount - float(thoat[0]["amount"])
        assert thoat[1]["ft_order_tag"] == "TP2_TRAIL"
        assert float(thoat[1]["amount"]) == pytest.approx(con_lai, rel=0.01)


class TestThuTuThoiGianDungCaiDatBenTrong:
    """🔴 Thứ tự các lệnh trong `t["orders"]` là thứ tự KHỚP THẬT (không
    phải thứ tự Freqtrade sắp xếp lại) — kiểm bằng cách đối chiếu với chốt
    "không DCA sau TP1": nếu tranche 2/3 tồn tại, chúng PHẢI đứng TRƯỚC
    lệnh TP1 trong danh sách, không đứng sau."""

    def test_moi_lenh_MUA_dung_TRUOC_lenh_TP1_dau_tien(self, kq_san_xuat) -> None:
        t = _lenh_du_ba_tranche(kq_san_xuat)
        thu_tu = [o["ft_order_side"] for o in t["orders"]]
        i_tp1 = thu_tu.index("sell")
        assert all(s == "buy" for s in thu_tu[:i_tp1]), thu_tu
        assert thu_tu[i_tp1:] == ["sell", "sell"], thu_tu


# ═══════════════════════════════════════════════════════════════════════
# Nhóm 2 — fixture RIÊNG: TP1 chốt trước, giá rồi rơi xuyên p2/p3
# ═══════════════════════════════════════════════════════════════════════

# `_bars_4h_co_trend()` cho zone ĐÁY cố định — vá lại đúng vị trí "chạm p1"
# (nến thứ 5 trong khối `b += [...]` cuối cùng của hàm, xem docstring
# `test_td0187`), rồi thay TOÀN BỘ phần SAU nến đó bằng kịch bản riêng.
# 40 = 10 (khối cuối, tường minh) + 30 (đuôi đơn điệu) — độ dài SUFFIX cố
# định của `_bars_4h_co_trend()`; "chạm p1" là phần tử thứ 5 (index 4) của
# khối 10 tường minh ⇒ offset từ cuối mảng = -40 + 4 = -36.
_OFFSET_CHAM_P1_TU_CUOI = -36


def _rows4_khong_dca_sau_tp1() -> list[tuple[float, float, float, float, float]]:
    base = list(_bars_4h_co_trend())
    i_cham_p1 = len(base) + _OFFSET_CHAM_P1_TU_CUOI
    cham_p1 = base[i_cham_p1]
    # Đối chứng: xác nhận đúng nến đang cắt — nếu bộ sinh dùng chung đổi
    # cấu trúc suffix, chỗ này RAISE thay vì âm thầm cắt sai nến (N6).
    assert cham_p1[2] == pytest.approx(95.30), (
        f"offset {_OFFSET_CHAM_P1_TU_CUOI} không còn trỏ đúng nến 'chạm p1' "
        f"(low={cham_p1[2]}, kỳ vọng 95.30) — `_bars_4h_co_trend()` đã đổi cấu "
        "trúc suffix, phải tính lại offset"
    )
    giu = base[: i_cham_p1 + 1]  # tới hết nến "chạm p1", GIỮ NGUYÊN warmup + zone

    # p1≈95.34, p2=95.0, p3≈94.66, sl≈94.21, R_eff(khoảng giá)≈p_avg×0,00832
    # ≈0,79 quanh p_avg≈95 ⇒ nạng TP1 ≈ 95+1,5×0,79 ≈ 96,2; trần tìm zone
    # (4×R_eff) ≈ 95+3,17 ≈ 98,2. Vọt lên 130 là an toàn VƯỢT XA cả hai,
    # không phụ thuộc TP1 rơi vào nhánh zone hay nạng.
    kich_ban = [
        (95.40, 130.0, 95.35, 128.0, 1000.0),   # vọt thẳng lên — chốt TP1 (bất kể nguồn)
        (128.0, 128.0, 126.0, 127.0, 1000.0),   # giữ đỉnh vài nến cho TP2 có mốc "đỉnh sau TP1"
        (127.0, 127.5, 125.5, 126.5, 1000.0),
        # Rơi THẲNG xuyên qua p2 (95,0) và p3 (94,66) — nếu code còn cho
        # DCA sau khi TP1 đã chốt, tranche 2/3 sẽ khớp Ở ĐÂY.
        (126.0, 126.0, 90.0, 91.0, 1000.0),
        (91.0, 92.5, 90.5, 92.0, 1000.0),
        (92.0, 93.0, 91.5, 92.5, 1000.0),
    ]
    # Đuôi ổn định, đủ để TP2 trail (đỉnh 128 − 1,5×ATR) chắc chắn bị xuyên
    # (giá đã ở ~92, cách đỉnh hơn 30) và để DG8/warmup không thiếu nến.
    duoi = [(92.5 + k * 0.01, 92.6 + k * 0.01, 92.4 + k * 0.01, 92.5 + k * 0.01, 1000.0) for k in range(20)]
    return giu + kich_ban + duoi


KET_THUC_RIENG = pd.Timestamp("2025-04-10 00:00", tz="UTC")


def _sinh_du_lieu_rieng(datadir: Path) -> None:
    rows4 = _rows4_khong_dca_sau_tp1()
    rows1 = [x for bar in rows4 for x in _chia_nho(bar, 4)]
    bat_dau = KET_THUC_RIENG - pd.Timedelta(hours=len(rows1) - 1)
    idx1 = pd.date_range(bat_dau, periods=len(rows1), freq="1h", tz="UTC")
    df1 = pd.DataFrame(rows1, columns=["open", "high", "low", "close", "volume"])
    df1.insert(0, "date", idx1)
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    df4 = df1.set_index("date").resample("4h").agg(agg).reset_index()
    df1d = df1.set_index("date").resample("1D").agg(agg).reset_index()
    rows5 = [x for bar in rows1 for x in _chia_nho(bar, 12)]
    df5 = pd.DataFrame(rows5, columns=["open", "high", "low", "close", "volume"])
    df5.insert(0, "date", pd.date_range(bat_dau, periods=len(rows5), freq="5min", tz="UTC"))

    d = datadir / "futures"
    fund = pd.DataFrame({"date": idx1, "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0, "volume": 0.0})
    cap = _td0187.CAP
    _ghi_feather(df1, d / f"{cap}-1h-futures.feather")
    _ghi_feather(df1, d / f"{cap}-1h-mark.feather")
    _ghi_feather(df5, d / f"{cap}-5m-futures.feather")
    _ghi_feather(df5, d / f"{cap}-5m-mark.feather")
    _ghi_feather(df4, d / f"{cap}-4h-futures.feather")
    _ghi_feather(df1d, d / f"{cap}-1d-futures.feather")
    _ghi_feather(fund, d / f"{cap}-1h-funding_rate.feather")

    # TIMERANGE phủ đúng 10 ngày cuối (đủ cả kịch bản riêng), phần đầu là
    # warmup (khớp cách neo mốc-KẾT-THÚC của TD-0182 — xem test_td0187).
    return (
        (KET_THUC_RIENG - pd.Timedelta(days=10)).strftime("%Y%m%d"),
        (KET_THUC_RIENG + pd.Timedelta(hours=1)).strftime("%Y%m%d"),
    )


def _chay_rieng(tmp: Path) -> dict:
    datadir, userdir = tmp / "data_rieng", tmp / "userdir_rieng"
    t0, t1 = _sinh_du_lieu_rieng(datadir)
    (userdir / "strategies").mkdir(parents=True, exist_ok=True)
    cfg = json.loads((REPO_ROOT / "config" / "freqtrade" / "config.json").read_text(encoding="utf-8"))
    cfg["exchange"]["pair_whitelist"] = ["LTC/USDT:USDT"]
    cfg["max_open_trades"] = 1
    cfg["stake_amount"] = 100
    cfg["dry_run"] = True
    cfg_path = tmp / "cfg_rieng.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable, "-m", "freqtrade", "backtesting",
            "--config", str(cfg_path), "--datadir", str(datadir), "--userdir", str(userdir),
            "--strategy", SAN_XUAT, "--strategy-path", str(REPO_ROOT / "user_data" / "strategies"),
            "--timerange", f"{t0}-{t1}", "--timeframe-detail", "5m", "--cache", "none", "--export", "trades",
        ],
        capture_output=True, text=True, timeout=900, cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, f"backtest thất bại:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    log = proc.stdout + proc.stderr
    nuot = [ln for ln in log.splitlines() if "Strategy caused the following exception" in ln]
    assert not nuot, f"{len(nuot)} exception bị Freqtrade nuốt — dòng đầu:\n{nuot[0][:300]}"
    from freqtrade.data.btanalysis import load_backtest_stats

    files = sorted((userdir / "backtest_results").glob("backtest-result-*.zip"))
    assert files, "không có file kết quả"
    return load_backtest_stats(files[-1])["strategy"][SAN_XUAT]


@pytest.fixture(scope="module")
def kq_rieng(tmp_path_factory) -> dict:
    return _chay_rieng(tmp_path_factory.mktemp("td0189_rieng"))


class TestKhongDCASauKhiTP1DaChot:
    """🔴 Chốt chủ dự án 09/09/2026 — sau khi TP1 đã chốt, KHÔNG bơm thêm
    tranche dù giá có tụt về đúng p2/p3."""

    def test_gia_that_su_co_xuyen_qua_p2_va_p3_sau_TP1(self, kq_rieng) -> None:
        """Guard PASS RỖNG: nếu kịch bản không thực sự đẩy giá qua p2/p3
        SAU khi TP1 đã chốt thì test dưới XANH-VÔ-NGHĨA — không phân biệt
        được "chặn đúng" với "chưa từng có cơ hội để DCA"."""
        assert kq_rieng["trades"], "0 lệnh — kịch bản riêng không sinh được tín hiệu vào lệnh"
        t = kq_rieng["trades"][0]
        tag = json.loads(t["enter_tag"])
        assert 90.0 < tag["p3"] < 95.5, tag  # p3 phải nằm TRONG vùng giá đã rơi qua (90-92.5)

    def test_KHONG_co_lenh_mua_nao_sau_lenh_TP1(self, kq_rieng) -> None:
        t = kq_rieng["trades"][0]
        thu_tu = [(o["ft_order_side"], o.get("ft_order_tag")) for o in t["orders"]]
        i_tp1 = next(i for i, (side, tag) in enumerate(thu_tu) if side == "sell" and str(tag).startswith("TP1_"))
        sau_tp1 = thu_tu[i_tp1 + 1 :]
        assert all(side != "buy" for side, _ in sau_tp1), (
            f"có lệnh MUA sau khi TP1 đã chốt — vi phạm chốt 09/09/2026: {thu_tu}"
        )
        # đúng 1 tranche trước TP1 (kịch bản đẩy giá lên NGAY sau khi tranche 1
        # khớp, trước khi kịp chạm p2) — nếu ra khác 1, kịch bản không còn đo
        # đúng câu hỏi "đã chốt TP1 chỉ với MỘT tranche" nữa.
        assert thu_tu[:i_tp1] == [("buy", thu_tu[0][1])], thu_tu

    def test_KIEM_CO_RANG_bang_AST_khoi_chan_dung_TRUOC_ca_hai_nhanh_no_bao_ve(self) -> None:
        """🔴 "Kiểm có răng" bản AST — thay cho phá-thật-chạy-lại-backtest.

        Đã THỬ bản phá-thật (gỡ dòng chặn rồi chạy lại đúng `kq_rieng`):
        kết quả KHÔNG khác biệt — vì TP2 (đang trail phần còn lại) đóng
        TOÀN BỘ vị thế TRƯỚC KHI giá kịp rơi tới `p2`/`p3` bất kể chặn có
        gỡ hay không, nên "guard removed" và "guard present" ra CÙNG một
        kết quả trên chính kịch bản này — một phép thử không phân biệt
        được hai nhánh thì tự nó là PASS RỖNG, không phải bằng chứng cho
        bên nào. Dựng lại một kịch bản khác (ATR đủ lớn để trail không kịp
        đuổi) khả thi nhưng rất dễ vỡ theo dữ liệu — đổi hướng sang kiểm
        CẤU TRÚC mã nguồn, đúng bài học `L-Z36`/`test_td0170`: hỏi *"khối
        chặn có ĐỨNG ĐÚNG CHỖ trong luồng thực thi không"*, không dựa vào
        việc dựng được một chuỗi giá dồn được engine vào đúng nhánh đó.

        Bốn điều kiện `assert` dưới đây, gộp lại, LOẠI được các cách viết
        sai điển hình: (1) không đứng ngay đầu hàm ⇒ có thể bị `has_open_
        orders` che khuất hoặc đặt sai tầng; (2) đứng SAU `_xet_tp1` ⇒ TP1
        sẽ không bao giờ được xét lần đầu (vì lúc đó exits luôn là 0, điều
        kiện vẫn đúng, nhưng đặt sai thứ tự đọc gây hiểu lầm — siết cho
        chắc); (3) đứng SAU `nr_of_successful_entries >= 3` ⇒ với lệnh đã
        đủ 3 tranche, `return None` của khối kia chạy trước nên khối chặn
        không được đọc — không đỏ khi test nhưng vẫn là logic mù."""
        src = (REPO_ROOT / "user_data" / "strategies" / "ZoneAbsorption.py").read_text(encoding="utf-8")
        i_def = src.index("def adjust_trade_position(")
        i_end = src.index("\n    def ", i_def + 1)  # tới đầu hàm kế tiếp
        than = src[i_def:i_end]

        i_chan = than.find("if trade.nr_of_successful_exits >= 1:")
        i_xet_tp1 = than.find("self._xet_tp1(")
        i_entries_3 = than.find("if trade.nr_of_successful_entries >= 3:")
        i_open_orders = than.find("if trade.has_open_orders:")

        assert -1 not in (i_chan, i_xet_tp1, i_entries_3, i_open_orders), (
            "thiếu một trong bốn mốc cần so — thân `adjust_trade_position` "
            "đã đổi hình dạng, cập nhật lại test này"
        )
        assert i_open_orders < i_chan, "khối chặn phải đứng SAU guard has_open_orders"
        assert i_chan < i_xet_tp1, "khối chặn PHẢI đứng TRƯỚC `_xet_tp1` — đứng sau thì vô nghĩa (exits luôn 0 khi tới đó)"
        assert i_chan < i_entries_3, "khối chặn PHẢI đứng TRƯỚC nhánh thêm-tranche — đứng sau thì không chặn được gì"
