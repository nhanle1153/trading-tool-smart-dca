"""TD-0252 (`DR-D1-05` §3b.4) — độ phủ của khung CHI TIẾT so với khung chính.

Vì sao cần một phép đo riêng thay vì đếm file trên đĩa: `backtesting.py:1739` có điều kiện
`and pair in self.detail_data`. Mã thiếu khung chi tiết **KHÔNG làm backtest đỏ** — nó lặng lẽ
chạy ở khung chính trong khi mã khác chạy khung chi tiết, và bảng kết quả không có cột nào nói
ra. Một lượt đo như thế trộn hai độ phân giải khớp lệnh mà tự khai là một.

Đếm file chứng minh được file TỒN TẠI; nó không chứng minh bộ chạy NẠP được, cũng không thấy
lỗ hổng GIỮA chuỗi của một mã đã có mặt. Nên hàm ở đây nhận **dataframe đã nạp** — cùng thứ bộ
chạy sẽ hỏi — chứ không tự đọc đĩa: một luật, mọi người gọi đi qua đúng đường sản xuất.

Chủ dự án chốt 18/09/2026: tiêu chí là **không một giờ khung chính nào thiếu nến khung chi tiết
tương ứng, ở mọi mã**; *đủ hoặc từ chối chạy*, không có mức giữa.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

#: Mã lý do, máy đọc được. Hai ca này đòi hai hành động khác nhau nên không gộp:
#: thiếu hẳn thì phải TẢI mã đó; thủng giữa chuỗi thì phải hỏi lại sàn (`--probe-gap`)
#: xem sàn có dữ liệu không, trước khi kết luận nguyên nhân (H19/LD-28).
KHONG_CO_KHUNG_CHI_TIET = "KHONG_CO_KHUNG_CHI_TIET"
THUNG_GIUA_CHUOI = "THUNG_GIUA_CHUOI"


@dataclass(frozen=True)
class ThieuChiTiet:
    """Một mã không đủ khung chi tiết. Mang LÝ DO đọc được, không phải một cờ đúng/sai —
    người gọi cần in ra được chuyện gì thiếu và thiếu ở đâu (cùng lý do `kiem_san_tool_d()`
    của `DR-D4-05` trả lý do thay vì `bool`)."""

    symbol: str
    ly_do: str
    so_gio_chinh: int
    so_gio_thieu: int
    vi_du_gio: tuple[str, ...]

    def mo_ta(self) -> str:
        if self.ly_do == KHONG_CO_KHUNG_CHI_TIET:
            return f"{self.symbol}: KHÔNG nạp được khung chi tiết (khung chính có {self.so_gio_chinh} giờ)"
        phan_tram = 100.0 * self.so_gio_thieu / self.so_gio_chinh if self.so_gio_chinh else 0.0
        vi_du = ", ".join(self.vi_du_gio)
        return (
            f"{self.symbol}: thủng {self.so_gio_thieu}/{self.so_gio_chinh} giờ "
            f"({phan_tram:.2f}%) — ví dụ: {vi_du}"
        )


def cho_thieu_khung_chi_tiet(
    nen_chinh: Mapping[str, pd.DataFrame],
    nen_chi_tiet: Mapping[str, pd.DataFrame],
    *,
    toi_da_vi_du: int = 5,
) -> list[ThieuChiTiet]:
    """Trả danh sách mã không đủ khung chi tiết. **Rỗng = đủ theo tiêu chí đã chốt.**

    `nen_chinh` / `nen_chi_tiet`: kết quả nạp của bộ chạy (vd `history.load_data(...)`), khoá là
    tên cặp. Mọi mã trong `nen_chinh` đều bị xét; mã chỉ có trong `nen_chi_tiet` không bị xét —
    dữ liệu thừa không phải lỗi độ phủ.

    Một giờ của khung chính coi là ĐƯỢC PHỦ khi có ít nhất một nến chi tiết rơi vào giờ đó. Với
    mã ngừng giao dịch đã cắt tại mốc ngừng, giờ cuối chỉ còn một nến chi tiết — vẫn tính là
    được phủ, đúng như `DR-D1-05` §3b.5 mô tả.
    """
    thieu: list[ThieuChiTiet] = []
    for symbol in sorted(nen_chinh):
        df_chinh = nen_chinh[symbol]
        gio_chinh = pd.DatetimeIndex(df_chinh["date"]).floor("h").unique()
        df_ct = nen_chi_tiet.get(symbol)
        if df_ct is None or df_ct.empty:
            thieu.append(
                ThieuChiTiet(
                    symbol=symbol,
                    ly_do=KHONG_CO_KHUNG_CHI_TIET,
                    so_gio_chinh=len(gio_chinh),
                    so_gio_thieu=len(gio_chinh),
                    vi_du_gio=(),
                )
            )
            continue
        gio_co = set(pd.DatetimeIndex(df_ct["date"]).floor("h"))
        con_thieu = sorted(g for g in gio_chinh if g not in gio_co)
        if con_thieu:
            thieu.append(
                ThieuChiTiet(
                    symbol=symbol,
                    ly_do=THUNG_GIUA_CHUOI,
                    so_gio_chinh=len(gio_chinh),
                    so_gio_thieu=len(con_thieu),
                    vi_du_gio=tuple(str(g) for g in con_thieu[:toi_da_vi_du]),
                )
            )
    return thieu


def tom_tat_theo_ma(
    nen_chinh: Mapping[str, pd.DataFrame],
    nen_chi_tiet: Mapping[str, pd.DataFrame],
    ro: Sequence[str],
) -> dict[str, dict]:
    """Bảng độ phủ theo mã cho artifact. Mã không nạp được khung nào mang `None` ở ô tương ứng —
    **không** `0` (N6: chưa đo được khác với đo ra 0)."""
    thieu = {t.symbol: t for t in cho_thieu_khung_chi_tiet(nen_chinh, nen_chi_tiet)}
    bang: dict[str, dict] = {}
    for symbol in ro:
        df_chinh = nen_chinh.get(symbol)
        df_ct = nen_chi_tiet.get(symbol)
        t = thieu.get(symbol)
        bang[symbol] = {
            "so_nen_chinh": None if df_chinh is None else len(df_chinh),
            "so_nen_chi_tiet": None if df_ct is None else len(df_ct),
            "dau": None if df_ct is None or df_ct.empty else str(df_ct["date"].min()),
            "cuoi": None if df_ct is None or df_ct.empty else str(df_ct["date"].max()),
            "so_gio_chinh_thieu_chi_tiet": None if df_chinh is None else (0 if t is None else t.so_gio_thieu),
            "ly_do": None if t is None else t.ly_do,
        }
    return bang
