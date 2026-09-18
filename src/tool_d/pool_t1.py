"""TD-0247 (`DR-D1-02`, `DR-D1-03`) — dựng lại rổ pool point-in-time tại `T1`.

Logic THUẦN: không tự gọi mạng (hàm đọc volume được TIÊM vào), không sửa
`pool.py` (`DR-D1-02` §2.3 — `pairlist_point_in_time()` giữ nguyên, đây là
module RIÊNG gọi nó).

🔴 `DR-D1-03` (17/09/2026) đính chính `DR-D1-02` §2:
  • tập EXPLORE bị loại vĩnh viễn = mọi mã có DỮ LIỆU trong thư mục EXPLORE
    (đã dùng để sinh giả thuyết), KHÔNG phải khối `explore:` của
    `config/pool.yaml` (426 mã = mọi mã trượt tiêu chí 09/2026 — áp khối đó
    loại 54/116 mã và tái tạo lệch sống sót);
  • "trượt tiêu chí" xét TẠI `T1`, không chuỗi `pairlist_over_time()` từ `T0`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from tool_d.api_client.binance_public import NenThangKhongCoError
from tool_d.pool import SymbolStat, pairlist_point_in_time

#: TD-0231 — ca nào |tuổi xấp xỉ theo THÁNG − ngưỡng| ≤ số ngày này thì đọc
#: NGÀY onboard chính xác từ file tháng đầu; xa ngưỡng thì mốc tháng đủ chắc.
BIEN_SAT_NGUONG_NGAY = 31

# Quy ước tên file dữ liệu Freqtrade futures: `ARKM_USDT_USDT-1h-futures.feather`,
# `ARKM_USDT_USDT-1h-funding_rate.feather`, `1000PEPE_USDT_USDT-4h-mark.feather`.
_TEN_FILE_FUTURES = re.compile(r"^(?P<base>.+)_USDT_USDT-[^/]+\.feather$")


class ThuMucExploreError(RuntimeError):
    """Không xác định được tập mã EXPLORE — fail-closed, không trả tập rỗng."""


def loai_tru_explore_hien_tai(
    ung_vien: Iterable[str], explore_hien_tai: Iterable[str]
) -> tuple[str, ...]:
    """Loại VĨNH VIỄN khỏi rổ `T1` mọi mã thuộc tập EXPLORE đã dùng, giữ thứ tự.

    🔄 `DR-D1-03` §1.1 (17/09/2026) — nghĩa ĐÚNG của `explore_hien_tai` là tập
    mã CÓ DỮ LIỆU EXPLORE (đọc bằng `ma_co_du_lieu_explore()`), KHÔNG phải khối
    `explore:` của `config/pool.yaml`. Docstring bản `4fe5068` ghi theo khối đó
    và là SAI: khối có 426 mã (mọi mã trượt tiêu chí đo 09/2026), áp nó loại 54
    mã của rổ `T1` — gồm 45 mã đủ tiêu chí giữa 2025 rồi suy giảm, tức tái tạo
    đúng lệch sống sót `TD-0247` sinh ra để sửa.

    Không ngoại lệ (spec §9c.4b ràng buộc (b)). Hàm KHÔNG hardcode tên mã nào.
    """
    loai = frozenset(explore_hien_tai)
    return tuple(s for s in ung_vien if s not in loai)


def loai_tru_tradifi_perpetual(
    ung_vien: Iterable[str], exchange_info_symbols: Sequence[dict]
) -> tuple[str, ...]:
    """TD-0247 bẫy (iii) / `DR-D1-01` §1 — ứng viên liệt kê từ kho lưu
    trữ tĩnh (`data.binance.vision`) chỉ lọc được theo TÊN (hậu tố
    `USDT`), nên hút cả `TRADIFI_PERPETUAL` (cổ phiếu token hoá đang
    giao dịch, ví dụ `AAPLUSDT`, `ANTHROPICUSDT` — kết thúc bằng `USDT`,
    `status=TRADING`, nhưng `contractType` KHÁC `"PERPETUAL"`).

    Loại bất kỳ mã nào XUẤT HIỆN trong `exchangeInfo` hôm nay với
    `contractType` KHÁC `"PERPETUAL"` — đó là tín hiệu chắc chắn nó
    không phải perpetual crypto, bất kể đã "huỷ niêm yết" theo nghĩa
    nào khác. Mã VẮNG MẶT hoàn toàn khỏi `exchangeInfo` (đã thật sự
    biến mất khỏi sàn — đúng ý `DR-D1-01`) KHÔNG bị loại ở đây: kho lưu
    trữ là nguồn DUY NHẤT còn giữ dấu vết của những mã đó.
    """
    khong_phai_perp_con_niem_yet = {
        s["symbol"] for s in exchange_info_symbols if s.get("contractType") != "PERPETUAL"
    }
    return tuple(s for s in ung_vien if s not in khong_phai_perp_con_niem_yet)


def ma_co_du_lieu_explore(thu_muc: Path) -> frozenset[str]:
    """`DR-D1-03` §1.1 — tập mã có dữ liệu trong thư mục EXPLORE (`futures/`).

    Fail-closed: thư mục không tồn tại, không có file `.feather` nào, hoặc có
    file `.feather` sai quy ước tên ⇒ raise `ThuMucExploreError`. Một tập RỖNG
    im lặng sẽ nhận lại vào rổ chính những mã phải loại — lệch đúng chiều PASS.
    """
    if not thu_muc.is_dir():
        raise ThuMucExploreError(f"không thấy thư mục EXPLORE: {thu_muc}")
    ma: set[str] = set()
    sai_ten: list[str] = []
    for f in thu_muc.iterdir():
        if f.suffix != ".feather":
            continue
        m = _TEN_FILE_FUTURES.match(f.name)
        if m is None:
            sai_ten.append(f.name)
            continue
        ma.add(f"{m.group('base')}USDT")
    if sai_ten:
        raise ThuMucExploreError(
            f"{len(sai_ten)} file .feather sai quy ước tên trong {thu_muc}, "
            f"không suy được mã (vd {sorted(sai_ten)[:3]}) — DỪNG, không đoán"
        )
    if not ma:
        raise ThuMucExploreError(f"thư mục EXPLORE {thu_muc} có 0 mã — DỪNG, không coi là rỗng")
    return frozenset(ma)


@dataclass(frozen=True)
class KetQuaMoc:
    """Rổ ĐỦ TIÊU CHÍ tại một mốc, trước khi loại EXPLORE/TRADIFI.

    Ba trạng thái tách riêng (N6): đủ tiêu chí · không đo được (404 / thiếu
    hàng của đúng ngày) · trượt tiêu chí. Không gộp "không đo được" vào "trượt".
    """

    moc: date
    ung_vien_song: tuple[str, ...]
    pool_dung: tuple[str, ...]
    khong_do_duoc_404: tuple[str, ...]
    khong_do_duoc_thieu_ngay: tuple[str, ...]
    onboard_chinh_xac: tuple[str, ...]
    onboard_xap_xi: int


def _thang_so(s: str) -> int:
    y, m = s.split("-")
    return int(y) * 12 + int(m)


def _dau_thang(s: str) -> date:
    y, m = s.split("-")
    return date(int(y), int(m), 1)


def _cuoi_thang(s: str) -> date:
    y, m = (int(x) for x in s.split("-"))
    return date(y + (m == 12), (m % 12) + 1, 1) - timedelta(days=1)


def _utc(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)


def dung_ro_tai_moc(
    moc: date,
    khoang_ton_tai: Mapping[str, Mapping[str, str | None]],
    *,
    doc_volume_thang: Callable[[str, int, int], Mapping[date, float]],
    age_floor_days: int,
    volume_floor_usdt: float,
) -> KetQuaMoc:
    """Rổ đủ tiêu chí §0.3 TẠI ngày `moc` — cùng logic `TD-0231`
    (`docs/du-lieu-do/do_td0231_pool_point_in_time.py::_dung_mot_moc`), đưa về
    `src/` để bộ sinh có xuất xứ gọi; kịch bản đo cũ giữ nguyên làm bằng chứng.

    `khoang_ton_tai[sym] = {"thang_dau": "YYYY-MM", "thang_cuoi": "YYYY-MM"}` (từ
    kho lưu trữ, artifact `TD-0230`). `doc_volume_thang(sym, nam, thang)` trả
    `{ngày: quote_volume}`; raise `NenThangKhongCoError` khi kho 404. Lỗi mạng
    khác (`KhoLuuTruError`) KHÔNG bị nuốt — fail-closed, khác kịch bản `TD-0231`
    vốn hạ lỗi đọc ngày onboard chính xác về mốc tháng.

    `delisted_at`: mã có `thang_cuoi` sớm hơn tháng cuối lớn nhất của toàn bộ kho
    coi như huỷ niêm yết cuối tháng đó (quy ước `TD-0231`).
    """
    thang_moc = _thang_so(f"{moc.year:04d}-{moc.month:02d}")
    co_du = {s: k for s, k in khoang_ton_tai.items() if k.get("thang_dau") and k.get("thang_cuoi")}
    if not co_du:
        raise ValueError("khoang_ton_tai rỗng — không dựng rổ trên 0 ứng viên")
    thang_cuoi_lon_nhat = max(k["thang_cuoi"] for k in co_du.values())  # type: ignore[type-var]

    song = sorted(
        s
        for s, k in co_du.items()
        if _thang_so(k["thang_dau"]) <= thang_moc <= _thang_so(k["thang_cuoi"])  # type: ignore[arg-type]
    )

    stats: list[SymbolStat] = []
    ko_404: list[str] = []
    ko_thieu_ngay: list[str] = []
    ob_chinh_xac: list[str] = []
    ob_xap_xi = 0

    for sym in song:
        k = co_du[sym]
        try:
            vol_thang = doc_volume_thang(sym, moc.year, moc.month)
        except NenThangKhongCoError:
            ko_404.append(sym)
            continue
        if moc not in vol_thang:
            ko_thieu_ngay.append(sym)
            continue

        onboard = _dau_thang(k["thang_dau"])  # type: ignore[arg-type]
        if abs((moc - onboard).days - age_floor_days) <= BIEN_SAT_NGUONG_NGAY:
            y, m = (int(x) for x in k["thang_dau"].split("-"))  # type: ignore[union-attr]
            try:
                onboard = min(doc_volume_thang(sym, y, m))
                ob_chinh_xac.append(sym)
            except NenThangKhongCoError:
                ob_xap_xi += 1
        else:
            ob_xap_xi += 1

        # `MT-59` / `DR-LOCKBOX-01` Q3 bước 2: có mốc ngừng giao dịch ĐO THẬT (artifact
        # `TD-0306`) thì dùng nó — không suy từ tháng cuối của kho, vốn kéo đời sống mã chết
        # tới tận tháng lớn nhất và gán `delisted_at = None`. Dữ liệu `TD-0230` không mang
        # khoá `moc_ngung` ⇒ nhánh cũ giữ nguyên ⇒ rổ `t0`/`t1` đã commit tái lập từng byte.
        if k.get("moc_ngung"):
            delisted_dt: datetime | None = datetime.fromisoformat(str(k["moc_ngung"]))
        else:
            delisted = None if k["thang_cuoi"] == thang_cuoi_lon_nhat else _cuoi_thang(k["thang_cuoi"])  # type: ignore[arg-type]
            delisted_dt = _utc(delisted) if delisted else None
        stats.append(
            SymbolStat(
                symbol=sym,
                onboard_date=_utc(onboard),
                quote_volume_24h=vol_thang[moc],
                delisted_at=delisted_dt,
            )
        )

    kq = pairlist_point_in_time(
        stats, t=_utc(moc), age_floor_days=age_floor_days, volume_floor_usdt=volume_floor_usdt
    )
    # Fail-closed: dữ liệu mang nhãn xuất xứ (`nguon_thang_cuoi`, artifact `TD-0306`) thì mọi
    # mã LỌT rổ phải có đời sống ĐO THẬT. Mã chỉ mang cận trên mà lọt rổ nghĩa là tập đã đo
    # không phủ rổ — đời sống của nó là đoán, không phải đo (N6). Không có nhãn ⇒ dữ liệu
    # cũ (`TD-0230`) ⇒ không áp, giữ tái lập được rổ `t0`/`t1`.
    if any("nguon_thang_cuoi" in k for k in co_du.values()):
        chua_do = sorted(s for s in kq.trading if co_du[s].get("nguon_thang_cuoi") != "do_that")
        if chua_do:
            raise ValueError(
                f"{len(chua_do)} mã lọt rổ tại {moc} nhưng đời sống CHƯA đo thật (chỉ là cận trên / "
                f"không đo được): {chua_do} — tập đã đo ở TD-0306 không phủ rổ, không dựng rổ trên số đoán"
            )
    return KetQuaMoc(
        moc=moc,
        ung_vien_song=tuple(song),
        pool_dung=kq.trading,
        khong_do_duoc_404=tuple(ko_404),
        khong_do_duoc_thieu_ngay=tuple(ko_thieu_ngay),
        onboard_chinh_xac=tuple(ob_chinh_xac),
        onboard_xap_xi=ob_xap_xi,
    )


@dataclass(frozen=True)
class RoT1:
    trading: tuple[str, ...]
    loai_explore_da_dung: tuple[str, ...]
    loai_tradifi: tuple[str, ...]


def ghep_ro_t1(
    pool_dung: Sequence[str],
    ma_explore_da_dung: Iterable[str],
    exchange_info_symbols: Sequence[dict],
) -> RoT1:
    """`DR-D1-03` §1 — rổ cuối = đủ tiêu chí tại `T1` − EXPLORE đã dùng − TRADIFI.

    Ghi riêng từng tập bị loại theo lý do (không gộp) để file rổ tự giải thích.
    """
    sau_explore = loai_tru_explore_hien_tai(pool_dung, ma_explore_da_dung)
    sau_tradifi = loai_tru_tradifi_perpetual(sau_explore, exchange_info_symbols)
    return RoT1(
        trading=tuple(sorted(sau_tradifi)),
        loai_explore_da_dung=tuple(sorted(set(pool_dung) - set(sau_explore))),
        loai_tradifi=tuple(sorted(set(sau_explore) - set(sau_tradifi))),
    )
