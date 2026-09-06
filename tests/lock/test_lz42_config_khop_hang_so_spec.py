"""L-Z42 🔴 — `config/freqtrade/config.json` KHỚP hằng số spec §3.5.

Spec dòng 1202: *"test đối chiếu config.json với hằng số spec — hai nơi
không được tự do lệch nhau."* Nên test này KHÔNG chép hằng số vào đây rồi
so với config: nó **đọc thẳng khối "ÁNH XẠ CONFIG FREQTRADE (LD-13)" trong
`tool-d-smart-dca.md`** làm một bên của phép so. Chép số vào test là tạo ra
nguồn sự thật THỨ BA — đúng chế độ hỏng mà LD-13 sinh ra để chặn.

Khối spec (dòng 1189-1201) sinh đúng 5 cặp `đường.khoá = giá_trị`. Test
assert đúng 5 cặp và đúng tập tên đó: spec thêm/bớt một hằng số thì test
đỏ, buộc người sửa mở lại config — thay vì im lặng bỏ qua hằng số mới.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "tool-d-smart-dca.md"
CONFIG_PATH = REPO_ROOT / "config" / "freqtrade" / "config.json"

BLOCK_START = "ÁNH XẠ CONFIG FREQTRADE"
BLOCK_END = "════"
# `a.b = "x"` hoặc `a.b = 180`, thụt lề ≥2. Dừng trước cột comment `#`.
PAIR = re.compile(r'^\s{2,}([a-z_]+(?:\.[a-z_]+)+)\s*=\s*("[^"]*"|[0-9]+)')

# Tập tên spec hiện quy định. Đây KHÔNG phải bản sao giá trị (giá trị vẫn
# đọc từ spec) — chỉ là chốt "spec có đúng 5 hằng số này" để việc spec đổi
# hình dạng không lọt qua im lặng.
EXPECTED_KEYS = {
    "order_types.entry",
    "order_time_in_force.entry",
    "entry_pricing.price_side",
    "unfilledtimeout.entry",
    "unfilledtimeout.unit",
}

_MISSING = object()


def _parse_spec_constants() -> dict[str, Any]:
    lines = SPEC_PATH.read_text(encoding="utf-8").splitlines()
    starts = [i for i, l in enumerate(lines) if BLOCK_START in l]
    assert len(starts) == 1, (
        f"Cần đúng 1 khối {BLOCK_START!r} trong spec, tìm thấy {len(starts)} — "
        "spec đã đổi cấu trúc, đọc lại §3.5 trước khi sửa test."
    )
    start = starts[0]
    out: dict[str, Any] = {}
    for line in lines[start + 1 :]:
        if BLOCK_END in line:
            break
        m = PAIR.match(line)
        if m is None:
            continue
        key, raw = m.groups()
        out[key] = json.loads(raw) if raw.startswith('"') else int(raw)
    return out


def _get(cfg: dict[str, Any], dotted: str) -> Any:
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


class TestConfigKhopHangSoSpec:
    def test_doc_duoc_dung_tap_hang_so_tu_spec(self) -> None:
        hang_so = _parse_spec_constants()
        assert set(hang_so) == EXPECTED_KEYS, (
            f"Khối §3.5 của spec sinh {sorted(hang_so)}, mong đợi "
            f"{sorted(EXPECTED_KEYS)} — spec đã đổi, mở §3.5 đọc lại."
        )

    def test_config_khop_tung_hang_so_spec(self) -> None:
        hang_so = _parse_spec_constants()
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        lech: list[str] = []
        for key, spec_value in sorted(hang_so.items()):
            actual = _get(cfg, key)
            if actual is _MISSING:
                lech.append(f"{key}: THIẾU trong config.json (spec: {spec_value!r})")
            elif actual != spec_value:
                lech.append(f"{key}: config={actual!r} ≠ spec={spec_value!r}")
        assert lech == [], f"config.json lệch spec §3.5: {lech}"

    def test_khong_dung_limit_maker(self) -> None:
        # Spec dòng 1192-1196 nói thẳng: "limit_maker" KHÔNG phải giá trị hợp
        # lệ của order_types — post-only THẬT đi qua time-in-force = "PO".
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        raw = json.dumps({k: v for k, v in cfg.items() if not k.startswith("_comment")})
        assert "limit_maker" not in raw, (
            "Còn 'limit_maker' trong config.json — dùng order_time_in_force."
            "entry = 'PO' (§3.5, LD-13)."
        )

    def test_ttl_lenh_cho_khop_ba_nen_1h(self) -> None:
        # 180 phút không phải con số rời: nó LÀ "tối đa 3 nến chờ" của §3.3b
        # nhân với timeframe. Buộc hai trường trong cùng config nhất quán.
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        assert cfg["timeframe"] == "1h", (
            f"timeframe phải là '1h' (§3.3c, L-Z33), nhận {cfg['timeframe']!r}"
        )
        assert _get(cfg, "unfilledtimeout.unit") == "minutes"
        assert _get(cfg, "unfilledtimeout.entry") == 3 * 60, (
            "unfilledtimeout.entry phải = 3 nến × 60 phút = 180 (tuổi thọ lệnh "
            "chờ tranche 1, §3.3b/§3.5)."
        )

    # ── Chứng minh bộ parse có răng ───────────────────────────────────
    def test_parse_bat_dung_dinh_dang_spec(self) -> None:
        assert PAIR.match('   order_types.entry            = "limit"').groups() == (
            "order_types.entry",
            '"limit"',
        )
        assert PAIR.match("   unfilledtimeout.entry        = 180  # phút").groups() == (
            "unfilledtimeout.entry",
            "180",
        )
        # Dòng văn xuôi và dòng mũi tên trong cùng khối không được lọt vào.
        assert PAIR.match("   custom_entry_price()         → trả p1_order") is None
        assert PAIR.match("stake_amount = 10") is None  # thụt lề <2

    def test_so_sanh_bat_duoc_lech(self) -> None:
        assert _get({"order_types": {"entry": "market"}}, "order_types.entry") == "market"
        assert _get({"order_types": {}}, "order_types.entry") is _MISSING
