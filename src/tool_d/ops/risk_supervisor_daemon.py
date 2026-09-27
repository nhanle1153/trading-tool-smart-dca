"""TD-0241 (`DR-D11-03`) — Risk Supervisor: tiến trình riêng thật (§6.6).

Nối các tầng thuần đã có (`risk_supervisor.py`, TD-0196) với hai điểm gọi
mạng thật (`api_client/binance_public.py` — đọc margin/vị thế/thanh lý;
`api_client/freqtrade_control.py` — dừng bot) thành MỘT vòng lặp chạy
được. Cùng khuôn `tool_d.ops.heartbeat_watchdog` (TD-0209): `chay_mot_vong
_giam_sat()` là đơn vị THUẦN có thể test độc lập (mọi lời gọi mạng nhận
qua tham số callable), `main()` chỉ là khung CLI mỏng.

🔴 KHÔNG phải entrypoint thứ 9 (N3, L-Z36) — module này không đánh giá một
cấu hình chiến lược nào, không chạm CALIB/WFO/LOCKBOX, không gọi
`measurement_guard()`. Vị trí/quyết định kiến trúc đã chốt ở `DR-D11-03`.

🔴 §6.6(2) "SUPERVISOR KHÔNG IMPORT CODE BOT" — file này KHÔNG import
`ZoneAbsorption`/bất kỳ gì dưới `user_data.strategies`/`freqtrade.strategy`.
Nó import `tool_d.config.loader` (cấu hình, không phải logic chiến lược)
để tự đối chiếu `L-Z44` SỐNG lúc khởi động — đây là daemon, không phải
`risk_supervisor.py`, nên được phép (xem `tests/lock/
test_lz44_khai_lai_hang_so_supervisor.py`, đã mở rộng phủ cả file này).

════ Ba điều fail-closed BẮT BUỘC trước khi vào vòng lặp, đúng thứ tự ════

1. `validate_credentials_for_live()` (TD-0242) — thiếu `BINANCE_API_KEY`/
   `BINANCE_API_SECRET` thì dừng ngay, 0 byte ra mạng.
2. Thiếu `FREQTRADE_API_USERNAME`/`FREQTRADE_API_PASSWORD` — daemon sẽ
   không gọi dừng được bot khi cần, khởi động là vô nghĩa.
3. `kiem_khai_lai_khop_ban_goc()` (L-Z44) SỐNG trên `tool_d_config.yaml`
   thật — lệch thì từ chối khởi động, không chỉ dựa vào test tĩnh.
4. Trạng thái đã lưu từ lần chạy trước có cờ đỏ (`la_thanh_ly`/
   `breaker.dung_han`) — từ chối khởi động lại êm xuôi (§6.6(2): "CỜ ĐỎ,
   KHÔNG tự gỡ" — người vận hành phải xoá/thừa nhận thủ công).

════ TODO (ghi để không quên, KHÔNG phải việc của TD-0241) ════
  1. Topology mạng thật daemon ↔ Freqtrade sống, và cơ chế khởi chạy tiến
     trình bền vững trên máy (Task Scheduler/dịch vụ Docker/khác) — quyết
     khi tới D11 setup thật (`DR-D11-03` mục "Ngoài phạm vi").
  2. `tu_thoi_diem_ms` lấy mốc KHỞI ĐỘNG tiến trình, không phải mốc MỞ vị
     thế — một lần thanh lý xảy ra đúng lúc daemon chết giữa hai lần chạy
     có thể bị bỏ lỡ. Chấp nhận có ý thức cho bản đầu; xem lại khi D11 có
     dữ liệu vị thế thật để neo mốc chính xác hơn.
"""

from __future__ import annotations

import argparse
import logging
import math
import re
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tool_d.api_client.binance_public import (
    BinanceBreakerMoError,
    BinanceCredentialsMissingError,
    BinancePrivateApiError,
    EXIT_MISSING_API_CREDENTIALS,
    get_account_info,
    get_force_orders,
    get_position_risk,
    trang_thai_breaker_hien_tai,
    validate_credentials_for_live,
)
from tool_d.api_client.freqtrade_control import (
    FreqtradeAuthError,
    FreqtradeControlError,
    doc_json_get,
    doc_so_lenh_dong,
    doc_so_vi_the_mo,
    dung_bot,
    mo_lai_bot,
    tam_ngung_mo_lenh,
)
from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.equity_peak import (
    ABORT as SU_KIEN_ABORT,
    TEN_FILE as TEN_FILE_DINH,
    SuKienDinh,
    cap_nhat_dinh,
    doc_dinh_equity,
    duong_dan_so_su_kien,
    ghi_su_kien,
    luu_dinh_equity,
)
from tool_d.tang_chan import RUNMODE_CO_SUPERVISOR, THU_MUC_SUPERVISOR
from tool_d.risk_supervisor import (
    ABORT,
    HALT,
    RiskSupervisorError,
    TrangThaiBenVung,
    TrangThaiBreaker,
    NUA_CO,
    ap_tran_halt,
    dieu_kien_mo_lai,
    TEN_FILE_DD_STATE,
    doc_co_do_tai_khoan,
    ghi_co_do_tai_khoan,
    ghi_dd_state,
    doc_snapshot_an_toan,
    doc_trang_thai,
    kiem_khai_lai_khop_ban_goc,
    luu_trang_thai,
    phat_hien_thanh_ly,
    quyet_dinh_tang_chan,
)

