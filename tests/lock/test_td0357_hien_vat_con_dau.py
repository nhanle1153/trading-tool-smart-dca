"""🔒 TD-0357 (`DR-D4-20`) — hiện vật con dấu: sổ không được khai một `seal_path` chưa tồn tại.

Ca thật sinh ra việc này: `D-0015` (lô `DR-D4-19`, `708a268`) niêm phong với
`seal_path = "runs/D-0015/metrics.seal"`, rồi lỗi ở bước sau con dấu. Suất đã tiêu (`L-Z53` không cho hoàn),
export backtest nằm trong thư mục tạm của container `--rm`, và **file con dấu chưa bao giờ được sinh** ⇒ không
còn gì để đọc lại về lượt chạy đã tiêu một suất trong 114.
"""

from __future__ import annotations

import ast
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from tool_d.ledger.con_dau import ConDauError, duong_con_dau, duong_khai_so, ghi_con_dau

REPO_ROOT = Path(__file__).resolve().parents[2]


def _kq(so_lenh: int = 3):
    return SimpleNamespace(
        tap="WFO", moc_ro="t1", file_ro=Path("config/pool_t1.yaml"), chien_luoc="ZoneAbsorption",
        config_sha256="a" * 64, timerange_yeu_cau="20250612-20260129",
        observed_start=date(2025, 6, 12), observed_end=date(2026, 1, 28),
        ma_da_chay=("BTCUSDT", "ETHUSDT"), so_lenh=so_lenh,
    )


class TestHienVat:
    def test_ghi_ra_dung_duong_so_khai(self, tmp_path) -> None:
        duong = ghi_con_dau(tmp_path, "D-9999", _kq(), them={"arm": "Z0-T1"})
        assert duong == duong_con_dau(tmp_path, "D-9999") and duong.is_file()
        d = json.loads(duong.read_text(encoding="utf-8"))
        assert d["trial_id"] == "D-9999" and d["arm"] == "Z0-T1"
        assert d["so_lenh"] == 3 and d["so_ma_da_chay"] == 2
        assert d["observed_start"] == "2025-06-12" and d["config_sha256"] == "a" * 64

    def test_tu_choi_ghi_de(self, tmp_path) -> None:
        ghi_con_dau(tmp_path, "D-9999", _kq())
        with pytest.raises(ConDauError, match="MỘT LẦN"):
            ghi_con_dau(tmp_path, "D-9999", _kq())

    def test_khoa_them_trung_khoa_goc_bi_tu_choi(self, tmp_path) -> None:
        """Một lời khai thêm KHÔNG được ghi đè sự thật đọc từ kết quả chạy (MT-10)."""
        with pytest.raises(ConDauError, match="trùng"):
            ghi_con_dau(tmp_path, "D-9999", _kq(), them={"so_lenh": 999})

    def test_khong_de_lai_file_dang_ghi(self, tmp_path) -> None:
        ghi_con_dau(tmp_path, "D-9999", _kq())
        assert list((tmp_path / "D-9999").glob("*.dang-ghi")) == []


class TestChuoiKhaiVaoSo:
    def test_dung_dang_schema_doi(self) -> None:
        assert duong_khai_so("D-0042") == "runs/D-0042/metrics.seal"


class TestThuTuTrenDuongChay:
    """Hiện vật phải ghi TRƯỚC `seal()` ở mọi chỗ gọi — ngược lại là lời khai đi trước sự thật."""

    @pytest.mark.parametrize(
        "duong_dan",
        ["src/tool_d/ablation/chay_lo.py", "entrypoints/run_backtest.py"],
    )
    def test_ghi_con_dau_dung_truoc_seal(self, duong_dan: str) -> None:
        nguon = (REPO_ROOT / duong_dan).read_text(encoding="utf-8")
        dong: dict[str, list[int]] = {}
        for n in ast.walk(ast.parse(nguon)):
            if isinstance(n, ast.Call):
                f = n.func
                ten = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
                if ten in ("ghi_con_dau", "seal"):
                    dong.setdefault(ten, []).append(n.lineno)
        assert dong.get("ghi_con_dau"), f"{duong_dan} không gọi ghi_con_dau"
        assert max(dong["ghi_con_dau"]) < min(dong["seal"]), dong

    @pytest.mark.parametrize(
        "duong_dan",
        ["src/tool_d/ablation/chay_lo.py", "entrypoints/run_backtest.py"],
    )
    def test_khong_tu_ghep_duong_dan_con_dau(self, duong_dan: str) -> None:
        """Chuỗi khai vào sổ do `duong_khai_so()` sinh — mỗi entrypoint tự ghép là hai nguồn cho một
        dạng đường dẫn mà `trial_event.schema.json:95` ràng buộc."""
        nguon = (REPO_ROOT / duong_dan).read_text(encoding="utf-8")
        assert "/metrics.seal" not in nguon
        assert "duong_khai_so(" in nguon
