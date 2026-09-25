"""TD-0384 (`DR-D10-02`) — dựng và khởi chạy bộ chạy D10: lệnh live TỐI THIỂU, TIỀN THẬT, trên tài khoản phụ.

Cùng khuôn `ops/dry_run.py` (hàm THUẦN trước, lời gọi tiến trình sau), nhưng đây là đường TIỀN THẬT nên mọi chốt
fail-closed chạy TRƯỚC khi một byte lệnh nào ra sàn, theo đúng thứ tự trong `main()`:

1. `validate_credentials_for_live()` (TD-0242) — ĐẦU TIÊN, ở `main()`, KHÔNG trong callback chiến lược (callback bị
   Freqtrade nuốt exception — MT-16 vii). Có phép kiểm AST vị trí gọi (`test_td0384_live_d10.py`).
2. `kiem_truoc_khi_bat()` (`DR-D10-02` Q3) — IP whitelist bật, quyền rút / chuyển tiền tắt; không đọc được ⇒ từ chối.
3. Rổ `config/d10_ro.yaml` (`DR-D10-02` §5.1) phải tồn tại, ĐÃ COMMIT và KHÔNG bị sửa sau commit (máy kiểm bằng git).
4. Dựng cấu hình phủ rồi `exec freqtrade trade`.

Chế độ `--chon-ro` (không khởi chạy bot): gọi metadata sàn công khai, áp luật §5.1, ghi `config/d10_ro.yaml`. Người vận
hành commit file đó rồi mới được bật D10.

🔴 KHÔNG phải entrypoint thứ 9 (N3, `L-Z36`): không đánh giá cấu hình nào trên CALIB/WFO/LOCKBOX, không sinh file đo.
🔴 Q6 (`DR-D10-02`): bật BẰNG TAY — service `live-d10` không có `restart`, nằm sau profile riêng `d10`.
🔴 Bí mật (key tài khoản phụ, token Telegram bot RIÊNG của D10) chỉ đi qua biến môi trường của tiến trình con; KHÔNG
   bao giờ ghi vào bản cấu hình phủ, KHÔNG in ra log.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from tool_d.api_client.binance_public import (
    EXIT_MISSING_API_CREDENTIALS,
    BinanceCredentialsMissingError,
    get_exchange_info,
    get_ticker_24hr,
    get_ticker_price,
    validate_credentials_for_live,
)
from tool_d.bo_chay.yeu_cau import ten_cap_freqtrade
from tool_d.config.loader import load_tool_d_config
from tool_d.notional import build_symbol_filters, san_tool_d
from tool_d.ops.ctrl_d10 import CtrlD10Error, UngVienRo, chon_ro, doc_tham_so
from tool_d.ops.dry_run import bien_moi_truong_telegram
from tool_d.ops.kiem_bao_mat_d10 import BaoMatD10Error, kiem_truoc_khi_bat
from tool_d.pool_giai_doan import POOL_HOM_NAY

TEN_CHIEN_LUOC = "CtrlD10"
CAU_HINH_FREQTRADE_GOC = Path("config/freqtrade/config.json")
CAU_HINH_API_SERVER = Path("config/freqtrade/config.risk_supervisor.json")  # TD-0241: control API cho Risk Supervisor
RO_D10 = Path("config/d10_ro.yaml")
#: Thư mục trạng thái vận hành của D10 — dưới `runs/` (đã `.gitignore`), TÁCH khỏi dry-run (N11).
THU_MUC_VAN_HANH = Path("runs/van_hanh/live")
#: DB live RIÊNG, tách hẳn DB dry-run (N11; TD-0202 để trống đường live tới lúc này).
DB_URL_LIVE = "sqlite:////workspace/user_data/tradesv3_live_d10.sqlite"
TEN_FILE_CAU_HINH_PHU = "cfg.json"
TEN_FILE_LOG = "freqtrade.log"
#: Nối tiếp dải exit code riêng của dự án (99 = thiếu credential, TD-0242).
EXIT_BAO_MAT_D10 = 100
EXIT_RO_D10 = 101


class LiveD10Error(RuntimeError):
    """Không dựng được cấu hình D10 an toàn — fail-closed."""


@dataclass(frozen=True)
class CauHinhLiveD10:
    duong_dan: Path
    so_cap: int


def doc_ro_d10(duong: Path) -> tuple[str, ...]:
    """Đọc rổ đã chọn. Thiếu file, sai dạng, rỗng, hoặc > `ro_so_cap` cặp ⇒ `LiveD10Error`."""
    if not duong.is_file():
        raise LiveD10Error(f"{duong} không tồn tại — chạy `python -m tool_d.ops.live_d10 --chon-ro` rồi commit file đó")
    try:
        noi_dung = yaml.safe_load(duong.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise LiveD10Error(f"{duong} không đọc được: {exc}") from exc
    cap = noi_dung.get("cap")
    if not isinstance(cap, list) or not cap or not all(isinstance(c, str) and c for c in cap):
        raise LiveD10Error(f"{duong}: khoá `cap` phải là danh sách tên cặp không rỗng")
    if len(set(cap)) != len(cap):
        raise LiveD10Error(f"{duong}: có cặp trùng")
    tran = doc_tham_so(load_tool_d_config()).ro_so_cap
    if len(cap) > tran:
        raise LiveD10Error(f"{duong}: {len(cap)} cặp > trần {tran} (`DR-D10-02` Q4)")
    return tuple(cap)


def kiem_ro_da_commit(duong: Path, *, repo_dir: Path = Path(".")) -> None:
    """`DR-D10-02` §5.1: rổ phải ĐÃ COMMIT và KHÔNG sửa sau commit — chọn lại là một commit mới, không sửa tay giữa phiên."""
    rel = str(duong)
    theo_doi = subprocess.run(["git", "-C", str(repo_dir), "ls-files", "--error-unmatch", rel], capture_output=True)
    if theo_doi.returncode != 0:
        raise LiveD10Error(f"{rel} CHƯA được commit — commit rổ trước khi bật D10 (DR-D10-02 §5.1)")
    sua = subprocess.run(["git", "-C", str(repo_dir), "diff", "--quiet", "HEAD", "--", rel], capture_output=True)
    if sua.returncode != 0:
        raise LiveD10Error(f"{rel} bị SỬA sau commit — chọn lại rổ bằng một commit mới, không sửa tay giữa phiên")


def dung_cau_hinh_live_d10(
    *, ro: tuple[str, ...], repo_dir: Path = Path("."), thu_muc_ra: Path | None = None
) -> CauHinhLiveD10:
    """Ghi `<thu_muc_ra>/cfg.json` = cấu hình gốc + khoá vận hành D10 + rổ. KHÔNG chứa bí mật nào."""
    goc = repo_dir / CAU_HINH_FREQTRADE_GOC
    if not goc.is_file():
        raise LiveD10Error(f"{goc} không tồn tại")
    ft = json.loads(goc.read_text(encoding="utf-8"))
    san = ft.get("exchange") or {}
    if san.get("key") or san.get("api_key") or san.get("secret"):
        raise LiveD10Error(f"{CAU_HINH_FREQTRADE_GOC} chứa api_key/secret khác rỗng — key chỉ đi qua biến môi trường")
    if "telegram" in ft:
        raise LiveD10Error(f"{CAU_HINH_FREQTRADE_GOC} có mục `telegram` — Telegram chỉ bật qua env (TD-0393)")
    if not ro:
        raise LiveD10Error("rổ D10 rỗng — từ chối bật (DR-D10-02 §5.1)")

    ft["dry_run"] = False  # ĐƯỜNG TIỀN THẬT — chỉ ở module này, không bao giờ là một cờ ở dry-run
    ft["strategy"] = TEN_CHIEN_LUOC
    ft["db_url"] = DB_URL_LIVE
    ft["bot_name"] = "tool_d_live_d10"
    ft["initial_state"] = "running"
    ft["max_open_trades"] = 1  # tuần tự (DR-D11-01 §4) — chốt thứ hai bên cạnh máy canh ngân sách
    ft["exchange"]["pair_whitelist"] = list(ro)

    ra = thu_muc_ra if thu_muc_ra is not None else repo_dir / THU_MUC_VAN_HANH
    ra.mkdir(parents=True, exist_ok=True)
    duong = ra / TEN_FILE_CAU_HINH_PHU
    duong.write_text(json.dumps(ft, ensure_ascii=False, indent=1), encoding="utf-8")
    return CauHinhLiveD10(duong_dan=duong, so_cap=len(ro))


def lenh_freqtrade(cau_hinh: CauHinhLiveD10) -> list[str]:
    """`freqtrade trade` trên cấu hình phủ + cấu hình control API (Risk Supervisor, TD-0241)."""
    return [
        "freqtrade", "trade",
        "--config", str(cau_hinh.duong_dan),
        "--config", str(CAU_HINH_API_SERVER),
        "--strategy", TEN_CHIEN_LUOC,
        "--strategy-path", "user_data/strategies",
        "--userdir", "user_data",
        "--logfile", str(cau_hinh.duong_dan.parent / TEN_FILE_LOG),
    ]


def bien_moi_truong_san(api_key: str, api_secret: str) -> dict[str, str]:
    """Key tài khoản phụ vào Freqtrade qua cơ chế gộp env chuẩn của chính nó — không qua file."""
    return {"FREQTRADE__EXCHANGE__KEY": api_key, "FREQTRADE__EXCHANGE__SECRET": api_secret}


def ung_vien_tu_san(exchange_info: dict, ticker_24h: list[dict], gia: list[dict], trading: list[str],
                    *, strategy_stoploss: float) -> list[UngVienRo]:
    """Dựng ứng viên rổ từ metadata sàn. Mã thiếu bộ lọc hay giá ⇒ `san_usdt=None` (bị loại ở `chon_ro`, không đoán)."""
    volume = {t["symbol"]: t.get("quoteVolume") for t in ticker_24h}
    ket_qua: list[UngVienRo] = []
    for ma in trading:
        try:
            (f,) = build_symbol_filters(exchange_info, gia, {ma})
            san: float | None = san_tool_d(f, strategy_stoploss=strategy_stoploss)
        except ValueError:
            san = None
        v = volume.get(ma)
        ket_qua.append(UngVienRo(cap=ten_cap_freqtrade(ma), quote_volume_24h=float(v) if v is not None else None,
                                 san_usdt=san))
    return ket_qua


def chon_ro_va_ghi(*, repo_dir: Path = Path("."), now: datetime | None = None) -> tuple[str, ...]:
    """Chế độ `--chon-ro`: áp luật `DR-D10-02` §5.1 lên metadata sàn công khai, ghi `config/d10_ro.yaml`."""
    trading = list((yaml.safe_load((repo_dir / POOL_HOM_NAY).read_text(encoding="utf-8")) or {}).get("trading") or [])
    if not trading:
        raise LiveD10Error(f"{POOL_HOM_NAY} có danh sách trading rỗng")
    goc = json.loads((repo_dir / CAU_HINH_FREQTRADE_GOC).read_text(encoding="utf-8"))
    ts = doc_tham_so(load_tool_d_config(repo_dir / "config/tool_d_config.yaml"))
    ung_vien = ung_vien_tu_san(get_exchange_info(), get_ticker_24hr(), get_ticker_price(), trading,
                               strategy_stoploss=float(goc["stoploss"]))
    ro = chon_ro(ung_vien, ts)
    moc = (now or datetime.now(timezone.utc)).isoformat()
    noi_dung = {
        "_nguon": "DR-D10-02 §5.1 — chọn bằng máy (`python -m tool_d.ops.live_d10 --chon-ro`). Chọn lại = commit mới.",
        "chon_luc_utc": moc,
        "tu_ro": str(POOL_HOM_NAY),
        "luat": {"ro_so_cap": ts.ro_so_cap, "ro_tran_san_usdt": ts.ro_tran_san_usdt, "xep": "quoteVolume 24h giảm dần"},
        "cap": list(ro),
    }
    (repo_dir / RO_D10).write_text(yaml.safe_dump(noi_dung, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return ro


def main(argv: list[str] | None = None) -> None:  # pragma: no cover — exec tiến trình thật; phần thuần đã khoá bằng test
    p = argparse.ArgumentParser(description="Bộ chạy D10 — lệnh live tối thiểu (DR-D10-02)")
    p.add_argument("--chon-ro", action="store_true", help="chỉ chọn rổ và ghi config/d10_ro.yaml, không bật bot")
    args = p.parse_args(argv)
    if args.chon_ro:
        ro = chon_ro_va_ghi()
        print(f"rổ D10 ({len(ro)} cặp) đã ghi {RO_D10} — COMMIT file này trước khi bật D10:", file=sys.stderr)
        for cap in ro:
            print(f"  {cap}", file=sys.stderr)
        return

    try:
        api_key, api_secret = validate_credentials_for_live()  # 1 — TRƯỚC mọi lời gọi mạng (TD-0242)
    except BinanceCredentialsMissingError as exc:
        print(str(exc), file=sys.stderr, flush=True)
        sys.exit(EXIT_MISSING_API_CREDENTIALS)
    try:
        kiem_truoc_khi_bat(api_key=api_key, api_secret=api_secret)  # 2 — DR-D10-02 Q3
    except BaoMatD10Error as exc:
        print(str(exc), file=sys.stderr, flush=True)
        sys.exit(EXIT_BAO_MAT_D10)
    try:
        kiem_ro_da_commit(RO_D10)  # 3 — DR-D10-02 §5.1
        ro = doc_ro_d10(RO_D10)
        cau_hinh = dung_cau_hinh_live_d10(ro=ro)
    except (LiveD10Error, CtrlD10Error) as exc:
        print(str(exc), file=sys.stderr, flush=True)
        sys.exit(EXIT_RO_D10)

    os.environ.update(bien_moi_truong_san(api_key, api_secret))
    telegram = bien_moi_truong_telegram(os.environ)  # bot Telegram RIÊNG của D10 (DR-D10-02 Q4), qua .env.d10
    os.environ.update(telegram)
    lenh = lenh_freqtrade(cau_hinh)
    print(
        f"D10 LIVE: {cau_hinh.so_cap} cặp, cấu hình {cau_hinh.duong_dan}, "
        f"Telegram {'BẬT' if telegram else 'TẮT'} — TIỀN THẬT",
        file=sys.stderr, flush=True,
    )
    os.execvp(lenh[0], lenh)


if __name__ == "__main__":  # pragma: no cover
    main()