_LOG = logging.getLogger("tool_d.ops.risk_supervisor_daemon")

#: TD-0435 — mỗi runmode một Supervisor, một thư mục (`DR-TANG-CHAN-01` §4 điều 1, N11): trạng thái, đỉnh, sổ sự kiện,
#: `dd_state.json` cùng nằm dưới `runs/risk_supervisor/<runmode>/`. Gốc dùng CHUNG với tầng đọc `tool_d.tang_chan`.
TEN_FILE_TRANG_THAI = "state.json"


def duong_dan_theo_runmode(runmode: str) -> Path:
    if runmode not in RUNMODE_CO_SUPERVISOR:
        raise ValueError(f"runmode {runmode!r} không có Supervisor — chỉ {RUNMODE_CO_SUPERVISOR}")
    return THU_MUC_SUPERVISOR / runmode / TEN_FILE_TRANG_THAI


#: TD-0442 — cờ đỏ cấp TÀI KHOẢN sàn, MỘT file cho mọi Supervisor live (mọi container gắn cùng repo). Dry-run là ví giấy
#: của Freqtrade, không có tài khoản sàn ⇒ không đọc, không ghi file này.
DUONG_DAN_CO_DO_TAI_KHOAN = THU_MUC_SUPERVISOR / "live" / "co_do_tai_khoan.json"


def ly_do_khong_bat_tien_that(
    *, duong_trang_thai: Path | None = None, duong_co_do_tai_khoan: Path = DUONG_DAN_CO_DO_TAI_KHOAN
) -> str | None:
    """Chốt cho MỌI bộ khởi chạy tiền thật (TD-0442): cờ đỏ tài khoản, hoặc Supervisor live đã ghi cờ đỏ ⇒ lý do từ chối.
    File trạng thái hỏng ⇒ cũng từ chối (có thể đang che cờ đỏ — `doc_trang_thai`, N6). `None` ⇔ được bật."""
    ly_do = doc_co_do_tai_khoan(duong_co_do_tai_khoan)
    if ly_do is not None:
        return f"cờ đỏ TÀI KHOẢN: {ly_do} — xử lý xong rồi người vận hành xoá {duong_co_do_tai_khoan}"
    duong = duong_trang_thai if duong_trang_thai is not None else duong_dan_theo_runmode("live")
    try:
        t = doc_trang_thai(duong)
    except (RiskSupervisorError, ValueError, KeyError, TypeError, OSError) as exc:
        return f"không đọc được trạng thái Supervisor live {duong} ({exc}) — có thể đang che cờ đỏ"
    if t.co_do:
        return (f"Supervisor live đang giữ cờ đỏ ({duong}: la_thanh_ly={t.la_thanh_ly} dung_han={t.breaker.dung_han} "
                f"muc={t.muc_tang_chan} leo_thang={t.leo_thang_dung}) — không tự gỡ (§6.6(2))")
    return None
DEFAULT_CHU_KY_S = 60.0  # cùng bậc chu kỳ watchdog TD-0209 (Mục 4.4b)
DEFAULT_FREQTRADE_API_BASE_URL = "http://127.0.0.1:8080"

ENV_FT_USERNAME = "FREQTRADE_API_USERNAME"
ENV_FT_PASSWORD = "FREQTRADE_API_PASSWORD"

# Nối tiếp dải exit code riêng của dự án (86 guard · 87 cache · 88-91
# lockbox · 92 audit · 94-98 cổng/entrypoint khác · 99 thiếu credential
# Binance, TD-0242). 100+ dành cho daemon này (TD-0241).
EXIT_MISSING_FREQTRADE_CREDENTIALS = 100
EXIT_L44_MISMATCH = 101
EXIT_CO_DO_TU_LAN_CHAY_TRUOC = 102
EXIT_DA_DUNG_VI_CO_DO = 103
EXIT_KHONG_DUNG_DUOC_BOT = 104


def _boc_loi_binance(ham: Callable[[], object]) -> Callable[[], object]:
    """`doc_snapshot_an_toan()` chỉ cô lập `RiskSupervisorError`/
    `TimeoutError`/`ConnectionError` (xem docstring của nó) — hai exception
    của `binance_public.py` là một HỆ THỨ BẬC khác, nên bọc lại ở ĐÂY
    (tầng nối dây, được phép biết cả hai vốn từ vựng) thay vì mở rộng danh
    sách bắt của `doc_snapshot_an_toan` cho một nhu cầu chỉ file này có."""

    def goi() -> object:
        try:
            return ham()
        except (BinancePrivateApiError, BinanceBreakerMoError) as exc:
            raise RiskSupervisorError(str(exc)) from exc

    return goi


