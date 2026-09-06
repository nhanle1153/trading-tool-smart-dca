"""L-Z25 🔴 CRITICAL — KHÔNG có dấu vết `hyperopt` ở bất cứ đâu trong repo.

Spec dòng 510-512: *"grep toàn repo + lịch sử lệnh: KHÔNG có `hyperopt`.
Phát hiện một lần chạy hyperopt → trial_registry MẤT HIỆU LỰC, phải khai
lại N từ đầu."* §0c.2 cấm tuyệt đối: 500 epoch = 500 phép thử ngầm, phá
sạch ngân sách N=114 của DR-010.

🔎 "lịch sử lệnh" được ánh xạ thế nào (quyết định của TD-0027, ghi ở đây
để không ai tưởng test bảo đảm nhiều hơn nó thật sự bảo đảm):
lịch sử shell của máy chủ dự án KHÔNG máy kiểm được từ trong container —
nó không được mount, khác nhau giữa các máy, và không phải bằng chứng tái
lập được. Thay vào đó test kiểm BA bề mặt mà một lần chạy hyperopt BẮT
BUỘC để lại dấu, cái nào cũng nằm trong repo:

  Tầng 1 — mã CHẠY ĐƯỢC: không token `hyperopt` trong code/config/docker.
  Tầng 2 — HIỆN VẬT trên đĩa: `*.fthypt`, `*hyperopt*.pickle`, và thư
           mục `hyperopt_results/` / `hyperopts/` CÓ FILE bên trong.
           🔴 Thư mục RỖNG không phải vi phạm: `freqtrade create-userdir`
           dựng sẵn cả cây `user_data/` (kể cả `hyperopts/`,
           `freqaimodels/`) ở lần khởi tạo, trước khi có bất kỳ lần chạy
           nào. Bắt cả thư mục rỗng là báo động giả kinh niên — và một
           test kêu oan thường xuyên sẽ bị người ta tắt đi, tức mất luôn
           lớp canh thật. Một lần CHẠY hyperopt để lại FILE.
  Tầng 3 — SỔ SÁCH: không dòng nào trong `registry/*.jsonl` hay `runs/`
           nhắc tới hyperopt.

Bề mặt thứ tư — file `<TênStrategy>.json` ẩn, dấu vết nguy hiểm nhất của
hyperopt — do `measurement_guard()` (§0d.1) + L-Z36/L-Z37 canh, không lặp
lại ở đây.

📌 Tầng 1 bỏ qua CHÍNH file này: các fixture "chứng minh bộ quét có răng"
bên dưới cố ý chứa chuỗi `"freqtrade hyperopt --epochs 500"` — quét chính
mình thì test luôn đỏ. Đây là ngoại lệ DUY NHẤT, và nó tự cân bằng: nếu ai
đó gỡ mất tính năng bắt lỗi, các test âm tính ở cuối file sẽ đỏ.

📌 Cách lọc: với `.py` chỉ bỏ COMMENT và chuỗi ba nháy (docstring). Chuỗi
một nháy VẪN bị quét — để `subprocess.run("freqtrade hyperopt ...")` không
lọt. Hệ quả đã biết: một chuỗi ba nháy chứa lệnh hyperopt sẽ lọt; đó là
đánh đổi có chủ ý để docstring giải thích LỆNH CẤM (như guard.py dòng 5)
không bị tính là vi phạm.
"""

from __future__ import annotations

import io
import json
import re
import tokenize
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_DIRS = ("src", "entrypoints", "config", "user_data", "docker", "tests")
SCAN_GLOBS = ("*.py", "*.json", "*.yaml", "*.yml", "*.sh")
EXTRA_FILES = ("docker/Dockerfile", ".gitignore", "pyproject.toml")
# Không quét: repo con của front-end (có .git riêng, ngoài phạm vi D0-PRE),
# bytecode, và bản thân .git.
EXCLUDE_PARTS = {".git", "__pycache__", "node_modules", "dashboard-ui", ".venv"}

FORBIDDEN = re.compile(r"hyperopt", re.IGNORECASE)

# Hiện vật freqtrade ghi ra sau MỘT lần chạy hyperopt.
ARTIFACT_GLOBS = ("*.fthypt", "*hyperopt*.pickle", "*hyperopt*.json")
# Thư mục chỉ tính là hiện vật khi CÓ FILE bên trong — xem docstring.
ARTIFACT_DIRS = ("hyperopt_results", "hyperopts")

# Tầng 1 không quét chính file này (ngoại lệ duy nhất, xem docstring).
SELF_PATH = Path(__file__).resolve()

LEDGER_PATHS = ("registry", "runs")

TRIPLE_PREFIXES = ('"""', "'''")


