"""Đời sống THẬT của một mã quanh giai đoạn lockbox — TD-0306, giải `MT-59`.

`MT-59`: artifact `TD-0230` suy "mã còn sống" từ SỰ CÓ MẶT file nến tháng trong
kho `data.binance.vision`. Nhưng sau khi sàn ngừng giao dịch, kho vẫn sinh nến ở
giá thanh toán, `volume = 0`, nhiều tháng liền ⇒ `khoang_ton_tai` kéo dài đời sống
mã đã chết. `dung_ro_tai_moc()` lại gán `delisted_at = None` cho mọi mã có
`thang_cuoi` bằng tháng lớn nhất của kho ⇒ mã chết được coi là đang sống.

Module này THUẦN (không mạng): nhận nến 1h đã đọc, trả trạng thái. Việc gọi mạng
nằm ở kịch bản đo `docs/du-lieu-do/do_td0306_khoang_ton_tai_that.py`.

🔑 Dùng lại `moc_ngung_giao_dich()` (`DR-D1-03` §5), không viết khuôn đo mới.

🔴 Bẫy đã tránh: gọi `moc_ngung_giao_dich(nen, T3)` trên kho chỉ có tới hết tháng 8
sẽ báo mã còn sống tới 31/08 là "ngừng lúc 31/08 23:00" — vì kho không có tháng 9,
chứ không phải vì mã ngừng. Mốc cắt phải là `min(T3, hết kho)`. Còn khoảng từ hết
kho tới `T3` thì kho tháng KHÔNG nhìn thấy: trạng thái là `SONG_TOI_HET_KHO`, và
chỉ nguồn độc lập (`exchangeInfo`) mới nâng nó thành "sống tới `T3`" (N6).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Mapping

import pandas as pd

from tool_d.data.pool_t1_du_lieu import NEN_CHET_TOI_THIEU, _moc_ts, duoi_nen_chet, moc_ngung_giao_dich

CHET_TRUOC_T2 = "chet_truoc_t2"
CHET_TRONG_T2_T3 = "chet_trong_t2_t3"
SONG_TOI_T3 = "song_toi_t3"
SONG_TOI_HET_KHO = "song_toi_het_kho"
KHONG_DO_DUOC = "khong_do_duoc"

TRANG_THAI_CHET = frozenset({CHET_TRUOC_T2, CHET_TRONG_T2_T3})

# `nguon_thang_cuoi` của từng mục trong `khoang_ton_tai` mới.
NGUON_DO_THAT = "do_that"
NGUON_CAN_TREN = "can_tren_td0230"
NGUON_KHONG_DO_DUOC = "khong_do_duoc"


class MauThuanNguonError(RuntimeError):
    """Kho nói mã đã chết, `exchangeInfo` nói hôm nay mã vẫn giao dịch.

    Mã còn niêm yết hôm nay thì không thể đã huỷ trước đó — trừ khi kho bị cụt
    tháng cuối, hoặc mã bị huỷ rồi niêm yết lại. Cả hai đều cần người xem, nên
    DỪNG cả phép đo thay vì tự chọn một nguồn (quy tắc 11).
    """


@dataclass(frozen=True)
class KetQuaDoiSong:
    trang_thai: str
    moc_ngung: pd.Timestamp | None


def phan_loai_doi_song(nen_1h: pd.DataFrame, *, t2: date, t3: date, het_kho: date) -> KetQuaDoiSong:
    """Trạng thái đời sống của một mã, CHỈ từ nến 1h của kho.

    `het_kho` = ngày đầu tiên SAU tháng cuối đã đọc (kho tới hết 08/2026 ⇒ 2026-09-01).
    Raise (qua `moc_ngung_giao_dich`) nếu không có nến nào có `volume > 0`.
    """
    moc_cat = min(t3, het_kho)
    ngung = moc_ngung_giao_dich(nen_1h, moc_cat)
    song = KetQuaDoiSong(SONG_TOI_T3 if het_kho >= t3 else SONG_TOI_HET_KHO, None)
    if ngung is None:
        return song
    # `DR-D1-03` §5: chỉ là ngừng khi sau nó có >= NEN_CHET_TOI_THIEU nến volume 0
    # liền nhau. Đuôi ngắn hơn ở cuối kho là một giờ vắng lệnh của mã ít thanh
    # khoản, không phải nến giá thanh toán — coi là ngừng thì exchangeInfo sẽ báo
    # mâu thuẫn và dừng cả phép đo vì một báo động giả.
    if duoi_nen_chet(nen_1h) < NEN_CHET_TOI_THIEU:
        return song
    if ngung < _moc_ts(t2):
        return KetQuaDoiSong(CHET_TRUOC_T2, ngung)
    return KetQuaDoiSong(CHET_TRONG_T2_T3, ngung)


def doi_chieu_exchange_info(kq: KetQuaDoiSong, *, dang_giao_dich_hom_nay: bool, symbol: str) -> str:
    """Trạng thái cuối, sau khi đối chiếu nguồn độc lập với kho.

    - Kho nói đã chết mà hôm nay vẫn giao dịch ⇒ `MauThuanNguonError`.
    - Kho nói sống tới hết kho: hôm nay giao dịch ⇒ sống tới `T3` (vì `T3` trước
      hôm nay); hôm nay không giao dịch ⇒ đã chết sau hết kho, không biết trước
      hay sau `T3` ⇒ `KHONG_DO_DUOC` (không đoán).
    """
    if kq.trang_thai in TRANG_THAI_CHET and dang_giao_dich_hom_nay:
        raise MauThuanNguonError(
            f"{symbol}: kho cho {kq.trang_thai} (ngừng {kq.moc_ngung}) nhưng exchangeInfo hôm nay "
            "vẫn TRADING — kho cụt tháng cuối, hoặc mã bị huỷ rồi niêm yết lại. DỪNG, cần người xem."
        )
    if kq.trang_thai == SONG_TOI_HET_KHO:
        return SONG_TOI_T3 if dang_giao_dich_hom_nay else KHONG_DO_DUOC
    return kq.trang_thai


def khoang_ton_tai_moi(
    cu: Mapping[str, Mapping[str, object]],
    do_that: Mapping[str, tuple[str, pd.Timestamp | None]],
) -> dict[str, dict[str, object]]:
    """`khoang_ton_tai` cùng schema `TD-0230`, sửa `thang_cuoi` cho mã đã đo.

    Mã chưa đo giữ số cũ làm CẬN TRÊN (sai lệch của kho chỉ một chiều: kéo đời
    sống dài ra, không bao giờ ngắn lại) và mang nhãn `can_tren_td0230` — để bên
    đọc biết số nào là đo, số nào chỉ là cận, không phải đoán.

    `do_that[sym] = (trang_thai_cuoi, moc_ngung)`.
    """
    ra: dict[str, dict[str, object]] = {}
    for sym, k in cu.items():
        muc = dict(k)
        if sym not in do_that:
            muc["nguon_thang_cuoi"] = NGUON_CAN_TREN
            ra[sym] = muc
            continue
        trang_thai, ngung = do_that[sym]
        muc["trang_thai"] = trang_thai
        if trang_thai in TRANG_THAI_CHET:
            assert ngung is not None
            muc["thang_cuoi"] = f"{ngung.year:04d}-{ngung.month:02d}"
            muc["moc_ngung"] = ngung.isoformat()
            muc["nguon_thang_cuoi"] = NGUON_DO_THAT
        elif trang_thai == KHONG_DO_DUOC:
            muc["nguon_thang_cuoi"] = NGUON_KHONG_DO_DUOC
        else:
            muc["nguon_thang_cuoi"] = NGUON_DO_THAT
        ra[sym] = muc
    return ra


def nghi_merge(ngung: Mapping[str, pd.Timestamp]) -> dict[str, list[str]]:
    """Mã ngừng CÙNG MỘT GIỜ với ít nhất một mã khác — chữ ký của merge/rebrand
    đồng loạt (tiền lệ AGIX+OCEAN→FET). Chỉ là dấu hiệu để người xem, không phải
    phán quyết: một đợt huỷ niêm yết hàng loạt cũng cùng giờ."""
    theo_gio: dict[pd.Timestamp, list[str]] = defaultdict(list)
    for sym, ts in ngung.items():
        theo_gio[ts].append(sym)
    return {
        sym: sorted(s for s in nhom if s != sym)
        for nhom in theo_gio.values()
        if len(nhom) > 1
        for sym in nhom
    }