def chay_mot_vong_giam_sat(
    trang_thai: TrangThaiBenVung,
    *,
    now: datetime,
    doc_account_fn: Callable[[], object],
    doc_position_fn: Callable[[], object],
    doc_force_orders_fn: Callable[[], object],
    doc_breaker_hien_tai_fn: Callable[[], object],
    tu_thoi_diem_ms: int,
    dung_bot_fn: Callable[[], object],
    tinh_dd_fn: Callable[[object], float | None] | None = None,
    tam_ngung_fn: Callable[[], object] | None = None,
    ghi_abort_fn: Callable[[], None] | None = None,
    luu_truoc_fn: Callable[[TrangThaiBenVung], None] | None = None,
    doc_so_lenh_dong_fn: Callable[[], int] | None = None,
    mo_lai: NoiMoLai | None = None,
    doc_co_do_tai_khoan_fn: Callable[[], str | None] | None = None,
    ghi_co_do_tai_khoan_fn: Callable[[str], None] | None = None,
) -> tuple[TrangThaiBenVung, bool]:
    """MỘT vòng: đọc snapshot ba endpoint (cô lập lỗi từng endpoint,
    §6.6(4)) → đọc lại breaker THẬT của `binance_public` → phát hiện thanh
    lý → nếu `LIQUIDATED` HOẶC breaker đã `dung_han` (418, cùng cấp
    `LIQUIDATED`) thì gọi `dung_bot_fn()` và báo NÊN DỪNG vòng lặp.

    Đã dừng từ vòng trước (`trang_thai.la_thanh_ly`/`breaker.dung_han`)
    ⇒ KHÔNG đọc mạng nữa, trả nguyên trạng thái + `True` — "CỜ ĐỎ, không
    tự gỡ" nghĩa là kể cả nếu bị gọi lại (lỗi vận hành gọi nhầm), vòng này
    KHÔNG được âm thầm tiếp tục làm việc.

    Một endpoint đọc LỖI (kể cả `force_orders`) KHÔNG được suy diễn thành
    "không thanh lý" — chỉ khi đọc ĐƯỢC mới cập nhật `la_thanh_ly` (N6:
    "chưa đọc được" phải khác "đã đo và biết là False"). Trường hợp sustained
    failure (đủ lỗi liên tiếp) đã có breaker của `binance_public` xử lý
    (backoff/`dung_han`), không cần thêm cơ chế thứ hai ở đây.

    TD-0442 — cờ đỏ CẤP TÀI KHOẢN (chỉ runmode live nối hai hàm cuối): Supervisor KHÁC đã ghi cờ ⇒ `/stop` bot của mình
    ngay, trước mọi lời gọi sàn; tự mình phát hiện thanh lý / 418 ⇒ GHI cờ TRƯỚC khi `/stop` (bot kia không phải chờ
    `/stop` của mình thành công mới biết).
    """
    if trang_thai.co_do:
        return trang_thai, True

    if doc_co_do_tai_khoan_fn is not None:
        ly_do_tk = doc_co_do_tai_khoan_fn()
        if ly_do_tk is not None:
            _LOG.critical("CỜ ĐỎ TÀI KHOẢN (%s) — gọi dừng bot", ly_do_tk)
            dung_bot_fn()
            return trang_thai, True

    snap = doc_snapshot_an_toan(
        {
            "account": _boc_loi_binance(doc_account_fn),
            "position_risk": _boc_loi_binance(doc_position_fn),
            "force_orders": _boc_loi_binance(doc_force_orders_fn),
        }
    )

    breaker_moi = doc_breaker_hien_tai_fn()
    la_thanh_ly_moi = trang_thai.la_thanh_ly

    kq_force_orders = snap["force_orders"]
    if kq_force_orders.doc_duoc:
        la_thanh_ly_moi = la_thanh_ly_moi or phat_hien_thanh_ly(
            kq_force_orders.gia_tri, tu_thoi_diem_ms=tu_thoi_diem_ms
        )
    else:
        _LOG.warning("không đọc được forceOrders vòng này: %s", kq_force_orders.loi)

    # `replace` từ trạng thái cũ, KHÔNG dựng lại từ hai trường: dựng lại thì ở nhánh THANH LÝ ngay dưới, trạng thái ghi
    # xuống đĩa mất `muc_tang_chan`/`moc_halt` (bot đang HALT mà hồ sơ ghi BINH_THUONG, mất đếm HALT). Không nguy hiểm — cờ
    # đỏ vẫn bật — nhưng là hồ sơ sai. (Nhánh tầng chặn bên dưới đọc từ `trang_thai` nên không bị; phá thật TD-0434 chặng 2.)
    trang_thai_moi = replace(trang_thai, breaker=breaker_moi, la_thanh_ly=la_thanh_ly_moi)

    if trang_thai_moi.la_thanh_ly or trang_thai_moi.breaker.dung_han:
        _LOG.critical(
            "CỜ ĐỎ — la_thanh_ly=%s dung_han=%s — gọi dừng bot",
            trang_thai_moi.la_thanh_ly,
            trang_thai_moi.breaker.dung_han,
        )
        if ghi_co_do_tai_khoan_fn is not None:
            ghi_co_do_tai_khoan_fn("LIQUIDATED" if trang_thai_moi.la_thanh_ly else "BINANCE_418_DUNG_HAN")
        dung_bot_fn()
        return trang_thai_moi, True

    if tinh_dd_fn is None:  # tầng chặn sụt vốn chưa nối — `main()` luôn nối (có test AST canh)
        return trang_thai_moi, False
    return _tang_chan_sut_von(
        trang_thai, trang_thai_moi, snap["account"], tinh_dd_fn=tinh_dd_fn, tam_ngung_fn=tam_ngung_fn,
        ghi_abort_fn=ghi_abort_fn, luu_truoc_fn=luu_truoc_fn, dung_bot_fn=dung_bot_fn,
        doc_so_lenh_dong_fn=doc_so_lenh_dong_fn, mo_lai=mo_lai, now=now,
    )


