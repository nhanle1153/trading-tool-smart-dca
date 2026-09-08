"""TD-0162 — DR-015 Bước 2: đo tỷ lệ KHÔNG KHỚP của lệnh chờ tại mốc vùng.

Mục tiêu DUY NHẤT (DR-015 §2): đo ca **"giá chạm vùng nhưng lệnh KHÔNG
khớp"** — thứ backtest gần như chắc chắn đang giả định là *luôn khớp*.
Con số này chảy thẳng vào Δ_R rồi vào quy tắc phân xử Z0-vs-DCA (§4),
tức nó góp phần quyết định **kiến trúc** của cả hệ thống.

════ Vì sao suy từ dữ liệu khớp lệnh thật, không đặt lệnh trên testnet ════

Chốt ở `docs/decisions/DR-D35-01-moi-truong-do-buoc-2.md` (chủ dự án,
08/09/2026). Tóm tắt lý do, vì nó là thứ dễ bị "sửa cho tiện" về sau:
tỷ lệ không-khớp là hàm của **độ sâu sổ lệnh và dòng lệnh thật**; Binance
futures testnet có sổ lệnh RIÊNG, mỏng, phần lớn là bot thử — con số đo
ở đó nói về **một thị trường khác**. Đó là lỗi mà `N6` tồn tại để chặn:
một số tự tin nhưng sai nguy hiểm hơn hẳn một ô trống.

════ Nguyên tắc suy luận (DR-D35-01 §3.1) ════

Với lệnh **MUA chờ** tại giá `p`, xét mọi giao dịch THẬT trong cửa sổ:

  • có giao dịch ở giá **< p**  → CHẮC CHẮN KHỚP. Người bán đã xuyên qua
    mức đó; theo ưu tiên giá-thời gian, mọi lệnh mua chờ ở `p` phải được
    lấp hết TRƯỚC khi giá đi thấp hơn.
  • giá thấp nhất **đúng bằng p** → BẤT ĐỊNH. Có khớp hay không phụ
    thuộc vị trí trong hàng đợi — thứ dữ liệu giao dịch không nói được.
  • không giao dịch nào ở **≤ p** → CHẮC CHẮN KHÔNG KHỚP.

SHORT đảo dấu hoàn toàn.

🔴 **Đầu ra là một KHOẢNG, không phải một số.** Vùng bất định là chỗ ta
thật sự không biết; ép nó về một điểm là bịa ra thông tin. Module này
KHÔNG cung cấp hàm nào trả về "tỷ lệ không khớp" dạng vô hướng — muốn
một con số thì phải tự chọn đầu nào của khoảng, và khi đó người chọn
phải nhìn thấy mình đang chọn.

════ Ba thứ phương án này KHÔNG thấy được (DR-D35-01 §3.3) ════

  1. post-only bị sàn TỪ CHỐI (lệnh sẽ khớp ngay lúc đặt);
  2. khớp MỘT PHẦN;
  3. vị trí hàng đợi.

Cả ba đều rơi vào vùng **bất định**, tức được tính về phía `p_nf_cao` —
lệch về phía bất lợi cho DCA. Không cái nào có thể làm kết luận **lạc
quan hơn** thực tế, và đó là điều kiện để phép đo này dùng được dù không
hoàn hảo (LD-31: thước nghi ngờ thì nghi về phía bất lợi cho cơ chế phức
tạp hơn).
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from tool_d.measurement.tri_state import Measured

# DR-015 §2 (§14 #29): quy mô đã chốt TRƯỚC — dưới mức này thì tỷ lệ khớp
# ghi UNKNOWN, KHÔNG bịa số từ mẫu quá nhỏ.
SO_SU_KIEN_TOI_THIEU = 30


class FillProbeError(RuntimeError):
    """Dữ liệu vào không dùng được cho phép đo. Fail-closed: raise chứ
    không trả về một con số đã biết là không có cơ sở."""


class TrangThaiKhop(Enum):
    CHAC_CHAN_KHOP = "chac_chan_khop"
    BAT_DINH = "bat_dinh"
    CHAC_CHAN_KHONG_KHOP = "chac_chan_khong_khop"


@dataclass(frozen=True)
class GiaoDich:
    """Một giao dịch THẬT đã khớp trên sàn (từ dump `aggTrades`)."""

    ts_ms: int
    gia: float
    khoi_luong: float


def phan_loai_khop(
    *,
    huong: str,
    p: float,
    giao_dich: Sequence[GiaoDich],
) -> TrangThaiKhop:
    """Phân loại một lệnh chờ tại `p` theo ba trạng thái.

    `giao_dich` phải là các giao dịch trong CỬA SỔ mà lệnh nằm chờ — bên
    gọi chịu trách nhiệm cắt cửa sổ; hàm này không đoán hộ.

    Cửa sổ rỗng → `CHẮC CHẮN KHÔNG KHỚP`, KHÔNG phải `BẤT ĐỊNH`: không có
    giao dịch nào nghĩa là không có ai để khớp với ta. Đây là kết luận
    chắc chắn, không phải thiếu thông tin.
    """
    if huong not in ("long", "short"):
        raise FillProbeError(f"huong phải là 'long' hoặc 'short', nhận: {huong!r}")
    if p <= 0:
        raise FillProbeError(f"giá p phải > 0, nhận: {p}")

    if not giao_dich:
        return TrangThaiKhop.CHAC_CHAN_KHONG_KHOP

    if huong == "long":
        # Mua chờ tại p: khớp chắc khi có giao dịch THẤP HƠN p.
        thap_nhat = min(g.gia for g in giao_dich)
        if thap_nhat < p:
            return TrangThaiKhop.CHAC_CHAN_KHOP
        if thap_nhat == p:
            return TrangThaiKhop.BAT_DINH
        return TrangThaiKhop.CHAC_CHAN_KHONG_KHOP

    cao_nhat = max(g.gia for g in giao_dich)
    if cao_nhat > p:
        return TrangThaiKhop.CHAC_CHAN_KHOP
    if cao_nhat == p:
        return TrangThaiKhop.BAT_DINH
    return TrangThaiKhop.CHAC_CHAN_KHONG_KHOP


@dataclass(frozen=True)
class KhoangNoFill:
    """Tỷ lệ KHÔNG khớp, dạng KHOẢNG.

    `thap` = chỉ tính ca chắc chắn không khớp.
    `cao`  = cộng thêm toàn bộ vùng bất định (fail-closed).

    Không có thuộc tính nào trả về "một con số" — xem docstring module.
    """

    n: int
    so_chac_chan_khop: int
    so_bat_dinh: int
    so_chac_chan_khong_khop: int
    thap: Measured[float]
    cao: Measured[float]

    @property
    def du_su_kien(self) -> bool:
        return self.n >= SO_SU_KIEN_TOI_THIEU


def tong_hop(trang_thai: Iterable[TrangThaiKhop]) -> KhoangNoFill:
    """Gộp danh sách trạng thái thành khoảng `[thap, cao]`.

    `n < SO_SU_KIEN_TOI_THIEU` → cả hai đầu ghi **`unreadable`**, KHÔNG
    phải một tỉ lệ tính từ mẫu quá nhỏ (DR-015 §2 gọi tình huống này là
    `UNKNOWN`). Số đếm từng loại VẪN được giữ — chúng là quan sát thật,
    chỉ có phép chia thành tỉ lệ mới là thứ không đủ cơ sở.
    """
    ds = list(trang_thai)
    n = len(ds)
    khop = sum(1 for t in ds if t is TrangThaiKhop.CHAC_CHAN_KHOP)
    bat_dinh = sum(1 for t in ds if t is TrangThaiKhop.BAT_DINH)
    khong = sum(1 for t in ds if t is TrangThaiKhop.CHAC_CHAN_KHONG_KHOP)

    if n < SO_SU_KIEN_TOI_THIEU:
        ly_do = (
            f"chỉ {n} sự kiện < {SO_SU_KIEN_TOI_THIEU} đã chốt trước (DR-015 §2) "
            "— tỷ lệ khớp ghi UNKNOWN, §4 phải chạy kịch bản fail-closed"
        )
        return KhoangNoFill(
            n=n,
            so_chac_chan_khop=khop,
            so_bat_dinh=bat_dinh,
            so_chac_chan_khong_khop=khong,
            thap=Measured.unreadable(ly_do),
            cao=Measured.unreadable(ly_do),
        )

    return KhoangNoFill(
        n=n,
        so_chac_chan_khop=khop,
        so_bat_dinh=bat_dinh,
        so_chac_chan_khong_khop=khong,
        thap=Measured.ok(khong / n),
        cao=Measured.ok((khong + bat_dinh) / n),
    )


# ── Đọc dump aggTrades ────────────────────────────────────────────────
# Cột của dump futures/um: agg_trade_id, price, quantity, first_trade_id,
# last_trade_id, transact_time, is_buyer_maker. Một số ngày có dòng tiêu
# đề, một số ngày không — phải nhận cả hai, xem `_bo_dong_tieu_de`.

def _bo_dong_tieu_de(dong: list[str]) -> bool:
    """Dump của Binance KHÔNG nhất quán: có ngày kèm dòng tiêu đề, có
    ngày không. Nhận diện bằng cách thử ép kiểu — không dựa vào tên cột,
    vì tên cột cũng đã từng đổi giữa các giai đoạn."""
    try:
        float(dong[1])
        int(dong[5])
    except (ValueError, IndexError):
        return True
    return False


def doc_dump_agg_trades(duong_dan: Path) -> Iterator[GiaoDich]:
    """Đọc dump `.zip` thành dòng `GiaoDich`, theo luồng (không nạp cả
    ngày vào bộ nhớ — một ngày của mã sôi động có hàng triệu dòng)."""
    with zipfile.ZipFile(duong_dan) as z:
        ten = [n for n in z.namelist() if n.endswith(".csv")]
        if len(ten) != 1:
            raise FillProbeError(f"{duong_dan}: cần đúng 1 file .csv, thấy {ten}")
        with z.open(ten[0]) as f:
            for dong in csv.reader(io.TextIOWrapper(f, encoding="utf-8")):
                if not dong or _bo_dong_tieu_de(dong):
                    continue
                yield GiaoDich(ts_ms=int(dong[5]), gia=float(dong[1]), khoi_luong=float(dong[2]))


@dataclass(frozen=True)
class SuKienChoKhop:
    """Một lệnh chờ cần phân loại: đặt tại `p`, xét cửa sổ kết thúc lúc
    `den_ms`. Cửa sổ bắt đầu ở `den_ms − ttl_ms` (thời gian tối đa lệnh
    nằm chờ, §3.5 `entry_order_ttl_bars_1h`)."""

    symbol: str  # dạng sàn, VD "1000BONKUSDT"
    huong: str
    p: float
    den_ms: int
    nhan: str = ""  # để truy ngược về dòng gốc, không tham gia tính toán


def do_ty_le_khong_khop(
    *,
    su_kien: Sequence[SuKienChoKhop],
    truoc_ms: int,
    sau_ms: int,
    nap_giao_dich,
) -> tuple[KhoangNoFill, list[dict]]:
    """Chạy phép đo Bước 2 trên một danh sách sự kiện.

    🔴 **Cửa sổ phải mở về CẢ HAI phía của `den_ms`, và đó là bài học
    phải trả giá mới có** (08/09/2026). Bản đầu chỉ lùi về trước
    (`[den_ms − ttl, den_ms]`) và cho ra **15/91 "chắc chắn không khớp"**
    — một con số trông rất đáng báo động. Kiểm lại: **15/15 ca đó chạm
    được `p` trong 3 GIỜ SAU `den_ms`.**

    Nguyên nhân: `order_filled_timestamp` của backtest KHÔNG phải mốc giá
    thật chạm mức. Freqtrade đánh giá theo nến và đóng dấu theo nhịp xử
    lý của nó, nên mốc đó có thể đi TRƯỚC lần chạm thật (và TD-0115 đã ghi
    nhận chiều ngược lại: 29% ca chạm ở nến LIỀN TRƯỚC). Neo cửa sổ một
    phía vào một mốc lệch hai chiều là tự tạo ra kết quả.

    Nên `truoc_ms`/`sau_ms` là hai tham số RIÊNG và BẮT BUỘC — không có
    mặc định, để chỗ gọi phải nói rõ mình giả định gì về vòng đời lệnh.

    `nap_giao_dich(symbol, tu_ms, het_ms) -> Sequence[GiaoDich]` được TIÊM
    VÀO, không gọi mạng từ trong đây. Hai lý do, cả hai đều không phải
    thẩm mỹ: (1) `R1 Single Egress` — mọi lệnh gọi mạng nằm ở
    `api_client/binance_public.py`, module này không được mở cửa thứ hai;
    (2) test chạy được toàn bộ logic mà không đụng mạng, nên nó là phép
    kiểm thật chứ không phải phép kiểm bị skip khi offline.

    Trả về `(khoảng, chi_tiết_từng_sự_kiện)`. Chi tiết giữ lại để truy
    ngược — một tỉ lệ tổng không cho biết ca nào rơi vào đâu, và khi số
    trông lạ thì thứ cần đầu tiên là danh sách ca.
    """
    if truoc_ms < 0 or sau_ms < 0:
        raise FillProbeError(f"truoc_ms/sau_ms phải >= 0, nhận: {truoc_ms}/{sau_ms}")
    if truoc_ms + sau_ms <= 0:
        raise FillProbeError("cửa sổ rỗng: truoc_ms + sau_ms phải > 0")

    chi_tiet: list[dict] = []
    trang_thai: list[TrangThaiKhop] = []
    for sk in su_kien:
        tu_ms = sk.den_ms - truoc_ms
        het_ms = sk.den_ms + sau_ms
        gd = list(nap_giao_dich(sk.symbol, tu_ms, het_ms))
        tt = phan_loai_khop(huong=sk.huong, p=sk.p, giao_dich=gd)
        trang_thai.append(tt)
        chi_tiet.append(
            {
                "nhan": sk.nhan,
                "symbol": sk.symbol,
                "huong": sk.huong,
                "p": sk.p,
                "tu_ms": tu_ms,
                "moc_backtest_ms": sk.den_ms,
                "het_ms": het_ms,
                "so_giao_dich_trong_cua_so": len(gd),
                "gia_thap_nhat": min((g.gia for g in gd), default=None),
                "gia_cao_nhat": max((g.gia for g in gd), default=None),
                "trang_thai": tt.value,
            }
        )
    return tong_hop(trang_thai), chi_tiet


def loc_cua_so(
    giao_dich: Iterable[GiaoDich], *, tu_ms: int, den_ms: int
) -> list[GiaoDich]:
    """Cắt cửa sổ `[tu_ms, den_ms]` — BAO GỒM hai đầu.

    Quy ước bao-gồm chọn có chủ đích và ngược với `Fold` (nửa mở): ở đây
    hai đầu là **mốc giao dịch thật**, không phải ranh giới phân chia dữ
    liệu. Bỏ sót giao dịch ngay tại mốc sẽ đẩy một ca từ "chắc chắn khớp"
    xuống "bất định" — tức làm khoảng RỘNG ra chứ không hẹp lại, nhưng
    vẫn là sai và không nên dựa vào việc sai theo hướng an toàn.
    """
    if tu_ms > den_ms:
        raise FillProbeError(f"cửa sổ đảo ngược: tu_ms={tu_ms} > den_ms={den_ms}")
    return [g for g in giao_dich if tu_ms <= g.ts_ms <= den_ms]
