"""Guard file tham số ẩn — ràng buộc 0d.1 (spec dòng 526-550). Canh bởi
L-Z36, L-Z37.

Đây là cái bẫy đã hạ Tool A BA LẦN: Freqtrade tự ghi `<TênStrategy>.json`
cạnh file strategy sau mỗi lần hyperopt, file đó ĐÈ mọi tham số ở mọi lần
chạy sau (kể cả backtesting thường), và thường nằm trong `.gitignore` nên
không ai thấy.

`measurement_guard()` là lệnh gọi DUY NHẤT thoả cả hai ràng buộc:
    - 0d.1: phát hiện file tham số ẩn, DỪNG, in nội dung, KHÔNG tự xoá.
    - 0d.4: env trùng tên tham số Tầng B/C (uỷ quyền cho
      `load_tool_d_config()`, KHÔNG bắt lỗi đó ở đây — một cấu hình bị
      nhiễm bởi env không đáng để guard tiếp tục chạy).

Gọi Ở DÒNG ĐẦU TIÊN sau parse tham số, trong mọi entrypoint E1-E8 (spec
dòng 652). KHÔNG bọc trong decorator — L-Z36 kiểm bằng AST, decorator làm
test phải suy luận và dễ PASS giả.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from tool_d.config.loader import DEFAULT_CONFIG_PATH, load_tool_d_config

# Exit code riêng cho "guard chặn vì phát hiện file tham số ẩn" — spec dòng
# 543 chỉ nói "DỪNG", không định con số; chọn 86 (không trùng exit code
# thường gặp của Python/Freqtrade: 0,1,2) để phân biệt được ngay trong log.
EXIT_GUARD_BLOCKED = 86

DEFAULT_STRATEGY_DIR = Path("user_data/strategies")


class GuardOutcome(Enum):
    PASS = "pass"
    BLOCKED = "blocked"
    PASS_WITH_PARAMS_FILE = "pass_with_params_file"


@dataclass(frozen=True)
class GuardReport:
    outcome: GuardOutcome
    entrypoint: str
    params_source: str  # "yaml" | "params_file"
    hidden_param_files: Mapping[str, str]
    cache_mode: str | None
    checked_at: datetime

    @property
    def guard_passed(self) -> bool:
        """True nếu guard không CHẶN chạy — dùng cho khối xuất xứ (0d.5).

        🔴 Lưu ý: guard_passed=True KHÔNG có nghĩa bản ghi hợp lệ cho gate —
        nếu outcome là PASS_WITH_PARAMS_FILE thì params_source == "params_file"
        và `validate_provenance()` (L-Z40) sẽ vẫn từ chối bản ghi đó.
        """
        return self.outcome is not GuardOutcome.BLOCKED


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _scan_hidden_param_files(strategy_dir: Path) -> dict[str, str]:
    """Quét *.json cạnh strategy.

    File JSON HỎNG vẫn được tính là "có mặt" (spec dòng 542) — đọc nội
    dung thô bằng text, KHÔNG parse JSON. Guard không quan tâm cấu trúc
    file, chỉ quan tâm sự tồn tại của nó.
    """
    if not strategy_dir.exists():
        return {}
    found: dict[str, str] = {}
    for f in sorted(strategy_dir.glob("*.json")):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            content = f"<KHÔNG ĐỌC ĐƯỢC: {exc}>"
        found[str(f)] = content
    return found


def _extract_cache_mode(argv: Sequence[str]) -> str | None:
    """Đọc giá trị theo sau `--cache` trong argv, nếu có. Không tự suy đoán
    giá trị mặc định — trả None nếu cờ vắng mặt, để `assert_cache_none()`
    (L-Z38) tự quyết định coi vắng mặt là vi phạm.
    """
    argv = list(argv)
    for i, a in enumerate(argv):
        if a == "--cache" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--cache="):
            return a.split("=", 1)[1]
    return None


def measurement_guard(
    entrypoint: str,
    *,
    strategy_dir: Path = DEFAULT_STRATEGY_DIR,
    config_path: Path = DEFAULT_CONFIG_PATH,
    argv: Sequence[str] = (),
    with_params_file: bool = False,
) -> GuardReport:
    """Guard tổng — gọi ở dòng đầu tiên sau parse tham số của mọi
    entrypoint E1-E8.

    Không raise cho trường hợp phát hiện file tham số ẩn — trả về
    `GuardReport(outcome=BLOCKED, ...)` để `main()` tự quyết định
    `sys.exit(EXIT_GUARD_BLOCKED)`. Việc IN nội dung file ra stdout xảy ra
    ngay tại đây (side effect cố ý — spec dòng 543 đòi in NGAY khi phát
    hiện, không phải sau một bước xử lý khác).

    `load_tool_d_config()` có thể raise `ConfigError` (0d.4, L-Z39) —
    KHÔNG bắt lỗi đó ở đây, để nó dừng chương trình ngay.
    """
    load_tool_d_config(config_path)  # raise ConfigError nếu env vi phạm

    hidden = _scan_hidden_param_files(strategy_dir)
    cache_mode = _extract_cache_mode(argv)
    checked_at = _utcnow()

    if hidden and not with_params_file:
        for path, content in hidden.items():
            print(f"\U0001f6d1 PHÁT HIỆN FILE THAM SỐ ẨN: {path}")
            print(content)
        return GuardReport(
            outcome=GuardOutcome.BLOCKED,
            entrypoint=entrypoint,
            params_source="yaml",
            hidden_param_files=hidden,
            cache_mode=cache_mode,
            checked_at=checked_at,
        )

    if hidden and with_params_file:
        return GuardReport(
            outcome=GuardOutcome.PASS_WITH_PARAMS_FILE,
            entrypoint=entrypoint,
            params_source="params_file",
            hidden_param_files=hidden,
            cache_mode=cache_mode,
            checked_at=checked_at,
        )

    return GuardReport(
        outcome=GuardOutcome.PASS,
        entrypoint=entrypoint,
        params_source="yaml",
        hidden_param_files={},
        cache_mode=cache_mode,
        checked_at=checked_at,
    )
