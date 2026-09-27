"""§6.6 — Risk Supervisor (TD-0196, OQ-09).

Tiến trình GIÁM SÁT RIÊNG của Tool D — đọc TRỰC TIẾP margin/vị thế từ
sàn, KHÔNG import code bot (§6.6 ràng buộc 2). File này CHỈ dựng tầng
THUẦN (phân loại lỗi, state machine circuit breaker, đối chiếu hằng số
khai lại) — theo đúng khuôn đã dùng cho mọi module khác của dự án
(`sizing.py`, `admission.py`, `take_profit.py`...): hàm thuần trước,
nối vào một tiến trình/entrypoint thật là việc SAU, khi tới gần D10/D11
(dry-run) — Risk Supervisor không cần CHẠY THẬT ở D4 (backtest-only),
chỉ cần TỒN TẠI và có phép kiểm để không bị quên tới lúc cần.

🔴 **KHÔNG được thêm entrypoint thứ 9** (L-Z36, N3). ✅ **Đã chốt**
(`DR-D11-03`, TD-0241): tiến trình chạy dạng module độc lập
`src/tool_d/ops/risk_supervisor_daemon.py` (cùng khuôn `heartbeat_watchdog.py`
của TD-0209) — script riêng ngoài `entrypoints/`, không phải một chế độ
của entrypoint có sẵn, không phải service Docker dài hạn mới.

════ Bốn ràng buộc vận hành (§6.6, LD-22/23/26) — module này phủ đến đâu ════

(1) SL sống trên sàn — KHÔNG thuộc phạm vi file này (đã đúng ở tầng
    chiến lược: `custom_stoploss`/`stoploss_from_absolute`, TD-0187).
(2) Supervisor không import code bot — `HANG_SO_KHAI_LAI` bên dưới là
    NGOẠI LỆ HỢP LỆ DUY NHẤT của "một nguồn sự thật" (LD-09), có ghi
    chú tường minh + `kiem_khai_lai_khop_ban_goc()` (L-Z44) đối chiếu
    với `tool_d_config.yaml` — hai bản khai PHẢI bằng nhau. `LIQUIDATED`
    là cờ dừng toàn hệ thống — `trang_thai_tai_khoan()` trả tri-state,
    KHÔNG bao giờ coi "chưa đọc được" là "OK" (N6).
(3) Trần API + phân tầng lùi giờ — `TranBreaker`/`ghi_nhan_ket_qua()`.
(4) Một endpoint lỗi không hỏng cả snapshot — `doc_snapshot_an_toan()`.

════ OQ-09 — hai số đã chốt (09/09/2026, TD-0196) ════

`api-integration-rules.md` Mục 4.4 đã xác nhận: **5 lỗi liên tiếp** kích
hoạt breaker, backoff **1s → 2s → 4s → … → 60s** (nhân đôi, kẹp trần).
Đây là tham số VẬN HÀNH (đọc từ ENV, xem `doc_nguong_breaker()`) — theo
N4/§0d.4, KHÔNG phải tham số tín hiệu Tầng B/C, nên KHÔNG qua `resolve()`
của `tool_d_config.yaml` và KHÔNG tính vào `N_ĐĂNG_KÝ`/DOF.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path

NGUONG_BREAKER_MAC_DINH = 5
BACKOFF_KHOI_DIEM_S = 1.0
BACKOFF_TOI_DA_S = 60.0

_ENV_NGUONG = "TOOLD_BREAKER_THRESHOLD"


class RiskSupervisorError(ValueError):
    """Lỗi cấu hình/đầu vào của tầng giám sát — fail-closed, không đoán."""


def doc_nguong_breaker(*, env: Mapping[str, str] | None = None) -> int:
    """§6.9.5/N4 — ngưỡng breaker là tham số VẬN HÀNH, đọc từ ENV, KHÔNG
    từ `tool_d_config.yaml` (đó là Tầng B/C, cấm đọc qua env — L-Z39;
    ở ĐÂY là chiều ngược lại: một tham số VẬN HÀNH đọc qua ENV là ĐÚNG
    chỗ của nó, không phải một vi phạm N4).

    Thiếu biến ENV → dùng mặc định `NGUONG_BREAKER_MAC_DINH` (đã chốt
    OQ-09/TD-0196) — khác các tham số TÍN HIỆU (không được mặc định);
    một tham số vận hành thiếu thì hệ thống vẫn phải chạy AN TOÀN chứ
    không phải dừng lại đòi khai, nên có giá trị đã chốt sẵn làm nền.
    """
    raw = (env if env is not None else os.environ).get(_ENV_NGUONG)
    if raw is None or raw == "":
        return NGUONG_BREAKER_MAC_DINH
    try:
        n = int(raw)
    except ValueError as exc:
        raise RiskSupervisorError(f"{_ENV_NGUONG}={raw!r} không phải số nguyên") from exc
    if n < 1:
        raise RiskSupervisorError(f"{_ENV_NGUONG}={n} phải >= 1")
    return n


# ═══════════════════════════════════════════════════════════════════
# R4 — phân loại lỗi (Mục 4.3 của api-integration-rules.md)
# ═══════════════════════════════════════════════════════════════════

RETRY = "retry"
DUNG_HAN = "dung_han"  # §6.6(1)(2) — CỜ ĐỎ, cùng cấp LIQUIDATED, KHÔNG tự phục hồi
LOI_LOGIC = "loi_logic"  # không retry — dừng đúng thao tác đó, ghi Decision Log
KHONG_NHAN_DIEN = "khong_nhan_dien"  # mã lỗi CHƯA có trong bảng — xử như LOI_LOGIC
# nhưng gắn nhãn RIÊNG để không âm thầm trộn vào các mã đã được cân nhắc
# kỹ (N6: "không đo được" phải tách khỏi "đã đo và biết là logic lỗi").

_RETRY_HTTP = {429}
_RETRY_MA = {-1003, -1015}
_DUNG_HAN_HTTP = {418}
_LOI_LOGIC_MA = {-1121, -2010, -2011, -2019}


def phan_loai_ma_loi(*, http_status: int | None = None, ma_binance: int | None = None) -> str:
    """Trả về một trong `RETRY` / `DUNG_HAN` / `LOI_LOGIC` /
    `KHONG_NHAN_DIEN`, theo ĐÚNG bảng Mục 4.3 — không phải đoán.

    `http_status`/`ma_binance` — CHỈ MỘT trong hai được truyền có nghĩa
    (một request lỗi mang MỘT trong hai kiểu mã); truyền cả hai NaN/None
    là RAISE, không đoán bên nào để đọc (N6, cùng chốt `KetQuaSan.ly_do`
    của `notional.py`).
    """
    if http_status is None and ma_binance is None:
        raise RiskSupervisorError("phải truyền http_status hoặc ma_binance — không có gì để phân loại")
    if http_status is not None:
        if http_status in _RETRY_HTTP or (500 <= http_status < 600):
            return RETRY
        if http_status in _DUNG_HAN_HTTP:
            return DUNG_HAN
        if ma_binance is None:
            return KHONG_NHAN_DIEN
    if ma_binance is not None:
        if ma_binance in _RETRY_MA:
            return RETRY
        if ma_binance in _LOI_LOGIC_MA:
            return LOI_LOGIC
    return KHONG_NHAN_DIEN


# ═══════════════════════════════════════════════════════════════════
# R3 — Circuit breaker (state machine THUẦN, không tự gọi mạng)
# ═══════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class TrangThaiBreaker:
    """Bất biến — mọi hàm bên dưới trả về TRẠNG THÁI MỚI, không sửa tại chỗ
    (cùng kỷ luật `KeHoachTranche`/`KeHoachChotLoi` — dễ kiểm bằng cách so
    hai giá trị, không cần lo về alias)."""

    so_loi_lien_tiep: int = 0
    dung_han: bool = False  # §6.6(1)(2) — CỜ ĐỎ, MANUAL reset, không tự gỡ
    mo_tam: bool = False  # breaker đang mở (backoff), tự đóng lại khi hết backoff
    thoi_diem_mo: datetime | None = None
    backoff_s: float = 0.0

    def duoc_phep_goi(self, *, now: datetime) -> bool:
        """`False` khi: đã `dung_han` (chỉ gỡ bằng can thiệp người — không
        có hàm nào trong file này tự đưa `dung_han` về `False`), HOẶC
        đang trong cửa sổ backoff của lần mở gần nhất."""
        if self.dung_han:
            return False
        if not self.mo_tam or self.thoi_diem_mo is None:
            return True
        return now >= self.thoi_diem_mo + timedelta(seconds=self.backoff_s)


def _backoff_ke_tiep(hien_tai: float) -> float:
    ke = BACKOFF_KHOI_DIEM_S if hien_tai <= 0 else hien_tai * 2.0
    return min(ke, BACKOFF_TOI_DA_S)


def ghi_nhan_ket_qua(
    trang_thai: TrangThaiBreaker,
    loai_loi: str | None,
    *,
    now: datetime,
    nguong: int = NGUONG_BREAKER_MAC_DINH,
) -> TrangThaiBreaker:
    """`loai_loi=None` nghĩa là GỌI THÀNH CÔNG — reset về sạch. Khác các
    hàm khác trong dự án cấm giá trị lính canh (N6): ở ĐÂY `None` KHÔNG
    phải "chưa đo được" mà là "đã đo, và câu trả lời là không có lỗi" —
    một sự thật rõ ràng, không phải một khoảng trống.

    🔴 `DUNG_HAN` (418, cùng cấp `LIQUIDATED`) đặt cờ **VĨNH VIỄN** trong
    trạng thái trả về — không có hàm nào ở đây tự gỡ nó, đúng chữ spec
    dòng 1965 *"CỜ ĐỎ DỪNG TOÀN HỆ THỐNG, không phải dòng log cảnh báo"*.
    `LOI_LOGIC`/`KHONG_NHAN_DIEN` KHÔNG cộng vào bộ đếm breaker — bảng
    Mục 4.3 đã nói "không retry" cho từng lỗi ĐÓ, không phải một tín hiệu
    về SỨC KHOẺ kết nối (đó là việc của `RETRY`); cộng nhầm vào đây sẽ mở
    breaker vì một lỗi logic lặp lại (ví dụ định cỡ sai liên tục), che
    mất nguyên nhân thật.
    """
    if trang_thai.dung_han:
        return trang_thai  # đã dừng hẳn — không có gì để cập nhật thêm

    if loai_loi == DUNG_HAN:
        return replace(trang_thai, dung_han=True, mo_tam=False)

    if loai_loi in (LOI_LOGIC, KHONG_NHAN_DIEN):
        return trang_thai  # không đụng bộ đếm breaker — xem docstring

    if loai_loi is None:  # thành công
        return TrangThaiBreaker()

    if loai_loi != RETRY:
        raise RiskSupervisorError(f"loai_loi lạ: {loai_loi!r}")

    so_loi = trang_thai.so_loi_lien_tiep + 1
    if so_loi < nguong:
        return replace(trang_thai, so_loi_lien_tiep=so_loi)

    backoff = _backoff_ke_tiep(trang_thai.backoff_s if trang_thai.mo_tam else 0.0)
    return TrangThaiBreaker(so_loi_lien_tiep=so_loi, mo_tam=True, thoi_diem_mo=now, backoff_s=backoff)


# ═══════════════════════════════════════════════════════════════════
# §6.6(2) — khai lại CÓ CHỦ ĐÍCH (ngoại lệ hợp lệ duy nhất của LD-09)
# ═══════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class HangSoKhaiLai:
    e_d: float
    dd_soft_pct: float
    dd_halt_pct: float
    dd_abort_pct: float
    tran_margin_ty_le: float  # 0.85 — xem §6.8f
    tran_halt_so_lan: int  # TD-0434 — §12c.5: số lần HALT tối đa trong một chu kỳ; lần kế tiếp ⇒ ABORT
    chu_ky_lenh_dong: int  # TD-0434 — §12c.1: một chu kỳ = khối cố định bao nhiêu lệnh đã đóng


# 🔴 KHAI LẠI CÓ CHỦ ĐÍCH — §6.6(2): "Supervisor KHÔNG import code bot",
# nên các con số này KHÔNG đọc qua `tool_d_config.loader.resolve()` (đó
# sẽ là import ngầm cả cây cấu hình + logic của bot). Đây là NGOẠI LỆ
# HỢP LỆ DUY NHẤT của nguyên tắc "một nguồn sự thật" — spec tự cho phép,
# với điều kiện có test đối chiếu hai bản khai bằng nhau (L-Z44, dưới).
# 🔑 Không lấy giá trị TRỰC TIẾP từ `tool_d_config.yaml` string-match —
# nếu làm vậy thì "khai lại" chỉ còn là đổi tên biến của MỘT nguồn, mất
# hết ý nghĩa "độc lập" mà ràng buộc (2) đòi.
HANG_SO_KHAI_LAI = HangSoKhaiLai(
    e_d=750.0,  # DR-D4-05, thay DR-D0PRE-06
    dd_soft_pct=5.0,  # DR-D0PRE-04
    dd_halt_pct=8.0,  # DR-D0PRE-04 (== tier_a.daily_loss_budget_pct)
    dd_abort_pct=20.0,  # DR-D0PRE-04
    tran_margin_ty_le=0.85,  # §6.8f
    tran_halt_so_lan=3,  # spec:4756 — DR-TANG-CHAN-01 §8 (a)
    chu_ky_lenh_dong=100,  # spec:4756 + §12c.1 — DR-TANG-CHAN-01 §8 (a)
)


def kiem_khai_lai_khop_ban_goc(
    cfg_that: Mapping[str, object], *, doc_resolve: Callable[[Mapping[str, object], str], object]
) -> list[str]:
    """L-Z44 — đối chiếu `HANG_SO_KHAI_LAI` với bản THẬT trong
    `tool_d_config.yaml`. Trả về danh sách CHỖ LỆCH (rỗng = khớp).

    Nhận `doc_resolve` qua tham số (thường là `tool_d.config.loader.
    resolve`) thay vì `import` thẳng ở đầu file — nhánh test gọi hàm này
    ĐANG import `resolve` để lấy giá trị đối chiếu, đó là hợp lệ (test
    không phải "code bot"); nhưng MODULE này (`risk_supervisor.py`) tự
    nó không `import tool_d.config.loader` ở top-level, giữ đúng chữ
    "supervisor không import code bot" cho phần SẢN XUẤT.
    """
    lech: list[str] = []
    #: 🔴 PHẢI phủ ĐỦ mọi trường của `HangSoKhaiLai` — §6.6(2) liệt kê bốn
    #: thứ (`E_D`, thang dd 5/8/20, trần margin 0.85) và cái làm cho ngoại
    #: lệ LD-09 này HỢP LỆ chính là phép đối chiếu, nên một trường khai lại
    #: mà KHÔNG có dòng ở đây là ngoại lệ mất đúng thứ biện minh cho nó.
    #: `L-Z44` có một ca ghim quan hệ đó bằng `dataclasses.fields()`, để
    #: thêm hằng số thứ sáu mà quên đối chiếu thì suite báo đỏ, không im.
    #: (TD-0241: `tran_margin_ty_le` đã khai từ TD-0196 nhưng KHÔNG được
    #: đối chiếu — đúng khoảng hở đó, phát hiện khi viết `L-Z44`.)
    doi_chieu = (
        ("e_d", "tier_a.E_D"),
        ("dd_soft_pct", "tier_c.dd_ladder_pct.soft"),
        ("dd_halt_pct", "tier_c.dd_ladder_pct.halt"),
        ("dd_abort_pct", "tier_c.dd_ladder_pct.abort"),
        # §6.8f là GỐC của 0,85; `tier_frozen.mult_deploy_thr` là bên MƯỢN
        # (xem `admission.py:80-88`). Đối chiếu qua đúng đường mà
        # `TRAN_MARGIN_TREN_E_D` đã bị ghim (`test_admission.py:148`) —
        # KHÔNG thêm khoá YAML mới, vì đó là nguồn sự thật thứ ba cho cùng
        # một số (bài học MT-03) và sẽ đụng kế toán DOF.
        ("tran_margin_ty_le", "tier_frozen.mult_deploy_thr.value"),
        ("tran_halt_so_lan", "tier_c.tran_halt.so_lan"),  # TD-0434, DR-TANG-CHAN-01 §8 (a)
        ("chu_ky_lenh_dong", "tier_c.tran_halt.chu_ky_lenh_dong"),
    )
    for truong, duong_dan in doi_chieu:
        that = float(doc_resolve(cfg_that, duong_dan))
        khai = float(getattr(HANG_SO_KHAI_LAI, truong))
        if not math.isclose(that, khai, rel_tol=1e-9):
            lech.append(f"{truong}: khai lại {khai} != tool_d_config.yaml {duong_dan}={that}")
    return lech


# ═══════════════════════════════════════════════════════════════════
# §6.6(1)(2) — trạng thái tài khoản: OK / LIQUIDATED / unreadable (N6)
# ═══════════════════════════════════════════════════════════════════

OK = "OK"
LIQUIDATED = "LIQUIDATED"
UNREADABLE = "unreadable"


def trang_thai_tai_khoan(*, la_thanh_ly: bool | None) -> str:
    """`la_thanh_ly` do TẦNG GỌI xác định từ dữ liệu sàn thật (dấu hiệu
    lệnh `LIQUIDATION` trên user data stream / REST — CHƯA verify chính
    xác tên trường Binance trong phiên này, xem TODO cuối module) — hàm
    này CHỈ làm phần phân loại tri-state, không tự đọc mạng.

    `None` (không xác định được) → `unreadable`, KHÔNG BAO GIỜ `OK` — N6:
    im lặng ở đây là gộp "không biết" vào "an toàn", đúng chiều fail-OPEN
    nguy hiểm nhất có thể có cho một cờ mang tên §6.6 gọi là "CỜ ĐỎ".
    """
    if la_thanh_ly is None:
        return UNREADABLE
    return LIQUIDATED if la_thanh_ly else OK


# ═══════════════════════════════════════════════════════════════════
# §6.6(4) — một endpoint lỗi không hỏng cả snapshot
# ═══════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class KetQuaEndpoint:
    ten: str
    gia_tri: object | None
    loi: str | None  # None = đọc được; ngược lại là mô tả lỗi (đã phân loại ở tầng gọi)

    @property
    def doc_duoc(self) -> bool:
        return self.loi is None


def doc_snapshot_an_toan(doc: Mapping[str, Callable[[], object]]) -> dict[str, KetQuaEndpoint]:
    """Gọi từng hàm đọc trong `doc` (khoá = tên endpoint), CÔ LẬP lỗi theo
    TỪNG endpoint — một endpoint raise KHÔNG được làm mất kết quả của các
    endpoint khác đã đọc thành công (§6.6(4)).

    🔴 Không bắt `Exception` trần — chỉ bắt lỗi mà tầng gọi đã đóng gói
    thành thông tin đọc được (`RiskSupervisorError` hoặc bất kỳ lỗi nào
    hàm đọc chủ động raise); lỗi lập trình thật (`TypeError`, `KeyError`
    do code tầng gọi sai) KHÔNG nên bị nuốt thành "unreadable" — nuốt
    silent một bug thật là đúng thứ MT-16(vii) đã cắn cả dự án một lần.
    Vì vậy chỉ bắt `RiskSupervisorError` + các lỗi mạng/timeout điển hình
    caller khai qua chính callable (không mở rộng danh sách ở đây mà
    không có lý do bằng chữ).
    """
    ra: dict[str, KetQuaEndpoint] = {}
    for ten, ham in doc.items():
        try:
            ra[ten] = KetQuaEndpoint(ten=ten, gia_tri=ham(), loi=None)
        except (RiskSupervisorError, TimeoutError, ConnectionError) as exc:
            ra[ten] = KetQuaEndpoint(ten=ten, gia_tri=None, loi=str(exc))
    return ra


# ═══════════════════════════════════════════════════════════════════
# TD-0241 (DR-D11-03) — phát hiện thanh lý + bền vững hoá trạng thái
# ═══════════════════════════════════════════════════════════════════


def phat_hien_thanh_ly(
    force_orders: Sequence[Mapping[str, object]], *, tu_thoi_diem_ms: int
) -> bool:
    """Đóng TODO (1) cũ: nguồn xác nhận thanh lý là REST
    `GET /fapi/v1/forceOrders?autoCloseType=LIQUIDATION` (xác nhận qua mã
    nguồn `ccxt`, `DR-D11-03` §2.4) — KHÔNG cần user data stream WebSocket
    (quyết định đã chốt, xem DR). `autoCloseType` là bộ lọc phía SERVER,
    nên bất kỳ phần tử nào trong `force_orders` (đã được tầng gọi lọc đúng
    filter đó) ⇒ ĐÃ có lệnh bị thanh lý.

    Hàm THUẦN — không tự gọi mạng. Tầng gọi (daemon) chỉ được truyền vào
    đây kết quả ĐÃ ĐỌC ĐƯỢC (`KetQuaEndpoint.doc_duoc is True` từ
    `doc_snapshot_an_toan()`); đọc lỗi/timeout phải đi thẳng
    `trang_thai_tai_khoan(la_thanh_ly=None)` → `unreadable`, KHÔNG BAO GIỜ
    gọi hàm này với dữ liệu rỗng-vì-lỗi rồi đọc kết quả `False` thành "an
    toàn" (N6 — gộp "không đọc được" vào "OK" là fail-OPEN trên đúng cờ
    §6.6(2) gọi là "CỜ ĐỎ").
    """
    for lenh in force_orders:
        thoi_diem = lenh.get("time")
        if thoi_diem is None:
            raise RiskSupervisorError(f"bản ghi forceOrders thiếu trường 'time': {lenh!r}")
        if int(thoi_diem) >= tu_thoi_diem_ms:
            return True
    return False


@dataclass(frozen=True)
class TrangThaiBenVung:
    """Phần trạng thái PHẢI sống sót qua khởi động lại tiến trình — bài học
    `MT-40`/`MT-41` (đỉnh equity/kế hoạch cỡ lệnh chỉ sống trong RAM, mất
    sạch mỗi lần restart, vô hiệu hoá một tầng Cấp C). `la_thanh_ly` là
    tri-state ĐÃ CHỐT (không phải lần đọc mới nhất) — một khi `True` thì
    KHÔNG hàm nào trong file này tự gỡ, đúng "CỜ ĐỎ, không tự phục hồi".
    """

    breaker: TrangThaiBreaker
    la_thanh_ly: bool = False
    #: TD-0434 (`DR-TANG-CHAN-01`) — mức tầng chặn sụt vốn: `BINH_THUONG` / `HALT` / `ABORT`. `ABORT` là cờ đỏ, không tự gỡ.
    muc_tang_chan: str = "BINH_THUONG"
    #: TD-0434 — `/stopentry` thất bại hết lượt (hoặc lỡ bật lại bot) nên đã leo thang `/stop`: cờ đỏ, không tự gỡ.
    leo_thang_dung: bool = False
    #: TD-0434 chặng 2 — số lệnh ĐÃ ĐÓNG tại mỗi lần CHUYỂN sang HALT (trần §12c.5); `None` = lúc đó không đọc được số lệnh.
    moc_halt: tuple[int | None, ...] = ()
    #: TD-0435 — mức sụt % đo ở vòng GẦN NHẤT, để daemon công bố vào `dd_state.json`. CHỈ trong bộ nhớ, KHÔNG ghi đĩa
    #: (`luu_trang_thai` bỏ qua): số cũ sau restart không được đọc lại như số mới (N6 — thà để trống).
    dd_pct_cuoi: float | None = None
    #: TD-0437 — lúc CHUYỂN sang HALT, và lúc Supervisor THẤY hết vị thế lần đầu sau đó (trễ ≤ 1 vòng so với thật ⇒ chờ
    #: lâu hơn một chút, phía an toàn). Ghi đĩa: Supervisor restart không được làm lại đồng hồ chờ từ đầu hay bỏ qua nó.
    luc_halt: datetime | None = None
    luc_het_vi_the: datetime | None = None
    #: TD-0437 — điều kiện mở lại còn thiếu ở vòng trước; chỉ để log khi ĐỔI (R8). Không ghi đĩa.
    thieu_mo_lai_cuoi: tuple[str, ...] = ()

    @property
    def co_do(self) -> bool:
        """Cờ đỏ DỪNG TOÀN HỆ THỐNG (§6.6(2)) — mọi lý do, một chỗ hỏi. Có cờ đỏ ⇒ KHÔNG gọi `/stopentry`
        (`api-integration-rules.md` 4.4d luật 1: gọi nó khi bot `STOPPED` là BẬT LẠI bot)."""
        return self.la_thanh_ly or self.breaker.dung_han or self.muc_tang_chan == ABORT or self.leo_thang_dung


# ═══ TD-0434 (`DR-TANG-CHAN-01`, §12c.5) — tầng chặn sụt vốn: quyết định THUẦN, không gọi mạng ═══

BINH_THUONG = "BINH_THUONG"
HALT = "HALT"
ABORT = "ABORT"
#: TD-0435/TD-0437 (§12c.5 BƯỚC 3) — mở lại sau HALT ở NỬA cỡ, giữ tới khi dd ≤ soft; trong mức này chỉ còn ABORT > abort.
NUA_CO = "NUA_CO"
MUC_TANG_CHAN = (BINH_THUONG, HALT, ABORT, NUA_CO)


# ═══ TD-0435 (`DR-TANG-CHAN-01` §4 điều 3) — `dd_state.json`: Supervisor CÔNG BỐ, chiến lược ĐỌC ═══

TEN_FILE_DD_STATE = "dd_state.json"


@dataclass(frozen=True)
class DdState:
    """Điều Supervisor công bố mỗi vòng. `co_do` tách riêng khỏi `muc`: thanh lý / breaker / leo thang đều là cờ đỏ mà
    `muc` vẫn có thể là `BINH_THUONG`/`HALT` — chiến lược phải thấy cả hai."""

    muc: str
    dd_pct: float | None
    co_do: bool
    luc_utc: datetime


def ghi_dd_state(duong_dan: Path, *, muc: str, dd_pct: float | None, co_do: bool, now: datetime) -> None:
    """Ghi NGUYÊN TỬ (khuôn `luu_trang_thai`) — chiến lược đọc file này mỗi lần định cỡ, không được thấy file dở."""
    if muc not in (*MUC_TANG_CHAN, NUA_CO):
        raise RiskSupervisorError(f"muc {muc!r} không hợp lệ")
    if now.tzinfo is None:
        raise RiskSupervisorError("now phải có múi giờ (UTC)")
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    noi_dung = {"muc": muc, "dd_pct": dd_pct, "co_do": co_do, "luc_utc": now.isoformat()}
    tam = duong_dan.with_name(duong_dan.name + ".dang-ghi")
    tam.write_text(json.dumps(noi_dung, ensure_ascii=False), encoding="utf-8")
    tam.replace(duong_dan)


def doc_dd_state(duong_dan: Path) -> DdState:
    """Thiếu file / hỏng / sai kiểu ⇒ RAISE `RiskSupervisorError` — tầng đọc (`tang_chan.py`) biến mọi raise thành
    "không mở lệnh" (fail-closed). Không có giá trị mặc định nào ở đây."""
    try:
        tho = json.loads(duong_dan.read_text(encoding="utf-8"))
        muc, dd, co_do = tho["muc"], tho["dd_pct"], tho["co_do"]
        luc = datetime.fromisoformat(tho["luc_utc"])
        if muc not in (*MUC_TANG_CHAN, NUA_CO) or type(co_do) is not bool or luc.tzinfo is None:
            raise ValueError(f"dd_state sai hình: {tho!r}")
        if dd is not None and (isinstance(dd, bool) or not isinstance(dd, (int, float)) or not math.isfinite(dd) or dd < 0):
            raise ValueError(f"dd_pct {dd!r} không hợp lệ")
        return DdState(muc=muc, dd_pct=None if dd is None else float(dd), co_do=co_do, luc_utc=luc)
    except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as exc:
        raise RiskSupervisorError(f"không đọc được {duong_dan}: {exc}") from exc


# ════ TD-0442 (`DR-CONG-AN-TOAN-01` §3.1(d)) — cờ đỏ CẤP TÀI KHOẢN ════
# Thanh lý / cấm IP (418) là sự kiện của TÀI KHOẢN, không của một bot. API điều khiển mỗi bot chỉ nghe localhost trong
# mạng riêng của nó (`DR-D11-03` §2.1) ⇒ một Supervisor không với tới bot khác. Nên: mỗi bot live có Supervisor riêng;
# Supervisor nào phát hiện thì GHI cờ chung trên đĩa, mọi Supervisor khác thấy cờ ở vòng kế tiếp thì `/stop` bot của nó,
# mọi bộ khởi chạy tiền thật từ chối bật. Không tự gỡ — người vận hành xoá file sau khi đã xử lý (§6.6(2)).


def ghi_co_do_tai_khoan(duong_dan: Path, *, ly_do: str, nguon: str, now: datetime) -> None:
    """Ghi NGUYÊN TỬ một lần. Đã có cờ ⇒ GIỮ bản đầu (lý do gốc quan trọng hơn lý do sau), không ghi đè."""
    if now.tzinfo is None:
        raise RiskSupervisorError("now phải có múi giờ (UTC)")
    if duong_dan.exists():
        return
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    noi_dung = {"ly_do": ly_do, "nguon": nguon, "luc_utc": now.isoformat()}
    tam = duong_dan.with_name(duong_dan.name + ".dang-ghi")
    tam.write_text(json.dumps(noi_dung, ensure_ascii=False), encoding="utf-8")
    tam.replace(duong_dan)


def doc_co_do_tai_khoan(duong_dan: Path) -> str | None:
    """`None` ⇔ chưa có cờ. Có file ⇒ trả lý do. File có mà hỏng ⇒ vẫn là CỜ ĐỎ (không đọc được lý do không có nghĩa là
    không có cờ — N6), trả chuỗi nói rõ file hỏng."""
    if not duong_dan.exists():
        return None
    try:
        tho = json.loads(duong_dan.read_text(encoding="utf-8"))
        return f"{tho['ly_do']} (nguồn {tho['nguon']}, {tho['luc_utc']})"
    except (json.JSONDecodeError, OSError, KeyError, TypeError) as exc:
        return f"file cờ đỏ tài khoản {duong_dan} có nhưng đọc hỏng ({exc}) — vẫn coi là CỜ ĐỎ"


def quyet_dinh_tang_chan(
    muc_cu: str, *, dd_pct: float | None, hang_so: HangSoKhaiLai = HANG_SO_KHAI_LAI,
) -> str:
    """Mức kế tiếp từ mức cũ + mức sụt đo được, đúng thang §12c.5 (*"dd > 8% → HALT"*, *"dd > 20% → ABORT"* — so sánh
    NGẶT, dùng `HANG_SO_KHAI_LAI` khai lại có chủ đích §6.6(2), `L-Z44` canh khớp cấu hình).

    - `ABORT` giữ nguyên mãi (cờ đỏ, không tự gỡ).
    - `dd_pct is None` (chưa đo được, N6) ⇒ giữ nguyên mức — không bịa "an toàn", không bịa "sụt".
    - `HALT` KHÔNG tự về `BINH_THUONG` khi dd hồi: điều kiện mở lại là việc của `TD-0437` (§12c.5 bước 2 — mở lại theo
      THỜI GIAN, không theo kết quả; mở theo dd hồi là phương án deadlock spec đã bác).
    - Bậc 5% (nửa cỡ lệnh) KHÔNG ở đây: đó là phép nhân cỡ lệnh của chiến lược (`TD-0435`).
    """
    if muc_cu not in MUC_TANG_CHAN:
        raise RiskSupervisorError(f"mức tầng chặn {muc_cu!r} không hợp lệ — chỉ {MUC_TANG_CHAN}")
    if muc_cu == ABORT or dd_pct is None:
        return muc_cu
    if math.isnan(dd_pct) or dd_pct < 0:
        raise RiskSupervisorError(f"dd_pct phải hữu hạn và ≥ 0, nhận {dd_pct}")
    if dd_pct > hang_so.dd_abort_pct:
        return ABORT
    if muc_cu == NUA_CO:
        # TD-0437 (§12c.5 BƯỚC 3–4): mở lại lúc dd còn > halt (HALT không đóng ép, dd đứng yên) ⇒ HALT lại ở đây là
        # đúng deadlock spec đã bác. Trong NUA_CO chỉ ABORT (ở trên) hoặc hồi về ≤ soft mới đổi mức.
        return BINH_THUONG if dd_pct <= hang_so.dd_soft_pct else NUA_CO
    if dd_pct > hang_so.dd_halt_pct:
        return HALT
    return muc_cu


def dieu_kien_mo_lai(
    *,
    so_vi_the_mo: int | None,
    luc_het_vi_the: datetime | None,
    now: datetime,
    cho_toi_thieu: timedelta,
    co_xac_nhan: bool,
) -> list[str]:
    """TD-0437 (§12c.5 BƯỚC 2) — điều kiện mở lại sau HALT còn THIẾU; rỗng ⇔ được mở lại. CẢ BA:
    (a) mọi vị thế đã đóng · (b) đã qua `cho_toi_thieu` (= 2 × `max_hold_bars`) kể từ lúc hết vị thế · (c) người vận hành
    ghi xác nhận vào research-log (không phải phê duyệt — chỉ xác nhận đã nhìn). Không đọc được ⇒ coi là CHƯA đủ (N6)."""
    thieu: list[str] = []
    if so_vi_the_mo is None:
        thieu.append("(a) không đọc được số vị thế đang mở")
    elif so_vi_the_mo > 0:
        thieu.append(f"(a) còn {so_vi_the_mo} vị thế đang mở")
    if luc_het_vi_the is None:
        thieu.append("(b) chưa có mốc hết vị thế")
    elif now - luc_het_vi_the < cho_toi_thieu:
        thieu.append(f"(b) mới {now - luc_het_vi_the} kể từ lúc hết vị thế, cần {cho_toi_thieu}")
    if not co_xac_nhan:
        thieu.append("(c) chưa có dòng XAC_NHAN_MO_LAI_HALT trong research-log sau lúc HALT")
    return thieu


def ap_tran_halt(
    muc_cu: str,
    muc_moi: str,
    *,
    moc_halt: tuple[int | None, ...],
    so_lenh_dong: int | None,
    hang_so: HangSoKhaiLai = HANG_SO_KHAI_LAI,
) -> tuple[str, tuple[int | None, ...]]:
    """TD-0434 chặng 2 (`DR-TANG-CHAN-01` §8 (a), §12c.5 `spec:4756`): *"3 lần trong một chu kỳ 100 lệnh đóng. Lần thứ 4
    → ABORT bất kể dd bao nhiêu."* Trả `(mức, mốc HALT mới)`.

    - Chỉ một lần CHUYỂN sang HALT (`muc_cu != HALT`, `muc_moi == HALT`) mới là một lần HALT — gọi lại `/stopentry` mỗi
      vòng không phải lần HALT mới.
    - Chu kỳ = khối CỐ ĐỊNH §12c.1: lệnh đóng thứ `k` thuộc chu kỳ `k // chu_ky_lenh_dong`.
    - Lần HALT thứ `tran_halt_so_lan + 1` trong cùng chu kỳ ⇒ ABORT.
    - `so_lenh_dong is None` (không đọc được, N6) ⇒ mốc `None`, và mốc `None` được tính vào MỌI chu kỳ: chỉ làm ABORT tới
      SỚM hơn, không bao giờ muộn hơn — lệch về phía an toàn, không bịa một con số lệnh.
    """
    if muc_moi != HALT or muc_cu == HALT:
        return muc_moi, moc_halt
    if so_lenh_dong is not None and (type(so_lenh_dong) is not int or so_lenh_dong < 0):
        raise RiskSupervisorError(f"so_lenh_dong phải là số nguyên ≥ 0 hoặc None, nhận {so_lenh_dong!r}")
    moc_moi = (*moc_halt, so_lenh_dong)
    if so_lenh_dong is None:
        cung_chu_ky = len(moc_moi)  # không biết đang ở chu kỳ nào ⇒ đếm mọi lần — phía an toàn
    else:
        chu_ky = so_lenh_dong // hang_so.chu_ky_lenh_dong
        cung_chu_ky = sum(1 for m in moc_moi if m is None or m // hang_so.chu_ky_lenh_dong == chu_ky)
    if cung_chu_ky > hang_so.tran_halt_so_lan:
        return ABORT, moc_moi
    return HALT, moc_moi


def luu_trang_thai(trang_thai: TrangThaiBenVung, duong_dan: Path) -> None:
    """Ghi NGUYÊN TỬ (file tạm + `rename`) — cùng khuôn
    `binance_public.tai_dump_agg_trades()`: tiến trình chết giữa chừng
    không được để lại một file mang TÊN THẬT nhưng nội dung dở dang."""
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    noi_dung = {
        "breaker": {
            "so_loi_lien_tiep": trang_thai.breaker.so_loi_lien_tiep,
            "dung_han": trang_thai.breaker.dung_han,
            "mo_tam": trang_thai.breaker.mo_tam,
            "thoi_diem_mo": (
                trang_thai.breaker.thoi_diem_mo.isoformat() if trang_thai.breaker.thoi_diem_mo else None
            ),
            "backoff_s": trang_thai.breaker.backoff_s,
        },
        "la_thanh_ly": trang_thai.la_thanh_ly,
        "muc_tang_chan": trang_thai.muc_tang_chan,
        "leo_thang_dung": trang_thai.leo_thang_dung,
        "moc_halt": list(trang_thai.moc_halt),
        "luc_halt": trang_thai.luc_halt.isoformat() if trang_thai.luc_halt else None,
        "luc_het_vi_the": trang_thai.luc_het_vi_the.isoformat() if trang_thai.luc_het_vi_the else None,
    }
    tam = duong_dan.with_name(duong_dan.name + ".dang-ghi")
    tam.write_text(json.dumps(noi_dung, indent=2, ensure_ascii=False), encoding="utf-8")
    tam.replace(duong_dan)


def doc_trang_thai(duong_dan: Path) -> TrangThaiBenVung:
    """Chưa có file (lần khởi động ĐẦU TIÊN của tiến trình) → trạng thái
    SẠCH — đây là ca DUY NHẤT "chưa đọc được" hợp lệ đọc thành trạng thái
    an toàn, vì "chưa từng ghi" là một sự thật rõ ràng, khác hẳn "có ghi
    nhưng đọc hỏng". File CÓ tồn tại mà hỏng ⇒ RAISE (fail-closed) — không
    được âm thầm coi hỏng là sạch, vì file hỏng có thể đang che một
    `dung_han=True`/`la_thanh_ly=True` đã ghi trước đó (N6).
    """
    if not duong_dan.exists():
        return TrangThaiBenVung(breaker=TrangThaiBreaker())
    try:
        tho = json.loads(duong_dan.read_text(encoding="utf-8"))
        b = tho["breaker"]
        breaker = TrangThaiBreaker(
            so_loi_lien_tiep=b["so_loi_lien_tiep"],
            dung_han=b["dung_han"],
            mo_tam=b["mo_tam"],
            thoi_diem_mo=(datetime.fromisoformat(b["thoi_diem_mo"]) if b["thoi_diem_mo"] else None),
            backoff_s=b["backoff_s"],
        )
        # TD-0434: file ghi TRƯỚC khi có tầng chặn không có hai khoá này — lúc đó chưa từng có HALT/ABORT/leo thang, nên
        # mặc định là sự thật, không phải đoán. Có khoá mà sai kiểu ⇒ raise như mọi khoá khác (có thể đang che cờ đỏ).
        muc = tho.get("muc_tang_chan", BINH_THUONG)
        leo_thang = tho.get("leo_thang_dung", False)
        if muc not in MUC_TANG_CHAN:
            raise ValueError(f"muc_tang_chan {muc!r} không hợp lệ")
        if type(leo_thang) is not bool:
            raise ValueError(f"leo_thang_dung phải là bool, nhận {leo_thang!r}")
        moc = tho.get("moc_halt", [])  # file trước TD-0434 chặng 2: chưa từng đếm HALT — sự thật, không đoán
        if not isinstance(moc, list) or any(m is not None and (type(m) is not int or m < 0) for m in moc):
            raise ValueError(f"moc_halt phải là danh sách số nguyên ≥ 0 hoặc null, nhận {moc!r}")
        moc_gio = {}
        for k in ("luc_halt", "luc_het_vi_the"):  # file trước TD-0437: chưa từng có HALT được theo dõi ⇒ None là sự thật
            v = tho.get(k)
            moc_gio[k] = None if v is None else datetime.fromisoformat(v)
            if moc_gio[k] is not None and moc_gio[k].tzinfo is None:
                raise ValueError(f"{k} phải có múi giờ, nhận {v!r}")
        return TrangThaiBenVung(
            breaker=breaker, la_thanh_ly=tho["la_thanh_ly"], muc_tang_chan=muc, leo_thang_dung=leo_thang,
            moc_halt=tuple(moc), **moc_gio,
        )
    except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as exc:
        raise RiskSupervisorError(
            f"trạng thái đã lưu ở {duong_dan} tồn tại nhưng KHÔNG đọc được: {exc} — "
            "không tự coi là sạch, có thể đang che một cờ đỏ đã ghi trước đó"
        ) from exc


# ════════════════════════════════════════════════════════════════════
# TODO (ghi để không quên, KHÔNG phải việc của TD-0196):
#   1. ✅ Giải bởi `DR-D11-03` (TD-0241) — `GET /fapi/v1/forceOrders`
#      (`phat_hien_thanh_ly` ở trên), không cần user data stream.
#   2. ✅ Giải bởi `DR-D11-03` — `src/tool_d/ops/risk_supervisor_daemon.py`,
#      không phải entrypoint thứ 9.
#   3. `provider-map.md` cần một dòng cho "Binance — Risk Supervisor
#      đọc margin/vị thế" nếu coi đây là dịch vụ tách biệt với market
#      data (TD-0079 mới điền market-data + đặt lệnh). — Đóng ở
#      `DR-D11-03` (TD-0241), xem `provider-map.md`.
# ════════════════════════════════════════════════════════════════════
