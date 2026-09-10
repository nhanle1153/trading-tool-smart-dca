"""Guard file tham số ẩn — ràng buộc 0d.1 (spec dòng 526-550). Canh bởi
L-Z36, L-Z37.

Đây là cái bẫy đã hạ Tool A BA LẦN: Freqtrade tự ghi `<TênStrategy>.json`
cạnh file strategy sau mỗi lần hyperopt, file đó ĐÈ mọi tham số ở mọi lần
chạy sau (kể cả backtesting thường), và thường nằm trong `.gitignore` nên
không ai thấy.

`measurement_guard()` là lệnh gọi DUY NHẤT thoả cả BA ràng buộc:
    - 0d.1: phát hiện file tham số ẩn, DỪNG, in nội dung, KHÔNG tự xoá.
    - 0d.4: env trùng tên tham số Tầng B/C (uỷ quyền cho
      `load_tool_d_config()`, KHÔNG bắt lỗi đó ở đây — một cấu hình bị
      nhiễm bởi env không đáng để guard tiếp tục chạy).
    - TD-0204: đường dẫn kiểu Windows lọt vào `argv` khi tiến trình đang
      chạy trên POSIX — xem `find_windows_path_leak()`.

Gọi Ở DÒNG ĐẦU TIÊN sau parse tham số, trong mọi entrypoint E1-E8 (spec
dòng 652). KHÔNG bọc trong decorator — L-Z36 kiểm bằng AST, decorator làm
test phải suy luận và dễ PASS giả.

════ TD-0204 — vì sao đặt Ở ĐÂY, không ở từng entrypoint ════

Ba sự cố THẬT (TD-0200, `docs/research-log.md` 09/09/2026 + phụ lục
10/09/2026): Git Bash (MSYS) tự dịch một đường dẫn POSIX (`/backup`)
thành dạng ổ đĩa Windows (`C:/Program Files/Git/backup`) TRƯỚC khi
truyền vào tiến trình Linux trong container. Chuỗi kết quả KHÔNG mở đầu
bằng `/` nên Linux hiểu nó là đường dẫn TƯƠNG ĐỐI — một thao tác ghi
(sao lưu H19, backup lockbox) âm thầm ghi sai chỗ, trong khi lệnh gọi
vẫn báo `✅ thành công`.

Phạm vi ĐÃ ĐO (không suy rộng): đúng 4 cờ nhận đường dẫn trong toàn bộ
`entrypoints/`, tất cả nằm trong `backfill_data.py` (`--data-dir`,
`--backup-root`, `--snapshot-out`, `--verify-after`). Nhưng một quy ước
văn xuôi ("nhớ dùng PowerShell") không có máy thi hành — đúng thứ
`MT-15`/`L-Z15` liên tục bắt được. Đặt máy canh trong `measurement_guard()`
(mọi entrypoint đã gọi Ở DÒNG ĐẦU, N5) thay vì sửa từng cờ: phủ được cả
4 cờ hiện có VÀ mọi cờ tương lai, không cần nhớ thêm một dòng nào mỗi khi
có entrypoint mới nhận thêm một tham số đường dẫn.
"""

from __future__ import annotations

import os
import re
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
    windows_path_leak: str | None = None
    """TD-0204 — giá trị `argv` đã bắt được, nếu `outcome is BLOCKED` vì lý
    do này (khác lý do file tham số ẩn). `None` ở mọi trường hợp khác."""

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


# `C:\...` hoặc `C:/...` — một ký tự chữ cái, dấu hai chấm, rồi dấu phân
# cách đường dẫn. KHÔNG khớp `C:` đứng một mình cuối chuỗi (không phải
# đường dẫn) và KHÔNG khớp cổng URL kiểu `host:1234` (bắt buộc dấu phân
# cách ngay sau dấu hai chấm, không phải chữ số).
_RE_WINDOWS_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def find_windows_path_leak(argv: Sequence[str]) -> str | None:
    """TD-0204 — token `argv` nào đó có hình dạng đường dẫn ổ đĩa Windows,
    trong khi tiến trình đang chạy trên POSIX? Trả token gốc (nguyên văn,
    chưa tách `=`) nếu có, `None` nếu sạch.

    🔴 Chỉ xét khi `os.name != "nt"` — trên chính host Windows của dự án,
    `C:\\...` là đường dẫn HỢP LỆ, không phải rò rỉ. Thiếu điều kiện này
    sẽ tự tạo báo động giả trên host (N6: không bịa vi phạm), và là đúng
    loại sai lầm mà giả thuyết "route thứ ba" của phiên `-46` cảnh báo:
    `backup_data_dir()` (nơi lỗi này từng gây hại) là Python thuần, chạy
    được trên host lẫn trong container — máy canh không được giả định
    "luôn chạy trong Docker".

    Xét cả hai cách viết cờ: `--co gia-tri` (token này CHÍNH LÀ giá trị,
    vì shell/`argparse` đã tách sẵn) và `--co=gia-tri` (giá trị nằm sau
    dấu `=` trong CÙNG một token) — cả 4 cờ nhận đường dẫn của
    `backfill_data.py` chấp nhận cả hai cách viết.
    """
    if os.name == "nt":
        return None
    for token in argv:
        value = token.split("=", 1)[1] if token.startswith("--") and "=" in token else token
        if _RE_WINDOWS_DRIVE_PATH.match(value):
            return token
    return None


def extract_cache_mode(argv: Sequence[str]) -> str | None:
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

    cache_mode = extract_cache_mode(argv)
    checked_at = _utcnow()

    # TD-0204 — kiểm TRƯỚC cả file tham số ẩn: một argv đã hỏng hình dạng
    # (Git Bash dịch nhầm đường dẫn) là chuyện của CHÍNH lệnh gọi, đứng
    # trước câu hỏi "cấu hình nào đang được dùng".
    leak = find_windows_path_leak(argv)
    if leak is not None:
        print(f"\U0001f6d1 ĐƯỜNG DẪN WINDOWS LỌT VÀO TIẾN TRÌNH POSIX: {leak!r}")
        print(
            "   Dấu hiệu Git Bash (MSYS) đã dịch một đường dẫn POSIX (vd `/backup`) "
            "thành dạng ổ đĩa Windows TRƯỚC khi truyền vào container — chuỗi kết quả "
            "không mở đầu bằng `/` nên bị hiểu là đường dẫn TƯƠNG ĐỐI, và một thao tác "
            "ghi có thể âm thầm ghi sai chỗ trong khi vẫn báo thành công (TD-0200)."
        )
        print("   Chạy lại bằng PowerShell, hoặc đặt MSYS_NO_PATHCONV=1 nếu cố ý dùng Git Bash.")
        return GuardReport(
            outcome=GuardOutcome.BLOCKED,
            entrypoint=entrypoint,
            params_source="yaml",
            hidden_param_files={},
            cache_mode=cache_mode,
            checked_at=checked_at,
            windows_path_leak=leak,
        )

    hidden = _scan_hidden_param_files(strategy_dir)

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
