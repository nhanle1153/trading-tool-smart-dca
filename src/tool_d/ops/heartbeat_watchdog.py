"""TD-0209 — watchdog: đọc file heartbeat, quyết định có cảnh báo Telegram
hay không. Tầng THUẦN (đánh giá + quyết định gửi) tách khỏi tầng GỌI MẠNG
(`telegram_client.gui_tin_nhan`) — cùng khuôn toàn dự án (`sizing.py`,
`admission.py`, `risk_supervisor.py`...).

🔴 KHÔNG phải entrypoint thứ 9 (N3, L-Z36) — module này không đánh giá một
cấu hình chiến lược nào, không chạm CALIB/WFO/LOCKBOX, không gọi
`measurement_guard()`. Khoá 8 file của `entrypoints/` áp cho việc SINH FILE
KẾT QUẢ đo lường (spec dòng 664, 671-674); heartbeat/cảnh báo tiến trình là
công cụ vận hành đứng ngoài phạm vi đó — quyết định đã ghi ở
`api-integration-rules.md` Mục 4.4b (13/09/2026).

🔴 CHƯA nối vào Freqtrade/launcher thật — D10-D12 chưa mở, chưa có tiến
trình dài nào để giám sát và chưa quyết cơ chế khởi chạy watchdog thật
trên máy (Task Scheduler/dịch vụ Docker/khác — TODO cuối file, cùng loại
TODO đã để ở `risk_supervisor.py`/TD-0196). `chay_mot_vong()` là đơn vị
THUẦN có thể test độc lập với việc tiến trình thật đã tồn tại hay chưa;
`main()` ở cuối file chỉ là khung CLI runnable, không phải bằng chứng đã
triển khai thật.

Chín tham số ngưỡng bên dưới lấy ĐÚNG số đã đề xuất ở Mục 4.4b — chủ dự án
gõ "bắt đầu code" không kèm điều chỉnh, coi là dùng nguyên đề xuất (cùng
khuôn OQ-09/TD-0196: đề xuất kèm lý do, xác nhận bằng cách không phản đối).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from tool_d.ops import telegram_client
from tool_d.ops.heartbeat import (
    KetQuaDocHeartbeat,
    doc_heartbeat,
    duong_dan_heartbeat,
    tuoi_giay,
    tuoi_trang_thai_giay,
)
from tool_d.ops.telegram_client import KetQuaGuiTelegram

# ═══════════════════════════════════════════════════════════════════
# Ngưỡng — Mục 4.4b của api-integration-rules.md (ĐỀ XUẤT → dùng nguyên)
# ═══════════════════════════════════════════════════════════════════

TRANG_THAI_BINH_THUONG = "RUNNING"
NGUONG_HEARTBEAT_CU_S = 300.0
NGUONG_TRANG_THAI_KHONG_BINH_THUONG_S = 300.0
CHU_KY_KIEM_S = 60.0

_LOG = logging.getLogger("tool_d.ops.heartbeat_watchdog")


# ═══════════════════════════════════════════════════════════════════
# Đánh giá MỘT lần đọc heartbeat — hàm THUẦN, không phụ thuộc lịch sử
# ═══════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class KetQuaDanhGia:
    bat_thuong: bool
    ly_do: str | None  # None khi bat_thuong=False


def danh_gia_heartbeat(
    ket_qua_doc: KetQuaDocHeartbeat,
    *,
    now: datetime,
    nguong_heartbeat_cu_s: float = NGUONG_HEARTBEAT_CU_S,
    nguong_trang_thai_s: float = NGUONG_TRANG_THAI_KHONG_BINH_THUONG_S,
    trang_thai_binh_thuong: str = TRANG_THAI_BINH_THUONG,
) -> KetQuaDanhGia:
    """Bất thường khi, theo đúng thứ tự kiểm:
    (1) không đọc được heartbeat (file mất/hỏng — tiến trình có thể đã
        chết trước cả khi kịp ghi, hoặc đĩa hỏng — cả hai đều đáng báo);
    (2) heartbeat CŨ quá ngưỡng (tiến trình chết/treo — không còn ghi);
    (3) `trang_thai` khác `trang_thai_binh_thuong` VÀ đã kéo dài quá
        ngưỡng (bot dừng ngoài ý muốn, tiến trình vẫn sống nên (2) không
        bắt được ca này).
    """
    if not ket_qua_doc.doc_duoc:
        return KetQuaDanhGia(bat_thuong=True, ly_do=f"không đọc được heartbeat: {ket_qua_doc.loi}")

    heartbeat = ket_qua_doc.heartbeat
    assert heartbeat is not None  # doc_duoc=True luôn kèm heartbeat (bất biến của KetQuaDocHeartbeat)

    tuoi = tuoi_giay(heartbeat, now=now)
    if tuoi > nguong_heartbeat_cu_s:
        return KetQuaDanhGia(
            bat_thuong=True,
            ly_do=(
                f"heartbeat cũ {tuoi:.0f}s > ngưỡng {nguong_heartbeat_cu_s:.0f}s "
                "(tiến trình có thể đã chết/treo)"
            ),
        )

    if heartbeat.trang_thai != trang_thai_binh_thuong:
        tuoi_trang_thai = tuoi_trang_thai_giay(heartbeat, now=now)
        if tuoi_trang_thai > nguong_trang_thai_s:
            return KetQuaDanhGia(
                bat_thuong=True,
                ly_do=(
                    f"trạng thái {heartbeat.trang_thai!r} kéo dài {tuoi_trang_thai:.0f}s "
                    f"> ngưỡng {nguong_trang_thai_s:.0f}s (khác {trang_thai_binh_thuong!r})"
                ),
            )

    return KetQuaDanhGia(bat_thuong=False, ly_do=None)


# ═══════════════════════════════════════════════════════════════════
# Chống spam — chỉ báo khi CHUYỂN trạng thái (Mục 4.4b)
# ═══════════════════════════════════════════════════════════════════

CANH_BAO = "CANH_BAO"
PHUC_HOI = "PHUC_HOI"


def quyet_dinh_loai_tin(bat_thuong_da_bao: bool | None, bat_thuong_hien_tai: bool) -> str | None:
    """`bat_thuong_da_bao=None` — chưa từng báo lần nào (lần chạy đầu của
    watchdog, hoặc watchdog vừa khởi động lại). Chỉ báo CANH_BAO nếu ngay
    từ đầu đã bất thường; KHÔNG báo PHUC_HOI cho một ca chưa từng báo
    CANH_BAO (không có gì để "phục hồi" từ nếu chưa ai được báo là hỏng)."""
    if bat_thuong_da_bao is None:
        return CANH_BAO if bat_thuong_hien_tai else None
    if bat_thuong_hien_tai and not bat_thuong_da_bao:
        return CANH_BAO
    if not bat_thuong_hien_tai and bat_thuong_da_bao:
        return PHUC_HOI
    return None


def xay_noi_dung_tin(loai: str, ket_qua: KetQuaDanhGia, *, ten_tien_trinh: str, now: datetime) -> str:
    moc = now.astimezone(timezone.utc).isoformat()
    if loai == CANH_BAO:
        return f"🔴 [{ten_tien_trinh}] BẤT THƯỜNG lúc {moc}: {ket_qua.ly_do}"
    if loai == PHUC_HOI:
        return f"✅ [{ten_tien_trinh}] ĐÃ PHỤC HỒI lúc {moc} — heartbeat bình thường trở lại"
    raise ValueError(f"loai tin không nhận diện được: {loai!r}")


# ═══════════════════════════════════════════════════════════════════
# Trạng thái watchdog xuyên suốt nhiều vòng poll — bất biến (cùng kỷ luật
# `TrangThaiBreaker`: mọi hàm trả về trạng thái MỚI, không sửa tại chỗ)
# ═══════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class TrangThaiWatchdog:
    bat_thuong_da_bao: bool | None = None


def chay_mot_vong(
    duong_dan_heartbeat: Path,
    trang_thai: TrangThaiWatchdog,
    *,
    now: datetime,
    ten_tien_trinh: str = "tool_d",
    gui_tin_nhan_fn: Callable[[str], KetQuaGuiTelegram] = telegram_client.gui_tin_nhan,
) -> tuple[TrangThaiWatchdog, KetQuaGuiTelegram | None]:
    """MỘT vòng kiểm tra: đọc → đánh giá → (có thể) gửi → trạng thái mới.

    Chỉ cập nhật `bat_thuong_da_bao` khi gửi Telegram THÀNH CÔNG — gửi
    thất bại (mạng lỗi, Telegram tự nó lỗi) thì GIỮ NGUYÊN trạng thái cũ,
    để vòng poll KẾ TIẾP (60s sau, `CHU_KY_KIEM_S`) tự thử gửi lại; đây là
    toàn bộ cơ chế "retry" của module này — không có backoff nội bộ (xem
    docstring `telegram_client.py`).

    Trả về `(trang_thai_moi, ket_qua_gui)` — `ket_qua_gui=None` nghĩa là
    vòng này không cần gửi gì (trạng thái không đổi). Không tự log ở đây
    (hàm thuần) — `main()` bên dưới chịu trách nhiệm log/in kết quả.
    """
    ket_qua_doc = doc_heartbeat(duong_dan_heartbeat)
    danh_gia = danh_gia_heartbeat(ket_qua_doc, now=now)

    loai_tin = quyet_dinh_loai_tin(trang_thai.bat_thuong_da_bao, danh_gia.bat_thuong)
    if loai_tin is None:
        return trang_thai, None

    noi_dung = xay_noi_dung_tin(loai_tin, danh_gia, ten_tien_trinh=ten_tien_trinh, now=now)
    ket_qua_gui = gui_tin_nhan_fn(noi_dung)
    if not ket_qua_gui.thanh_cong:
        return trang_thai, ket_qua_gui  # giữ nguyên — thử lại vòng sau

    return TrangThaiWatchdog(bat_thuong_da_bao=danh_gia.bat_thuong), ket_qua_gui


def phan_tich_tham_so(argv: list[str] | None = None) -> tuple[Path, str]:
    """`--runmode dry_run|live` (BẮT BUỘC, không mặc định) → `(đường heartbeat, tên tiến trình)`.

    TD-0350: không có mặc định vì dry-run và live có thể chạy cùng lúc — một watchdog lặng lẽ canh nhầm tiến
    trình kia sẽ báo "còn sống" cho một bot đã chết."""
    import argparse

    p = argparse.ArgumentParser(description="Watchdog heartbeat Tool D (TD-0209)")
    p.add_argument("--runmode", required=True, choices=("dry_run", "live"))
    ns = p.parse_args(argv)
    return duong_dan_heartbeat(ns.runmode), f"tool_d_{ns.runmode}"


def main(argv: list[str] | None = None) -> None:  # pragma: no cover — vòng lặp vô hạn + mạng thật
    logging.basicConfig(level=logging.INFO)
    duong_dan_hb, ten_tien_trinh = phan_tich_tham_so(argv)
    telegram_client.doc_thong_tin_bot()  # fail-fast nếu thiếu credential, trước khi vào vòng lặp

    trang_thai = TrangThaiWatchdog()
    while True:
        trang_thai, ket_qua_gui = chay_mot_vong(
            duong_dan_hb, trang_thai, now=datetime.now(timezone.utc), ten_tien_trinh=ten_tien_trinh
        )
        if ket_qua_gui is not None and not ket_qua_gui.thanh_cong:
            _LOG.error("gửi Telegram thất bại (%s): %s", ket_qua_gui.loai_loi, ket_qua_gui.chi_tiet)
        time.sleep(CHU_KY_KIEM_S)


# ════════════════════════════════════════════════════════════════════
# TODO (ghi để không quên, KHÔNG phải việc của TD-0209):
#   1. Quyết định watchdog CHẠY Ở ĐÂU trên máy thật (Task Scheduler/dịch
#      vụ Docker/khác) — khi tới D11 setup thật (cùng TODO (2) đã treo ở
#      `risk_supervisor.py`, TD-0196).
#   2. Nối `ghi_heartbeat()` vào vòng lặp thật của Freqtrade (worker loop,
#      KHÔNG phải một callback chiến lược — callback bị `strategy_safe_
#      wrapper` nuốt exception, MT-16 vii) khi launcher live được viết.
#      Cần xác nhận Freqtrade có gọi `bot_loop_start`/tương đương ở CẢ hai
#      trạng thái RUNNING và STOPPED hay chỉ RUNNING — chưa đọc mã nguồn
#      Freqtrade cho câu này (rule 6, chưa đoán).
# ════════════════════════════════════════════════════════════════════


if __name__ == "__main__":  # pragma: no cover
    main()
