"""TD-0254 — chọn giá trị tham số từ kết quả calibration (`DR-D5-01` §5).

Tầng THUẦN: nhận `R_realized` theo lệnh đã tính sẵn (khoá = `(pair, giờ mở)`), không
đọc file, không biết Freqtrade — cùng khuôn `gates/ket_cuc.py`.

════ Vì sao HAI thước đo, không phải một ════

`DR-D5-01` §2.1 chia bảy tham số làm hai nhóm theo thứ chúng đổi:

    KẾT CỤC  (buf_sl_atr, tp1_haircut_pct, dg7_funding_frac, max_hold_bars_4h)
             giữ tập lệnh vào, đổi cách lệnh kết thúc ⇒ so CẶP trên tập giao
    LỌC LỆNH (zss_threshold, wick_close_upper_frac, v_min)
             đổi tập lệnh vào, lệnh chung giữ nguyên kết cục
             ⇒ đo riêng NHÓM LỆNH BỊ THÊM/BỚT

🔴 Dùng phép so cặp cho nhóm LỌC LỆNH là PASS RỖNG dựng sẵn: lệnh chung có
kết cục y hệt nên `d ≡ 0` trên tập giao ⇒ luôn *"không khác"* — hình dạng
`MT-21` (hai cột giống hệt nhau, bảng trông bình thường). Có test ghim ca đó.

════ Ngưỡng: > 0 SAU KHI trừ nhiễu, không thêm con số nào ════

Mọi phép trừ nhiễu đi qua `thue_nhieu()` / `dsr_hurdle()` (MT-03: một nguồn
sự thật, `h = √(2·ln 114) = 3,0777`). Không đặt ngưỡng hiệu ứng riêng — đó là
bịa một tham số không ai đăng ký (`DR-D4-09` §6). KHÔNG dùng `so_paired()`:
nó đòi `ty_le_vuot ∈ (0,1)` nên không biểu diễn được ngưỡng 0.

════ Kết cục là HÀNH ĐỘNG, không phải con số ════

`GIU_MOC` · `DOI` · `BO_DIEU_KIEN_C` · `PENDING`. `v_min` *"0 thắng"* trả
`BO_DIEU_KIEN_C`, KHÔNG trả `0.0` (`DR-D5-01` §3.1): ghi `0.0` vào cấu hình chỉ
*gần như* tắt (c), và việc bỏ một điều kiện spec gọi là bắt buộc đi qua một
thay đổi riêng có test, không lọt vào YAML dưới dạng một số.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Hashable, Mapping, Sequence

from tool_d.gates.dsr import N_DANG_KY, dsr_hurdle
from tool_d.gates.ket_cuc import thue_nhieu


class ChonGiaTriError(ValueError):
    """Đầu vào không đủ để quyết. Fail-closed: raise, KHÔNG lặng lẽ giữ mốc —
    *"không tính được"* mà trông như *"đã tính và giữ mốc"* là mất dấu lỗi."""


class MotPhia(Enum):
    """Kết luận về MỘT nhóm lệnh so với 0."""

    LOI_RO = "LOI_RO"
    LO_RO = "LO_RO"
    KHONG_PHAN_BIET = "KHONG_PHAN_BIET"
    PENDING = "PENDING"


class SoSanhLoc(Enum):
    LONG_TOT_HON = "LONG_TOT_HON"
    CHAT_TOT_HON = "CHAT_TOT_HON"
    KHONG_PHAN_BIET = "KHONG_PHAN_BIET"
    KHONG_LONG_NHAU = "KHONG_LONG_NHAU"
    PENDING = "PENDING"


class PhanXet(Enum):
    THANG_RO = "THANG_RO"
    KHONG_THANG = "KHONG_THANG"
    PENDING = "PENDING"


class HanhDong(Enum):
    GIU_MOC = "GIU_MOC"
    DOI = "DOI"
    BO_DIEU_KIEN_C = "BO_DIEU_KIEN_C"
    PENDING = "PENDING"


# ════ Nhóm một phía ════


@dataclass(frozen=True)
class KetQuaMotPhia:
    ket_luan: MotPhia
    n: int
    mean_r: float | None
    thue: float | None

    def dien_giai(self) -> str:
        if self.mean_r is None:
            return f"{self.ket_luan.value} — n = {self.n}"
        return f"{self.ket_luan.value} — mean {self.mean_r:.4f} ± thuế {self.thue:.4f} · n = {self.n}"


def _kiem_so(r: Mapping[Hashable, float], ten: str) -> None:
    for k, v in r.items():
        if v is None or v != v:
            raise ChonGiaTriError(f"{ten}[{k!r}] là {v!r} — 'chưa đo' KHÁC 'đo được' (N6)")


def _mean_std(xs: Sequence[float]) -> tuple[float, float]:
    n = len(xs)
    m = sum(xs) / n
    return m, math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def xet_mot_phia(r: Sequence[float], *, n_trials: int = N_DANG_KY) -> KetQuaMotPhia:
    """Nhóm lệnh này lời rõ / lỗ rõ / không phân biệt được so với 0.

        m − t > 0 ⇒ LOI_RO ;  m + t < 0 ⇒ LO_RO ;  còn lại KHONG_PHAN_BIET
        n < 2     ⇒ PENDING (không có std — N6, không đoán)
    """
    xs = [float(x) for x in r]
    if any(x != x for x in xs):
        raise ChonGiaTriError("có NaN trong R_realized — 'chưa đo' KHÁC 'đo được' (N6)")
    if len(xs) < 2:
        return KetQuaMotPhia(ket_luan=MotPhia.PENDING, n=len(xs), mean_r=None, thue=None)
    m, s = _mean_std(xs)
    t = thue_nhieu(std_r=s, n_trades=len(xs), n_trials=n_trials)
    if m - t > 0:
        kl = MotPhia.LOI_RO
    elif m + t < 0:
        kl = MotPhia.LO_RO
    else:
        kl = MotPhia.KHONG_PHAN_BIET
    return KetQuaMotPhia(ket_luan=kl, n=len(xs), mean_r=m, thue=t)


# ════ §5.2 — nhóm LỌC LỆNH ════


@dataclass(frozen=True)
class KetQuaSoLoc:
    ket_qua: SoSanhLoc
    phan_them: KetQuaMotPhia
    """Lệnh CHỈ có ở giá trị lỏng — đúng câu hỏi *"lệnh thêm vào có lời không"*."""
    n_giao: int
    n_chi_o_chat: int

    def dien_giai(self) -> str:
        return (
            f"{self.ket_qua.value} — phần thêm: {self.phan_them.dien_giai()} · "
            f"n_giao {self.n_giao} · chỉ ở chặt {self.n_chi_o_chat}"
        )


def so_loc_lenh(
    *, r_long: Mapping[Hashable, float], r_chat: Mapping[Hashable, float], n_trials: int = N_DANG_KY
) -> KetQuaSoLoc:
    """`DR-D5-01` §5.2 — hai giá trị kề nhau, `r_long` lỏng hơn, `r_chat` chặt hơn.

    `E` = lệnh chỉ có ở lỏng. Phần thêm lời rõ ⇒ lỏng tốt hơn; lỗ rõ ⇒ chặt tốt
    hơn. Có lệnh CHỈ ở chặt ⇒ hai tập không lồng nhau ⇒ phép này không áp được
    sạch ⇒ `KHONG_LONG_NHAU` (tầng chọn giữ mốc, không vá bằng một phép nghĩ ra
    sau khi thấy số).
    """
    _kiem_so(r_long, "r_long")
    _kiem_so(r_chat, "r_chat")
    chi_long = [r_long[k] for k in r_long if k not in r_chat]
    n_chi_chat = sum(1 for k in r_chat if k not in r_long)
    n_giao = sum(1 for k in r_long if k in r_chat)
    phan_them = xet_mot_phia(chi_long, n_trials=n_trials)
    if n_chi_chat > 0:
        kq = SoSanhLoc.KHONG_LONG_NHAU
    elif phan_them.ket_luan is MotPhia.PENDING:
        kq = SoSanhLoc.PENDING
    elif phan_them.ket_luan is MotPhia.LOI_RO:
        kq = SoSanhLoc.LONG_TOT_HON
    elif phan_them.ket_luan is MotPhia.LO_RO:
        kq = SoSanhLoc.CHAT_TOT_HON
    else:
        kq = SoSanhLoc.KHONG_PHAN_BIET
    return KetQuaSoLoc(ket_qua=kq, phan_them=phan_them, n_giao=n_giao, n_chi_o_chat=n_chi_chat)


# ════ §5.1 — nhóm KẾT CỤC ════


@dataclass(frozen=True)
class KetQuaSoKetCuc:
    ket_qua: PhanXet
    n_giao: int
    mean_hieu: float | None
    thue: float | None
    can_duoi_hieu: float | None
    """`mean(d) − h·std(d)/√n_giao` — thứ đem so với 0 và dùng để xếp hai ứng viên."""
    phan_them: KetQuaMotPhia
    """Lệnh chỉ có ở ứng viên."""
    phan_bo: KetQuaMotPhia
    """Lệnh chỉ có ở mốc — ứng viên đã bỏ chúng."""
    mau_thuan: bool
    """Phép giao nói thắng rõ nhưng phần chênh nói thua rõ."""

    def dien_giai(self) -> str:
        hieu = "—" if self.can_duoi_hieu is None else f"{self.can_duoi_hieu:.4f}"
        return (
            f"{self.ket_qua.value} — cận dưới hiệu {hieu} · n_giao {self.n_giao} · "
            f"thêm [{self.phan_them.dien_giai()}] · bỏ [{self.phan_bo.dien_giai()}]"
            + (" · 🔴 HAI PHÉP NÓI NGƯỢC NHAU" if self.mau_thuan else "")
        )


def so_ket_cuc(
    *, r_moc: Mapping[Hashable, float], r_thu: Mapping[Hashable, float], n_trials: int = N_DANG_KY
) -> KetQuaSoKetCuc:
    """`DR-D5-01` §5.1 — ứng viên có thắng rõ mốc không.

        d_i = R_thu,i − R_moc,i   trên tập GIAO
        thắng rõ ⟺ mean(d) − h·std(d)/√n_giao > 0  VÀ  phần chênh không nói thua rõ

    🔴 **DIỄN GIẢI, ghi ra để cãi lại được.** §5.1 viết *"áp thêm phép §5.2 cho
    phần chênh"*, nhưng §5.2 giả định tập lồng nhau (chỉ một phía có lệnh thêm).
    Với nhóm KẾT CỤC, đổi `buf_sl_atr` đổi cỡ lệnh ⇒ cổng kết nạp có thể vừa
    nhận thêm vừa loại bớt. Áp §5.2 cho TỪNG phía: ứng viên *"thua rõ ở phần
    chênh"* khi lệnh nó THÊM lỗ rõ, HOẶC lệnh nó BỎ lời rõ. Không thêm con số
    nào; cùng một phép một phía, dùng hai lần.
    """
    _kiem_so(r_moc, "r_moc")
    _kiem_so(r_thu, "r_thu")
    giao = [k for k in r_moc if k in r_thu]
    phan_them = xet_mot_phia([r_thu[k] for k in r_thu if k not in r_moc], n_trials=n_trials)
    phan_bo = xet_mot_phia([r_moc[k] for k in r_moc if k not in r_thu], n_trials=n_trials)
    thua_o_chenh = phan_them.ket_luan is MotPhia.LO_RO or phan_bo.ket_luan is MotPhia.LOI_RO

    if len(giao) < 2:
        return KetQuaSoKetCuc(
            ket_qua=PhanXet.PENDING, n_giao=len(giao), mean_hieu=None, thue=None,
            can_duoi_hieu=None, phan_them=phan_them, phan_bo=phan_bo, mau_thuan=False,
        )
    d = [float(r_thu[k]) - float(r_moc[k]) for k in giao]
    m, s = _mean_std(d)
    t = thue_nhieu(std_r=s, n_trades=len(d), n_trials=n_trials)
    can_duoi = m - t
    thang_giao = can_duoi > 0
    kq = PhanXet.THANG_RO if thang_giao and not thua_o_chenh else PhanXet.KHONG_THANG
    return KetQuaSoKetCuc(
        ket_qua=kq, n_giao=len(giao), mean_hieu=m, thue=t, can_duoi_hieu=can_duoi,
        phan_them=phan_them, phan_bo=phan_bo, mau_thuan=thang_giao and thua_o_chenh,
    )


# ════ Tầng CHỌN ════


@dataclass(frozen=True)
class QuyetDinh:
    hanh_dong: HanhDong
    gia_tri: object | None
    """Giá trị sau quyết định. `None` khi `BO_DIEU_KIEN_C`."""
    ly_do: str

    def dien_giai(self) -> str:
        return f"{self.hanh_dong.value} → {self.gia_tri!r} — {self.ly_do}"


def chon_ket_cuc(*, moc: object, ket_qua: Mapping[object, KetQuaSoKetCuc]) -> QuyetDinh:
    """§5.1 — không ứng viên nào thắng rõ ⇒ giữ mốc; cả hai thắng ⇒ lấy cận dưới
    hiệu lớn hơn. Mọi phép PENDING ⇒ `PENDING` (giá trị giữ mốc, N6)."""
    if not ket_qua:
        raise ChonGiaTriError("không có ứng viên nào để chọn")
    thang = {v: kq for v, kq in ket_qua.items() if kq.ket_qua is PhanXet.THANG_RO}
    if thang:
        v = max(thang, key=lambda x: thang[x].can_duoi_hieu)
        return QuyetDinh(HanhDong.DOI, v, f"thắng rõ: {thang[v].dien_giai()}")
    if all(kq.ket_qua is PhanXet.PENDING for kq in ket_qua.values()):
        return QuyetDinh(HanhDong.PENDING, moc, "mọi phép so thiếu mẫu (n_giao < 2)")
    return QuyetDinh(HanhDong.GIU_MOC, moc, "không ứng viên nào thắng rõ sau khi trừ nhiễu")


def chon_loc_lenh(
    *,
    thu_tu_long_den_chat: Sequence[object],
    moc: object,
    so_sanh: Mapping[tuple[object, object], KetQuaSoLoc],
    gia_tri_tat: object | None = None,
) -> QuyetDinh:
    """§5.2 — đi TỪNG BƯỚC từ mốc, mỗi bước cần bằng chứng riêng.

    `so_sanh[(lỏng, chặt)]` cho mỗi cặp KỀ NHAU. Về phía lỏng chỉ đi tiếp khi
    bước trước nói `LONG_TOT_HON`; về phía chặt khi `CHAT_TOT_HON`. Hai phía cùng
    đi được ⇒ không đơn điệu ⇒ **giữ mốc**. Cặp cần xét mà thiếu ⇒ raise.

    `gia_tri_tat` (vd `0` của `v_min`): chọn đúng giá trị đó ⇒ `BO_DIEU_KIEN_C`,
    không trả số (`DR-D5-01` §3.1).
    """
    tt = list(thu_tu_long_den_chat)
    if moc not in tt:
        raise ChonGiaTriError(f"mốc {moc!r} không nằm trong thứ tự {tt!r}")
    if len(set(map(repr, tt))) != len(tt):
        raise ChonGiaTriError(f"thứ tự có giá trị trùng: {tt!r}")
    i0 = tt.index(moc)

    def _lay(cap: tuple[object, object]) -> KetQuaSoLoc:
        if cap not in so_sanh:
            raise ChonGiaTriError(f"thiếu phép so cho cặp kề nhau {cap!r}")
        return so_sanh[cap]

    buoc_dau: list[KetQuaSoLoc] = []
    i = i0
    while i > 0:
        kq = _lay((tt[i - 1], tt[i]))
        if i == i0:
            buoc_dau.append(kq)
        if kq.ket_qua is not SoSanhLoc.LONG_TOT_HON:
            break
        i -= 1
    j = i0
    while j < len(tt) - 1:
        kq = _lay((tt[j], tt[j + 1]))
        if j == i0:
            buoc_dau.append(kq)
        if kq.ket_qua is not SoSanhLoc.CHAT_TOT_HON:
            break
        j += 1

    if i < i0 and j > i0:
        return QuyetDinh(HanhDong.GIU_MOC, moc, "KHÔNG ĐƠN ĐIỆU — cả phía lỏng lẫn phía chặt đều nói tốt hơn mốc")
    if i < i0 or j > i0:
        moi = tt[i] if i < i0 else tt[j]
        if gia_tri_tat is not None and moi == gia_tri_tat:
            return QuyetDinh(HanhDong.BO_DIEU_KIEN_C, None, f"giá trị tắt {gia_tri_tat!r} tốt hơn rõ")
        return QuyetDinh(HanhDong.DOI, moi, "đi từng bước từ mốc, mỗi bước tốt hơn rõ")
    if buoc_dau and all(kq.ket_qua is SoSanhLoc.PENDING for kq in buoc_dau):
        return QuyetDinh(HanhDong.PENDING, moc, "mọi bước đầu thiếu mẫu (phần thêm < 2 lệnh)")
    ghi = [kq.ket_qua.value for kq in buoc_dau]
    return QuyetDinh(HanhDong.GIU_MOC, moc, f"không bước nào tốt hơn rõ ({', '.join(ghi)})")


# ════ §5.3 — xác nhận cấu hình ghép ════


@dataclass(frozen=True)
class KetQuaXacNhan:
    xac_nhan: bool | None
    """`None` = không đủ mẫu để xét (N6) — tầng gọi giữ nguyên toàn bộ mốc."""
    delta: float
    se: float
    can_duoi: float
    n_giao: int
    n_chi_ghep: int
    n_chi_moc: int
    han_che: tuple[str, ...]

    def dien_giai(self) -> str:
        tt = {True: "XÁC NHẬN", False: "KHÔNG XÁC NHẬN", None: "PENDING"}[self.xac_nhan]
        return (
            f"{tt} — Δ {self.delta:.4f} − h·SE {self.delta - self.can_duoi:.4f} = {self.can_duoi:.4f} · "
            f"giao {self.n_giao} / chỉ ghép {self.n_chi_ghep} / chỉ mốc {self.n_chi_moc}"
        )


def xac_nhan_ghep(
    *, r_moc: Mapping[Hashable, float], r_ghep: Mapping[Hashable, float], n_trials: int = N_DANG_KY
) -> KetQuaXacNhan:
    """`DR-D5-01` §5.3 — chênh TỔNG R_realized, tách ba phần.

        Δ  = Σ_giao d  +  Σ_{chỉ ghép} R_realized  −  Σ_{chỉ mốc} R_realized
        SE = √( n_giao·var(d) + n_G'·var(R_chỉG) + n_A'·var(R_chỉA) )
        xác nhận ⟺ Δ − h·SE > 0

    Phần có `n < 2` góp 0 vào SE và được ghi hạn chế. Cả ba phần đều `n < 2`
    ⇒ `xac_nhan = None`.
    """
    _kiem_so(r_moc, "r_moc")
    _kiem_so(r_ghep, "r_ghep")
    giao = [k for k in r_moc if k in r_ghep]
    d = [float(r_ghep[k]) - float(r_moc[k]) for k in giao]
    chi_g = [float(r_ghep[k]) for k in r_ghep if k not in r_moc]
    chi_a = [float(r_moc[k]) for k in r_moc if k not in r_ghep]

    han_che: list[str] = []
    tong_var = 0.0
    du_mau = False
    for ten, xs in (("giao", d), ("chỉ ghép", chi_g), ("chỉ mốc", chi_a)):
        if len(xs) >= 2:
            _, s = _mean_std(xs)
            tong_var += len(xs) * s * s
            du_mau = True
        elif xs:
            han_che.append(f"phần {ten} có {len(xs)} lệnh (< 2) — góp 0 vào SE")
    delta = sum(d) + sum(chi_g) - sum(chi_a)
    se = math.sqrt(tong_var)
    can_duoi = delta - dsr_hurdle(n_trials) * se
    return KetQuaXacNhan(
        xac_nhan=(can_duoi > 0) if du_mau else None,
        delta=delta, se=se, can_duoi=can_duoi,
        n_giao=len(giao), n_chi_ghep=len(chi_g), n_chi_moc=len(chi_a),
        han_che=tuple(han_che),
    )


__all__ = [
    "ChonGiaTriError",
    "HanhDong",
    "KetQuaMotPhia",
    "KetQuaSoKetCuc",
    "KetQuaSoLoc",
    "KetQuaXacNhan",
    "MotPhia",
    "PhanXet",
    "QuyetDinh",
    "SoSanhLoc",
    "chon_ket_cuc",
    "chon_loc_lenh",
    "so_ket_cuc",
    "so_loc_lenh",
    "xac_nhan_ghep",
    "xet_mot_phia",
]