@dataclass(frozen=True)
class NoiMoLai:
    """TD-0437 (§12c.5 bước 2) — mọi thứ cần để mở lại sau HALT. Thiếu bộ này ⇒ không bao giờ tự mở lại (phía an toàn)."""

    doc_so_vi_the_mo_fn: Callable[[], int]
    mo_lai_fn: Callable[[], object]
    co_xac_nhan_fn: Callable[[datetime], bool]  # nhận `luc_halt`
    cho_toi_thieu: timedelta  # 2 × max_hold_bars_4h × 4 h


def _thu_mo_lai(t: TrangThaiBenVung, mo_lai: NoiMoLai, *, now: datetime) -> tuple[TrangThaiBenVung, bool]:
    """Đủ (a)(b)(c) ⇒ `/start` rồi mức `NUA_CO` (§12c.5 BƯỚC 3). Không đủ ⇒ giữ HALT, log danh sách thiếu khi nó ĐỔI (R8).
    Cờ đỏ không tới được đây (`chay_mot_vong_giam_sat` trả sớm) — 4.4d luật 3."""
    try:
        so_mo: int | None = mo_lai.doc_so_vi_the_mo_fn()
    except FreqtradeAuthError:
        raise
    except FreqtradeControlError as exc:
        _LOG.warning("không đọc được số vị thế đang mở (%s) — chưa mở lại", exc)
        so_mo = None
    luc_het = t.luc_het_vi_the
    if so_mo == 0 and luc_het is None:
        luc_het = now
    elif so_mo is not None and so_mo > 0:
        luc_het = None
    co_xac_nhan = t.luc_halt is not None and mo_lai.co_xac_nhan_fn(t.luc_halt)
    thieu = dieu_kien_mo_lai(so_vi_the_mo=so_mo, luc_het_vi_the=luc_het, now=now,
                             cho_toi_thieu=mo_lai.cho_toi_thieu, co_xac_nhan=co_xac_nhan)
    t = replace(t, luc_het_vi_the=luc_het)
    if thieu:
        if tuple(thieu) != t.thieu_mo_lai_cuoi:
            _LOG.info("HALT — chưa mở lại, còn thiếu: %s", " | ".join(thieu))
        return replace(t, thieu_mo_lai_cuoi=tuple(thieu)), False
    try:
        mo_lai.mo_lai_fn()
    except FreqtradeAuthError:
        raise
    except FreqtradeControlError as exc:
        _LOG.critical("đủ điều kiện mở lại nhưng /start lỗi (%s) — giữ HALT, thử lại vòng sau", exc)
        return t, False
    _LOG.critical("TẦNG CHẶN SỤT VỐN: HALT → %s (đủ (a)(b)(c) §12c.5, /start) — nửa cỡ tới khi dd ≤ soft", NUA_CO)
    return replace(t, muc_tang_chan=NUA_CO, luc_halt=None, luc_het_vi_the=None, thieu_mo_lai_cuoi=()), True


def _doc_so_lenh_dong_an_toan(doc_so_lenh_dong_fn: Callable[[], int] | None) -> int | None:
    """Không có hàm / đọc lỗi ⇒ `None` (N6) — `ap_tran_halt` tính mốc `None` vào MỌI chu kỳ (phía an toàn)."""
    if doc_so_lenh_dong_fn is None:
        return None
    try:
        return doc_so_lenh_dong_fn()
    except FreqtradeAuthError:
        raise
    except FreqtradeControlError as exc:
        _LOG.warning("không đọc được số lệnh đã đóng lúc chuyển HALT (%s) — mốc None, tính vào mọi chu kỳ", exc)
        return None