# ── lọc bình luận ────────────────────────────────────────────────────
def _strip_hash_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def _is_triple_quoted(tok_string: str) -> bool:
    # Bỏ tiền tố f/r/b/u (tối đa 2 ký tự) trước khi xét ba nháy.
    body = tok_string.lstrip("fFrRbBuU")
    return body.startswith(TRIPLE_PREFIXES)


def _strip_py_noise(text: str) -> str:
    """Bỏ COMMENT và chuỗi ba nháy; giữ mọi thứ khác (xem docstring module).

    File .py hỏng cú pháp → trả nguyên văn (thà báo động giả còn hơn im
    lặng bỏ qua một file không đọc được).
    """
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return text
    giu: list[str] = []
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            continue
        if tok.type == tokenize.STRING and _is_triple_quoted(tok.string):
            continue
        giu.append(tok.string)
    return "\n".join(giu)


def _strip_json_comment_keys(node: Any) -> Any:
    if isinstance(node, dict):
        return {
            k: _strip_json_comment_keys(v)
            for k, v in node.items()
            if not k.startswith("_comment")
        }
    if isinstance(node, list):
        return [_strip_json_comment_keys(v) for v in node]
    return node


def _executable_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".py":
        return _strip_py_noise(raw)
    if path.suffix == ".json":
        try:
            return json.dumps(_strip_json_comment_keys(json.loads(raw)), ensure_ascii=False)
        except json.JSONDecodeError:
            return raw
    return _strip_hash_comments(raw)


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDE_PARTS for part in path.parts)


def _walk_pruned(root: Path):
    """Duyệt toàn bộ cây con của `root`, CẮT NHÁNH loại trừ NGAY khi
    duyệt — không đi vào bên trong rồi mới lọc. Trả về (dirpath: Path,
    dirnames: list[str], filenames: list[str]) từng cấp, giống os.walk.

    🔴 Bẫy đã gặp thật: `Path.rglob()` PHẢI liệt kê xong toàn bộ cây con
    của một thư mục trước khi `_is_excluded()` (lọc ở tầng Python) có cơ
    hội loại nó — với `dashboard-ui/node_modules` (47.000+ file, front-end
    riêng, ngoài phạm vi D0-PRE), điều đó có nghĩa duyệt hết 47.000 file
    qua bind-mount Windows->Docker chậm TRƯỚC KHI vứt đi, treo cả bộ test
    nhiều phút. `os.walk` với `topdown=True` cho phép cắt `dirnames` TẠI
    CHỖ — không bao giờ bước chân vào thư mục bị loại trừ. Áp dụng cho
    MỌI lượt duyệt REPO_ROOT không giới hạn (Tầng 2) — Tầng 1/3 đã tự
    giới hạn đúng phạm vi (SCAN_DIRS/LEDGER_PATHS) nên không cần đổi.
    """
    import os

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_PARTS]
        yield Path(dirpath), dirnames, filenames


def _files_in_artifact_dirs(root: Path) -> list[str]:
    """File nằm trong `hyperopt_results/` / `hyperopts/` — dấu vết một lần
    CHẠY. Thư mục rỗng trả về [] (khung `create-userdir`, xem docstring)."""
    out: list[str] = []
    for dirpath, dirnames, filenames in _walk_pruned(root):
        if dirpath.name not in ARTIFACT_DIRS:
            continue
        for sub_dirpath, _sub_dirnames, sub_filenames in _walk_pruned(dirpath):
            out += [str((sub_dirpath / f).relative_to(root)) for f in sub_filenames]
    return sorted(out)


def _artifact_files_by_glob(root: Path, patterns: tuple[str, ...]) -> list[str]:
    """Tương đương `root.rglob(pattern)` cho nhiều pattern cùng lúc,
    nhưng cắt nhánh loại trừ (xem `_walk_pruned`) — dùng thay
    `REPO_ROOT.rglob(pattern)` không giới hạn phạm vi.
    """
    import fnmatch

    out: list[str] = []
    for dirpath, _dirnames, filenames in _walk_pruned(root):
        for f in filenames:
            if any(fnmatch.fnmatch(f, p) for p in patterns):
                out.append(str((dirpath / f).relative_to(root)))
    return sorted(out)


def _scanned_files() -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        base = REPO_ROOT / d
        if not base.exists():
            continue
        for pattern in SCAN_GLOBS:
            files.extend(
                p
                for p in base.rglob(pattern)
                if not _is_excluded(p) and p.resolve() != SELF_PATH
            )
    for rel in EXTRA_FILES:
        p = REPO_ROOT / rel
        if p.exists():
            files.append(p)
    return files


