"""TD-0391 (`DR-XAC-NHAN-01` §9) — ĐƯỜNG ĐỐI CHIẾU THỨ HAI cho rổ `XAC_NHAN` tại ngày CHỌN. 0 trial.

Chạy lại logic chọn rổ của kịch bản đo `TD-0231` (`do_td0231_pool_point_in_time.py::_dung_mot_moc`, KHÔNG sửa file đó)
cho ngày CHỌN của `--slot`, rồi ghi `td0391-ro-xac-nhan-doi-chieu.json`. E7 `--ro-xac-nhan` (đường thứ nhất,
`pool_t1.dung_ro_tai_moc`) đòi KHÍT với hiện vật này trước khi ghi `config/pool_xac_nhan.yaml` (khuôn `t0`/`t1` của
`DR-D1-03` §2). Hiện vật phải commit TRƯỚC khi chạy E7 `--ghi`.

Hai đường chung ĐẦU VÀO (cùng khuôn `t0`/`t1`, vốn cũng chung một bộ đọc kho): mốc từ sổ ý tưởng
(`pool_xac_nhan.lan_chon`), khoảng tồn tại `TD-0306` nối tới tháng mốc (`pool_xac_nhan.mo_rong_khoang`), volume ngày
mốc từ kho NGÀY (`pool_xac_nhan.doc_volume_cho_moc`). Khác nhau ở phần CHỌN rổ.

Chạy (Docker, cần mạng):
  docker compose -f docker/docker-compose.yml run --rm --entrypoint python freqtrade \\
      docs/du-lieu-do/do_td0391_ro_xac_nhan_doi_chieu.py --slot IQ-0003 [--ghi]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from tool_d.api_client.binance_public import doc_quote_volume_1d_ngay, doc_quote_volume_1d_thang
from tool_d.measurement.gitinfo import get_git_info
from tool_d.pool_xac_nhan import doc_volume_cho_moc, lan_chon, mo_rong_khoang

REPO = Path(__file__).resolve().parents[2]
NGUON_TD0306 = REPO / "docs" / "du-lieu-do" / "td0306-khoang-ton-tai-that.json"
KICH_BAN_TD0231 = REPO / "docs" / "du-lieu-do" / "do_td0231_pool_point_in_time.py"
KET_QUA = REPO / "docs" / "du-lieu-do" / "td0391-ro-xac-nhan-doi-chieu.json"


def _nap_td0231():
    spec = importlib.util.spec_from_file_location("do_td0231_doi_chieu", KICH_BAN_TD0231)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # `@dataclass` của kịch bản cũ tra `sys.modules[cls.__module__]` lúc định nghĩa lớp ⇒ phải đăng ký trước exec.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slot", required=True)
    ap.add_argument("--ghi", action="store_true", help="Ghi hiện vật (từ chối ghi đè). Thiếu cờ chỉ IN.")
    args = ap.parse_args(argv)

    if args.ghi and KET_QUA.exists():
        print(f"🛑 {KET_QUA.name} đã tồn tại — không ghi đè (lần CHỌN mới: xoá tay + DR).")
        return 1
    moc, selected_at = lan_chon(args.slot, REPO)
    if moc >= datetime.now(timezone.utc).date():
        print(f"🛑 Ngày CHỌN {moc} chưa đóng — chạy lại từ hôm sau.")
        return 1

    td0231 = _nap_td0231()
    # Tiêm bộ đọc vào ĐÚNG tên kịch bản cũ gọi (`doc_quote_volume_1d_thang(symbol=, nam=, thang=)`): tháng mốc đọc kho
    # NGÀY, tháng khác (ngày onboard sát ngưỡng) đọc kho THÁNG như cũ.
    doc = doc_volume_cho_moc(
        moc,
        doc_ngay=lambda sym, ngay: doc_quote_volume_1d_ngay(symbol=sym, ngay=ngay),
        doc_thang=lambda sym, nam, thang: doc_quote_volume_1d_thang(symbol=sym, nam=nam, thang=thang),
    )
    td0231.doc_quote_volume_1d_thang = lambda *, symbol, nam, thang: doc(symbol, nam, thang)

    nguon = json.loads(NGUON_TD0306.read_text(encoding="utf-8"))
    khoang, da_noi = mo_rong_khoang(nguon["khoang_ton_tai"], moc, age_floor_days=td0231.AGE_FLOOR_DAYS)
    print(f"Mốc {moc} ({args.slot}) · nối đời sống {len(da_noi)} mã · chạy logic TD-0231 …")
    kq = td0231._dung_mot_moc(moc, khoang)
    print(f"Đủ tiêu chí: {len(kq.pool_dung)} · 404: {len(kq.khong_do_duoc_404)} · thiếu ngày: {len(kq.khong_do_duoc_thieu_ngay)}")

    ket_qua = {
        "nguon": "TD-0391 / DR-XAC-NHAN-01 §9 — đường đối chiếu thứ hai (logic _dung_mot_moc của TD-0231), 0 trial",
        "moc": moc.isoformat(),
        "hypothesis_slot": args.slot,
        "selected_at": selected_at,
        "pool_dung": sorted(kq.pool_dung),
        "dem": {
            "ung_vien_song": kq.ung_vien_song,
            "do_duoc": kq.do_duoc,
            "du_tieu_chi": len(kq.pool_dung),
            "onboard_chinh_xac": len(kq.onboard_chinh_xac),
            "onboard_xap_xi": kq.onboard_xap_xi,
            "n_ma_duoc_noi_doi_song": len(da_noi),
        },
        "khong_do_duoc": {
            "kho_404": sorted(kq.khong_do_duoc_404),
            "thieu_hang_dung_ngay": sorted(kq.khong_do_duoc_thieu_ngay),
        },
        "git_sha": get_git_info(REPO).sha,
        "chay_luc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trial": 0,
    }
    if not args.ghi:
        print("(chạy thử — thêm --ghi để ghi hiện vật)")
        return 0
    KET_QUA.write_text(json.dumps(ket_qua, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Đã ghi {KET_QUA.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