def _tang_chan_sut_von(
    trang_thai: TrangThaiBenVung,
    trang_thai_moi: TrangThaiBenVung,
    kq_account,
    *,
    tinh_dd_fn: Callable[[object], float | None],
    tam_ngung_fn: Callable[[], object] | None,
    ghi_abort_fn: Callable[[], None] | None,
    luu_truoc_fn: Callable[[TrangThaiBenVung], None] | None,
    dung_bot_fn: Callable[[], object],
    doc_so_lenh_dong_fn: Callable[[], int] | None = None,
    mo_lai: NoiMoLai | None = None,
    now: datetime | None = None,
) -> tuple[TrangThaiBenVung, bool]:
    """TD-0434 (`DR-TANG-CHAN-01`, §12c.5) — phần CỨNG của thang sụt vốn cho MỌI chiến lược.

    > 20% ⇒ ABORT: LƯU cờ đỏ → `/stop` → ghi sự kiện `ABORT` vào sổ đỉnh. Thứ tự có chủ đích: ghi sự kiện trước (đặt lại
    đỉnh) mà `/stop` thất bại thì lần khởi động sau không có cờ đỏ, đỉnh đã mới ⇒ bot chạy tiếp như chưa từng sụt.
    > 8% ⇒ HALT: `/stopentry` MỖI vòng (HALT không sống qua restart bot — 4.4d luật 2). Thất bại hết lượt, hoặc lỡ bật lại
    một bot đã dừng ⇒ leo thang: LƯU cờ đỏ → `/stop`.
    Chưa đọc được account ⇒ dd `None` ⇒ giữ nguyên mức (N6); lỗi đọc kéo dài đã có breaker của `binance_public` lo.
    """
    if kq_account.doc_duoc:
        dd = tinh_dd_fn(kq_account.gia_tri)
    else:
        dd = None
        _LOG.warning("không đọc được account vòng này — giữ nguyên mức tầng chặn: %s", kq_account.loi)
    muc_moi = quyet_dinh_tang_chan(trang_thai.muc_tang_chan, dd_pct=dd)
    moc_halt = trang_thai.moc_halt
    if muc_moi == HALT and trang_thai.muc_tang_chan != HALT:  # CHUYỂN sang HALT ⇒ trần §12c.5 (TD-0434 chặng 2)
        muc_moi, moc_halt = ap_tran_halt(
            trang_thai.muc_tang_chan, muc_moi, moc_halt=moc_halt,
            so_lenh_dong=_doc_so_lenh_dong_an_toan(doc_so_lenh_dong_fn),
        )
    trang_thai_moi = replace(trang_thai_moi, muc_tang_chan=muc_moi, moc_halt=moc_halt, dd_pct_cuoi=dd)
    if muc_moi == HALT and trang_thai.muc_tang_chan != HALT:  # TD-0437: bắt đầu đồng hồ HALT mới
        trang_thai_moi = replace(trang_thai_moi, luc_halt=now, luc_het_vi_the=None, thieu_mo_lai_cuoi=())
    elif muc_moi != HALT and (trang_thai_moi.luc_halt is not None or trang_thai_moi.luc_het_vi_the is not None):
        trang_thai_moi = replace(trang_thai_moi, luc_halt=None, luc_het_vi_the=None, thieu_mo_lai_cuoi=())
    if muc_moi != trang_thai.muc_tang_chan:  # R8: log khi CHUYỂN, không lặp mỗi vòng
        _LOG.critical("TẦNG CHẶN SỤT VỐN: %s → %s (dd=%.4f%%)", trang_thai.muc_tang_chan, muc_moi, dd)

    if muc_moi == ABORT:
        if luu_truoc_fn is not None:
            luu_truoc_fn(trang_thai_moi)  # ABORT: cờ đỏ xuống đĩa TRƯỚC /stop
        dung_bot_fn()
        if ghi_abort_fn is not None:
            ghi_abort_fn()
        return trang_thai_moi, True

    if muc_moi == HALT and mo_lai is not None and now is not None:
        trang_thai_moi, da_mo = _thu_mo_lai(trang_thai_moi, mo_lai, now=now)
        if da_mo:
            return trang_thai_moi, False

    if trang_thai_moi.muc_tang_chan == HALT:
        if tam_ngung_fn is None:
            raise RiskSupervisorError("mức HALT nhưng không có tam_ngung_fn — không được lặng lẽ để bot mở lệnh")
        try:
            tam_ngung_fn()
        except FreqtradeAuthError:
            raise
        except FreqtradeControlError as exc:  # gồm `FreqtradeBatLaiBotError`
            _LOG.critical("HALT không thi hành được (%s) — leo thang /stop + cờ đỏ", exc)
            trang_thai_moi = replace(trang_thai_moi, leo_thang_dung=True)
            if luu_truoc_fn is not None:
                luu_truoc_fn(trang_thai_moi)
            dung_bot_fn()
            return trang_thai_moi, True

    return trang_thai_moi, False


#: `GET /fapi/v2/account` của tài khoản USDⓈ-M: `totalMarginBalance` tính bằng USDT (tài sản gốc) = số dư ví + lãi/lỗ CHƯA
#: chốt — đúng thước §12c.5 (`spec:4713-4714`). Đỉnh bền vững ghi bằng đơn vị này.
DON_VI_EQUITY_SAN = "USDT"


def duong_dan_dinh_supervisor(state_path: Path) -> Path:
    """Đỉnh của Supervisor nằm CẠNH file trạng thái của chính nó (`DR-TANG-CHAN-01` §4 điều 1) — mỗi Supervisor (dry-run,
    live) một thư mục, một đỉnh, một sổ sự kiện (N11). Supervisor là chủ DUY NHẤT của đỉnh này."""
    return state_path.parent / TEN_FILE_DINH


def dd_tu_account(account: object, *, duong_dan_dinh: Path) -> float | None:
    """Mức sụt % từ snapshot account, qua `equity_peak.cap_nhat_dinh()` (áp sổ `NAP_RUT`/`ABORT` của `TD-0426`).

    Không đọc được `totalMarginBalance` hoặc nó ≤ 0 ⇒ `None` (N6 — chưa đo được, không bịa). File đỉnh HỎNG ⇒ raise
    `DinhEquityError` (không tự coi là sạch — có thể đang che một đỉnh thật), daemon dừng và lộ ra.
    """
    try:
        tong = float(account["totalMarginBalance"])  # type: ignore[index]
    except (KeyError, TypeError, ValueError) as exc:
        _LOG.warning("account thiếu/sai totalMarginBalance (%s) — dd chưa đo được vòng này", exc)
        return None
    if not math.isfinite(tong) or tong <= 0:
        _LOG.warning("totalMarginBalance = %r — không lấy làm equity, dd chưa đo được vòng này", tong)
        return None
    cu = doc_dinh_equity(duong_dan_dinh)
    moi = cap_nhat_dinh(cu, tong_hien_tai=tong, stake_currency=DON_VI_EQUITY_SAN,
                        so_su_kien=duong_dan_so_su_kien(duong_dan_dinh))
    if moi != cu:
        luu_dinh_equity(moi, duong_dan_dinh)
    return max(0.0, (moi.dinh - tong) / moi.dinh * 100.0)



