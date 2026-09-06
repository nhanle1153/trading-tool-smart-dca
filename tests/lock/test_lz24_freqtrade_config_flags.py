"""L-Z24 🔴 CRITICAL — config Freqtrade thoả TẤT CẢ sáu điều kiện của §0c.4
(spec dòng 502-508):

    freqai.enabled             = false
    edge.enabled               = false
    trailing_stop              = false
    position_adjustment_enable = true
    use_exit_signal            = true
    protections                = []   (hoặc lý do ghi rõ)

Hai chỗ spec cho phép co giãn, và cách test này khoá lại:

* `freqai` — freqtrade 2026.8 đòi đủ bộ khoá con MỘT KHI khoá "freqai" xuất
  hiện, nên "khai báo tắt" bằng `{"enabled": false}` làm show-config lỗi.
  Vắng mặt hoàn toàn = tắt theo mặc định. Test chấp nhận CẢ HAI dạng
  (vắng mặt HOẶC enabled=false) — nhưng KHÔNG chấp nhận enabled=true.
* `protections` — spec viết "[] (hoặc lý do ghi rõ)". Khoá này đã bị
  freqtrade 2026.8 deprecate trong config.json. Test không thả cửa cho
  "vắng mặt là được": vắng mặt CHỈ hợp lệ khi trong chính file config có
  một khoá `_comment_*` giải thích, tức "lý do ghi rõ" là chuỗi máy kiểm
  được chứ không phải lời hứa miệng.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config" / "freqtrade" / "config.json"

# Năm cờ có giá trị bắt buộc tuyệt đối (spec dòng 503-507). `freqai` và
# `protections` xử lý riêng vì spec cho phép hai dạng — xem docstring.
REQUIRED_FLAGS: dict[str, bool] = {
    "edge.enabled": False,
    "trailing_stop": False,
    "position_adjustment_enable": True,
    "use_exit_signal": True,
}

_MISSING = object()


def _load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _get(cfg: dict[str, Any], dotted: str) -> Any:
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


def _reason_comments_mentioning(cfg: dict[str, Any], word: str) -> list[str]:
    """Các khoá `_comment_*` ở cấp cao nhất có nhắc tới `word`."""
    return [
        v
        for k, v in cfg.items()
        if k.startswith("_comment") and isinstance(v, str) and word in v
    ]


class TestConfigFreqtradeThoaLZ24:
    def test_config_ton_tai_va_la_json_hop_le(self) -> None:
        assert CONFIG_PATH.exists(), f"Không tìm thấy {CONFIG_PATH}"
        assert isinstance(_load_config(), dict)

    def test_bon_co_bat_buoc_dung_gia_tri(self) -> None:
        cfg = _load_config()
        sai: list[str] = []
        for dotted, expected in REQUIRED_FLAGS.items():
            actual = _get(cfg, dotted)
            if actual is _MISSING:
                sai.append(f"{dotted}: THIẾU (spec đòi {expected})")
            elif actual is not expected:
                sai.append(f"{dotted}: {actual!r}, spec đòi {expected!r}")
        assert sai == [], f"config.json vi phạm L-Z24: {sai}"

    def test_freqai_tat_hoac_vang_mat(self) -> None:
        # §0c.2 CẤM TUYỆT ĐỐI FreqAI. Hai dạng hợp lệ, một dạng cấm.
        cfg = _load_config()
        enabled = _get(cfg, "freqai.enabled")
        assert enabled is _MISSING or enabled is False, (
            f"freqai phải vắng mặt hoặc enabled=false, nhận: {enabled!r}"
        )
        if "freqai" in cfg:
            # Nếu có mặt thì phải là dict — tránh dạng `"freqai": false` lọt
            # qua vì _get trả _MISSING khi node không phải dict.
            assert isinstance(cfg["freqai"], dict), "freqai phải là object"

    def test_protections_rong_hoac_co_ly_do_ghi_ro(self) -> None:
        cfg = _load_config()
        protections = _get(cfg, "protections")
        if protections is not _MISSING:
            assert protections == [], (
                f"protections phải là [] (§0c.3: chọn MỘT nguồn sự thật, dùng "
                f"logic Tool D), nhận: {protections!r}"
            )
            return
        # Vắng mặt → spec đòi "lý do ghi rõ". Lý do phải nằm trong chính file
        # config, không phải ở chat hay commit message.
        ly_do = _reason_comments_mentioning(cfg, "protections")
        assert ly_do != [], (
            "protections vắng mặt trong config.json mà KHÔNG có khoá "
            "`_comment_*` nào giải thích vì sao — spec dòng 508 cho phép bỏ "
            "trống nhưng đòi 'lý do ghi rõ'."
        )

    # ── Chứng minh bộ kiểm có răng: cấu hình sai phải bị bắt ──────────
    def test_bo_kiem_bat_duoc_config_sai(self) -> None:
        xau = {"edge": {"enabled": True}, "trailing_stop": True}
        assert _get(xau, "edge.enabled") is True
        assert _get(xau, "position_adjustment_enable") is _MISSING
        assert _get(xau, "freqai.enabled") is _MISSING  # vắng mặt = hợp lệ

    def test_bo_kiem_bat_duoc_freqai_bat(self) -> None:
        assert _get({"freqai": {"enabled": True}}, "freqai.enabled") is True

    def test_bo_kiem_bat_duoc_protections_khong_rong(self) -> None:
        cfg = {"protections": [{"method": "CooldownPeriod"}]}
        assert _get(cfg, "protections") != []
        assert _reason_comments_mentioning({"_comment_x": "về edge"}, "protections") == []
