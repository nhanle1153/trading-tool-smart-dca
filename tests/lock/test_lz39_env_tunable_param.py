"""L-Z39 — grep repo: KHÔNG có os.environ / os.getenv đọc tên tham số Tầng
B/C (danh sách tên lấy từ tool_d_config.yaml). Spec dòng 679-680.

Hai lớp kiểm: (1) tĩnh — quét mã nguồn tìm truy cập env bằng đúng tên một
tham số Tầng B/C; (2) động — loader.py phải RAISE khi biến môi trường thật
sự trùng tên (0d.4).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tool_d.config.loader import ConfigError, DEFAULT_CONFIG_PATH, _non_underscore_keys
from tool_d.config.loader import load_tool_d_config

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("src", "entrypoints")

# Bắt các dạng truy cập env bằng MỘT TÊN LITERAL: os.getenv("x"),
# os.environ.get("x"), os.environ["x"] / os.environ.get('x', ...).
_ENV_ACCESS = re.compile(
    r"os\.(?:getenv|environ\.get)\(\s*['\"]([A-Za-z0-9_]+)['\"]"
    r"|os\.environ\[\s*['\"]([A-Za-z0-9_]+)['\"]\s*\]"
)


def _guarded_names() -> frozenset[str]:
    cfg = load_tool_d_config(Path(DEFAULT_CONFIG_PATH))
    return _non_underscore_keys(cfg.tier_b) | _non_underscore_keys(cfg.tier_c)


def _python_files() -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        base = REPO_ROOT / d
        if base.exists():
            files.extend(base.rglob("*.py"))
    return files


class TestKhongDocEnvBangTenThamSo:
    def test_khong_co_truy_cap_env_bang_ten_tham_so_tang_b_c(self) -> None:
        guarded = _guarded_names()
        vi_pham: list[str] = []
        for f in _python_files():
            text = f.read_text(encoding="utf-8", errors="replace")
            for match in _ENV_ACCESS.finditer(text):
                name = match.group(1) or match.group(2)
                if name in guarded:
                    vi_pham.append(f"{f.relative_to(REPO_ROOT)}: env đọc '{name}'")
        assert vi_pham == [], f"Phát hiện env đọc tham số Tầng B/C: {vi_pham}"

    def test_bo_quet_co_rang(self) -> None:
        guarded = _guarded_names()
        mot_ten = next(iter(guarded))
        text_gia_lap = f'os.getenv("{mot_ten}")'
        match = _ENV_ACCESS.search(text_gia_lap)
        assert match is not None
        assert match.group(1) == mot_ten


class TestLoaderRaiseKhiEnvTrungTen:
    def test_env_trung_ten_tham_so_tang_b_thi_raise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("zss_threshold", "0.7")
        with pytest.raises(ConfigError):
            load_tool_d_config(Path(DEFAULT_CONFIG_PATH))

    def test_env_trung_ten_tham_so_tang_c_thi_raise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("k_swing_confirm", "5")
        with pytest.raises(ConfigError):
            load_tool_d_config(Path(DEFAULT_CONFIG_PATH))

    def test_env_khong_lien_quan_thi_khong_sao(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FREQTRADE__DRY_RUN", "true")  # tên vận hành, hợp lệ
        cfg = load_tool_d_config(Path(DEFAULT_CONFIG_PATH))
        assert cfg is not None
