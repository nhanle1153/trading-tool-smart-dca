"""TD-0400 — chiến lược rổ funding chéo trung tính của ứng viên suất (d) `IQ-0003` (`DR-D0-IQ0003`).

Phiên dựng file này ĐÃ NHIỄM (DR-009): nó chỉ dịch tờ chọn sang máy, không đánh giá, không thêm biến thể. Nguồn sự thật
của luật là bốn trường cửa CHỌN của `IQ-0003` trong `registry/idea_queue.jsonl` và `DR-D0-IQ0003` §2–§5.

Hình dạng:
  • mỗi ngày, lệnh khớp tại giá MỞ nến 1H `ro_gio_can_ro_utc`:00 UTC. Tín hiệu đặt trên nến 1H liền trước (đóng đúng lúc
    đó), vì Freqtrade khớp tín hiệu ở giá mở nến KẾ TIẾP;
  • nhóm do `tool_d.ro_funding.nhom_tai()` quyết (tầng thuần, có test riêng); chiến lược chỉ nạp dữ liệu và ánh xạ nhóm
    thành cột `enter_*` / `exit_*`;
  • thoát tại lần cân rổ bằng TÍN HIỆU thoát mang `exit_tag = "CAN_RO"` (khớp ở cùng giá mở nến với lệnh vào — một lần
    cân rổ là một thời điểm khớp duy nhất); nhãn thoát hợp lệ khác duy nhất là stop thảm hoạ (`DR-CAN-RO-01` §3);
  • không chốt lời, không DCA, không cửa thoát theo thời gian.

N4: mọi tham số đọc từ `tool_d_config.yaml` qua `resolve()`, đúng danh sách khối `DR-BIEN-THE-01:KHOA` của DR thiết kế
(test AST canh: đọc một khoá ngoài danh sách là mở lại lối "chỉnh một khoá không khai").
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd
from freqtrade.enums import RunMode
from freqtrade.strategy import IStrategy

from tool_d.ablation.chi_so_export import EXIT_CAN_RO
from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.ro_funding import NhomRo, RoFundingError, la_moc_can_ro, ma_goc, nhom_tai, notional_moi_vi_the

logger = logging.getLogger(__name__)

TAG_VAO = "RO"


class RoFunding(IStrategy):
    timeframe = "1h"
    # Rổ luôn có chân Short; công tắc THẬT là `tier_a.enable_short` (`DR-SHORT-02`, chốt kép ở `confirm_trade_entry`).
    can_short = True
    startup_candle_count = 0
    # Stop thảm hoạ là stop TĨNH đặt qua file phủ (`config/freqtrade/phu/RoFunding.json`, `_stoploss_tu_khoa`), không
    # `custom_stoploss`: Freqtrade gắn nhãn `trailing_stop_loss` cho stop bị custom dời (đo được TD-0400), nằm ngoài lớp
    # `CAN_RO_THEO_LICH`. `_kiem_stop_hieu_dung()` từ chối chạy nếu stop hiệu dụng khác mức YAML.
    use_custom_stoploss = False
    process_only_new_candles = True
    # Giá trị lớp; cấu hình thắng thuộc tính — stop hiệu dụng do file phủ đặt, kiểm ở `_kiem_stop_hieu_dung()`.
    stoploss = -0.99
    # Không chốt lời (tờ chọn): TẮT ROI. Cấu hình chung `{"0": 10}` thắng thuộc tính này, và ở đòn bẩy sàn 2 nó CÓ chạm
    # (2 lệnh `roi` trên EXPLORE, TD-0401) ⇒ file phủ THAY TRỌN `minimal_roi` bằng `{}`.
    minimal_roi: dict = {}

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._cfg = load_tool_d_config()
        self._enable_long = bool(resolve(self._cfg, "tier_a.enable_long"))
        self._enable_short = bool(resolve(self._cfg, "tier_a.enable_short"))
        von = resolve(self._cfg, "tier_a.von_ro_usdt")
        if von is None:
            # DR-D0-IQ0003 §2: vốn chưa chốt ⇒ từ chối chạy, không lấy mặc định (fail-closed).
            raise RoFundingError("tier_a.von_ro_usdt = null — vốn rổ chưa chốt (DR-D0-IQ0003 §10 câu c)")
        self._von = float(von)
        self._cua_so_gio = int(resolve(self._cfg, "tier_c.ro_funding.ro_cua_so_gio"))
        self._ty_le_k = float(resolve(self._cfg, "tier_c.ro_funding.ro_ty_le_k"))
        self._k_toi_thieu = int(resolve(self._cfg, "tier_c.ro_funding.ro_k_toi_thieu"))
        self._so_coin_toi_thieu = int(resolve(self._cfg, "tier_c.ro_funding.ro_so_coin_toi_thieu"))
        self._gio_can_ro = int(resolve(self._cfg, "tier_c.ro_funding.ro_gio_can_ro_utc"))
        self._stop_pct = float(resolve(self._cfg, "tier_c.ro_funding.ro_stop_tham_hoa_pct"))
        # Hai đòn bẩy KHÁC NGHĨA (chủ dự án chốt 24/09/2026, đính chính DR-D0-IQ0003): `ro_don_bay` = phơi nhiễm kinh tế
        # (notional = ro_don_bay × vốn / 2k), `ro_don_bay_san` = đặt trên sàn (ký quỹ = notional / ro_don_bay_san). Ở
        # sàn 1x ký quỹ = cả notional, rổ lỗ là không mở lại được vị thế cỡ cũ (đo được trong test: cần 500, còn 457).
        self._don_bay = float(resolve(self._cfg, "tier_c.ro_funding.ro_don_bay"))
        self._don_bay_san = float(resolve(self._cfg, "tier_c.ro_funding.ro_don_bay_san"))
        self._nhom_cache: dict[datetime, NhomRo] = {}

    # ── dữ liệu ─────────────────────────────────────────────────────
    def informative_pairs(self):
        """Live/dry-run chỉ thấy funding của cặp được khai ở đây (TD-0328); backtest tự nạp từ đĩa."""
        khung = self.dp.get_funding_rate_timeframe()
        return [(cap, khung, "funding_rate") for cap in self.dp.current_whitelist()]

    def _la_backtest(self) -> bool:
        return self.dp.runmode == RunMode.BACKTEST

    def _nhom(self, t: datetime) -> NhomRo:
        """Nhóm của lần cân rổ khớp tại `t`. Chỉ dùng dữ liệu có `date ≤ t` (tầng thuần cắt tường minh)."""
        if self._la_backtest() and t in self._nhom_cache:
            return self._nhom_cache[t]
        khung_funding = self.dp.get_funding_rate_timeframe()
        funding: dict[str, pd.DataFrame] = {}
        co_mat: set[str] = set()
        for cap in self.dp.current_whitelist():
            ma = ma_goc(cap)
            funding[ma] = self.dp.get_pair_dataframe(cap, timeframe=khung_funding, candle_type="funding_rate")
            # "Có mặt tại t" = có nến tín hiệu (đóng đúng lúc t). Nến MỞ tại t chưa tồn tại ở live, nên không dùng.
            nen = self.dp.get_pair_dataframe(cap, timeframe=self.timeframe)
            if not nen.empty and (nen["date"] == t - timedelta(hours=1)).any():
                co_mat.add(ma)
        nhom = nhom_tai(
            funding, co_mat, t,
            cua_so_gio=self._cua_so_gio, ty_le_k=self._ty_le_k,
            k_toi_thieu=self._k_toi_thieu, so_coin_toi_thieu=self._so_coin_toi_thieu,
        )
        if self._la_backtest():
            self._nhom_cache[t] = nhom
        return nhom

    def _nhom_theo_dong(self, dataframe: pd.DataFrame, metadata: dict) -> pd.Series:
        """Nhóm của cặp tại mỗi nến TÍN HIỆU (nến đóng lúc cân rổ); `None` ở mọi nến khác."""
        ma = ma_goc(metadata["pair"])
        moc = dataframe["date"] + timedelta(hours=1)
        la_tin_hieu = moc.apply(lambda t: la_moc_can_ro(t.to_pydatetime(), gio_utc=self._gio_can_ro))
        ket_qua = pd.Series([None] * len(dataframe), index=dataframe.index, dtype=object)
        for i in dataframe.index[la_tin_hieu]:
            ket_qua.at[i] = self._nhom(moc.at[i].to_pydatetime()).nhom_cua(ma)
        return ket_qua

    def _kiem_stop_hieu_dung(self) -> None:
        """Stop hiệu dụng phải đúng `−(ro_stop_tham_hoa_pct × ro_don_bay_san)/100` (tỉ lệ trên ký quỹ). Chạy thiếu file
        phủ thì stop là lưới −0,99 của cấu hình chung ⇒ rổ không có stop thảm hoạ ⇒ TỪ CHỐI (không raise trong
        callback — Freqtrade nuốt; `populate_indicators` không bị bọc)."""
        mong_doi = -self._stop_pct * self._don_bay_san / 100
        if abs(self.stoploss - mong_doi) > 1e-9:
            raise RoFundingError(
                f"stoploss hiệu dụng {self.stoploss} ≠ {mong_doi} — thiếu file phủ config/freqtrade/phu/RoFunding.json?"
            )

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        self._kiem_stop_hieu_dung()
        dataframe["ro_tin_hieu"] = (dataframe["date"] + timedelta(hours=1)).apply(
            lambda t: la_moc_can_ro(t.to_pydatetime(), gio_utc=self._gio_can_ro)
        )
        dataframe["ro_nhom"] = self._nhom_theo_dong(dataframe, metadata)
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        if self._enable_long:
            dataframe.loc[dataframe["ro_nhom"] == "long", ["enter_long", "enter_tag"]] = (1, TAG_VAO)
        if self._enable_short:
            dataframe.loc[dataframe["ro_nhom"] == "short", ["enter_short", "enter_tag"]] = (1, TAG_VAO)
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Rời nhóm tại lần cân rổ ⇒ đóng. Mã vẫn cùng nhóm ⇒ không có tín hiệu thoát ⇒ giữ nguyên."""
        tin_hieu = dataframe["ro_tin_hieu"]
        dataframe.loc[tin_hieu & (dataframe["ro_nhom"] != "long"), ["exit_long", "exit_tag"]] = (1, EXIT_CAN_RO)
        dataframe.loc[tin_hieu & (dataframe["ro_nhom"] != "short"), ["exit_short", "exit_tag"]] = (1, EXIT_CAN_RO)
        return dataframe

    # ── lệnh ────────────────────────────────────────────────────────
    def confirm_trade_entry(
        self, pair, order_type, amount, rate, time_in_force, current_time, entry_tag, side, **kwargs
    ) -> bool:
        """Chốt kép: công tắc hướng (`DR-SHORT-02`) + chỉ vào lệnh tại lần cân rổ."""
        if side == "short" and not self._enable_short:
            return False
        if side == "long" and not self._enable_long:
            return False
        t = current_time.replace(minute=0, second=0, microsecond=0)
        return la_moc_can_ro(t, gio_utc=self._gio_can_ro)

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs) -> float:
        if self._don_bay_san > max_leverage:
            raise RoFundingError(f"{pair}: ro_don_bay_san {self._don_bay_san} > max_leverage {max_leverage} của sàn")
        return self._don_bay_san

    def custom_stake_amount(
        self, pair, current_time, current_rate, proposed_stake, min_stake, max_stake, leverage, entry_tag, side, **kwargs
    ) -> float:
        """Notional = `ro_don_bay × von / (2k)` (DR §4); ký quỹ = notional / đòn bẩy sàn. Dưới sàn/ trên trần thì RAISE, không để Freqtrade cắt hay bỏ lệnh im lặng
        (MT-16, DR-D4-05) — Freqtrade nuốt exception thành một dòng log, và test khoá cấm đúng dòng log đó."""
        t = current_time.replace(minute=0, second=0, microsecond=0)
        nhom = self._nhom(t)
        stake = notional_moi_vi_the(self._don_bay * self._von, nhom.k) / leverage
        if min_stake is not None and stake < min_stake:
            raise RoFundingError(f"{pair}: stake {stake:.4f} < min_stake {min_stake:.4f} tại {t} (k = {nhom.k})")
        if stake > max_stake:
            raise RoFundingError(f"{pair}: stake {stake:.4f} > max_stake {max_stake:.4f} tại {t}")
        return stake
