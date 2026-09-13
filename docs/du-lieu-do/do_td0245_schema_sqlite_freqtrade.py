"""TD-0245 — xuất SCHEMA THẬT của database SQLite mà Freqtrade dùng. **0 trial.**

🔴 **Câu hỏi:** `tu-dien-du-lieu.md` chưa bao giờ tồn tại ở gốc repo, nên
Quy tắc 7 (`CLAUDE.md:25`) đang chặn `TD-0238` (đường vốn từ bảng `trades`)
và `TD-0240` (11/22 chỉ số đọc `trades`/`orders`). Muốn viết từ điển thì
Quy tắc 8 (`CLAUDE.md:27`) đòi *"xuất schema thật từ database (sau khi
migration đã chạy) … Database thật luôn là chân lý"*.

🔴 **Gà-và-trứng, và cách giải đã được chủ dự án chốt (14/09/2026).**
Không có file `.sqlite` nào trên đĩa — `config/freqtrade/config.json:18` mới
chỉ *ghim đường dẫn* `sqlite:////workspace/user_data/tradesv3_dryrun.sqlite`.
DB chỉ sinh ra khi chạy dry-run, tức chính thứ Quy tắc 7 đang chặn.

Lối ra: **để chính Freqtrade tạo DB thật**. Kịch bản này gọi
`freqtrade.persistence.init_db()` — hàm mà **bản thân bot gọi khi khởi
động** — lên một đường dẫn tạm, rồi đọc lại schema bằng `PRAGMA table_info`
từ **file SQLite có thật trên đĩa**. Đọc mã nguồn trước khi viết
(`/freqtrade/freqtrade/persistence/models.py:48`, bản 2026.8): `init_db`
chạy `ModelBase.metadata.create_all(engine)` **rồi** `check_migrate(...)`
⇒ đúng chữ *"sau khi migration đã chạy"*. Đây là **cùng một đường mã** mà
dry-run sẽ đi, nên schema sinh ra y hệt schema của DB thật sau này.

🔴 **Vì sao 0 trial và không vướng `MT-19`:** kịch bản này **không đọc một
nến nào**, không chạm CALIB/WFO/LOCKBOX, không đánh giá cấu hình nào. Nó chỉ
hỏi thư viện *"bảng của mày hình dạng gì"* — không phải *"chiến lược của ta
tốt đến đâu"*. DR-014 §2 chỉ tính *đánh giá cấu hình* là "chạm".

🔴 **KHÔNG sinh file `.sqlite` nào trong repo.** DB tạm nằm trong `/tmp` của
container (`--rm` ⇒ mất khi container thoát). Lý do không chỉ là sạch sẽ:
một file `tradesv3*.sqlite` nằm trong repo sẽ bị `.gitignore` nuốt im lặng
rồi sau này có người tưởng đó là DB thật của một lần chạy thật.

⚠️ **Con số "6 bảng / 109 cột" đang lưu hành là LỜI KHAI, chưa phải bằng
chứng** — grep `109` · `6 bảng` · `sqlite_master` toàn repo cho 0 kết quả
liên quan. Kịch bản này sinh ra bằng chứng ấy. Nếu số đo lệch, **số đo
thắng** và phải báo cáo, không sửa cho khớp lời khai.

Chạy (N7 — bằng chứng phải từ Docker; service `freqtrade` vì entrypoint là
`python`, **không** service `tests` vốn có entrypoint `pytest`):

    docker compose -f docker/docker-compose.yml run --rm freqtrade \
        docs/du-lieu-do/do_td0245_schema_sqlite_freqtrade.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tool_d.measurement.provenance import doc_runtime_image_digest  # noqa: E402

FILE_KET_QUA = REPO_ROOT / "docs/du-lieu-do/td0245-schema-sqlite-freqtrade.json"

# Hai file do `docker/Dockerfile` nướng vào ảnh lúc build (dòng 28-39). Đọc
# thẳng từ đây thay vì gọi `freqtrade --version`: đây là bản ghi CỦA CHÍNH
# ẢNH, không phụ thuộc việc CLI có chạy được dưới user hiện tại hay không.
FILE_PHIEN_BAN = Path("/opt/freqtrade_version.txt")
FILE_COMMIT_NGUON = Path("/opt/freqtrade_source_commit.txt")


def _doc_neu_co(path: Path) -> str | None:
    """Trả nội dung file, hoặc `None` nếu không có.

    `None` chứ không phải `""` — N6 cấm giá trị lính canh: một chuỗi rỗng
    trong artifact trông giống "đo được và nó rỗng", còn `null` nói thẳng
    "không đọc được".
    """
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


def _tach_phien_ban(tho: str | None) -> str | None:
    """Rút đúng chuỗi phiên bản từ đầu ra nhiều dòng của `freqtrade --version`.

    Giữ CẢ bản thô trong artifact (`freqtrade_version_raw`) — nó ghi luôn
    Python/CCXT/OS của ảnh, đều là thứ có thể làm schema đổi. Bản rút gọn chỉ
    để tiêu đề từ điển đọc được; **không** thay thế bản thô.
    """
    if tho is None:
        return None
    for dong in tho.splitlines():
        if dong.lower().startswith("freqtrade version:"):
            return dong.split(":", 1)[1].strip()
    return None


def xuat_schema(db_path: Path) -> list[dict[str, Any]]:
    """Đọc schema THẬT từ một file SQLite đã tồn tại trên đĩa.

    Mở ở `mode=ro` — kịch bản này không có lý do gì để ghi, và một cửa chỉ
    đọc thì không thể lỡ tay đổi thứ nó đang đo.
    """
    uri = f"file:{db_path}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        bang = [
            (r[0], r[1])
            for r in con.execute(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
        ]
        ket_qua: list[dict[str, Any]] = []
        for ten, ddl in bang:
            cot = [
                {
                    "cid": r[0],
                    "ten": r[1],
                    "kieu": r[2],
                    "notnull": bool(r[3]),
                    "mac_dinh": r[4],
                    "khoa_chinh": bool(r[5]),
                }
                # PRAGMA không nhận tham số ràng buộc; tên bảng lấy từ chính
                # `sqlite_master` của DB này nên không có đường chèn chuỗi lạ.
                for r in con.execute(f'PRAGMA table_info("{ten}")')
            ]
            khoa_ngoai = [
                {
                    "cot": r[3],
                    "bang_dich": r[2],
                    "cot_dich": r[4],
                }
                for r in con.execute(f'PRAGMA foreign_key_list("{ten}")')
            ]
            chi_muc = sorted(
                r[1] for r in con.execute(f'PRAGMA index_list("{ten}")')
            )
            ket_qua.append(
                {
                    "ten": ten,
                    "ddl": ddl,
                    "so_cot": len(cot),
                    "cot": cot,
                    "khoa_ngoai": khoa_ngoai,
                    "chi_muc": chi_muc,
                }
            )
        return ket_qua
    finally:
        con.close()


def main() -> int:
    # Fail-closed TRƯỚC khi làm gì khác: hàm này từ chối chạy ngoài ảnh Docker
    # của project (N7 — lần chạy trên host không phải bằng chứng). Đặt ở dòng
    # đầu để không bao giờ sinh ra một artifact "gần đúng" rồi mới phát hiện.
    digest = doc_runtime_image_digest(REPO_ROOT)

    from freqtrade.persistence import init_db  # noqa: PLC0415

    with tempfile.TemporaryDirectory(prefix="td0245-") as thu_muc:
        db_path = Path(thu_muc) / "td0245_schema.sqlite"
        # 4 gạch chéo = đường TUYỆT ĐỐI theo cú pháp SQLAlchemy sqlite,
        # cùng quy ước `config/freqtrade/config.json:18`.
        init_db(f"sqlite:///{db_path}")
        if not db_path.is_file():
            raise RuntimeError(
                f"init_db() chạy xong nhưng không thấy {db_path} — "
                "không có database thật để xuất schema, từ chối ghi artifact"
            )
        bang = xuat_schema(db_path)

    so_cot = sum(b["so_cot"] for b in bang)
    ket_qua = {
        "ma_viec": "TD-0245",
        "cau_hoi": (
            "Database SQLite mà Freqtrade dùng có những bảng/cột nào — "
            "đọc từ file SQLite THẬT do chính init_db() của Freqtrade tạo "
            "và migrate"
        ),
        "trial": 0,
        "nguon_schema": {
            "ham": "freqtrade.persistence.init_db",
            "mo_ta": (
                "models.py:48 — create_all(engine) rồi check_migrate(...); "
                "cùng đường mã bot gọi lúc khởi động"
            ),
            "doc_lai_bang": "PRAGMA table_info trên file sqlite, mode=ro",
        },
        "freqtrade_version": _tach_phien_ban(_doc_neu_co(FILE_PHIEN_BAN)),
        "freqtrade_version_raw": _doc_neu_co(FILE_PHIEN_BAN),
        "freqtrade_source_commit": _doc_neu_co(FILE_COMMIT_NGUON),
        "runtime_image_digest": digest,
        "so_bang": len(bang),
        "so_cot": so_cot,
        "bang": bang,
    }

    FILE_KET_QUA.write_text(
        json.dumps(ket_qua, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Đã ghi {FILE_KET_QUA.relative_to(REPO_ROOT)}")
    print(f"  Freqtrade      : {ket_qua['freqtrade_version']}")
    print(f"  source commit  : {ket_qua['freqtrade_source_commit']}")
    print(f"  image digest   : {digest}")
    print(f"  SỐ BẢNG        : {len(bang)}")
    print(f"  SỐ CỘT         : {so_cot}")
    for b in bang:
        print(f"    - {b['ten']:<24} {b['so_cot']:>3} cột")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
