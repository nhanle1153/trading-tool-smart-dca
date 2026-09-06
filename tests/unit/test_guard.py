"""TD-0015 — measurement_guard(). Test khoá đầy đủ hơn (wiring vào 8
entrypoint, danh sách đóng) nằm ở test_lz36_entrypoint_guard.py (TD-0017).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tool_d.config.loader import ConfigError
from tool_d.measurement.guard import GuardOutcome, measurement_guard


@pytest.fixture()
def config_path() -> Path:
    return Path("config/tool_d_config.yaml")


class TestKhongCoFileAn:
    def test_pass_khi_thu_muc_rong(self, tmp_path: Path, config_path: Path) -> None:
        strategy_dir = tmp_path / "strategies"
        strategy_dir.mkdir()
        report = measurement_guard(
            "E1", strategy_dir=strategy_dir, config_path=config_path
        )
        assert report.outcome is GuardOutcome.PASS
        assert report.params_source == "yaml"
        assert report.hidden_param_files == {}
        assert report.guard_passed is True

    def test_pass_khi_thu_muc_khong_ton_tai(self, tmp_path: Path, config_path: Path) -> None:
        report = measurement_guard(
            "E1", strategy_dir=tmp_path / "khong_ton_tai", config_path=config_path
        )
        assert report.outcome is GuardOutcome.PASS


class TestPhatHienFileThamSoAn:
    def test_json_hop_le_bi_chan(
        self, tmp_path: Path, config_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        strategy_dir = tmp_path / "strategies"
        strategy_dir.mkdir()
        f = strategy_dir / "ZoneAbsorptionStrategy.json"
        f.write_text('{"zss_threshold": 0.9}')

        report = measurement_guard(
            "E1", strategy_dir=strategy_dir, config_path=config_path
        )

        assert report.outcome is GuardOutcome.BLOCKED
        assert report.guard_passed is False
        assert str(f) in report.hidden_param_files
        # File PHẢI vẫn còn nguyên — guard không được tự xoá (spec dòng 543-544).
        assert f.exists()
        assert f.read_text() == '{"zss_threshold": 0.9}'
        # Nội dung phải được IN ra stdout (spec dòng 543).
        out = capsys.readouterr().out
        assert "0.9" in out
        assert str(f) in out

    def test_json_hong_van_tinh_la_co(
        self, tmp_path: Path, config_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # "kể cả JSON hỏng vẫn tính là có" (spec dòng 542).
        strategy_dir = tmp_path / "strategies"
        strategy_dir.mkdir()
        f = strategy_dir / "Broken.json"
        f.write_text("{ khong phai json hop le !!!")

        report = measurement_guard(
            "E1", strategy_dir=strategy_dir, config_path=config_path
        )

        assert report.outcome is GuardOutcome.BLOCKED
        assert f.exists()
        out = capsys.readouterr().out
        assert "khong phai json hop le" in out

    def test_co_co_with_params_file_thi_khong_chan_nhung_params_source_doi(
        self, tmp_path: Path, config_path: Path
    ) -> None:
        strategy_dir = tmp_path / "strategies"
        strategy_dir.mkdir()
        (strategy_dir / "X.json").write_text("{}")

        report = measurement_guard(
            "E1",
            strategy_dir=strategy_dir,
            config_path=config_path,
            with_params_file=True,
        )

        assert report.outcome is GuardOutcome.PASS_WITH_PARAMS_FILE
        assert report.params_source == "params_file"
        # guard_passed=True (không chặn) NHƯNG params_source != "yaml" —
        # bản ghi này vẫn phải bị validate_provenance() từ chối cho gate.
        assert report.guard_passed is True


class TestCacheMode:
    def test_doc_duoc_cache_none_dang_hai_cach_viet(
        self, tmp_path: Path, config_path: Path
    ) -> None:
        strategy_dir = tmp_path / "strategies"
        strategy_dir.mkdir()
        r1 = measurement_guard(
            "E1", strategy_dir=strategy_dir, config_path=config_path,
            argv=["--cache", "none"],
        )
        r2 = measurement_guard(
            "E1", strategy_dir=strategy_dir, config_path=config_path,
            argv=["--cache=none"],
        )
        assert r1.cache_mode == "none"
        assert r2.cache_mode == "none"

    def test_vang_mat_thi_none_khong_tu_suy_doan(
        self, tmp_path: Path, config_path: Path
    ) -> None:
        strategy_dir = tmp_path / "strategies"
        strategy_dir.mkdir()
        report = measurement_guard(
            "E1", strategy_dir=strategy_dir, config_path=config_path, argv=[]
        )
        assert report.cache_mode is None


class TestUyQuyenKiemEnv:
    def test_env_vi_pham_thi_raise_truoc_khi_kiem_file_an(
        self, tmp_path: Path, config_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("zss_threshold", "0.9")
        strategy_dir = tmp_path / "strategies"
        strategy_dir.mkdir()
        with pytest.raises(ConfigError):
            measurement_guard("E1", strategy_dir=strategy_dir, config_path=config_path)
