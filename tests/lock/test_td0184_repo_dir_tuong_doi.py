"""TD-0184 (lô `DR-D4-19`, lượt 1 — `a2f4c60`) — `chay_mot_luot()` nhận `repo_dir` TƯƠNG ĐỐI.

Lỗi thật, 19/09/2026: E3 (`run_ablation.py`) và E1 (`run_backtest.py`) truyền `repo_dir=Path(".")`.
Bước 5 của `chay_mot_luot()` gọi Freqtrade với `cwd` = thư mục TẠM, nên `--strategy-path`,
`--datadir` và `PYTHONPATH` dựng từ `repo_dir` bị hiểu tương đối với thư mục tạm ⇒ Freqtrade báo
*"Impossible to load Strategy 'ZoneAbsorption'"*, thoát 2 ở arm đầu. 4 suất B2 được REFUND theo máy
(lỗi trước con dấu, `L-Z53`) — không mất suất, nhưng lô không chạy được.

Vì sao mọi test cũ không bắt: `test_td0312` gọi bộ chạy THẬT nhưng với `repo_dir` TUYỆT ĐỐI
(`tmp_path_factory`); `test_td0335` đi đúng đường E3 nhưng với bộ chạy GIẢ. Không ca nào đi qua
tổ hợp *E-point thật + đường dẫn tương đối* — đúng hình "ca sai chỉ đi qua mẫu dựng tay".

Ca dưới chạy MỘT lượt Freqtrade thật, trên repo giả của `test_td0312` (dữ liệu tổng hợp, sổ tạm),
từ `cwd` = gốc repo giả và `repo_dir=Path(".")` — đúng tổ hợp của E1/E3.
"""

from __future__ import annotations

from pathlib import Path

from test_td0312_loi_bo_chay import (  # noqa: F401 — `repo_gia` là fixture, pytest cần tên trong module
    CHIEN_LUOC,
    DEN_KHONG_GOM,
    MA,
    TU,
    _dat_cho,
    _so_tam,
    repo_gia,
)
from tool_d.bo_chay.chay import chay_mot_luot
from tool_d.bo_chay.yeu_cau import GiayPhepChay, YeuCauChay


def test_repo_dir_tuong_doi_van_nap_duoc_chien_luoc_va_du_lieu(repo_gia: Path, monkeypatch) -> None:
    # Đặt chỗ TRƯỚC khi đổi `cwd`: sổ đọc schema theo đường dẫn tương đối với gốc repo thật —
    # biến số duy nhất của ca này phải là `repo_dir`, không phải `cwd` của sổ.
    so = _so_tam(repo_gia)
    tid = _dat_cho(so)
    monkeypatch.chdir(repo_gia)
    kq = chay_mot_luot(
        YeuCauChay(tap="WFO", tu=TU, den_khong_gom=DEN_KHONG_GOM, chien_luoc=CHIEN_LUOC, ma_gioi_han=(MA,)),
        giay_phep=GiayPhepChay(ledger=so, trial_id=tid, budget_line="B3"),
        repo_dir=Path("."),
    )
    # Đọc được kết quả = Freqtrade đã nạp chiến lược + dữ liệu. Trước bản vá: BacktestHongError (thoát 2).
    assert kq.observed_start is not None and kq.observed_end is not None