def equity_dry_run(balance: object, profit: object) -> float | None:
    """TD-0438 (`TD-0433`) — equity của ví giấy Freqtrade = `/balance.starting_capital` + `/profit.profit_all_coin`
    (lãi/lỗ đã chốt + CHƯA chốt, §12c.5). KHÔNG dùng `/balance.total`: lấy giá lỗi thì nó rơi lặng lẽ lãi/lỗ chưa chốt
    (`rpc.py:896-915`); `profit_all_coin` thì thành NaN (`rpc.py:556-563`) ⇒ lộ ra ⇒ ở đây trả `None` (N6)."""
    try:
        von = balance["starting_capital"]  # type: ignore[index]
        lai = profit["profit_all_coin"]  # type: ignore[index]
    except (KeyError, TypeError) as exc:
        _LOG.warning("dry-run: thiếu starting_capital/profit_all_coin (%s) — equity chưa đo được", exc)
        return None
    for ten, v in (("starting_capital", von), ("profit_all_coin", lai)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            _LOG.warning("dry-run: %s = %r (NaN/null ⇔ có vị thế lấy giá lỗi) — equity chưa đo được", ten, v)
            return None
    return float(von) + float(lai)


def _boc_loi_freqtrade(ham: Callable[[], object]) -> Callable[[], object]:
    """Cùng vai `_boc_loi_binance`: `doc_snapshot_an_toan` chỉ cô lập `RiskSupervisorError`. 401 KHÔNG bọc — lỗi cấu hình
    phải làm daemon dừng và lộ ra, không thành một vòng "chưa đọc được" lặp mãi."""

    def goi() -> object:
        try:
            return ham()
        except FreqtradeAuthError:
            raise
        except FreqtradeControlError as exc:
            raise RiskSupervisorError(str(exc)) from exc

    return goi


#: TD-0437 (§12c.5 bước 2 (c)) — người vận hành xác nhận đã đọc `periodic_report.py` của kỳ HALT (không phải phê duyệt).
#: Một dòng riêng trong `docs/research-log.md`: `XAC_NHAN_MO_LAI_HALT <runmode> <yyyy-mm-dd>` — ngày ≥ ngày HALT (UTC).
DUONG_DAN_RESEARCH_LOG = Path("docs/research-log.md")
_DONG_XAC_NHAN = re.compile(r"^XAC_NHAN_MO_LAI_HALT (live|dry_run) (\d{4}-\d{2}-\d{2})\s*$")


def co_xac_nhan_mo_lai(duong_log: Path, *, runmode: str, luc_halt: datetime) -> bool:
    """Có dòng xác nhận cho ĐÚNG runmode, ngày ≥ ngày HALT? Không đọc được file ⇒ `False` (chưa xác nhận — N6)."""
    try:
        noi_dung = duong_log.read_text(encoding="utf-8")
    except OSError as exc:
        _LOG.warning("không đọc được %s (%s) — coi như chưa xác nhận mở lại", duong_log, exc)
        return False
    ngay_halt = luc_halt.astimezone(timezone.utc).date()
    for dong in noi_dung.splitlines():
        m = _DONG_XAC_NHAN.match(dong.strip())
        if m and m.group(1) == runmode:
            try:
                if datetime.strptime(m.group(2), "%Y-%m-%d").date() >= ngay_halt:
                    return True
            except ValueError:
                continue
    return False


def ghi_su_kien_abort(duong_dan_dinh: Path, *, now: datetime) -> None:
    """ABORT ⇒ một dòng `ABORT` trong sổ đỉnh (`DR-D6D8-01` §4.2 sự kiện (b)): chu trình giả thuyết mới bắt đầu với đỉnh mới."""
    ghi_su_kien(
        duong_dan_so_su_kien(duong_dan_dinh),
        SuKienDinh(loai=SU_KIEN_ABORT, stake_currency=DON_VI_EQUITY_SAN, luc_utc=now.isoformat(),
                   ghi_chu="Risk Supervisor: dd > dd_abort_pct (§12c.5) — ABORT, cờ đỏ, bot đã /stop"),
    )


@dataclass(frozen=True)
class ThamSoCli:
    runmode: str
    state_path: Path
    chu_ky_s: float
    freqtrade_api_base_url: str
    max_iterations: int | None


def _doc_tham_so(argv: list[str] | None) -> ThamSoCli:
    parser = argparse.ArgumentParser(description="TD-0241 — Risk Supervisor daemon (§6.6)")
    parser.add_argument("--runmode", required=True, choices=RUNMODE_CO_SUPERVISOR,
                        help="TD-0435: live (sàn thật) hay dry_run (ví giấy của Freqtrade, TD-0438)")
    parser.add_argument("--state-path", type=Path, default=None,
                        help="mặc định runs/risk_supervisor/<runmode>/state.json")
    parser.add_argument("--chu-ky-s", type=float, default=DEFAULT_CHU_KY_S)
    parser.add_argument("--freqtrade-api-base-url", default=DEFAULT_FREQTRADE_API_BASE_URL)
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Giới hạn số vòng lặp (R5, bounded loop) — dùng cho test/smoke test. "
        "Bỏ trống = chạy tới khi bị dừng hoặc gặp cờ đỏ.",
    )
    args = parser.parse_args(argv)
    return ThamSoCli(
        runmode=args.runmode,
        state_path=args.state_path if args.state_path is not None else duong_dan_theo_runmode(args.runmode),
        chu_ky_s=args.chu_ky_s,
        freqtrade_api_base_url=args.freqtrade_api_base_url,
        max_iterations=args.max_iterations,
    )


