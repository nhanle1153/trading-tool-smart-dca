"""TD-0333 (`DR-D4-14`) — test khoá cho `bo_chay/trich_lenh.py`.

Canh ba thứ:

1. **Công thức**: `rui_ro_da_trien_khai_usdt` và `planned_risk_usdt` đúng tới sai số
   dấu phẩy động trên lệnh dựng tay — tính tay ngay trong test, không chép từ mã.
2. **Không trôi khỏi chiến lược**: `doc_tag_long()` cho `R_eff` TRÙNG TỪNG BIT với
   `ZoneAbsorption._giai_ma` — hai chỗ tính một công thức là hai nguồn sự thật, nên
   phải có một phép kiểm bắt chúng nhìn nhau.
3. **Phép suy ngược đứng vững trên export THẬT**: `planned_risk_usdt` là SUY NGƯỢC
   (export không mang `custom_data` — đo 19/09/2026, `DR-D4-14` §10). Kiểm độc lập:
   `n_full` suy từ tranche 1 nhân `w[1]` phải khớp notional tranche 2 mà chiến lược
   THẬT SỰ đặt. Nếu phép suy sai, hai con số này không thể khớp.

Fixture sinh lệnh là `_chay` của `test_td0187` (tiền lệ: `test_td0189`, `test_td0193`,
`test_td0239` đều nạp nó như vậy) — chạy trong `tmp`, không đụng sổ thật.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import pytest

from tool_d.bo_chay.trich_lenh import TrichLenhError, doc_tag_long, lenh_tu_freqtrade
from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.sizing import doc_trong_so_tranche

REPO_ROOT = Path(__file__).resolve().parents[2]
CFG = load_tool_d_config()
L = float(resolve(CFG, "tier_a.L_exchange"))
W = doc_trong_so_tranche(CFG)


def _tag(p1=100.0, p2=98.0, p3=96.0, sl=94.0, **them) -> str:
    d = {"zl": 95.0, "zh": 101.0, "p1": p1, "p2": p2, "p3": p3, "sl": sl, "zs": 0.5, "t4": "UP", "sw": 0}
    d.update(them)
    return json.dumps(d)


def _order(amount: float, gia: float, ts: int, *, vao: bool = True) -> dict:
    return {
        "amount": amount,
        "safe_price": gia,
        "ft_order_side": "buy" if vao else "sell",
        "order_filled_timestamp": ts,
        "ft_is_entry": vao,
        "cost": amount * gia,
    }


def _lenh(orders, *, tag=None, pnl=5.0, don_bay=None, **them) -> dict:
    t = {
        "pair": "LTC/USDT:USDT",
        "open_date": "2025-07-01 04:00:00+00:00",
        "close_date": "2025-07-03 10:00:00+00:00",
        "profit_abs": pnl,
        "enter_tag": _tag() if tag is None else tag,
        "is_short": False,
        "leverage": L if don_bay is None else don_bay,
        "orders": orders,
    }
    t.update(them)
    return t


# ── 1. công thức, tính tay ───────────────────────────────────────────────────


class TestCongThuc:
    def test_mot_tranche(self) -> None:
        # notional tranche 1 = 3 × 100 = 300 USDT, ký quỹ = 300 / L
        lw = lenh_tu_freqtrade(_lenh([_order(3.0, 100.0, 1)]), cfg=CFG, arm="Z0-T1")
        assert lw.rui_ro_da_trien_khai_usdt == pytest.approx(300.0 * (100.0 - 94.0) / 100.0, rel=1e-12)
        n_full = (300.0 / L) * L / W[0]
        r_eff = ((100.0 + 98.0 + 96.0) / 3 - 94.0) / ((100.0 + 98.0 + 96.0) / 3)
        assert lw.planned_risk_usdt == pytest.approx(n_full * r_eff, rel=1e-12)
        assert lw.r_trien_khai == pytest.approx(5.0 / lw.rui_ro_da_trien_khai_usdt, rel=1e-12)

    def test_ba_tranche_cong_don_va_sap_theo_gio_khop(self) -> None:
        # Cố ý đưa order sai thứ tự: tranche 1 là order có `order_filled_timestamp` NHỎ NHẤT.
        orders = [_order(3.0, 96.0, 30), _order(3.0, 100.0, 10), _order(3.0, 98.0, 20)]
        lw = lenh_tu_freqtrade(_lenh(orders), cfg=CFG, arm="Z0")
        mong = sum(3.0 * g * (g - 94.0) / g for g in (100.0, 98.0, 96.0))
        assert lw.rui_ro_da_trien_khai_usdt == pytest.approx(mong, rel=1e-12)
        # planned dựng từ tranche 1 = order giá 100, không phải order đầu danh sách
        assert lw.planned_risk_usdt == pytest.approx((300.0 / W[0]) * (98.0 - 94.0) / 98.0, rel=1e-12)

    def test_order_thoat_khong_tinh_la_tranche(self) -> None:
        a = lenh_tu_freqtrade(_lenh([_order(3.0, 100.0, 1)]), cfg=CFG, arm="Z0")
        b = lenh_tu_freqtrade(
            _lenh([_order(3.0, 100.0, 1), _order(1.5, 103.0, 2, vao=False)]), cfg=CFG, arm="Z0"
        )
        assert a.rui_ro_da_trien_khai_usdt == b.rui_ro_da_trien_khai_usdt

    def test_ngay_ve_utc_khong_mui_gio(self) -> None:
        lw = lenh_tu_freqtrade(
            _lenh([_order(3.0, 100.0, 1)], open_date="2025-07-01 11:00:00+07:00"), cfg=CFG, arm="Z0"
        )
        assert lw.open_date == datetime(2025, 7, 1, 4, 0) and lw.open_date.tzinfo is None


# ── 2. không trôi khỏi chiến lược ────────────────────────────────────────────


def _giai_ma_chien_luoc():
    thu_muc = REPO_ROOT / "user_data" / "strategies"
    if str(thu_muc) not in sys.path:
        sys.path.insert(0, str(thu_muc))
    spec = importlib.util.spec_from_file_location("ZoneAbsorption", thu_muc / "ZoneAbsorption.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m._giai_ma


class TestKhopChienLuoc:
    @pytest.mark.parametrize(
        "gia", [(100.0, 98.0, 96.0, 94.0), (0.0123, 0.0121, 0.0119, 0.0117), (61234.5, 60100.0, 59000.1, 57777.7)]
    )
    def test_r_eff_trung_tung_bit_voi_giai_ma(self, gia) -> None:
        tag = _tag(*gia)
        kh, _ = _giai_ma_chien_luoc()(tag, atr_1h_tai_tranche1=0.0)
        sl, r_eff = doc_tag_long(tag)
        assert sl == kh.sl
        assert r_eff == kh.r_eff_plan  # bằng tuyệt đối, không approx


# ── 3. từ chối ───────────────────────────────────────────────────────────────


class TestTuChoi:
    @pytest.mark.parametrize(
        "lenh, trong_loi",
        [
            (_lenh([_order(3.0, 100.0, 1)], tag=_tag(h="s")), "SHORT"),
            (_lenh([_order(3.0, 100.0, 1)], is_short=True), "SHORT"),
            (_lenh([]), "không có tranche"),
            (_lenh([_order(0.0, 100.0, 1)]), "không có tranche"),
            (_lenh([_order(3.0, 100.0, None)]), "không có tranche"),
            (_lenh([_order(3.0, 100.0, 1)], don_bay=L + 1), "đòn bẩy"),
            (_lenh([_order(3.0, 100.0, 1)], tag="không phải json"), "JSON"),
            (_lenh([_order(3.0, 100.0, 1)], tag=json.dumps({"p1": 1})), "thiếu"),
            (_lenh([_order(3.0, 100.0, 1)], tag=_tag(sl=101.0)), "R_eff"),
            (_lenh([_order(3.0, 93.0, 1)]), "entry"),
            (_lenh([_order(3.0, 100.0, 1)], open_date=None), "open_date"),
        ],
    )
    def test_tu_choi(self, lenh, trong_loi) -> None:
        with pytest.raises(TrichLenhError, match=trong_loi):
            lenh_tu_freqtrade(lenh, cfg=CFG, arm="Z0")

    def test_thieu_profit_abs(self) -> None:
        t = _lenh([_order(3.0, 100.0, 1)])
        del t["profit_abs"]
        with pytest.raises(TrichLenhError, match="profit_abs"):
            lenh_tu_freqtrade(t, cfg=CFG, arm="Z0")


# ── 4. export THẬT ───────────────────────────────────────────────────────────


def _nap_td0187():
    spec = importlib.util.spec_from_file_location(
        "td0187", REPO_ROOT / "tests" / "lock" / "test_td0187_dinh_co_lenh_backtest_that.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def export_that(tmp_path_factory) -> tuple[dict, object]:
    td = _nap_td0187()
    tmp = tmp_path_factory.mktemp("td0333")
    kq = td._chay(tmp, td.SAN_XUAT)
    cfg_luot = load_tool_d_config(tmp / "config" / "tool_d_config.yaml")
    return kq, cfg_luot


class TestExportThat:
    def test_moi_lenh_that_deu_trich_duoc(self, export_that) -> None:
        kq, cfg_luot = export_that
        assert kq["trades"], "fixture ra 0 lệnh — mọi khẳng định bên dưới sẽ đúng-vô-nghĩa"
        for t in kq["trades"]:
            lw = lenh_tu_freqtrade(t, cfg=cfg_luot, arm="Z0")
            assert math.isfinite(lw.r_trien_khai) and math.isfinite(lw.r_realized)

    def test_n_full_suy_nguoc_khop_notional_tranche_hai_that(self, export_that) -> None:
        """Phép kiểm ĐỘC LẬP cho phép suy ngược: chiến lược đặt tranche 2 bằng
        `n_full × w[1]`. Suy `n_full` từ tranche 1 rồi so với tranche 2 THẬT."""
        kq, cfg_luot = export_that
        l_luot = float(resolve(cfg_luot, "tier_a.L_exchange"))
        w = doc_trong_so_tranche(cfg_luot)
        da_so = 0
        for t in kq["trades"]:
            vao = sorted(
                (o for o in t["orders"] if o["ft_is_entry"] and o["order_filled_timestamp"]),
                key=lambda o: o["order_filled_timestamp"],
            )
            if len(vao) < 2:
                continue
            ky_quy_t1 = vao[0]["amount"] * vao[0]["safe_price"] / l_luot
            n_full = ky_quy_t1 * l_luot / w[0]
            notional_t2 = vao[1]["amount"] * vao[1]["safe_price"]
            # Sai số duy nhất được phép: làm tròn khối lượng theo bước sàn.
            assert notional_t2 == pytest.approx(n_full * w[1], rel=0.01), t["pair"]
            # …và CHÍNH module phải cho đúng `n_full` đó — không thì phép kiểm trên
            # chỉ chứng minh công thức trong test, không chứng minh mã sản xuất.
            _, r_eff = doc_tag_long(t["enter_tag"])
            lw = lenh_tu_freqtrade(t, cfg=cfg_luot, arm="Z0")
            assert lw.planned_risk_usdt == pytest.approx(n_full * r_eff, rel=1e-9), t["pair"]
            da_so += 1
        assert da_so >= 1, "không lệnh nào có ≥ 2 tranche — phép kiểm này thành PASS RỖNG"
