"""Nguồn sự thật duy nhất cho tham số — ràng buộc 0d.2, 0d.4 (spec §6.9.5).

Cấm *Parameter của Freqtrade cho BẤT KỲ khoá nào (0d.2, L-Z37) — hệ quả:
loader chỉ trả về cấu trúc dict/mapping bất biến, không có khái niệm
"Parameter" nào ở đây để mà dùng sai. Cấm đọc tham số Tầng B/C từ biến môi
trường (0d.4, L-Z39) — loader RAISE nếu phát hiện env trùng tên.

Mọi tham số đọc qua `load_tool_d_config()` rồi `resolve()` — không có
đường nào khác trong codebase được phép đọc trực tiếp `tier_*` từ dict.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("config/tool_d_config.yaml")


class ConfigError(RuntimeError):
    """Lỗi cấu hình — VD env trùng tên tham số Tầng B/C (0d.4, L-Z39), hoặc
    khoá `_budget_remaining_B3` không phải `null` (MT-03)."""


def _freeze(obj: Any) -> Any:
    """Đệ quy biến dict/list thường thành cấu trúc bất biến (MappingProxyType
    / tuple). Cấm sửa runtime — đúng tinh thần "loader trả dict bất biến,
    truyền vào hàm" (spec dòng 562).
    """
    if isinstance(obj, dict):
        return MappingProxyType({k: _freeze(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return tuple(_freeze(v) for v in obj)
    return obj


def _non_underscore_keys(tier: Mapping[str, Any]) -> frozenset[str]:
    """Bỏ khoá `_`-prefix (khoá meta/hệ thống, VD `_budget_remaining_B3`,
    `_derived`, `_unfreeze_count`) — chỉ đây mới là tham số THẬT.
    """
    return frozenset(k for k in tier.keys() if not k.startswith("_"))


@dataclass(frozen=True)
class ToolDConfig:
    tier_a: Mapping[str, Any]
    tier_b: Mapping[str, Any]
    tier_frozen: Mapping[str, Any]
    tier_c: Mapping[str, Any]
    raw_text: str
    sha256: str


def load_tool_d_config(path: Path = DEFAULT_CONFIG_PATH) -> ToolDConfig:
    """Đọc `tool_d_config.yaml`.

    Raise `ConfigError` nếu:
      - có biến môi trường trùng tên bất kỳ tham số Tầng B hoặc Tầng C nào
        (0d.4, L-Z39) — env chỉ dùng cho vận hành (khoá/mở, chế độ, đường
        dẫn), KHÔNG BAO GIỜ cho tham số tín hiệu hay ngưỡng;
      - `tier_b._budget_remaining_B3` khác `null` (MT-03) — registry là
        nguồn sự thật duy nhất cho ngân sách B3, không phải YAML này.
    """
    raw_text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text) or {}

    tier_a = data.get("tier_a", {}) or {}
    tier_b = data.get("tier_b", {}) or {}
    tier_frozen = data.get("tier_frozen", {}) or {}
    tier_c = data.get("tier_c", {}) or {}

    guarded_names = _non_underscore_keys(tier_b) | _non_underscore_keys(tier_c)
    env_violations = sorted(name for name in guarded_names if name in os.environ)
    if env_violations:
        raise ConfigError(
            "Biến môi trường trùng tên tham số Tầng B/C (cấm bởi 0d.4, "
            f"L-Z39): {env_violations}. Env chỉ dùng cho vận hành "
            "(khoá/mở, chế độ, đường dẫn) — KHÔNG BAO GIỜ cho tham số "
            "tín hiệu hay ngưỡng."
        )

    if tier_b.get("_budget_remaining_B3") is not None:
        raise ConfigError(
            "tier_b._budget_remaining_B3 phải là null — Khả dụng B3 tính "
            "từ registry/trial_registry.jsonl, không phải từ YAML (MT-03, "
            "back-end-note.md mục 7). Nhận: "
            f"{tier_b.get('_budget_remaining_B3')!r}"
        )

    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    return ToolDConfig(
        tier_a=_freeze(tier_a),
        tier_b=_freeze(tier_b),
        tier_frozen=_freeze(tier_frozen),
        tier_c=_freeze(tier_c),
        raw_text=raw_text,
        sha256=digest,
    )


def tunable_param_names(cfg: ToolDConfig) -> frozenset[str]:
    """Tên các tham số Tầng B thật sự "tunable" (bỏ khoá `_`-prefix).

    DR-010 chốt con số này là 12 (spec §6.9.5) — lệch một cũng chặn L-Z29.
    """
    return _non_underscore_keys(cfg.tier_b)


def resolve(cfg: ToolDConfig, dotted: str) -> Any:
    """Cách DUY NHẤT đọc một tham số, VD `resolve(cfg, "tier_b.zss_threshold")`.

    Không hardcode, không đọc trực tiếp dict `tier_*` ở bất kỳ nơi nào khác
    trong codebase.
    """
    parts = dotted.split(".")
    if not parts or not hasattr(cfg, parts[0]):
        raise KeyError(f"không có tầng '{dotted.split('.')[0]}' trong ToolDConfig")
    node: Any = getattr(cfg, parts[0])
    for part in parts[1:]:
        if not isinstance(node, Mapping) or part not in node:
            raise KeyError(f"không tìm thấy '{dotted}' (dừng ở '{part}')")
        node = node[part]
    return node