def main(argv: list[str] | None = None) -> int:  # pragma: no cover — khung CLI, xem test cho chay_mot_vong_giam_sat
    logging.basicConfig(level=logging.INFO)
    tham_so = _doc_tham_so(argv)
    # Cạnh file trạng thái; với đường mặc định trùng đúng `tang_chan.duong_dan_dd_state(runmode)` mà chiến lược đọc.
    duong_dd_state = tham_so.state_path.parent / TEN_FILE_DD_STATE
    la_dry_run = tham_so.runmode == "dry_run"

    def _co_do_tai_khoan() -> str | None:  # TD-0442 — chỉ live có tài khoản sàn
        return None if la_dry_run else doc_co_do_tai_khoan(DUONG_DAN_CO_DO_TAI_KHOAN)

    def _cong_bo(t: TrangThaiBenVung) -> None:
        # TD-0435 — MỖI vòng (kể cả khi không đổi: mốc giờ tươi là bằng chứng Supervisor còn sống cho chiến lược đọc).
        ghi_dd_state(duong_dd_state, muc=t.muc_tang_chan, dd_pct=t.dd_pct_cuoi,
                     co_do=t.co_do or _co_do_tai_khoan() is not None, now=datetime.now(timezone.utc))
    api_key = api_secret = ""
    if not la_dry_run:  # TD-0438: dry-run là ví giấy của Freqtrade — không có tài khoản sàn để đọc, không cần key Binance
        try:
            api_key, api_secret = validate_credentials_for_live()  # fail-closed, 0 byte ra mạng nếu thiếu
        except BinanceCredentialsMissingError as exc:
            _LOG.critical(str(exc))
            return EXIT_MISSING_API_CREDENTIALS

    ft_username = os.environ.get(ENV_FT_USERNAME, "")
    ft_password = os.environ.get(ENV_FT_PASSWORD, "")
    if not ft_username or not ft_password:
        _LOG.critical("thiếu %s/%s — daemon không thể dừng bot khi cần", ENV_FT_USERNAME, ENV_FT_PASSWORD)
        return EXIT_MISSING_FREQTRADE_CREDENTIALS

    cfg = load_tool_d_config()
    lech = kiem_khai_lai_khop_ban_goc(cfg, doc_resolve=resolve)
    if lech:
        for dong in lech:
            _LOG.critical("L-Z44 lệch: %s", dong)
        return EXIT_L44_MISMATCH

    trang_thai = doc_trang_thai(tham_so.state_path)
    co_tk_luc_dau = _co_do_tai_khoan()
    if co_tk_luc_dau is not None:
        _cong_bo(trang_thai)
        _LOG.critical("cờ đỏ TÀI KHOẢN (%s) — KHÔNG khởi động, cần can thiệp thủ công (%s)", co_tk_luc_dau,
                      DUONG_DAN_CO_DO_TAI_KHOAN)
        return EXIT_CO_DO_TU_LAN_CHAY_TRUOC
    if trang_thai.co_do:
        _cong_bo(trang_thai)  # chiến lược thấy cờ đỏ NGAY, không đợi file cũ quá hạn
        _LOG.critical(
            "cờ đỏ đã ghi từ lần chạy trước (%s) — KHÔNG tự khởi động lại, cần can thiệp thủ công",
            tham_so.state_path,
        )
        return EXIT_CO_DO_TU_LAN_CHAY_TRUOC

    tu_thoi_diem_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    duong_dan_dinh = duong_dan_dinh_supervisor(tham_so.state_path)
    # TD-0434: bản MỚI NHẤT đã lưu. `luu_truoc_fn` lưu cờ đỏ TRƯỚC khi gọi /stop; nếu /stop thất bại, nhánh except dưới
    # phải lưu lại ĐÚNG bản này — lưu `trang_thai` (bản đầu vòng) sẽ ghi đè mất cờ đỏ vừa đặt.
    da_luu: list[TrangThaiBenVung] = [trang_thai]

    def _luu_truoc(t: TrangThaiBenVung) -> None:
        luu_trang_thai(t, tham_so.state_path)
        da_luu[0] = t

    # TD-0437 — "2 × max_hold_bars" (§12c.5 bước 2 (b)): Tầng B, đọc qua `resolve()` (daemon được phép import cấu hình,
    # §6.6(2) chỉ cấm code bot) — KHÔNG khai lại: Tầng B chỉnh được, bản khai lại sẽ lệch âm thầm.
    mo_lai = NoiMoLai(
        doc_so_vi_the_mo_fn=lambda: doc_so_vi_the_mo(
            tham_so.freqtrade_api_base_url, username=ft_username, password=ft_password
        ),
        mo_lai_fn=lambda: mo_lai_bot(tham_so.freqtrade_api_base_url, username=ft_username, password=ft_password),
        co_xac_nhan_fn=lambda luc_halt: co_xac_nhan_mo_lai(
            DUONG_DAN_RESEARCH_LOG, runmode=tham_so.runmode, luc_halt=luc_halt
        ),
        cho_toi_thieu=timedelta(hours=4 * 2 * int(resolve(cfg, "tier_b.max_hold_bars_4h"))),
    )

    if la_dry_run:
        # TD-0438 — dựng "account" có ĐÚNG trường `totalMarginBalance` từ ví giấy ⇒ `dd_tu_account`/đỉnh/sổ sự kiện dùng
        # lại NGUYÊN, không nhánh tính thứ hai. Ví giấy không có thanh lý thật, không có breaker Binance ⇒ rỗng tường minh.
        def _account_dry_run() -> object:
            eq = equity_dry_run(
                doc_json_get(tham_so.freqtrade_api_base_url, "/api/v1/balance", username=ft_username, password=ft_password),
                doc_json_get(tham_so.freqtrade_api_base_url, "/api/v1/profit", username=ft_username, password=ft_password),
            )
            return {} if eq is None else {"totalMarginBalance": eq}

        doc_account_fn = _boc_loi_freqtrade(_account_dry_run)
        doc_position_fn = lambda: []  # noqa: E731
        doc_force_orders_fn = lambda: []  # noqa: E731
        doc_breaker_fn = TrangThaiBreaker
    else:
        doc_account_fn = lambda: get_account_info(api_key=api_key, api_secret=api_secret)  # noqa: E731
        doc_position_fn = lambda: get_position_risk(api_key=api_key, api_secret=api_secret)  # noqa: E731
        doc_force_orders_fn = lambda: get_force_orders(  # noqa: E731
            api_key=api_key, api_secret=api_secret, start_time_ms=tu_thoi_diem_ms
        )
        doc_breaker_fn = trang_thai_breaker_hien_tai

    vong = 0
    while tham_so.max_iterations is None or vong < tham_so.max_iterations:
        da_luu[0] = trang_thai
        try:
            trang_thai, nen_dung = chay_mot_vong_giam_sat(
                trang_thai,
                now=datetime.now(timezone.utc),
                doc_account_fn=doc_account_fn,
                doc_position_fn=doc_position_fn,
                doc_force_orders_fn=doc_force_orders_fn,
                doc_breaker_hien_tai_fn=doc_breaker_fn,
                tu_thoi_diem_ms=tu_thoi_diem_ms,
                dung_bot_fn=lambda: dung_bot(
                    tham_so.freqtrade_api_base_url, username=ft_username, password=ft_password
                ),
                # TD-0434 (`DR-TANG-CHAN-01`) — tầng chặn sụt vốn cho MỌI chiến lược. Có test AST canh bốn khoá này.
                tinh_dd_fn=lambda account: dd_tu_account(account, duong_dan_dinh=duong_dan_dinh),
                tam_ngung_fn=lambda: tam_ngung_mo_lenh(
                    tham_so.freqtrade_api_base_url, username=ft_username, password=ft_password
                ),
                ghi_abort_fn=lambda: ghi_su_kien_abort(duong_dan_dinh, now=datetime.now(timezone.utc)),
                luu_truoc_fn=_luu_truoc,
                doc_so_lenh_dong_fn=lambda: doc_so_lenh_dong(
                    tham_so.freqtrade_api_base_url, username=ft_username, password=ft_password
                ),
                mo_lai=mo_lai,  # TD-0437 — mở lại sau HALT (§12c.5 bước 2–4)
                # TD-0442 — cờ đỏ cấp tài khoản: dry-run (ví giấy) không nối.
                doc_co_do_tai_khoan_fn=None if la_dry_run else _co_do_tai_khoan,
                ghi_co_do_tai_khoan_fn=None if la_dry_run else (
                    lambda ly_do: ghi_co_do_tai_khoan(DUONG_DAN_CO_DO_TAI_KHOAN, ly_do=ly_do,
                                                      nguon=str(tham_so.state_path), now=datetime.now(timezone.utc))
                ),
            )
        except FreqtradeControlError as exc:
            # KHÔNG nuốt: "không dừng được bot khi tài khoản đã thanh lý"
            # là sự kiện nghiêm trọng nhất có thể — ghi trạng thái ĐÃ CÓ
            # (nếu vòng trước đã đặt cờ) rồi thoát khác 0, không lặng lẽ
            # tiếp tục vòng lặp coi như chưa có gì xảy ra.
            _LOG.critical("KHÔNG dừng được bot qua Freqtrade API: %s", exc)
            luu_trang_thai(da_luu[0], tham_so.state_path)
            _cong_bo(da_luu[0])
            return EXIT_KHONG_DUNG_DUOC_BOT
        luu_trang_thai(trang_thai, tham_so.state_path)
        _cong_bo(trang_thai)
        vong += 1

        if nen_dung:
            _LOG.critical(
                "Risk Supervisor DỪNG sau %d vòng — la_thanh_ly=%s dung_han=%s muc_tang_chan=%s leo_thang_dung=%s",
                vong,
                trang_thai.la_thanh_ly,
                trang_thai.breaker.dung_han,
                trang_thai.muc_tang_chan,
                trang_thai.leo_thang_dung,
            )
            return EXIT_DA_DUNG_VI_CO_DO

        if tham_so.max_iterations is None or vong < tham_so.max_iterations:
            time.sleep(tham_so.chu_ky_s)

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
