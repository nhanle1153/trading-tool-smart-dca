"""🔒 TD-0239 — bản ghi `VAO_RA_LENH` phải nối vào ĐƯỜNG SẢN XUẤT thật,
không chỉ tồn tại dưới dạng hàm thuần được test bằng mẫu dựng tay
(`TD-0168`: *"thứ được canh không nằm trên đường chạy"*, ở dạng nặng
nhất — sổ tồn tại, luật đầy đủ, không ai ghi vào).

Tái dùng NGUYÊN VẸN bộ sinh dữ liệu backtest của `TD-0187` (`_sinh_du_lieu`,
`_lenh_vao`, `TIMERANGE`) qua importlib — không viết lại logic dựng
zone/DCA phức tạp lần thứ hai. Nhưng KHÔNG tái dùng hàm `_chay()` của nó
nguyên vẹn, vì `_chay()` chạy subprocess với `cwd=REPO_ROOT` (`-54` chỉ
ra: `DEFAULT_DECISION_LOG_PATH` VÀ `DEFAULT_CONFIG_PATH`
(`config/tool_d_config.yaml`) đều là đường dẫn TƯƠNG ĐỐI — mọi tiến
trình Tool D bắt buộc chạy với CWD = REPO_ROOT để đọc đúng config, nên
`_chay()` sẽ ghi THẲNG vào `registry/decision_log.jsonl` CỦA REPO, không
phải sandbox).

════ Cách cô lập — copy `config/` sang cwd tạm, không backup/restore
sổ thật ════
Cùng khuôn `docs/du-lieu-do/do_td0193_lenh_nam_explore.py::_yaml_voi_arm`:
chạy subprocess với `cwd = tmp`, chép TOÀN BỘ `config/` (bao gồm
`tool_d_config.yaml`) sang `tmp/config/`, `--strategy-path` vẫn trỏ
ABSOLUTE tới `REPO_ROOT/user_data/strategies` (mã chiến lược không cần
copy). Với `cwd=tmp`, mọi đường dẫn tương đối chiến lược mở ra
(`registry/decision_log.jsonl`, `config/tool_d_config.yaml`) đều resolve
vào `tmp/`, KHÔNG BAO GIỜ chạm `registry/` thật của repo — an toàn hơn
hẳn backup/restore (không có cửa sổ rủi ro nào, kể cả khi process bị
kill giữa chừng).
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# ── tái dùng bộ sinh dữ liệu + hằng số của TD-0187 ─────────────────────
_spec = importlib.util.spec_from_file_location(
    "td0187", REPO_ROOT / "tests" / "lock" / "test_td0187_dinh_co_lenh_backtest_that.py"
)
_td0187 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_td0187)  # type: ignore[union-attr]
_sinh_du_lieu = _td0187._sinh_du_lieu
_lenh_vao = _td0187._lenh_vao
CAP = _td0187.CAP
SAN_XUAT = _td0187.SAN_XUAT
TIMERANGE = _td0187.TIMERANGE


def _chay_co_lap(tmp: Path) -> dict:
    """Một lượt backtest THẬT, hoàn toàn cô lập trong `tmp` — không đụng
    `config/`/`registry/` của repo. Gọi lại với CÙNG `tmp` để mô phỏng
    "chạy lại cùng timerange" (data/config đã có sẵn, không sinh lại)."""
    datadir = tmp / "data"
    if not (datadir / "futures").exists():
        _sinh_du_lieu(datadir)

    cfg_dir = tmp / "config"
    if not cfg_dir.exists():
        shutil.copytree(REPO_ROOT / "config", cfg_dir)

    userdir = tmp / "user_data"
    (userdir / "strategies").mkdir(parents=True, exist_ok=True)
    cfg = json.loads((cfg_dir / "freqtrade" / "config.json").read_text(encoding="utf-8"))
    cfg["exchange"]["pair_whitelist"] = ["LTC/USDT:USDT"]
    cfg["max_open_trades"] = 1
    cfg["stake_amount"] = 100  # bị custom_stake_amount ghi đè
    cfg["dry_run"] = True
    cfg_path = cfg_dir / "freqtrade" / "config.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable, "-m", "freqtrade", "backtesting",
            "--config", str(cfg_path), "--datadir", str(datadir), "--userdir", str(userdir),
            "--strategy", SAN_XUAT, "--strategy-path", str(REPO_ROOT / "user_data" / "strategies"),
            "--timerange", TIMERANGE, "--timeframe-detail", "5m", "--cache", "none", "--export", "trades",
        ],
        capture_output=True, text=True, timeout=900, cwd=tmp,
    )
    assert proc.returncode == 0, f"backtest thất bại:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    log = proc.stdout + proc.stderr
    # Cùng phép kiểm TD-0187 đã ghim: Freqtrade NUỐT exception của callback
    # (`strategy_safe_wrapper`) — một chốt fail-closed bị nuốt là một chốt
    # KHÔNG TỒN TẠI. Nếu `_ghi_vao_lenh` raise, dòng này phải bắt được.
    nuot = [d for d in log.splitlines() if "Strategy caused the following exception" in d]
    assert not nuot, f"{len(nuot)} exception bị Freqtrade nuốt — dòng đầu:\n{nuot[0][:300]}"

    from freqtrade.data.btanalysis import load_backtest_stats

    files = sorted((userdir / "backtest_results").glob("backtest-result-*.zip"))
    assert files, "không có file kết quả"
    return load_backtest_stats(files[-1])["strategy"][SAN_XUAT]


def _doc_dong_vao_lenh(tmp: Path) -> list[dict]:
    path = tmp / "registry" / "decision_log.jsonl"
    if not path.exists():
        return []
    ket_qua = []
    for dong in path.read_text(encoding="utf-8").splitlines():
        if not dong.strip():
            continue
        d = json.loads(dong)
        if d.get("loai") == "VAO_RA_LENH":
            ket_qua.append(d)
    return ket_qua


def test_moi_tranche_khop_sinh_dung_mot_ban_ghi_va_no_op_khi_chay_lai(tmp_path: Path) -> None:
    """Tiêu chí XONG của `TD-0239` (`TASKS.md`): *"Mỗi tranche khớp sinh
    đúng một bản ghi (dedup theo `order_id`) ... chạy lại cùng timerange
    ⇒ thêm 0 dòng"* — đúng bug Tool A số 7 mà `L-Z45` sinh ra để chặn."""
    kq1 = _chay_co_lap(tmp_path)
    so_fill_that = sum(len(_lenh_vao(t)) for t in kq1["trades"])
    assert so_fill_that > 0, "backtest không sinh entry fill nào — fixture đã hỏng (PASS RỖNG)"

    dong_sau_lan_1 = _doc_dong_vao_lenh(tmp_path)
    assert len(dong_sau_lan_1) == so_fill_that, (
        f"{len(dong_sau_lan_1)} bản ghi VAO_RA_LENH nhưng {so_fill_that} entry fill thật "
        "— hoặc thiếu bản ghi (dạng nặng nhất của TD-0168), hoặc ghi trùng"
    )
    khoa = [d["exchange_order_id"] for d in dong_sau_lan_1]
    assert len(khoa) == len(set(khoa)), (
        "có hai bản ghi cùng exchange_order_id — spec §8.3 đòi khoá theo order_id "
        "TỪNG tranche, trùng khoá nghĩa là hai tranche khác nhau bị gộp làm một"
    )

    so_dong_truoc_lan_2 = len(dong_sau_lan_1)
    kq2 = _chay_co_lap(tmp_path)  # CÙNG tmp_path, CÙNG TIMERANGE — data/config tái dùng
    assert len(kq2["trades"]) == len(kq1["trades"]), "chạy lại cùng timerange ra khác số lệnh"

    dong_sau_lan_2 = _doc_dong_vao_lenh(tmp_path)
    assert len(dong_sau_lan_2) == so_dong_truoc_lan_2, (
        f"chạy lại cùng timerange thêm {len(dong_sau_lan_2) - so_dong_truoc_lan_2} dòng "
        "— đúng bug Tool A số 7 (L-Z45 sinh ra để chặn), không phải 0"
    )


def test_khong_dung_den_registry_that_cua_repo(tmp_path: Path) -> None:
    """Kiểm-có-răng cho chính việc CÔ LẬP: nếu `cwd`/đường dẫn cấu hình bị
    sửa nhầm về tương đối với repo thật, ca này phải bắt được TRƯỚC khi
    một lượt chạy nào khác kịp ghi rác vào sổ thật dùng cho D4/D10/D11."""
    truoc = None
    duong_that = REPO_ROOT / "registry" / "decision_log.jsonl"
    if duong_that.exists():
        truoc = duong_that.stat().st_mtime_ns
    _chay_co_lap(tmp_path)
    sau = duong_that.stat().st_mtime_ns if duong_that.exists() else None
    assert sau == truoc, (
        f"registry/decision_log.jsonl CỦA REPO bị đụng tới (mtime {truoc} -> {sau}) "
        "— test đã ghi nhầm vào sổ thật thay vì sandbox"
    )
