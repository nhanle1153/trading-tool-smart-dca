"""TD-0238 — Đỉnh equity phải BỀN VỮNG qua restart tiến trình (MT-40).

`ZoneAbsorption.py:286` khởi tạo `self._dinh_equity: float | None = None`
mỗi lần tiến trình strategy chạy — kể cả khi đó là một lần RESTART giữa
một đợt drawdown sâu, không phải lần chạy đầu tiên thật sự. Hậu quả:
`_dd_pct()` coi equity hiện tại là đỉnh, `dd_pct` về 0%, và `mult_dd()`
(`sizing.py`) không bao giờ chạm ngưỡng `soft`/`halt` — một trong BA
tầng Cấp C (`DR-D0PRE-04`, §12b.2) chặn vòng lặp thua lỗ tự vô hiệu hoá
sau mỗi lần restart.

Hai quyết định đã chốt qua `AskUserQuestion` với chủ dự án (14/09/2026):
(1) cơ chế = checkpoint SỐNG, ghi liên tục mỗi khi có đỉnh mới — KHÔNG
    tính lại từ DB Freqtrade (số dư gốc + cộng dồn `close_profit_abs`),
    vì cách đó bỏ sót phí funding tích luỹ trên vị thế ĐANG MỞ giữa hai
    lần đóng lệnh, có thể đánh giá THẤP đỉnh thật — nới lỏng HALT sai
    hướng an toàn;
(2) chính sách reset = KHÔNG BAO GIỜ — đỉnh là cực đại lịch sử của toàn
    bộ vòng đời sub-account Tool D, chỉ tăng không giảm. Không thêm
    tham số mới vào kiểm kê DOF (né bẫy `DR-D4-02`).
    🔄 THAY 17/09/2026 (`DR-D6D8-01` §4.2 + §8, chủ dự án), THI HÀNH ở TD-0426
    (26/09/2026 — trước đó mã vẫn chạy (2) cũ, `MT-40`): đỉnh đặt lại ở ĐÚNG HAI
    sự kiện có ghi sổ — `NAP_RUT` (đỉnh DỊCH đúng số tiền) và `ABORT` (chu trình
    giả thuyết mới, đỉnh mới = equity lần đọc kế tiếp). Ngoài hai sự kiện đó vẫn
    KHÔNG BAO GIỜ: không sau HALT, không theo lịch, không khi restart. Cấp C,
    không phải tham số, không vào kiểm kê DOF.

════ Sổ sự kiện `equity_peak_events.jsonl` (TD-0426) ════

Nằm CẠNH file trạng thái, append-only (khuôn N8): trạng thái ghi SỐ dòng đã áp
+ băm các dòng đó; lần đọc sau áp phần mới, và một dòng ĐÃ áp bị sửa/xoá ⇒ raise.

🔑 Quy ước thứ tự, để mọi lệch tạm thời giữa sổ và tiền thật đều ra phía AN
TOÀN (drawdown hiện CAO hơn thật ⇒ có thể HALT oan, không bao giờ che sụt thật):
ghi `NAP_RUT` dương (nạp) TRƯỚC khi chuyển tiền vào; ghi `NAP_RUT` âm (rút) SAU
khi tiền đã rời tài khoản.

Module này KHÔNG đổi ý nghĩa "equity" (vẫn `wallets.get_total()`, đã
thực hiện) — khoảng hở "equity phải gồm PnL chưa thực hiện" (§12c.5) đã
được `ZoneAbsorption.py` (dòng 61-67) hoãn có chủ đích tới D11, ngoài
phạm vi việc này.

════ Vì sao một module riêng, không gộp vào `sizing.py`/`risk_supervisor.py` ════

`sizing.py` giới hạn ở công thức §6.2 + `KeHoachCoLenh` — `mult_dd()`
bản thân không đổi, chỉ nguồn của `dd_pct` đổi. `risk_supervisor.py`/
`TrangThaiBenVung` thuộc tiến trình RISK SUPERVISOR RIÊNG (§6.6, không
import code bot, TD-0241) — nhét trạng thái tiến trình STRATEGY vào đó
phá đúng ranh giới process vừa dựng xong. Khuôn ghi/đọc nguyên tử CỐ Ý
lặp lại (không factor chung với `risk_supervisor.py`): file đó vừa niêm
phong ở TD-0241, và phần lặp lại chỉ là khuôn I/O chung (~15 dòng),
không phải công thức nghiệp vụ nhân đôi (MT-03 chỉ lo nhân đôi TÍN HIỆU).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

#: TD-0353 (`DR-TRIEN-KHAI-01`) — thay hằng `DUONG_DAN_MAC_DINH` dùng CHUNG mọi runmode. Dry-run D11 và lệnh live
#: tối thiểu D10 chạy song song; chung một file thì mỗi bên ghi đè đỉnh của bên kia ⇒ `mult_dd` của live tính trên
#: đỉnh của ví giấy (N11: dry-run TÁCH hẳn live).
THU_MUC_GOC = Path("runs/zone_absorption")
TEN_FILE = "equity_peak_state.json"
#: TD-0426 (`MT-40`) — sổ sự kiện đặt lại đỉnh, cùng thư mục với `TEN_FILE`.
TEN_SO_SU_KIEN = "equity_peak_events.jsonl"
NAP_RUT = "NAP_RUT"
ABORT = "ABORT"
#: Cấp C (`DR-D6D8-01` §4.2) — ĐÚNG HAI loại. Loại thứ ba trong sổ ⇒ raise, không bỏ qua.
LOAI_SU_KIEN = (NAP_RUT, ABORT)
BAM_RONG = hashlib.sha256(b"").hexdigest()
_BAM_HOP_LE = re.compile(r"^[0-9a-f]{64}$")


class DinhEquityError(ValueError):
    """Lỗi đọc/ghi/cập nhật đỉnh equity bền vững — fail-closed, không đoán (N6)."""


def duong_dan_theo_runmode(runmode: str) -> Path:
    """`runs/zone_absorption/<runmode>/equity_peak_state.json`. Chỉ live/dry_run có đỉnh bền vững."""
    if runmode not in ("live", "dry_run"):
        raise DinhEquityError(f"runmode {runmode!r} không có đỉnh equity bền vững — chỉ live/dry_run")
    return THU_MUC_GOC / runmode / TEN_FILE


@dataclass(frozen=True)
class DinhEquityBenVung:
    """Đỉnh equity ĐÃ QUAN SÁT, sống sót qua restart — bài học MT-40.
    Bất biến, cùng kỷ luật `KeHoachCoLenh`/`TrangThaiBenVung`."""

    dinh: float
    stake_currency: str  # phát hiện lệch đơn vị nếu config đổi stake_currency giữa hai lần chạy
    #: TD-0426 — số dòng đầu của sổ sự kiện ĐÃ áp vào `dinh` + băm các dòng đó (phát hiện sửa/xoá dòng cũ, N8).
    so_su_kien_da_ap: int = 0
    bam_su_kien_da_ap: str = BAM_RONG


def dinh_equity_moi(
    dinh_cu: DinhEquityBenVung | None, *, tong_hien_tai: float, stake_currency: str,
) -> DinhEquityBenVung:
    """Đỉnh MỚI = `max(đỉnh cũ, tong_hien_tai)` — CHÍNH SÁCH ĐÃ CHỐT:
    không bao giờ giảm, không bao giờ reset theo kỳ (14/09/2026, chủ dự án).

    - `dinh_cu=None` (lần đọc đầu tiên, chưa từng lưu) → đỉnh = `tong_hien_tai`.
    - `tong_hien_tai` NaN hoặc `<= 0` → raise (N6: không lấy số rác làm đỉnh).
    - `dinh_cu.stake_currency != stake_currency` → raise (fail-closed:
      không âm thầm trộn đơn vị nếu cấu hình đổi `stake_currency` giữa
      hai lần chạy).
    - `tong_hien_tai <= dinh_cu.dinh` → trả NGUYÊN `dinh_cu` (bất biến,
      không tạo instance mới khi không có gì đổi).
    """
    if math.isnan(tong_hien_tai) or tong_hien_tai <= 0:
        raise DinhEquityError(
            f"equity hiện tại phải hữu hạn và dương, nhận {tong_hien_tai} — "
            "một ví báo 0/âm/NaN là dấu hiệu đọc hỏng, không phải thị trường yên bình"
        )
    if dinh_cu is None:
        return DinhEquityBenVung(dinh=tong_hien_tai, stake_currency=stake_currency)
    if dinh_cu.stake_currency != stake_currency:
        raise DinhEquityError(
            f"đỉnh equity đã lưu ở đơn vị {dinh_cu.stake_currency!r}, cấu hình hiện tại "
            f"là {stake_currency!r} — không âm thầm trộn đơn vị"
        )
    if tong_hien_tai <= dinh_cu.dinh:
        return dinh_cu
    return replace(dinh_cu, dinh=tong_hien_tai)  # giữ bộ đếm sự kiện đã áp (TD-0426)


def luu_dinh_equity(trang_thai: DinhEquityBenVung, duong_dan: Path) -> None:
    """Ghi NGUYÊN TỬ (file tạm `.dang-ghi` + `rename`) — cùng khuôn
    `risk_supervisor.luu_trang_thai()`: tiến trình chết giữa chừng không
    được để lại một file mang TÊN THẬT nhưng nội dung dở dang."""
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    noi_dung = {
        "dinh": trang_thai.dinh,
        "stake_currency": trang_thai.stake_currency,
        "so_su_kien_da_ap": trang_thai.so_su_kien_da_ap,
        "bam_su_kien_da_ap": trang_thai.bam_su_kien_da_ap,
    }
    tam = duong_dan.with_name(duong_dan.name + ".dang-ghi")
    tam.write_text(json.dumps(noi_dung, indent=2, ensure_ascii=False), encoding="utf-8")
    tam.replace(duong_dan)


def doc_dinh_equity(duong_dan: Path) -> DinhEquityBenVung | None:
    """Chưa có file (lần khởi động ĐẦU TIÊN thật sự) → `None` — ca DUY
    NHẤT "chưa đọc được" hợp lệ đọc thành "chưa có đỉnh", vì gọi nơi cần
    biết equity HIỆN TẠI để dùng làm đỉnh đầu tiên (không có ở đây).

    File TỒN TẠI mà hỏng (JSON lỗi/thiếu khoá/kiểu sai/`dinh` NaN hoặc
    `<= 0`) ⇒ RAISE — KHÔNG âm thầm coi là sạch, vì file hỏng có thể
    đang che một đỉnh thật đã ghi trước đó; coi nó là "chưa có" sẽ tự
    gỡ HALT (N6, cùng lý do `risk_supervisor.doc_trang_thai()` raise).
    """
    if not duong_dan.exists():
        return None
    try:
        tho = json.loads(duong_dan.read_text(encoding="utf-8"))
        dinh = float(tho["dinh"])
        stake_currency = tho["stake_currency"]
        if not isinstance(stake_currency, str) or not stake_currency:
            raise ValueError(f"stake_currency phải là chuỗi không rỗng, nhận {stake_currency!r}")
        if math.isnan(dinh) or dinh <= 0:
            raise ValueError(f"dinh phải hữu hạn và dương, nhận {dinh}")
        # File ghi TRƯỚC TD-0426 không có hai khoá này — lúc đó sổ sự kiện chưa tồn tại, nên "chưa áp dòng nào" là
        # sự thật, không phải đoán. Có khoá mà sai kiểu ⇒ raise như mọi khoá khác.
        da_ap = tho.get("so_su_kien_da_ap", 0)
        bam = tho.get("bam_su_kien_da_ap", BAM_RONG)
        if type(da_ap) is not int or da_ap < 0:
            raise ValueError(f"so_su_kien_da_ap phải là số nguyên ≥ 0, nhận {da_ap!r}")
        if not isinstance(bam, str) or not _BAM_HOP_LE.match(bam):
            raise ValueError(f"bam_su_kien_da_ap phải là sha256 hex, nhận {bam!r}")
        return DinhEquityBenVung(
            dinh=dinh, stake_currency=stake_currency, so_su_kien_da_ap=da_ap, bam_su_kien_da_ap=bam,
        )
    except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as exc:
        raise DinhEquityError(
            f"đỉnh equity đã lưu ở {duong_dan} tồn tại nhưng KHÔNG đọc được: {exc} — "
            "không tự coi là sạch, có thể đang che một đỉnh thật đã ghi trước đó"
        ) from exc


# ════════════════════════ TD-0426 — sổ sự kiện đặt lại đỉnh (`MT-40`, `DR-D6D8-01` §4.2) ════════════════════════

_KHOA_SU_KIEN = {
    NAP_RUT: {"loai", "stake_currency", "so_tien", "luc_utc", "ghi_chu"},
    ABORT: {"loai", "stake_currency", "luc_utc", "ghi_chu"},
}


@dataclass(frozen=True)
class SuKienDinh:
    """Một dòng sổ. `so_tien` chỉ có ở `NAP_RUT` (dương = nạp, âm = rút); `ABORT` không mang số tiền."""

    loai: str
    stake_currency: str
    luc_utc: str
    ghi_chu: str
    so_tien: float | None = None

    def sang_dict(self) -> dict:
        d = {"loai": self.loai, "stake_currency": self.stake_currency, "luc_utc": self.luc_utc, "ghi_chu": self.ghi_chu}
        if self.loai == NAP_RUT:
            d["so_tien"] = self.so_tien
        return d


def duong_dan_so_su_kien(duong_dan_trang_thai: Path) -> Path:
    """Sổ nằm CẠNH file trạng thái ⇒ tách theo runmode y như đỉnh (TD-0353, N11)."""
    return duong_dan_trang_thai.with_name(TEN_SO_SU_KIEN)


def _doc_mot_dong(dong: str, so_thu_tu: int) -> SuKienDinh:
    try:
        tho = json.loads(dong)
    except json.JSONDecodeError as exc:
        raise DinhEquityError(f"sổ sự kiện dòng {so_thu_tu}: không phải JSON — {exc}") from exc
    if not isinstance(tho, dict):
        raise DinhEquityError(f"sổ sự kiện dòng {so_thu_tu}: phải là object JSON")
    loai = tho.get("loai")
    if loai not in LOAI_SU_KIEN:
        raise DinhEquityError(
            f"sổ sự kiện dòng {so_thu_tu}: loại {loai!r} KHÔNG hợp lệ — đỉnh equity chỉ được đặt lại ở ĐÚNG HAI "
            f"sự kiện {LOAI_SU_KIEN} (DR-D6D8-01 §4.2, Cấp C); không sau HALT, không theo lịch, không khi restart"
        )
    if set(tho) != _KHOA_SU_KIEN[loai]:
        raise DinhEquityError(
            f"sổ sự kiện dòng {so_thu_tu} ({loai}): khoá {sorted(tho)} ≠ {sorted(_KHOA_SU_KIEN[loai])}"
        )
    for k in ("stake_currency", "luc_utc", "ghi_chu"):
        if not isinstance(tho[k], str) or not tho[k].strip():
            raise DinhEquityError(f"sổ sự kiện dòng {so_thu_tu}: `{k}` phải là chuỗi không rỗng")
    so_tien = None
    if loai == NAP_RUT:
        so_tien = tho["so_tien"]
        if isinstance(so_tien, bool) or not isinstance(so_tien, (int, float)) or not math.isfinite(so_tien) \
                or so_tien == 0:
            raise DinhEquityError(
                f"sổ sự kiện dòng {so_thu_tu}: `so_tien` phải là số hữu hạn khác 0 (dương = nạp, âm = rút), "
                f"nhận {so_tien!r}"
            )
        so_tien = float(so_tien)
    return SuKienDinh(loai=loai, stake_currency=tho["stake_currency"], luc_utc=tho["luc_utc"],
                      ghi_chu=tho["ghi_chu"], so_tien=so_tien)


def doc_so_su_kien(duong: Path) -> list[tuple[str, SuKienDinh]]:
    """`[(dòng thô, sự kiện)]` theo thứ tự ghi. Chưa có file ⇒ `[]` (chưa từng có sự kiện — sự thật, không đoán).

    FAIL-CLOSED: dòng cuối không kết thúc bằng xuống dòng (ghi dở), dòng trống xen giữa, dòng nào sai hình ⇒ raise.
    """
    if not duong.exists():
        return []
    try:
        noi_dung = duong.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DinhEquityError(f"sổ sự kiện {duong} tồn tại nhưng KHÔNG đọc được: {exc}") from exc
    if not noi_dung:
        return []
    if not noi_dung.endswith("\n"):
        raise DinhEquityError(f"sổ sự kiện {duong}: dòng cuối không kết thúc bằng xuống dòng — có thể ghi dở")
    dong = noi_dung[:-1].split("\n")
    return [(d, _doc_mot_dong(d, i + 1)) for i, d in enumerate(dong)]


def _bam_cac_dong(dong_tho: Sequence[str]) -> str:
    return hashlib.sha256("".join(d + "\n" for d in dong_tho).encode("utf-8")).hexdigest()


def ghi_su_kien(duong: Path, su_kien: SuKienDinh) -> None:
    """Nối MỘT dòng vào sổ (append-only). Kiểm sự kiện bằng CHÍNH bộ đọc trước khi ghi — không ghi được thứ sau này
    không đọc lại được. Ghi bytes `\\n` để host Windows không đổi thành CRLF (sẽ lệch băm các dòng đã áp)."""
    dong = json.dumps(su_kien.sang_dict(), ensure_ascii=False, sort_keys=True)
    _doc_mot_dong(dong, 0)
    doc_so_su_kien(duong)  # sổ hiện có phải đọc được, không nối vào một sổ hỏng
    duong.parent.mkdir(parents=True, exist_ok=True)
    with duong.open("ab") as f:
        f.write((dong + "\n").encode("utf-8"))


def ap_su_kien_moi(
    dinh_cu: DinhEquityBenVung | None, *, so_su_kien: Path, stake_currency: str,
) -> tuple[float | None, int, str]:
    """Áp các dòng sổ CHƯA áp lên `dinh_cu`. Trả `(đỉnh | None, số dòng đã áp, băm các dòng đã áp)`.

    - `NAP_RUT` ⇒ đỉnh DỊCH đúng `so_tien` (không về mức hiện tại). Chưa có đỉnh ⇒ không có gì để dịch: lần đọc
      equity kế tiếp đã gồm khoản nạp/rút đó.
    - `ABORT` ⇒ đỉnh = `None`: chu trình mới, đỉnh mới là equity ở lần đọc kế tiếp.
    - Dòng ĐÃ áp bị sửa/xoá (băm lệch) hoặc sổ ngắn đi ⇒ raise (append-only, N8).
    - Rút làm đỉnh ≤ 0, hoặc lệch `stake_currency` ⇒ raise (không trộn đơn vị, không bịa đỉnh).
    """
    ds = doc_so_su_kien(so_su_kien)
    da_ap = dinh_cu.so_su_kien_da_ap if dinh_cu is not None else 0
    bam = dinh_cu.bam_su_kien_da_ap if dinh_cu is not None else BAM_RONG
    if len(ds) < da_ap:
        raise DinhEquityError(
            f"sổ sự kiện {so_su_kien} còn {len(ds)} dòng nhưng đỉnh đã áp {da_ap} — sổ bị cắt/xoá (append-only, N8)"
        )
    if _bam_cac_dong([d for d, _ in ds[:da_ap]]) != bam:
        raise DinhEquityError(
            f"sổ sự kiện {so_su_kien}: {da_ap} dòng ĐÃ áp không còn khớp băm — dòng cũ bị sửa (append-only, N8)"
        )
    dinh = dinh_cu.dinh if dinh_cu is not None else None
    for i, (_, sk) in enumerate(ds[da_ap:], start=da_ap + 1):
        if sk.stake_currency != stake_currency:
            raise DinhEquityError(
                f"sổ sự kiện dòng {i}: đơn vị {sk.stake_currency!r} ≠ cấu hình {stake_currency!r} — không trộn đơn vị"
            )
        if sk.loai == ABORT:
            dinh = None
        elif dinh is not None:
            dinh += sk.so_tien  # type: ignore[operator]
            if dinh <= 0:
                raise DinhEquityError(f"sổ sự kiện dòng {i}: rút {sk.so_tien} làm đỉnh ≤ 0 ({dinh})")
    return dinh, len(ds), _bam_cac_dong([d for d, _ in ds])


def cap_nhat_dinh(
    dinh_cu: DinhEquityBenVung | None, *, tong_hien_tai: float, stake_currency: str, so_su_kien: Path | None,
) -> DinhEquityBenVung:
    """Đường DUY NHẤT chiến lược cập nhật đỉnh: áp sự kiện mới (nếu có sổ) rồi `dinh_equity_moi()`.

    `so_su_kien=None` (backtest — không đỉnh bền vững) ⇒ đúng hành vi `dinh_equity_moi()` cũ.
    """
    if so_su_kien is None:
        return dinh_equity_moi(dinh_cu, tong_hien_tai=tong_hien_tai, stake_currency=stake_currency)
    dinh, da_ap, bam = ap_su_kien_moi(dinh_cu, so_su_kien=so_su_kien, stake_currency=stake_currency)
    co_so = (
        DinhEquityBenVung(dinh=dinh, stake_currency=stake_currency, so_su_kien_da_ap=da_ap, bam_su_kien_da_ap=bam)
        if dinh is not None else None
    )
    moi = dinh_equity_moi(co_so, tong_hien_tai=tong_hien_tai, stake_currency=stake_currency)
    if co_so is None:  # sau ABORT / lần đầu: `dinh_equity_moi` dựng mới, gắn lại bộ đếm
        moi = replace(moi, so_su_kien_da_ap=da_ap, bam_su_kien_da_ap=bam)
    return moi


__all__ = [
    "ABORT",
    "BAM_RONG",
    "LOAI_SU_KIEN",
    "NAP_RUT",
    "TEN_SO_SU_KIEN",
    "SuKienDinh",
    "ap_su_kien_moi",
    "cap_nhat_dinh",
    "doc_so_su_kien",
    "duong_dan_so_su_kien",
    "ghi_su_kien",
    "THU_MUC_GOC",
    "DinhEquityBenVung",
    "DinhEquityError",
    "dinh_equity_moi",
    "doc_dinh_equity",
    "duong_dan_theo_runmode",
    "luu_dinh_equity",
]