class TestKhongCoDauVetHyperopt:
    def test_co_file_de_quet(self) -> None:
        assert len(_scanned_files()) > 0

    # ── Tầng 1: mã chạy được ─────────────────────────────────────────
    def test_khong_hyperopt_trong_ma_chay_duoc(self) -> None:
        vi_pham: list[str] = []
        for f in _scanned_files():
            for match in FORBIDDEN.finditer(_executable_text(f)):
                vi_pham.append(f"{f.relative_to(REPO_ROOT)}: {match.group(0)}")
        assert vi_pham == [], (
            f"Phát hiện `hyperopt` trong mã chạy được: {vi_pham}. §0c.2 CẤM "
            "TUYỆT ĐỐI — nếu đây là dấu vết một lần CHẠY thật thì toàn bộ "
            "trial_registry MẤT HIỆU LỰC (spec dòng 511-512)."
        )

    # ── Tầng 2: hiện vật trên đĩa ────────────────────────────────────
    def test_khong_co_hien_vat_hyperopt_tren_dia(self) -> None:
        found: list[str] = _artifact_files_by_glob(REPO_ROOT, ARTIFACT_GLOBS)
        found += _files_in_artifact_dirs(REPO_ROOT)
        assert found == [], (
            f"Hiện vật hyperopt trên đĩa: {found}. Freqtrade chỉ ghi những "
            "file này khi hyperopt ĐÃ CHẠY → toàn bộ trial_registry MẤT HIỆU "
            "LỰC, phải khai lại N từ đầu (spec dòng 511-512)."
        )

    # ── Tầng 3: sổ sách ──────────────────────────────────────────────
    def test_khong_hyperopt_trong_so_sach(self) -> None:
        vi_pham: list[str] = []
        for d in LEDGER_PATHS:
            base = REPO_ROOT / d
            if not base.exists():
                continue
            for f in base.rglob("*"):
                if not f.is_file() or _is_excluded(f):
                    continue
                text = f.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(text.splitlines(), start=1):
                    if FORBIDDEN.search(line):
                        vi_pham.append(f"{f.relative_to(REPO_ROOT)}:{i}")
        assert vi_pham == [], f"Sổ sách nhắc tới hyperopt: {vi_pham}"

    # ── Chứng minh bộ quét có răng ───────────────────────────────────
    def test_bat_duoc_lenh_hyperopt_trong_chuoi_mot_nhay(self) -> None:
        ma = 'subprocess.run("freqtrade hyperopt --epochs 500")\n'
        assert FORBIDDEN.search(_strip_py_noise(ma)) is not None

    def test_thu_muc_rong_bo_qua_nhung_co_file_thi_bat(self, tmp_path: Path) -> None:
        # Nới "thư mục rỗng không tính" phải KHÔNG làm mất khả năng bắt.
        (tmp_path / "user_data" / "hyperopts").mkdir(parents=True)
        assert _files_in_artifact_dirs(tmp_path) == []
        ket_qua = tmp_path / "user_data" / "hyperopt_results"
        ket_qua.mkdir(parents=True)
        (ket_qua / "strategy_2026.fthypt").write_text("x", encoding="utf-8")
        bat_duoc = _files_in_artifact_dirs(tmp_path)
        assert len(bat_duoc) == 1
        assert bat_duoc[0].endswith("strategy_2026.fthypt")

    def test_bat_duoc_import_va_goi_ham(self) -> None:
        ma = "from freqtrade.optimize import hyperopt\nhyperopt.start()\n"
        assert FORBIDDEN.search(_strip_py_noise(ma)) is not None

    def test_bat_duoc_trong_yaml_va_json(self) -> None:
        assert FORBIDDEN.search(_strip_hash_comments("mode: hyperopt\n")) is not None
        assert (
            FORBIDDEN.search(
                json.dumps(_strip_json_comment_keys({"strategy": "hyperopt_x"}))
            )
            is not None
        )

    def test_docstring_va_comment_giai_thich_lenh_cam_khong_bi_tinh_vi_pham(self) -> None:
        # Đúng hình dạng src/tool_d/measurement/guard.py dòng 5 — tài liệu
        # về lệnh cấm là BẰNG CHỨNG tuân thủ, không phải vi phạm.
        ma = '"""Freqtrade ghi file cạnh strategy sau mỗi lần hyperopt."""\nx = 1\n'
        assert FORBIDDEN.search(_strip_py_noise(ma)) is None
        assert FORBIDDEN.search(_strip_hash_comments("# cấm hyperopt\n")) is None
        assert (
            FORBIDDEN.search(
                json.dumps(_strip_json_comment_keys({"_comment_x": "không hyperopt"}))
            )
            is None
        )
