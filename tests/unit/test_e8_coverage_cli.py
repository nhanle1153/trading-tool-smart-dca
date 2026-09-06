"""TD-0092 — E8 `--coverage`: khoá đúng ca đã suýt làm công cụ này vô dụng.

Chạy lần đầu trên dữ liệu THẬT, bảng độ phủ báo "thiếu 87,5%" cho 102 file
`funding_rate` hoàn toàn lành lặn — vì tên file ghi `1h` nhưng sàn trả
funding mỗi 8 giờ. Một công cụ cảnh báo 102 lần sai thì lần thứ 103 (đúng)
sẽ bị bỏ qua. Test này khoá việc loại nhóm đó ra khỏi bảng tính theo khung.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from backfill_data import do_coverage  # noqa: E402

H = 60 * 60_000
START = "2026-01-01"
END = "2026-01-02"


def _write(path: Path, *, step_ms: int, n: int, cols: dict) -> None:
    t0 = pd.Timestamp(START, tz="UTC").value // 1_000_000
    ts = [t0 + i * step_ms for i in range(n)]
    df = pd.DataFrame({"date": pd.to_datetime(ts, unit="ms", utc=True).astype("datetime64[ms, UTC]"), **{k: [v] * n for k, v in cols.items()}})
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_feather(path)


OHLCV = {"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}


class TestLocLoaiNen:
    def test_funding_rate_bi_loai_va_co_giai_thich(self, tmp_path, capsys) -> None:
        d = tmp_path / "futures"
        _write(d / "AAA_USDT_USDT-1h-futures.feather", step_ms=H, n=25, cols=OHLCV)
        # funding: mỗi 8h -> nếu đo theo bước 1h sẽ ra ~12.5%, báo động giả
        _write(d / "AAA_USDT_USDT-1h-funding_rate.feather", step_ms=8 * H, n=4, cols={"funding_rate": 0.0001})

        rc = do_coverage(
            data_dir=d, timeframe="1h", candle_type="futures", range_from=START, range_to=END
        )
        out = capsys.readouterr().out
        assert rc == 0
        assert "Bỏ qua 1 file `funding_rate`" in out
        assert "nhịp funding do SÀN quy định" in out
        assert "funding_rate.feather" not in out.split("FILE")[1]  # không nằm trong bảng
        assert "Tổng 1 file: 1 đủ" in out

    def test_chon_duoc_loai_mark(self, tmp_path, capsys) -> None:
        d = tmp_path / "futures"
        _write(d / "AAA-1h-futures.feather", step_ms=H, n=25, cols=OHLCV)
        _write(d / "AAA-1h-mark.feather", step_ms=H, n=20, cols=OHLCV)  # thiếu 5
        do_coverage(data_dir=d, timeframe="1h", candle_type="mark", range_from=START, range_to=END)
        out = capsys.readouterr().out
        assert "AAA-1h-mark.feather" in out and "Tổng 1 file: 0 đủ, 1 thiếu" in out


class TestKhongKetLuanNguyenNhan:
    def test_bang_khong_bao_gio_tu_ket_luan_nguyen_nhan(self, tmp_path, capsys) -> None:
        d = tmp_path / "futures"
        _write(d / "AAA-1h-futures.feather", step_ms=H, n=10, cols=OHLCV)  # thiếu nhiều
        do_coverage(
            data_dir=d, timeframe="1h", candle_type="futures", range_from=START, range_to=END
        )
        out = capsys.readouterr().out
        assert "chưa kiểm nguồn trực tiếp" in out
        assert "phải chạy `--probe-gap` trước khi kết luận" in out
        for cam in ("sàn thiếu dữ liệu", "do sàn", "phần lớn"):
            assert cam not in out

    def test_thu_muc_khong_ton_tai_thi_bao_loi_khong_im_lang(self, tmp_path, capsys) -> None:
        rc = do_coverage(
            data_dir=tmp_path / "khong_co",
            timeframe="1h",
            candle_type="futures",
            range_from=START,
            range_to=END,
        )
        assert rc != 0
        assert "không tồn tại" in capsys.readouterr().out
