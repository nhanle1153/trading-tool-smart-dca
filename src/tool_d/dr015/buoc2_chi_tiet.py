"""TD-0168 — DR-015 Bước 2: PERSIST dấu vết từng ca (`chi_tiet`).

`do_ty_le_khong_khop()` trả `(khoảng, chi_tiet)` và docstring của nó nói
thẳng vì sao vế thứ hai tồn tại: *"một tỉ lệ tổng không cho biết ca nào
rơi vào đâu, và khi số trông lạ thì thứ cần đầu tiên là danh sách ca"*.
Nhưng vòng đo chốt của TD-0162 để `chi_tiet` trong thư mục tạm rồi bỏ, và
`dr015-buoc2-ty-le-khong-khop.json` chỉ giữ số tổng cùng vài phân vị. Lời
văn hứa một dấu vết mà artifact không có. Module này sinh ra dấu vết đó.

════ Ba điều phải nói thẳng, vì chúng đổi cách đọc kết quả ════

**1. Đây là một lần chạy MỚI, không phải dấu vết thừa kế.** Vòng đo chốt
của TD-0162 KHÔNG đi qua `do_ty_le_khong_khop()` — nó là kịch bản viết
thẳng, quét mỗi dump đúng một lần rồi phân loại tại chỗ, vì gọi hàm kia
một cách ngây thơ sẽ mở lại 45 dump (599 MB) tới 91 lần. Cùng LUẬT phân
loại, khác ĐƯỜNG CHẠY. Nên `chi_tiet` ở đây không được coi là "dấu vết
của con số đã niêm phong" — nó là dấu vết của một lần chạy độc lập, và
chỉ có giá trị khi lần chạy đó **cho ra đúng con số đã niêm phong**.

Vì vậy module TỪ CHỐI GHI nếu kết quả tính lại lệch artifact ở bất kỳ đại
lượng nào không phụ thuộc phương pháp (xem `_doi_chieu_niem_phong`). Ghi
ra rồi báo lệch là để lại hai bộ số cho người sau tự hoà giải.

**2. Lần này hàm được test CHÍNH LÀ hàm sinh số.** Đó là lý do module
này gọi `do_ty_le_khong_khop()` thay vì chép luật phân loại: 33 phép kiểm
của TD-0162 canh một hàm mà đường sản xuất chưa từng gọi. Câu hỏi chẩn
đoán của dự án (*"ca sai đó có đi qua đường sản xuất thật không?"*) ở đây
xuất hiện ở chiều ngược lại — thứ được canh không nằm trên đường chạy.

**3. KHÔNG chạm ba artifact mà `L-Z56` niêm phong.** Cổng D3.5 đã đóng và
ghi `d3_5_git_sha`; sửa một trong ba file đó bây giờ làm "thứ cổng đã
thấy" khác "thứ nằm trên đĩa", dù cả hai đều hợp lệ. `chi_tiet` là dấu
vết CHẨN ĐOÁN, không phải kết quả — nó thuộc file riêng, và file riêng đó
**không** được thêm vào `FILE_KET_QUA_D35` (danh sách đóng đúng ba).

════ Vì sao có lớp nạp gom theo ngày ════

`do_ty_le_khong_khop()` gọi `nap_giao_dich(symbol, tu_ms, het_ms)` một
lần cho MỖI sự kiện. Nạp ngây thơ = giải nén lại cùng một dump cho mọi sự
kiện rơi vào ngày đó. `NapGomTheoNgay` giữ dump đã phân tích trong bộ nhớ
và **giải phóng ngay khi không sự kiện nào còn cần** — nên bộ nhớ bị chặn
theo cửa sổ chứ không theo tổng số sự kiện, mà mỗi dump vẫn chỉ đọc một
lượt.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from tool_d.api_client.binance_public import tai_dump_agg_trades
from tool_d.fill_probe import (
    GiaoDich,
    KhoangNoFill,
    SuKienChoKhop,
    do_ty_le_khong_khop,
    doc_dump_agg_trades,
    loc_cua_so,
)

DEFAULT_DU_LIEU_THO_PATH = Path("docs/du-lieu-do/dr015-luot-khop-tranche.json")
DEFAULT_NIEM_PHONG_PATH = Path("docs/du-lieu-do/dr015-buoc2-ty-le-khong-khop.json")
DEFAULT_CHI_TIET_PATH = Path("docs/du-lieu-do/dr015-buoc2-chi-tiet.json")

# ±3 giờ quanh `order_filled_timestamp` — cùng cửa sổ vòng chốt của
# TD-0162 đã dùng (`ket_qua.cua_so` của artifact niêm phong). KHÔNG phải
# một lựa chọn mới: đổi con số này là đo một thứ khác, và lúc đó phép đối
# chiếu bên dưới sẽ đỏ, đúng như nó phải thế.
CUA_SO_MS = 3 * 60 * 60 * 1000

# Sai số cho phép khi đối chiếu với artifact: artifact làm tròn 4 chữ số
# thập phân, nên so ở đúng độ chính xác đó. KHÔNG phải biên "gần đúng".
LAM_TRON_ARTIFACT = 4


class Buoc2ChiTietError(RuntimeError):
    """Không sinh được dấu vết tin cậy. Fail-closed: raise chứ không ghi
    ra một file mà chính ta biết là không khớp con số đã niêm phong."""


# ── Dựng sự kiện từ dữ liệu thô ───────────────────────────────────────

def _symbol_san(pair: str) -> str:
    """`"1000BONK/USDT:USDT"` → `"1000BONKUSDT"` (dạng tên dump của sàn)."""
    return pair.split("/")[0] + "USDT"


def dung_su_kien(du_lieu_tho: dict[str, Any]) -> tuple[list[SuKienChoKhop], list[int]]:
    """91 lượt khớp → 91 `SuKienChoKhop`, kèm số tranche của từng cái.

    `den_ms = fill_ts_ms` là **mốc backtest**, không phải lần chạm giá
    thật — đó chính là lý do cửa sổ mở về CẢ HAI phía (xem docstring của
    `do_ty_le_khong_khop`). `nhan` là chỉ số dòng trong mảng `luot_khop`,
    để một dòng trong dấu vết truy thẳng về dòng dữ liệu thô sinh ra nó.

    `tranche` trả riêng chứ không nhét vào `SuKienChoKhop`: cấu trúc đó
    thuộc `fill_probe` và không biết gì về tranche — thêm trường vào nó
    chỉ để tiện cho một chỗ gọi là làm bẩn một khuôn dùng chung.
    """
    rows = du_lieu_tho["luot_khop"]
    if not rows:
        raise Buoc2ChiTietError("dữ liệu thô không có lượt khớp nào")
    su_kien = [
        SuKienChoKhop(
            symbol=_symbol_san(r["pair"]),
            huong=r["huong"],
            p=r["p_ke_hoach"],
            den_ms=r["fill_ts_ms"],
            nhan=str(i),
        )
        for i, r in enumerate(rows)
    ]
    return su_kien, [r["tranche"] for r in rows]


def _ngay_utc(ts_ms: int) -> date:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).date()


def _ngay_can(*, tu_ms: int, het_ms: int) -> list[date]:
    """Mọi ngày UTC mà cửa sổ chạm tới — cửa sổ bắc qua nửa đêm thì cần
    HAI dump, và bỏ sót cái thứ hai sẽ lặng lẽ làm cửa sổ hẹp lại."""
    d, het = _ngay_utc(tu_ms), _ngay_utc(het_ms)
    ra = []
    while d <= het:
        ra.append(d)
        d += timedelta(days=1)
    return ra


# ── Nạp giao dịch, gom theo ngày ──────────────────────────────────────

class NapGomTheoNgay:
    """`nap_giao_dich` tiêm vào `do_ty_le_khong_khop()`, đọc mỗi dump một
    lượt và giữ nó chỉ trong khoảng còn có sự kiện cần.

    🔴 Lớp này bám vào THỨ TỰ gọi của `do_ty_le_khong_khop()` (nó duyệt
    `su_kien` tuần tự). Ràng buộc đó được kiểm tường minh ở mỗi lời gọi
    thay vì tin ngầm: gọi sai thứ tự → raise. Bám ngầm vào thứ tự rồi im
    lặng là cách một dòng dấu vết bị gán cho nhầm sự kiện — đúng loại lỗi
    không phép kiểm tổng nào bắt được.
    """

    def __init__(
        self,
        su_kien: Sequence[SuKienChoKhop],
        *,
        truoc_ms: int,
        sau_ms: int,
        thu_muc_cache: Path,
        tai: Callable[..., Path] | None = None,
        doc: Callable[[Path], Any] | None = None,
    ) -> None:
        # Giải quyết tên ở LÚC CHẠY, không phải lúc định nghĩa lớp — để
        # test thay được cửa mạng mà không cần một tham số riêng chạy dọc
        # `chay()`.
        self._su_kien = list(su_kien)
        self._truoc_ms = truoc_ms
        self._sau_ms = sau_ms
        self._thu_muc_cache = Path(thu_muc_cache)
        self._tai = tai or tai_dump_agg_trades
        self._doc = doc or doc_dump_agg_trades
        self._i = 0
        self._kho: dict[tuple[str, date], list[GiaoDich]] = {}

        # Sự kiện CUỐI CÙNG cần mỗi (symbol, ngày) — để giải phóng đúng
        # lúc, không giữ cả 45 dump trong bộ nhớ.
        self._can_toi: dict[tuple[str, date], int] = {}
        for i, sk in enumerate(self._su_kien):
            for ngay in _ngay_can(tu_ms=sk.den_ms - truoc_ms, het_ms=sk.den_ms + sau_ms):
                self._can_toi[(sk.symbol, ngay)] = i

        # Dấu vết phụ, ghi trong lúc nạp vì chỉ ở đây mới còn giao dịch
        # thô: thời điểm XUYÊN đầu tiên (giao dịch đầu tiên vượt qua `p`
        # theo chiều lệnh). Nó là thứ dựng lại được `tre_so_voi_moc_
        # backtest_phut` của artifact — không có nó thì khối số đó cũng
        # không có dấu vết nào phía sau, cùng một lỗ hổng với `chi_tiet`.
        self.ts_xuyen_dau_ms: list[int | None] = []
        self.so_lan_doc_dump = 0

    def _lay_ngay(self, symbol: str, ngay: date) -> list[GiaoDich]:
        khoa = (symbol, ngay)
        if khoa not in self._kho:
            duong_dan = self._tai(symbol=symbol, ngay=ngay, thu_muc_cache=self._thu_muc_cache)
            self._kho[khoa] = list(self._doc(duong_dan))
            self.so_lan_doc_dump += 1
        return self._kho[khoa]

    def __call__(self, symbol: str, tu_ms: int, het_ms: int) -> list[GiaoDich]:
        if self._i >= len(self._su_kien):
            raise Buoc2ChiTietError(
                f"gọi nạp lần thứ {self._i + 1} nhưng chỉ có {len(self._su_kien)} sự kiện"
            )
        sk = self._su_kien[self._i]
        cho_doi = (sk.symbol, sk.den_ms - self._truoc_ms, sk.den_ms + self._sau_ms)
        if (symbol, tu_ms, het_ms) != cho_doi:
            raise Buoc2ChiTietError(
                f"sự kiện #{self._i} chờ cửa sổ {cho_doi} nhưng bị hỏi {(symbol, tu_ms, het_ms)} "
                "— thứ tự gọi không khớp, dấu vết sẽ gán nhầm sự kiện"
            )

        gd: list[GiaoDich] = []
        for ngay in _ngay_can(tu_ms=tu_ms, het_ms=het_ms):
            gd.extend(loc_cua_so(self._lay_ngay(symbol, ngay), tu_ms=tu_ms, den_ms=het_ms))
        gd.sort(key=lambda g: g.ts_ms)

        xuyen = (
            (g for g in gd if g.gia < sk.p)
            if sk.huong == "long"
            else (g for g in gd if g.gia > sk.p)
        )
        dau = next(xuyen, None)
        self.ts_xuyen_dau_ms.append(None if dau is None else dau.ts_ms)

        self._i += 1
        for khoa in [k for k, cuoi in self._can_toi.items() if cuoi < self._i and k in self._kho]:
            del self._kho[khoa]
        return gd


# ── Thống kê + đối chiếu với artifact đã niêm phong ───────────────────

def _phan_vi(gia_tri: Sequence[float], q: float) -> float:
    """Nội suy tuyến tính (mặc định của `numpy.percentile`) — CÙNG quy tắc
    với `_p90()` của TD-0161; có phép kiểm ghim hai bên khớp nhau ở q=0,9
    để chúng không trôi lệch về sau."""
    xs = sorted(gia_tri)
    n = len(xs)
    if n == 0:
        raise Buoc2ChiTietError("không có giá trị nào để lấy phân vị")
    if n == 1:
        return xs[0]
    vi_tri = q * (n - 1)
    duoi, tren = math.floor(vi_tri), math.ceil(vi_tri)
    if duoi == tren:
        return xs[duoi]
    trong_so = vi_tri - duoi
    return xs[duoi] * (1 - trong_so) + xs[tren] * trong_so


def _bien_xam_nhap_pct(c: dict[str, Any]) -> float | None:
    """Giá cực trị thật so với `p` kế hoạch, tính theo %. Âm = đã xuyên
    qua `p` theo chiều có lợi cho việc khớp."""
    gia = c["gia_thap_nhat"] if c["huong"] == "long" else c["gia_cao_nhat"]
    if gia is None:
        return None
    dau = 1.0 if c["huong"] == "long" else -1.0
    return dau * (gia - c["p"]) / c["p"] * 100.0


def _doi_chieu_niem_phong(
    *, khoang: KhoangNoFill, chi_tiet: list[dict[str, Any]], niem_phong: dict[str, Any]
) -> dict[str, Any]:
    """Lần chạy này phải cho ra ĐÚNG con số đã niêm phong, nếu không thì
    không ghi gì cả.

    Chỉ đối chiếu các đại lượng **không phụ thuộc phương pháp** — số đếm,
    min, max, trung vị của mẫu lẻ (n=91), và số ca vượt ngưỡng. P10/P25/
    P75/P90 cố ý ĐỨNG NGOÀI phép đối chiếu: artifact không ghi nó dùng
    cách nội suy nào, nên một chênh lệch ở đó sẽ là chênh lệch về quy ước
    chứ không phải về dữ liệu, và một phép kiểm báo đỏ vì lý do sai là
    phép kiểm sớm muộn bị gỡ.
    """
    lech: list[str] = []

    def so_sanh(ten: str, moi: Any, cu: Any) -> None:
        if isinstance(moi, float) or isinstance(cu, float):
            moi, cu = round(float(moi), LAM_TRON_ARTIFACT), round(float(cu), LAM_TRON_ARTIFACT)
        if moi != cu:
            lech.append(f"{ten}: tính lại = {moi!r}, artifact niêm phong = {cu!r}")

    kq = niem_phong["ket_qua"]
    so_sanh("chac_chan_khop", khoang.so_chac_chan_khop, kq["chac_chan_khop"])
    so_sanh("bat_dinh", khoang.so_bat_dinh, kq["bat_dinh"])
    so_sanh("chac_chan_khong_khop", khoang.so_chac_chan_khong_khop, kq["chac_chan_khong_khop"])
    if not (khoang.thap.is_ok() and khoang.cao.is_ok()):
        lech.append("p_nf tính lại là `unreadable` trong khi artifact có số")
    else:
        so_sanh("p_nf_thap", khoang.thap.value, kq["p_nf_thap"])
        so_sanh("p_nf_cao", khoang.cao.value, kq["p_nf_cao"])

    biens = [b for c in chi_tiet if (b := _bien_xam_nhap_pct(c)) is not None]
    if len(biens) != len(chi_tiet):
        lech.append(f"chỉ {len(biens)}/{len(chi_tiet)} ca có giá cực trị — cửa sổ rỗng ở đâu đó")
    else:
        bn = niem_phong["bien_xam_nhap_pct"]
        so_sanh("bien.sau_nhat", min(biens), bn["sau_nhat"])
        so_sanh("bien.nong_nhat", max(biens), bn["nong_nhat"])
        so_sanh("bien.trung_vi", _phan_vi(biens, 0.5), bn["trung_vi"])
        so_sanh(
            "bien.so_ca_nong_hon_0_05pct",
            sum(1 for b in biens if b > -0.05),
            bn["so_ca_nong_hon_0_05pct"],
        )

    tres = [c["tre_phut"] for c in chi_tiet if c["tre_phut"] is not None]
    if len(tres) == len(chi_tiet):
        tr = niem_phong["tre_so_voi_moc_backtest_phut"]
        so_sanh("tre.min", min(tres), tr["min"])
        so_sanh("tre.max", max(tres), tr["max"])
        so_sanh("tre.trung_vi", _phan_vi(tres, 0.5), tr["trung_vi"])
        so_sanh("tre.so_ca_xuyen_TRUOC_moc", sum(1 for t in tres if t < 0), tr["so_ca_xuyen_TRUOC_moc"])
    else:
        lech.append(f"chỉ {len(tres)}/{len(chi_tiet)} ca có thời điểm xuyên")

    if lech:
        raise Buoc2ChiTietError(
            "🛑 TỪ CHỐI ghi dấu vết: lần chạy này KHÔNG cho ra con số đã niêm phong.\n"
            + "\n".join(f"  • {d}" for d in lech)
            + "\nDấu vết chỉ có giá trị khi nó là dấu vết của CHÍNH con số đang dùng. "
            "Ghi ra rồi báo lệch là để lại hai bộ số cho người sau tự hoà giải."
        )
    return {
        "so_ca": len(chi_tiet),
        "bien_xam_nhap_pct": {
            "sau_nhat": min(biens),
            "P10": _phan_vi(biens, 0.10),
            "trung_vi": _phan_vi(biens, 0.50),
            "P90": _phan_vi(biens, 0.90),
            "nong_nhat": max(biens),
        },
        "tre_phut": {
            "min": min(tres),
            "P25": _phan_vi(tres, 0.25),
            "trung_vi": _phan_vi(tres, 0.50),
            "P75": _phan_vi(tres, 0.75),
            "max": max(tres),
        },
        # Ghi thẳng ra thay vì để im: đây là những phân vị KHÔNG được đối
        # chiếu, nên người đọc sau sẽ gặp hai con số khác nhau cho cùng
        # một tên. Nói trước rằng chênh ở đây là chênh QUY ƯỚC nội suy —
        # dữ liệu đã khớp, vì min/max/trung vị đều khớp tuyệt đối.
        "phan_vi_KHONG_doi_chieu": {
            "_vi_sao": (
                "HAI QUY ƯỚC PHÂN VỊ KHÁC NHAU trong cùng một repo, và đây là chỗ "
                "chúng gặp nhau. File này nội suy tuyến tính (mặc định của "
                "numpy.percentile) — cùng quy tắc với _p90() của TD-0161, vốn ghi rõ "
                "lựa chọn đó trong docstring. Vòng đo chốt của TD-0162 dùng CHỈ SỐ CẮT "
                "CỤT, KHÔNG nội suy (xs[int(q*(n-1))]) và không ghi ra ở đâu cả "
                "(tác giả xác nhận 08/09/2026). Vì n=91, trung vị rơi đúng phần tử thứ "
                "46 và min/max không cần nội suy nên chúng khớp TUYỆT ĐỐI ở cả hai "
                "cách; còn 0,25*90 = 22,5 và 0,75*90 = 67,5 là chỗ BẮT BUỘC phải nội "
                "suy, nên P25/P75 lệch. Bốn ô dưới đây so cho biết chứ KHÔNG dùng để "
                "phán quyết: chênh ở đây là chênh QUY ƯỚC, không phải chênh dữ liệu — "
                "và điều đó đã được chứng minh chứ không phải phỏng đoán, vì mọi đại "
                "lượng không phụ thuộc phương pháp đều khớp."
            ),
            "bien.P10": {"tinh_lai": _phan_vi(biens, 0.10), "artifact": niem_phong["bien_xam_nhap_pct"].get("P10")},
            "bien.P90": {"tinh_lai": _phan_vi(biens, 0.90), "artifact": niem_phong["bien_xam_nhap_pct"].get("P90")},
            "tre.P25": {"tinh_lai": _phan_vi(tres, 0.25), "artifact": niem_phong["tre_so_voi_moc_backtest_phut"].get("P25")},
            "tre.P75": {"tinh_lai": _phan_vi(tres, 0.75), "artifact": niem_phong["tre_so_voi_moc_backtest_phut"].get("P75")},
        },
    }


# ── Chạy trọn ─────────────────────────────────────────────────────────

def chay(
    *,
    thu_muc_cache: Path,
    du_lieu_tho_path: Path = DEFAULT_DU_LIEU_THO_PATH,
    niem_phong_path: Path = DEFAULT_NIEM_PHONG_PATH,
    chi_tiet_path: Path = DEFAULT_CHI_TIET_PATH,
    truoc_ms: int = CUA_SO_MS,
    sau_ms: int = CUA_SO_MS,
    ghi: bool = True,
) -> dict[str, Any]:
    """Đo lại Bước 2 QUA `do_ty_le_khong_khop()`, đối chiếu artifact đã
    niêm phong, rồi ghi dấu vết từng ca ra file RIÊNG.

    Trả về nội dung đã ghi. `ghi=False` để chạy thử mà không đụng đĩa.
    """
    du_lieu_tho = json.loads(Path(du_lieu_tho_path).read_text(encoding="utf-8"))
    niem_phong = json.loads(Path(niem_phong_path).read_text(encoding="utf-8"))
    su_kien, tranche = dung_su_kien(du_lieu_tho)

    nap = NapGomTheoNgay(
        su_kien, truoc_ms=truoc_ms, sau_ms=sau_ms, thu_muc_cache=Path(thu_muc_cache)
    )
    khoang, chi_tiet = do_ty_le_khong_khop(
        su_kien=su_kien, truoc_ms=truoc_ms, sau_ms=sau_ms, nap_giao_dich=nap
    )

    for c, t, ts in zip(chi_tiet, tranche, nap.ts_xuyen_dau_ms, strict=True):
        c["tranche"] = t
        c["bien_xam_nhap_pct"] = _bien_xam_nhap_pct(c)
        c["ts_xuyen_dau_ms"] = ts
        c["tre_phut"] = None if ts is None else (ts - c["moc_backtest_ms"]) / 60_000.0

    tom_tat = _doi_chieu_niem_phong(khoang=khoang, chi_tiet=chi_tiet, niem_phong=niem_phong)

    noi_dung = {
        "_viec": "TD-0168 — dấu vết TỪNG CA của DR-015 Bước 2 (91 lượt khớp)",
        "_vi_sao_file_rieng": (
            "Ba artifact trong FILE_KET_QUA_D35 đã được cổng D3.5 niêm phong "
            "(d3_5_git_sha); sửa chúng bây giờ làm 'thứ cổng đã thấy' khác 'thứ trên "
            "đĩa'. Dấu vết là thứ CHẨN ĐOÁN, không phải kết quả — file này KHÔNG "
            "thuộc FILE_KET_QUA_D35 và không được thêm vào đó."
        ),
        "_duong_chay": (
            "Sinh bằng tool_d.dr015.buoc2_chi_tiet.chay(), gọi THẲNG "
            "fill_probe.do_ty_le_khong_khop(). Vòng đo chốt của TD-0162 dùng kịch bản "
            "viết thẳng, cùng luật phân loại nhưng KHÁC đường chạy — nên đây là một "
            "lần chạy MỚI, và nó chỉ được ghi ra sau khi khớp đúng artifact niêm phong."
        ),
        "_doi_chieu_niem_phong": (
            "ĐẠT — số đếm ba trạng thái, p_nf hai đầu, biên xâm nhập (sâu nhất / nông "
            "nhất / trung vị / số ca nông hơn 0,05%) và độ trễ (min / max / trung vị / "
            "số ca xuyên trước mốc) đều khớp docs/du-lieu-do/dr015-buoc2-ty-le-khong-"
            "khop.json. P10/P25/P75/P90 KHÔNG đối chiếu — hai bên dùng hai quy ước "
            "phân vị khác nhau, xem tom_tat.phan_vi_KHONG_doi_chieu._vi_sao."
        ),
        "_cua_so": {"truoc_ms": truoc_ms, "sau_ms": sau_ms},
        "_don_vi": {
            "bien_xam_nhap_pct": "% so với p kế hoạch; ÂM = đã xuyên qua p theo chiều lệnh",
            "tre_phut": "phút giữa lần XUYÊN đầu tiên và mốc backtest; ÂM = xuyên TRƯỚC mốc",
            "nhan": "chỉ số dòng trong mảng luot_khop của dr015-luot-khop-tranche.json",
        },
        "tom_tat": tom_tat,
        "chi_tiet": chi_tiet,
    }
    if ghi:
        Path(chi_tiet_path).write_text(
            json.dumps(noi_dung, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
    return noi_dung
