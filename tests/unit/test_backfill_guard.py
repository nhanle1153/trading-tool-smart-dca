"""TD-0091 — H19 backfill an toàn (spec dòng 4350, LD-27/28).

Test quan trọng nhất ở đây là `test_ghi_de_bang_dai_hep_hon_thi_bi_bat` —
nó tái hiện ĐÚNG cái bẫy suýt xoá nhiều năm dữ liệu của Tool A: script tải
"khoảng ngày yêu cầu" rồi GHI ĐÈ file thay vì gộp. Nếu lớp gác này không
bắt được ca đó thì nó vô dụng, dù mọi test khác xanh.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tool_d.data.backfill_guard import (
    backup_data_dir,
    read_candles,
    snapshot_dir,
    verify_old_candles_preserved,
)


def _frame(start: str, n: int, *, freq: str = "1h", close_base: float = 100.0) -> pd.DataFrame:
    dates = pd.date_range(start=start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame(
        {
            "date": dates.astype("datetime64[ms, UTC]"),
            "open": [close_base + i for i in range(n)],
            "high": [close_base + i + 0.5 for i in range(n)],
            "low": [close_base + i - 0.5 for i in range(n)],
            "close": [close_base + i + 0.1 for i in range(n)],
            "volume": [1000.0 + i for i in range(n)],
        }
    )


def _write(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_feather(path)


class TestDocNen:
    def test_file_khong_ton_tai_thi_unreadable(self, tmp_path: Path) -> None:
        m = read_candles(tmp_path / "khong_co.feather")
        assert not m.is_ok()
        assert m.value is None  # N6: không bịa DataFrame rỗng

    def test_file_hong_thi_unreadable_khong_crash(self, tmp_path: Path) -> None:
        p = tmp_path / "hong.feather"
        p.write_bytes(b"day khong phai feather")
        m = read_candles(p)
        assert not m.is_ok()
        assert "feather" in m.render().lower()

    def test_file_rong_khong_duoc_coi_la_du_lieu(self, tmp_path: Path) -> None:
        # (d) của H19: tải hỏng -> KHÔNG ghi/không nhận cache rỗng.
        p = tmp_path / "rong.feather"
        _write(p, _frame("2026-01-01", 0))
        m = read_candles(p)
        assert not m.is_ok()
        assert "0 nến" in m.render()

    def test_thieu_cot_gia_tri_van_doc_duoc_neu_con_date_va_1_cot(self, tmp_path: Path) -> None:
        # Bản đầu đòi ĐỦ 6 cột OHLCV và coi thiếu cột là `unreadable`. Luật
        # đó SAI: nó loại luôn `*-funding_rate.feather` (date + funding_rate)
        # — 102 file thật. Luật đúng: `date` + ít nhất một cột giá trị.
        # Ca "thiếu cột thật sự" giờ do TestSchemaKhacOHLCV canh.
        p = tmp_path / "thieu_volume.feather"
        _write(p, _frame("2026-01-01", 3).drop(columns=["volume"]))
        assert read_candles(p).is_ok()

    def test_thieu_cot_date_thi_unreadable(self, tmp_path: Path) -> None:
        p = tmp_path / "khong_co_date.feather"
        _write(p, _frame("2026-01-01", 3).drop(columns=["date"]))
        assert not read_candles(p).is_ok()

    def test_file_hop_le_thi_ok(self, tmp_path: Path) -> None:
        p = tmp_path / "ok.feather"
        _write(p, _frame("2026-01-01", 5))
        m = read_candles(p)
        assert m.is_ok()
        assert len(m.value) == 5


class TestGopKhongGhiDe:
    def _setup_old(self, tmp_path: Path) -> tuple[Path, dict]:
        data = tmp_path / "futures"
        _write(data / "AAA_USDT_USDT-1h-futures.feather", _frame("2024-01-01", 100))
        return data, snapshot_dir(data)

    def test_khong_doi_gi_thi_khong_co_vi_pham(self, tmp_path: Path) -> None:
        data, before = self._setup_old(tmp_path)
        assert verify_old_candles_preserved(before, data) == []

    def test_gop_them_nen_moi_o_cuoi_van_hop_le(self, tmp_path: Path) -> None:
        # Đây là trường hợp ĐÚNG của một lần backfill: dữ liệu cũ nguyên
        # vẹn, chỉ nối thêm nến mới. Bytes file đổi — nhưng đó là hợp lệ,
        # lớp gác KHÔNG được báo động (nếu báo, người ta sẽ tắt nó đi).
        data, before = self._setup_old(tmp_path)
        p = data / "AAA_USDT_USDT-1h-futures.feather"
        old = pd.read_feather(p)
        new = pd.concat([old, _frame("2024-01-05 04:00", 50, close_base=200.0)], ignore_index=True)
        _write(p, new)
        assert verify_old_candles_preserved(before, data) == []

    def test_gop_them_nen_moi_o_dau_van_hop_le(self, tmp_path: Path) -> None:
        # `--prepend` của Freqtrade: thêm lịch sử CŨ HƠN vào đầu.
        data, before = self._setup_old(tmp_path)
        p = data / "AAA_USDT_USDT-1h-futures.feather"
        old = pd.read_feather(p)
        new = pd.concat([_frame("2023-12-01", 30, close_base=50.0), old], ignore_index=True)
        _write(p, new)
        assert verify_old_candles_preserved(before, data) == []

    def test_ghi_de_bang_dai_hep_hon_thi_bi_bat(self, tmp_path: Path) -> None:
        # 🔴 BẪY LD-27 — chính ca suýt xoá nhiều năm dữ liệu của Tool A:
        # script tải đúng "khoảng ngày yêu cầu" rồi ghi đè cả file.
        data, before = self._setup_old(tmp_path)
        p = data / "AAA_USDT_USDT-1h-futures.feather"
        _write(p, _frame("2024-01-04", 20))  # chỉ còn 20 nến cuối
        errors = verify_old_candles_preserved(before, data)
        assert errors and "bị ghi đè" in errors[0]

    def test_nen_cu_doi_gia_tri_thi_bi_bat(self, tmp_path: Path) -> None:
        data, before = self._setup_old(tmp_path)
        p = data / "AAA_USDT_USDT-1h-futures.feather"
        df = pd.read_feather(p)
        df.loc[10, "close"] = 999.0  # sửa một nến cũ
        _write(p, df)
        errors = verify_old_candles_preserved(before, data)
        assert errors and "ĐỔI GIÁ TRỊ" in errors[0]

    def test_file_bi_xoa_thi_bi_bat(self, tmp_path: Path) -> None:
        data, before = self._setup_old(tmp_path)
        (data / "AAA_USDT_USDT-1h-futures.feather").unlink()
        errors = verify_old_candles_preserved(before, data)
        assert errors and "mất hoặc không đọc được" in errors[0]

    def test_file_moi_hoan_toan_khong_bi_coi_la_vi_pham(self, tmp_path: Path) -> None:
        # Mã mới vào pool -> file mới xuất hiện. Không phải vi phạm.
        data, before = self._setup_old(tmp_path)
        _write(data / "BBB_USDT_USDT-1h-futures.feather", _frame("2024-01-01", 10))
        assert verify_old_candles_preserved(before, data) == []


def _funding_frame(start: str, n: int, *, base: float = 0.0001) -> pd.DataFrame:
    dates = pd.date_range(start=start, periods=n, freq="8h", tz="UTC")
    return pd.DataFrame(
        {
            "date": dates.astype("datetime64[ms, UTC]"),
            "funding_rate": [base * (i + 1) for i in range(n)],
        }
    )


class TestSchemaKhacOHLCV:
    """🔴 Ca đã bỏ sót ở bản đầu: Freqtrade ghi `*-funding_rate.feather` với
    schema (date, funding_rate) — bản đầu khoá cứng vào 6 cột OHLCV nên âm
    thầm bỏ qua ĐÚNG 102 file thật (1/5 dữ liệu lockbox), mất bảo vệ cho
    chính dữ liệu DG7 (§4c) cần. Phát hiện khi chạy trên dữ liệu thật, không
    phải khi chạy test tự dựng — lý do phải luôn chạy thử ở quy mô thật.
    """

    def test_file_funding_rate_duoc_chup(self, tmp_path: Path) -> None:
        data = tmp_path / "futures"
        _write(data / "AAA_USDT_USDT-1h-funding_rate.feather", _funding_frame("2026-01-01", 50))
        snap = snapshot_dir(data)
        assert set(snap) == {"AAA_USDT_USDT-1h-funding_rate.feather"}
        assert snap["AAA_USDT_USDT-1h-funding_rate.feather"].n_rows == 50

    def test_ghi_de_file_funding_rate_bi_bat(self, tmp_path: Path) -> None:
        data = tmp_path / "futures"
        p = data / "AAA_USDT_USDT-1h-funding_rate.feather"
        _write(p, _funding_frame("2026-01-01", 50))
        before = snapshot_dir(data)
        _write(p, _funding_frame("2026-01-10", 10))  # ghi đè bằng dải hẹp hơn
        errors = verify_old_candles_preserved(before, data)
        assert errors and "bị ghi đè" in errors[0]

    def test_doi_gia_tri_funding_bi_bat(self, tmp_path: Path) -> None:
        data = tmp_path / "futures"
        p = data / "AAA-1h-funding_rate.feather"
        _write(p, _funding_frame("2026-01-01", 20))
        before = snapshot_dir(data)
        df = pd.read_feather(p)
        df.loc[5, "funding_rate"] = -0.05
        _write(p, df)
        errors = verify_old_candles_preserved(before, data)
        assert errors and "ĐỔI GIÁ TRỊ" in errors[0]

    def test_chi_co_cot_thoi_gian_thi_unreadable(self, tmp_path: Path) -> None:
        p = tmp_path / "chi_co_date.feather"
        _write(p, _funding_frame("2026-01-01", 5).drop(columns=["funding_rate"]))
        assert not read_candles(p).is_ok()

    def test_hai_schema_song_song_trong_cung_thu_muc(self, tmp_path: Path) -> None:
        # Đúng hiện trạng thư mục thật: OHLCV + mark + funding_rate lẫn lộn.
        data = tmp_path / "futures"
        _write(data / "AAA-1h-futures.feather", _frame("2026-01-01", 10))
        _write(data / "AAA-1h-mark.feather", _frame("2026-01-01", 10))
        _write(data / "AAA-1h-funding_rate.feather", _funding_frame("2026-01-01", 4))
        assert len(snapshot_dir(data)) == 3


class TestSnapshot:
    def test_thu_muc_khong_ton_tai_thi_rong(self, tmp_path: Path) -> None:
        assert snapshot_dir(tmp_path / "khong_co") == {}

    def test_bo_qua_file_hong_khong_crash(self, tmp_path: Path) -> None:
        data = tmp_path / "futures"
        data.mkdir()
        (data / "hong.feather").write_bytes(b"rac")
        _write(data / "tot.feather", _frame("2026-01-01", 3))
        snap = snapshot_dir(data)
        assert set(snap) == {"tot.feather"}


class TestSaoLuuTruoc:
    def test_sao_luu_du_file(self, tmp_path: Path) -> None:
        data = tmp_path / "futures"
        _write(data / "AAA-1h.feather", _frame("2026-01-01", 5))
        _write(data / "BBB-1h.feather", _frame("2026-01-01", 5))
        dest = backup_data_dir(source_dir=data, dest_root=tmp_path / "backup")
        assert sorted(p.name for p in dest.glob("*.feather")) == ["AAA-1h.feather", "BBB-1h.feather"]

    def test_nguon_khong_ton_tai_thi_raise_khong_tao_thu_muc_rong(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            backup_data_dir(source_dir=tmp_path / "khong_co", dest_root=tmp_path / "backup")
        assert not (tmp_path / "backup").exists()

    def test_chay_lai_thi_ghi_de_ban_cu(self, tmp_path: Path) -> None:
        data = tmp_path / "futures"
        _write(data / "AAA-1h.feather", _frame("2026-01-01", 5))
        backup_data_dir(source_dir=data, dest_root=tmp_path / "backup")
        _write(data / "CCC-1h.feather", _frame("2026-01-01", 5))
        dest = backup_data_dir(source_dir=data, dest_root=tmp_path / "backup")
        assert (dest / "CCC-1h.feather").exists()

    def test_ban_sao_luu_khoi_phuc_duoc_va_khop_snapshot(self, tmp_path: Path) -> None:
        # Sao lưu phải dùng được thật: snapshot bản gốc == snapshot bản sao.
        data = tmp_path / "futures"
        _write(data / "AAA-1h.feather", _frame("2026-01-01", 20))
        before = snapshot_dir(data)
        dest = backup_data_dir(source_dir=data, dest_root=tmp_path / "backup")
        assert verify_old_candles_preserved(before, dest) == []
