"""`TD-0312` — `chay_mot_luot()`: một lượt backtest thật, rổ lấy qua `ro_cho_tap()`.

Khuôn lời gọi Freqtrade lấy từ `do_backtest()`
(`docs/du-lieu-do/do_td0193_lenh_nam_explore.py:289`) — đường đã chạy thật và đã
sinh ra artifact `td0193-lenh-nam-explore.json`. Khác biệt duy nhất, và là toàn bộ
lý do module này tồn tại: kịch bản đó **tự quét thư mục** để dựng danh sách mã
(`:69-75`), còn ở đây danh sách mã **chỉ có thể** đến từ `ro_cho_tap()`.

🔑 **Thứ tự các bước dưới đây là một phần của thiết kế, không tuỳ tiện:**

  1. kiểm giấy phép   — `L-Z52`: TRƯỚC khi mở bất kỳ file dữ liệu nào
  2. `ro_cho_tap()`   — cửa duy nhất lấy rổ + thư mục (`DR-D1-05` §1)
  3. kiểm độ phủ `5m` — fail-closed, TRƯỚC khi tốn thời gian dựng môi trường (TD-0314)
  4. dựng môi trường  — cấu hình phủ + `pair_whitelist`
  5. gọi Freqtrade
  6. đọc kết quả      — `observed_*` đọc THẬT (TD-0148)

Bước 1 đứng đầu vì `L-Z52` nói *"TRƯỚC KHI CHẠM BẤT KỲ DỮ LIỆU NÀO"*
(`ledger/registry.py:497`). Bước 3 đứng trước bước 4 vì từ chối sớm rẻ hơn: dựng
môi trường là chép cả cây `config/`.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from tool_d.bo_chay.doc_ket_qua import doc_ket_qua
from tool_d.bo_chay.moi_truong import dung_moi_truong
from tool_d.bo_chay.yeu_cau import (
    BoChayError,
    GiayPhepChay,
    KetQuaChay,
    YeuCauChay,
    chuoi_timerange,
    kiem_ma_thuoc_ro,
    ten_cap_freqtrade,
)
from tool_d.ledger.registry import TrialState, UnknownTrialError
from tool_d.pool_giai_doan import ro_cho_tap

#: Đuôi file dữ liệu Freqtrade futures: `AAVE_USDT_USDT-1h-futures.feather`.
def _ten_file(ma: str, khung: str, loai: str = "futures") -> str:
    return f"{ma[:-4]}_USDT_USDT-{khung}-{loai}.feather"


def _pythonpath(repo_dir: Path) -> str:
    """`repo_dir/src` ĐỨNG TRƯỚC `PYTHONPATH` sẵn có, không thay thế nó.

    Ghi đè hẳn sẽ hỏng ở đúng ca quan trọng: khi `repo_dir` là một cây tạm (test,
    hoặc một bản sao để tái lập), cây đó không có `src/`, và chiến lược thì `import
    tool_d`. Thay thế ⇒ `ModuleNotFoundError`; đặt trước ⇒ cây tạm thắng nếu nó có
    `src/`, còn không thì rơi về gói đang cài (trong Docker là `/workspace/src`).
    """
    san_co = os.environ.get("PYTHONPATH", "")
    rieng = str((repo_dir / "src").resolve())
    return rieng + (os.pathsep + san_co if san_co else "")


class ChuaDatChoError(BoChayError):
    """Khởi chạy khi không có đặt chỗ hợp lệ — `L-Z52`. TỪ CHỐI, không chạm dữ liệu."""


class BacktestHongError(BoChayError):
    """Tiến trình `freqtrade backtesting` thoát khác 0. Mang theo mã thoát THẬT để
    chỗ gọi truyền vào `refund(cause_machine=...)` — `DR-014` §3 đòi nguyên nhân do
    MÁY xác định, không nhận lời khai người vận hành."""

    def __init__(self, thong_diep: str, *, returncode: int) -> None:
        super().__init__(thong_diep)
        self.returncode = returncode


def _kiem_giay_phep(giay_phep: GiayPhepChay) -> None:
    """Đọc lại sổ. Không nhận lời khai — cùng triết lý `DR-014` §3."""
    try:
        proj = giay_phep.ledger.get(giay_phep.trial_id)
    except UnknownTrialError as exc:
        raise ChuaDatChoError(
            f"{giay_phep.trial_id} chưa từng được RESERVE — TỪ CHỐI khởi chạy (L-Z52)"
        ) from exc
    if proj.state is not TrialState.RESERVED:
        raise ChuaDatChoError(
            f"{giay_phep.trial_id} đang ở trạng thái {proj.state.value}, cần RESERVED — "
            "TỪ CHỐI khởi chạy (L-Z52)"
        )


#: Khung chính của mọi chiến lược Tool D — N3 / `L-Z33`: 1H chính, 5m chỉ là khung chi tiết.
KHUNG_CHINH = "1h"


def _kiem_do_phu_chi_tiet(thu_muc: Path, ma: tuple[str, ...], khung: str, timerange: str) -> None:
    """`TD-0314` (`DR-D1-05` §3b.4): không một giờ khung chính nào thiếu nến `khung` tương ứng,
    ở mọi mã — đủ hoặc TỪ CHỐI, không có mức giữa.

    Chủ dự án chốt 18/09/2026: **NẠP HAI LẦN.** Tự nạp ở đây thay vì để tiến trình con khai,
    vì lời khai của chính thứ đang bị kiểm không phải bằng chứng (`DR-014` §3 / `MT-10`); và
    thiếu 5m phải bị bắt TRƯỚC khi chạy, không phải sau khi suất đã tiêu. Giá đo được trên rổ
    `T0` (143 mã, [T0,T1]): ~4 s cho 1h + ~12 s cho 5m mỗi lượt.

    Tham số nạp chép từ `Backtesting._load_bt_data_detail()` (đọc mã nguồn trong image,
    18/09/2026): cùng `datadir` cha, cùng CHUỖI `timerange` sẽ truyền cho Freqtrade,
    `startup_candles=0`, `feather`, `CandleType.FUTURES` — **trừ một khoá, cố ý:**

    🔴 `fill_up_missing=False`. Mặc định của `history.load_data` là `True`, và khi đó Freqtrade
    **tự lấp chỗ thủng bằng nến giả** (OHLC = giá đóng trước đó). Đo 18/09/2026 trên một file 5m
    thủng 3 giờ: lấp ⇒ 576 nến, `cho_thieu_khung_chi_tiet()` trả RỖNG; không lấp ⇒ 540 nến, bắt
    đúng 3 giờ. Tức nạp y hệt backtest thì phép kiểm **không bao giờ thấy thủng giữa chuỗi** —
    đúng thứ nó sinh ra để thấy. Tiêu chí §3b.4 nói về nến 5m THẬT, không phải nến Freqtrade bịa.
    Khung chính cũng nạp không lấp: một giờ 1H bịa ra không phải giờ cần phủ.

    ⚠️ Chặt hơn backtest ở một ca, chấp nhận có ý thức: nếu thiếu nến khởi động, Freqtrade dời
    điểm bắt đầu lên (`adjust_start_if_necessary`) và không giao dịch mấy giờ đầu; phép kiểm ở
    đây vẫn xét chúng.

    Bộ nhớ: hai `dict` dataframe chỉ sống trong hàm này, được giải phóng trước khi tiến trình
    con backtest nạp lại lần nữa.
    """
    from freqtrade.configuration import TimeRange
    from freqtrade.data import history
    from freqtrade.enums import CandleType

    from tool_d.data.do_phu_chi_tiet import cho_thieu_khung_chi_tiet

    cap = [ten_cap_freqtrade(m) for m in ma]
    tr = TimeRange.parse_timerange(timerange)

    def _nap(k: str) -> dict:
        # `datadir` là thư mục CHA: với FUTURES Freqtrade tự nối `futures/` (bẫy đã dính ở
        # `E8 --ro-do-phu`, 18/09/2026 — truyền thẳng `.../futures` thì nạp được 0 mã).
        return history.load_data(
            datadir=thu_muc.parent,
            pairs=cap,
            timeframe=k,
            timerange=tr,
            startup_candles=0,
            fail_without_data=False,
            fill_up_missing=False,
            data_format="feather",
            candle_type=CandleType.FUTURES,
        )

    nen_chinh = _nap(KHUNG_CHINH)
    # Tập rỗng: "không có giờ nào để phủ" KHÔNG phải "đủ" (N6) — cùng bẫy `if not ma` ở trên.
    if not nen_chinh:
        raise BoChayError(
            f"KHÔNG ĐO ĐƯỢC độ phủ {khung}: nạp được 0/{len(cap)} mã khung {KHUNG_CHINH} trong "
            f"timerange {timerange}. TỪ CHỐI — đây không phải 'đủ điều kiện'."
        )
    thieu = cho_thieu_khung_chi_tiet(nen_chinh, _nap(khung))
    if thieu:
        chi_tiet = "\n  ".join(t.mo_ta() for t in thieu[:10])
        raise BoChayError(
            f"xin --timeframe-detail {khung} nhưng {len(thieu)}/{len(nen_chinh)} mã không phủ đủ "
            f"(`DR-D1-05` §3b.4):\n  {chi_tiet}\nTỪ CHỐI — chạy ở độ phân giải thô hơn mà không báo "
            "là một phép đo nói dối về chính nó."
        )


def _pham_vi_du_lieu(thu_muc: Path, ma: tuple[str, ...]) -> tuple[date | None, date | None]:
    """Ngày đầu/cuối CÓ SẴN trong file 1H của các mã sẽ chạy.

    Không phải phép đo "warm-up đã đọc tới đâu" — báo cáo Freqtrade không khai điều
    đó. Đây là CẬN TRÊN; xem docstring `KetQuaChay`. Đọc sau khi đã có đặt chỗ nên
    không vướng `L-Z52`.
    """
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        return None, None
    dau: date | None = None
    cuoi: date | None = None
    for m in ma:
        f = thu_muc / _ten_file(m, "1h")
        if not f.is_file():
            continue
        cot = pd.read_feather(f, columns=["date"])["date"]
        if cot.empty:
            continue
        a, b = cot.iloc[0].date(), cot.iloc[-1].date()
        dau = a if dau is None else min(dau, a)
        cuoi = b if cuoi is None else max(cuoi, b)
    return dau, cuoi


def chay_mot_luot(
    yeu_cau: YeuCauChay,
    *,
    giay_phep: GiayPhepChay,
    repo_dir: Path = Path("."),
    goc_tam: Path | None = None,
    timeout_giay: int = 7200,
) -> KetQuaChay:
    """Chạy một lượt backtest cho `yeu_cau`. Xem thứ tự các bước ở docstring module."""
    # 1 — L-Z52. Đứng trước mọi thứ, kể cả trước khi biết thư mục dữ liệu ở đâu.
    _kiem_giay_phep(giay_phep)

    # 2 — cửa DUY NHẤT lấy rổ. `yeu_cau` không mang đường dẫn rổ nào để mà lách.
    ro = ro_cho_tap(yeu_cau.tap, repo_dir=repo_dir)
    thu_muc_du_lieu = repo_dir / ro.thu_muc_du_lieu
    if not thu_muc_du_lieu.is_dir():
        raise BoChayError(
            f"thư mục dữ liệu {ro.thu_muc_du_lieu} của tập {yeu_cau.tap} chưa tồn tại"
        )
    ma = (
        kiem_ma_thuoc_ro(yeu_cau.ma_gioi_han, ro.trading)
        if yeu_cau.ma_gioi_han is not None
        else tuple(ro.trading)
    )

    # 🔴 TẬP RỖNG LÀM MỌI KHẲNG ĐỊNH PHỔ QUÁT THÀNH ĐÚNG-VÔ-NGHĨA. Chốt này phải
    #    đứng TRƯỚC mọi phép kiểm "mọi mã đều …" bên dưới, không phải sau. Với `ma`
    #    rỗng thì chốt 5m ở bước 3 cho `thieu == []` và kết luận "đủ" — trên 0 mã.
    #    Lượt chạy rồi cũng bị `dung_moi_truong()` từ chối ở bước 4, nhưng lúc đó
    #    CHỐT 5m ĐÃ NÓI "ĐỦ" rồi; một cổng nói đúng vì không có gì để xét là một
    #    cổng không tồn tại.
    #    Phiên `-ef` gặp đúng hình này trên đường chạy thật ngày 18/09/2026:
    #    `--ro-do-phu` nạp hụt 0/143 mã (sai `datadir`) rồi in `✅ Không một giờ nào
    #    thiếu nến 5m, trên toàn bộ 0 mã` và trả exit 0. "Rỗng" bị đọc thành "đủ".
    if not ma:
        raise BoChayError(
            f"0 mã để chạy (rổ {ro.file_ro} có {len(ro.trading)} mã, `ma_gioi_han` lọc còn 0). "
            "TỪ CHỐI — đây là KHÔNG ĐO ĐƯỢC, không phải 'đủ điều kiện'."
        )

    # 3 — fail-closed cho `--timeframe-detail`. Rổ `T0` KHÔNG có 5m (`DR-D1-05` §3,
    #     `TD-0252` ⏸). Im lặng chạy ở độ phân giải 1H là đúng cái bẫy đã ghi ở
    #     `do_td0193_lenh_nam_explore.py:21-22`: đủ để ĐẾM lệnh, KHÔNG đủ để nói về TP.
    #     Cơ chế (phiên `-ef` đọc mã nguồn, 18/09/2026): `backtesting.py:1739` có vế
    #     `and pair in self.detail_data` — mã thiếu 5m KHÔNG làm backtest đỏ, nó lặng
    #     lẽ tụt về 1H trong khi mã khác chạy 5m, và không cột nào trong bảng kết quả
    #     nói ra. Tức một phép đo trộn hai độ phân giải khớp lệnh mà tự khai là một.
    #
    #     `TD-0314`: tiêu chí đầy đủ của `DR-D1-05` §3b.4 — mọi giờ 1H có nến 5m THẬT,
    #     ở mọi mã, trên đúng `timerange` sẽ truyền cho Freqtrade. Chốt cũ (chỉ kiểm
    #     FILE 5m có tồn tại) đã XOÁ: giữ cả hai là giữ hai nguồn sự thật cho một việc.
    timerange = chuoi_timerange(yeu_cau.tu, yeu_cau.den_khong_gom)
    if yeu_cau.timeframe_detail:
        _kiem_do_phu_chi_tiet(thu_muc_du_lieu, ma, yeu_cau.timeframe_detail, timerange)

    # 4 — môi trường chạy tạm.
    goc = Path(tempfile.mkdtemp(prefix=f"bochay_{yeu_cau.tap.lower()}_")) if goc_tam is None else goc_tam
    mt = dung_moi_truong(
        repo_dir=repo_dir, goc=goc, ghi_de=yeu_cau.ghi_de_config, ma_trong_ro=ma
    )

    # 5 — gọi Freqtrade. `timerange` là CÙNG chuỗi phép kiểm độ phủ ở bước 3 đã dùng.
    lenh = [
        sys.executable, "-m", "freqtrade", "backtesting",
        "--config", str(mt.config_freqtrade),
        "--datadir", str(thu_muc_du_lieu.parent),
        "--userdir", str(mt.userdir),
        "--strategy", yeu_cau.chien_luoc,
        "--strategy-path", str(repo_dir / "user_data" / "strategies"),
        "--timerange", timerange,
        "--cache", "none",  # TD-0115: cache từng cho ra kết quả sai lệch
        "--export", "trades",
    ]
    if yeu_cau.timeframe_detail:
        lenh += ["--timeframe-detail", yeu_cau.timeframe_detail]

    proc = subprocess.run(
        lenh,
        capture_output=True,
        text=True,
        cwd=mt.thu_muc,
        timeout=timeout_giay,
        env={**os.environ, "PYTHONPATH": _pythonpath(repo_dir)},
    )
    if proc.returncode != 0:
        raise BacktestHongError(
            f"freqtrade backtesting thoát {proc.returncode}\n{(proc.stdout + proc.stderr)[-4000:]}",
            returncode=proc.returncode,
        )

    # 6 — đọc kết quả. `observed_*` đọc THẬT, không suy từ `timerange` (TD-0148).
    files = sorted((mt.userdir / "backtest_results").glob("backtest-result-*.zip"))
    if not files:
        raise BoChayError(f"không có file kết quả trong {mt.userdir / 'backtest_results'}")
    doc = doc_ket_qua(files[-1], yeu_cau.chien_luoc)
    co_tu, co_den = _pham_vi_du_lieu(thu_muc_du_lieu, ma)

    return KetQuaChay(
        tap=ro.tap,
        moc_ro=ro.moc,
        file_ro=ro.file_ro,
        thu_muc_du_lieu=ro.thu_muc_du_lieu,
        ma_da_chay=ma,
        timerange_yeu_cau=timerange,
        observed_start=doc["observed_start"],
        observed_end=doc["observed_end"],
        du_lieu_co_tu=co_tu,
        du_lieu_co_den=co_den,
        starting_balance=doc["starting_balance"],
        final_balance=doc["final_balance"],
        pnl_abs=doc["pnl_abs"],
        lenh=doc["lenh"],
        config_sha256=mt.sha256_phu,
        duong_ket_qua=files[-1],
        chien_luoc=yeu_cau.chien_luoc,
    )
