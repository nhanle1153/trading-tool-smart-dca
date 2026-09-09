"""§6.6 — Risk Supervisor (TD-0196, OQ-09).

Tiến trình GIÁM SÁT RIÊNG của Tool D — đọc TRỰC TIẾP margin/vị thế từ
sàn, KHÔNG import code bot (§6.6 ràng buộc 2). File này CHỈ dựng tầng
THUẦN (phân loại lỗi, state machine circuit breaker, đối chiếu hằng số
khai lại) — theo đúng khuôn đã dùng cho mọi module khác của dự án
(`sizing.py`, `admission.py`, `take_profit.py`...): hàm thuần trước,
nối vào một tiến trình/entrypoint thật là việc SAU, khi tới gần D10/D11
(dry-run) — Risk Supervisor không cần CHẠY THẬT ở D4 (backtest-only),
chỉ cần TỒN TẠI và có phép kiểm để không bị quên tới lúc cần.

🔴 **KHÔNG được thêm entrypoint thứ 9** (L-Z36, N3). Cách tiến trình này
chạy thật (một script riêng ngoài `entrypoints/`? một chế độ của một
entrypoint có sẵn?) là quyết định CHƯA CHỐT — ghi vào Open Questions khi
tới lúc, không tự chọn ở đây.

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

import math
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

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
    doi_chieu = (
        ("e_d", "tier_a.E_D"),
        ("dd_soft_pct", "tier_c.dd_ladder_pct.soft"),
        ("dd_halt_pct", "tier_c.dd_ladder_pct.halt"),
        ("dd_abort_pct", "tier_c.dd_ladder_pct.abort"),
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


# ════════════════════════════════════════════════════════════════════
# TODO (ghi để không quên, KHÔNG phải việc của TD-0196):
#   1. Xác nhận CHÍNH XÁC trường Binance đánh dấu lệnh thanh lý (REST
#      `positionRisk`/`userTrades`, hay field `x`/`X` của user data
#      stream `ORDER_TRADE_UPDATE`) trước khi viết tầng ĐỌC THẬT gọi
#      `trang_thai_tai_khoan()` — chưa verify trong phiên này (rule 6).
#   2. Quyết định tiến trình này CHẠY Ở ĐÂU (không phải entrypoint thứ
#      9 — L-Z36) khi tới gần D10/D11.
#   3. `provider-map.md` cần một dòng cho "Binance — Risk Supervisor
#      đọc margin/vị thế" nếu coi đây là dịch vụ tách biệt với market
#      data (TD-0079 mới điền market-data + đặt lệnh).
# ════════════════════════════════════════════════════════════════════
