"""TD-0145 — nối folds + cache + equity thành một lần chạy walk-forward.

Đây là phần "H3-D orchestrator" mà spec dòng 4340 bắt **VIẾT LẠI TỪ ĐẦU**,
kèm danh sách chín bug Tool A phải có máy canh trước khi được coi là xong.
Module này nối ba mảnh đã có, mỗi mảnh giữ nguyên trách nhiệm của nó:

    folds.sinh_folds()      -> cửa sổ train/test, neo gốc (DR-D3-01)
    cache.doc_cache()       -> HIT / MISS / STALE theo vân tay (§0d.3)
    equity.kiem_can_doi_fold() + ghep_duong_von()  -> L-Z47, ghép bằng NHÂN

🔑 **Bộ chạy backtest được TIÊM VÀO, không gọi thẳng.** `chay_mot_fold` là
   tham số bắt buộc. Hai lý do, và lý do thứ hai mới là lý do thật:

   (a) Chưa có bộ chạy backtest thật ở bất kỳ đâu — E1 `run_backtest.py`
       cũng còn `NotImplementedError` (việc của Khối 2/3). Viết một lời gọi
       freqtrade ở đây sẽ là mã không ai chạy được và không test nào kiểm
       được.
   (b) Quan trọng hơn: nó khiến toàn bộ logic ĐIỀU PHỐI kiểm được một cách
       TẤT ĐỊNH — cache HIT/MISS/STALE, fail-closed của L-Z47, sàn số lệnh
       — mà không cần dữ liệu thị trường. Nếu logic này chỉ chạy được khi
       có backtest thật thì nó sẽ chỉ được kiểm ở D9, tức sau khi đã tin nó
       suốt nhiều tháng.

🔴 **Chỗ nối trial reservation (L-Z52) khi có bộ chạy thật:** `reserve()`
   phải được gọi TRƯỚC khi `chay_mot_fold` chạm dữ liệu, không phải sau.
   Module này cố ý KHÔNG tự đặt chỗ: nó không biết `budget_line` nào, và
   đoán hộ là cách chắc chắn tiêu sai ngân sách. Chỗ gọi truyền vào một
   `chay_mot_fold` đã tự đặt chỗ.

🔴 **Fold dưới sàn số lệnh KHÔNG ghi số** — DR-D3-01 §5.2 + N6. Nó nhận
   `Measured.unreadable(...)`, không phải `0.0`, không phải số kèm cảnh
   báo. Ngưỡng đọc từ `folds.san_lenh_moi_fold(cfg)`, không gõ lại ở đây.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from tool_d.config.loader import ToolDConfig
from tool_d.measurement.tri_state import Measured
from tool_d.wfo.cache import (
    DEFAULT_CACHE_DIR,
    TrangThai,
    VanTay,
    doc_cache,
    ghi_cache,
    van_tay_hien_tai,
)
from tool_d.wfo.equity import FoldEquity, ghep_duong_von, he_so_tong, kiem_can_doi_fold
from tool_d.ledger.timerange import dataset_boundaries_from_config
from tool_d.wfo.folds import (
    Fold,
    kiem_pham_vi_du_lieu,
    san_lenh_moi_fold,
    sinh_folds,
)

ChayMotFold = Callable[[Fold], FoldEquity]


@dataclass(frozen=True)
class KetQuaFold:
    """Một fold sau khi chạy xong (hoặc lấy lại từ cache).

    `he_so` là `Measured` chứ không phải `float` thẳng: fold dưới sàn số
    lệnh KHÔNG có con số nào đáng in ra, và cách duy nhất để điều đó không
    âm thầm biến thành `0.0` ở một chỗ nào đó phía sau là làm cho kiểu dữ
    liệu không cho phép.
    """

    fold: Fold
    equity: FoldEquity
    tu_cache: bool
    he_so: Measured[float]

    @property
    def so_lenh(self) -> int:
        return len(self.equity.pnl_abs)


@dataclass(frozen=True)
class KetQuaWFO:
    folds: tuple[KetQuaFold, ...]
    duong_von: tuple[float, ...]
    he_so_gop: Measured[float]
    canh_bao: tuple[str, ...]

    @property
    def so_fold_doc_duoc(self) -> int:
        return sum(1 for f in self.folds if f.he_so.is_ok())


def chay_wfo(
    *,
    cfg: ToolDConfig,
    chay_mot_fold: ChayMotFold,
    data_hashes: dict[str, str],
    von_ban_dau: float,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    repo_dir: Path = Path("."),
    in_ra: Callable[[str], None] = print,
) -> KetQuaWFO:
    """Chạy toàn bộ chuỗi fold, trả kết quả đã kiểm L-Z47 và ghép bằng NHÂN.

    Thứ tự mỗi fold — thứ tự này là một phần của thiết kế, không tuỳ tiện:

      1. đọc cache theo vân tay
      2. STALE → IN CẢNH BÁO TO rồi chạy lại; MISS → chạy, im lặng
      3. `kiem_pham_vi_du_lieu()` (L-Z55, TD-0148) — phạm vi ngày THẬT
      4. `kiem_can_doi_fold()` (L-Z47) — SAI thì raise, không ghi cache
      5. ghi cache kèm vân tay
      6. áp sàn số lệnh → `Measured.unreadable` nếu dưới sàn

    Bước 4 đứng TRƯỚC bước 5 là có chủ ý: ghi cache một kết quả chưa qua
    L-Z47 nghĩa là lần chạy sau sẽ HIT ngay vào một con số sai, và lúc đó
    phép kiểm không còn cơ hội chạy nữa.

    Bước 3 đứng TRƯỚC bước 4 cũng có chủ ý: một kết quả đọc sai phạm vi
    ngày thì có cân đối vốn hoàn hảo cũng vô nghĩa — nó đo một khoảng thời
    gian khác khoảng người đọc tưởng.

    🔑 **Hai điều PHẢI ghi rõ về bước 3, không được ngầm hiểu** (TD-0148):
      • Tới khi có bộ chạy backtest THẬT (D3.5), phép kiểm này chỉ được
        nuôi bằng bộ chạy GIẢ trong test. **Cơ chế** đã tại chỗ và bị
        khoá; **bảo đảm trên dữ liệu thật** thì D3.5 mới có.
      • Nó **vẫn tin lời khai của bộ chạy**. Một bộ chạy trả ngày *dự
        kiến* thay vì ngày *thật đọc được từ dataframe* sẽ vô hiệu hoá nó
        hoàn toàn. Khi viết bộ chạy thật, bắt buộc đọc từ dataframe và
        phải có test khoá riêng cho đúng điều đó.
    """
    ds_fold = sinh_folds(cfg)
    bien_wfo = dataset_boundaries_from_config(cfg)["WFO"]
    san = san_lenh_moi_fold(cfg)
    van_tay = van_tay_hien_tai(cfg=cfg, data_hashes=data_hashes, repo_dir=repo_dir)

    ket_qua: list[KetQuaFold] = []
    canh_bao: list[str] = []

    for fold in ds_fold:
        khoa = _khoa_cache(fold)
        doc = doc_cache(khoa=khoa, van_tay=van_tay, cache_dir=cache_dir)

        if doc.trang_thai is TrangThai.STALE:
            # KHÔNG gộp vào MISS: kết quả cuối vẫn đúng vì đằng nào cũng
            # chạy lại, nên không test nào đỏ — nhưng mất đúng tín hiệu
            # "có gì đó đổi ngoài ý muốn" mà TD-0143 sinh ra để bắt.
            in_ra(doc.canh_bao)
            canh_bao.append(doc.canh_bao)

        if doc.trang_thai is TrangThai.HIT:
            equity = _tu_payload(doc.payload, fold=fold)
            tu_cache = True
        else:
            equity = chay_mot_fold(fold)
            tu_cache = False

        # 🔴 TD-0148 — L-Z55 ĐÚNG NGHĨA: đối chiếu phạm vi ngày THẬT bộ chạy
        # đã đọc với biên WFO (tầng a) và với cửa sổ của chính fold (tầng b).
        # Đứng TRƯỚC L-Z47: một kết quả đọc sai phạm vi thì có cân đối vốn
        # hoàn hảo cũng vô nghĩa — nó đo một khoảng thời gian khác.
        # Chạy cho CẢ kết quả lấy từ cache, cùng lý do như L-Z47 bên dưới.
        kiem_pham_vi_du_lieu(
            observed_start=equity.observed_start,
            observed_end=equity.observed_end,
            fold=fold,
            boundary=bien_wfo,
        )

        # L-Z47 chạy cho CẢ kết quả lấy từ cache: một mục cache có thể được
        # ghi bởi phiên bản code cũ hơn phép kiểm này.
        kiem_can_doi_fold(equity)

        if not tu_cache:
            ghi_cache(
                khoa=khoa,
                payload=_thanh_payload(equity),
                van_tay=van_tay,
                cache_dir=cache_dir,
                ghi_luc=_gio_utc(),
            )

        ket_qua.append(
            KetQuaFold(
                fold=fold,
                equity=equity,
                tu_cache=tu_cache,
                he_so=_he_so_co_san(equity, san=san),
            )
        )

    return KetQuaWFO(
        folds=tuple(ket_qua),
        duong_von=ghep_duong_von([k.equity for k in ket_qua], von_ban_dau=von_ban_dau),
        he_so_gop=_he_so_gop_co_san(ket_qua),
        canh_bao=tuple(canh_bao),
    )


def _he_so_co_san(equity: FoldEquity, *, san: int) -> Measured[float]:
    """Dưới sàn số lệnh → `unreadable`, KHÔNG phải 0.0 (DR-D3-01 §5.2, N6).

    Lý do sàn tồn tại, chép lại để chỗ này đọc được mà không phải mở DR:
    dưới ~30 lệnh thì sai số chuẩn của expectancy đã lớn hơn khoảng cách
    giữa các arm mà D0.9 định phân biệt — con số in ra không mang thông
    tin, nó chỉ tạo cảm giác có thông tin.
    """
    n = len(equity.pnl_abs)
    if n < san:
        return Measured.unreadable(
            f"fold {equity.chi_so}: {n} lệnh < sàn {san} (DR-D3-01 §5.2)"
        )
    return Measured.ok(equity.he_so)


def _he_so_gop_co_san(ket_qua: Sequence[KetQuaFold]) -> Measured[float]:
    """Hệ số gộp chỉ có nghĩa khi MỌI fold đều đọc được.

    Bỏ qua fold `unreadable` rồi nhân các fold còn lại sẽ cho ra một con số
    trông bình thường nhưng đo một khoảng thời gian KHÁC với khoảng người
    đọc tưởng — đúng loại sai lặng lẽ mà PHẦN 0d tồn tại để chặn.
    """
    thieu = [k.fold.chi_so for k in ket_qua if not k.he_so.is_ok()]
    if thieu:
        return Measured.unreadable(
            f"fold {thieu} dưới sàn số lệnh — hệ số gộp của chuỗi không đọc được"
        )
    return Measured.ok(he_so_tong([k.equity for k in ket_qua]))


def _khoa_cache(fold: Fold) -> str:
    """Khoá mang cả mốc thời gian, không chỉ chỉ số fold.

    `fold3` một mình sẽ va nhau nếu sơ đồ fold đổi (đổi phải qua L-Z26, có
    thật) — hai sơ đồ khác nhau cùng dùng khoá `fold3` thì vân tay không
    cứu được, vì `params_hash` chỉ đổi khi `tool_d_config.yaml` đổi... mà
    đó đúng là thứ đổi khi sơ đồ fold đổi. Vẫn đưa mốc vào khoá: rẻ, và
    làm cho lập luận trên không cần phải đúng.
    """
    return f"fold{fold.chi_so}_{fold.test_start:%Y%m%d}_{fold.test_end:%Y%m%d}"


def _thanh_payload(equity: FoldEquity) -> dict[str, Any]:
    # `observed_*` PHẢI vào payload: thiếu nó thì kết quả lấy lại từ cache
    # không dựng lại được `FoldEquity`, và phép kiểm L-Z55 ở bước 3 sẽ
    # không có gì để kiểm cho đúng nhánh HIT — tức tắt lặng lẽ đúng lúc
    # dùng lại số cũ. Đây là DỮ LIỆU của kết quả, không phải xuất xứ (xuất
    # xứ vẫn KHÔNG vào cache — xem TD-0146).
    return {
        "chi_so": equity.chi_so,
        "starting_balance": equity.starting_balance,
        "final_balance": equity.final_balance,
        "pnl_abs": list(equity.pnl_abs),
        "observed_start": equity.observed_start.isoformat(),
        "observed_end": equity.observed_end.isoformat(),
    }


def _tu_payload(payload: dict[str, Any] | None, *, fold: Fold) -> FoldEquity:
    if payload is None:
        raise ValueError(f"fold {fold.chi_so}: cache HIT nhưng payload rỗng")
    thieu = {"observed_start", "observed_end"} - set(payload)
    if thieu:
        # Mục cache do phiên bản code TRƯỚC TD-0148 ghi ra. Fail-closed:
        # KHÔNG đoán ngày, KHÔNG bỏ qua phép kiểm — buộc chạy lại.
        raise ValueError(
            f"fold {fold.chi_so}: mục cache thiếu {sorted(thieu)} (ghi bởi code "
            "trước TD-0148) — TỪ CHỐI dùng lại, xoá cache và chạy lại."
        )
    return FoldEquity(
        chi_so=payload["chi_so"],
        starting_balance=payload["starting_balance"],
        final_balance=payload["final_balance"],
        pnl_abs=tuple(payload["pnl_abs"]),
        observed_start=date.fromisoformat(payload["observed_start"]),
        observed_end=date.fromisoformat(payload["observed_end"]),
    )


def _gio_utc() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
