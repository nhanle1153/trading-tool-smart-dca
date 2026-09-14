"""TD-0245 — sinh `tu-dien-du-lieu.md` từ artifact schema THẬT. Hàm THUẦN.

Từ điển **không được gõ tay**: Quy tắc 8 (`CLAUDE.md:27`) viết thẳng *"Không
được tự viết từ điển dựa trên trí nhớ đã viết migration gì — phải xuất schema
thật từ database … Database thật luôn là chân lý — nếu lệch, sửa từ điển theo
database, không phải ngược lại."* Một bộ sinh tất định biến câu đó thành thứ
máy làm được: kiểu dữ liệu, khoá chính, ràng buộc NOT NULL và khoá ngoại đều
suy **trực tiếp** từ `PRAGMA`, không ai chép.

Thứ duy nhất do người viết là cột *Ý nghĩa* — và nó bị chặn hai đầu: phải có
`file:line` (xem `y_nghia_cot.py`), hoặc là `⏳ chưa tra cứu`.

🔴 **Đúng 9 cột, và đó không phải chuyện thẩm mỹ.** `TD-0233` đã đo: bảng
markdown **bỏ im lặng** mọi ô vượt quá số cột của header — nội dung vẫn nằm
trong file nhưng **vô hình ở bản render**. Nên mọi giá trị đều được escape dấu
`|`, và bộ sinh tự đếm ô trước khi trả chuỗi: sinh sai thì `raise`, không ghi.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from tool_d.tu_dien.quet_cot import ChoDoc
from tool_d.tu_dien.y_nghia_cot import NGUON_BANG_CHUNG, NghiaCot

CHUA_TRA = "⏳ chưa tra cứu"
PHIEN_BAN_DONG = "v1.0"

COT_BANG_CHINH: tuple[str, ...] = (
    "Trường",
    "Kiểu dữ liệu",
    "Ý nghĩa (định nghĩa rõ, không nhập nhằng)",
    "Bắt buộc?",
    "Giá trị hợp lệ",
    "Ràng buộc/Khóa ngoại",
    "Dùng bởi (module/function nào)",
    "Version",
    "Ngày cập nhật",
)

COT_LICH_SU: tuple[str, ...] = (
    "Bảng.Trường",
    "Loại thay đổi (➕ Thêm mới / ❌ Xóa / ♻️ Sửa đổi)",
    "Nội dung cũ",
    "Nội dung mới",
    "Lý do",
    "Ngày",
)


class LoiSinhTuDien(RuntimeError):
    """Bộ sinh tạo ra một dòng sai số ô. Fail-closed: raise TRƯỚC khi ghi file."""


def _o(gia_tri: str) -> str:
    """Một ô markdown an toàn.

    Escape `|` (nếu không, một ô chứa dấu ống sẽ tự tách thành hai ô và đẩy
    mọi ô sau nó lệch cột — rồi ô cuối rơi ra ngoài header và **biến mất** ở
    bản render, đúng cơ chế `TD-0233`). Xuống dòng cũng bị cấm vì nó cắt đôi
    hàng.
    """
    return gia_tri.replace("|", r"\|").replace("\n", " ").strip() or "—"


def _hang(o: Sequence[str], so_cot_mong_doi: int) -> str:
    if len(o) != so_cot_mong_doi:
        raise LoiSinhTuDien(
            f"dòng có {len(o)} ô, bảng cần đúng {so_cot_mong_doi} — "
            "markdown sẽ bỏ im lặng phần thừa (TD-0233)"
        )
    return "| " + " | ".join(_o(x) for x in o) + " |"


def _bang(tieu_de: Sequence[str], cac_hang: Sequence[Sequence[str]]) -> list[str]:
    n = len(tieu_de)
    dong = [_hang(tieu_de, n), "|" + "---|" * n]
    dong.extend(_hang(h, n) for h in cac_hang)
    return dong


def _bat_buoc(cot: Mapping[str, Any]) -> str:
    if cot["khoa_chinh"]:
        return "✅ (khoá chính)"
    return "✅" if cot["notnull"] else "—"


def _rang_buoc(cot: Mapping[str, Any], fk_theo_cot: Mapping[str, dict]) -> str:
    phan: list[str] = []
    if cot["khoa_chinh"]:
        phan.append("PK")
    fk = fk_theo_cot.get(cot["ten"])
    if fk:
        phan.append(f"FK → {fk['bang_dich']}.{fk['cot_dich']}")
    if cot["mac_dinh"] is not None:
        phan.append(f"mặc định {cot['mac_dinh']}")
    return " · ".join(phan) if phan else "—"


def sinh_noi_dung(
    *,
    artifact: Mapping[str, Any],
    y_nghia: Mapping[tuple[str, str], NghiaCot],
    dung_boi: Mapping[tuple[str, str], Sequence[str]],
    ngay: str,
) -> str:
    """Toàn bộ nội dung `tu-dien-du-lieu.md`, tất định từng ký tự.

    Tất định là điều kiện để test khoá sinh lại trong bộ nhớ rồi so với file
    trên đĩa — lệch một ký tự là đỏ.
    """
    bang = artifact["bang"]
    so_da_tra = sum(1 for b in bang for c in b["cot"] if (b["ten"], c["ten"]) in y_nghia)

    d: list[str] = [
        "# Từ điển Dữ liệu (Data Dictionary)",
        "",
        "> Nguồn tham chiếu DUY NHẤT về ý nghĩa mọi bảng/trường trong hệ thống — không phải tài liệu tham khảo tùy chọn.",
        "> AI bắt buộc tra file này trước khi đọc/ghi bất kỳ trường nào, không suy đoán ý nghĩa từ tên trường hay code cũ.",
        "> Cập nhật theo kiểu NỐI THÊM có version từng dòng — không ghi đè lịch sử.",
        "> **Bất kỳ thay đổi migration nào (thêm/xóa/sửa bảng hoặc trường) đều bắt buộc cập nhật file này + ERD trong ARCHITECTURE.md ngay lập tức — dù thay đổi nhỏ đến đâu.**",
        "",
        "---",
        "",
        "## 0. File này do MÁY SINH — đừng sửa tay",
        "",
        "🔴 **Sửa tay ở đây sẽ bị test khoá bắt đỏ** (`tests/lock/test_td0245_tu_dien_soi_schema_that.py`).",
        "Toàn bộ nội dung sinh từ **schema THẬT** bằng:",
        "",
        "```",
        "docker compose -f docker/docker-compose.yml run --rm freqtrade \\",
        "    docs/du-lieu-do/do_td0245_schema_sqlite_freqtrade.py   # đo lại schema",
        "docker compose -f docker/docker-compose.yml run --rm freqtrade \\",
        "    -m tool_d.tu_dien.ghi_tu_dien                          # sinh lại file này",
        "```",
        "",
        "Muốn sửa một dòng thì sửa **nguồn** của nó: kiểu dữ liệu/ràng buộc nằm ở chính database",
        "(đo lại), cột *Ý nghĩa* nằm ở `src/tool_d/tu_dien/y_nghia_cot.py`.",
        "",
        "### Xuất xứ của bản này",
        "",
        f"- **Nguồn schema:** `{artifact['nguon_schema']['ham']}` — {artifact['nguon_schema']['mo_ta']}",
        f"- **Đọc lại bằng:** {artifact['nguon_schema']['doc_lai_bang']}",
        f"- **Freqtrade:** `{artifact['freqtrade_version']}`",
        f"- **Source commit:** `{artifact['freqtrade_source_commit']}`",
        f"- **Image digest:** `{artifact['runtime_image_digest']}`",
        f"- **Artifact:** `docs/du-lieu-do/td0245-schema-sqlite-freqtrade.json`",
        f"- **Quy mô:** **{artifact['so_bang']} bảng / {artifact['so_cot']} cột**",
        "",
        "⚠️ **Image đổi thì phải ĐO LẠI, không dùng số cũ.** Mọi `file:line` trong cột *Ý nghĩa*",
        "là ảnh chụp mã nguồn Freqtrade tại thời điểm đọc, không phải hằng số.",
        "",
        "### Ba trạng thái của cột *Ý nghĩa* — vì sao không điền cho đủ",
        "",
        f"- **đã tra** ({so_da_tra}/{artifact['so_cot']} cột): ý nghĩa đọc ra từ mã nguồn Freqtrade, có `file:line` kèm theo.",
        f"- **{CHUA_TRA}**: chưa ai đọc mã cho cột này.",
        "",
        "Quy tắc 7 cấm *\"suy đoán ý nghĩa từ tên trường\"*. Điền nốt phần còn lại bằng suy đoán sẽ",
        "tạo ra những dòng **trông y hệt** dòng đã tra — nguy hơn hẳn một ô ghi thẳng là chưa biết (N6).",
        "",
        "🔴 **Cần một cột đang `⏳`?** Đọc mã nguồn Freqtrade trong ảnh Docker, thêm mục vào",
        "`y_nghia_cot.py` kèm `file:line`, sinh lại. **Đừng đoán, và đừng đọc nó khi chưa tra** —",
        "test khoá sẽ chặn đúng ở đó.",
        "",
        "---",
        "",
        "## 1. Phạm vi — đọc trước khi dùng",
        "",
        "File này mô tả **database SQLite mà Freqtrade ghi lệnh** (`config/freqtrade/config.json` → `db_url`).",
        "",
        "**KHÔNG thuộc phạm vi bản này** (mỗi mục là một việc riêng, chưa mở):",
        "",
        "- **Hình dạng bên trong `trade_custom_data.cd_value`** — nơi Tool D cất dữ liệu riêng",
        "  (`co_lenh`, `ke_hoach`, `tag`, `zone_dinh`, `chot_loi`). Chưa có schema nào mô tả.",
        "- **Các sổ JSONL** (`trial_registry`, `idea_queue`, `param_change_proposals`, `decision_log`).",
        "  Nguồn sự thật hình dạng của chúng là **JSON Schema trong `registry/schemas/`**, và",
        "  `ARCHITECTURE.md:271-273` đã ràng buộc trước: nếu mô tả ở đây thì phải **sinh/kiểm tự động**,",
        "  không chép tay — chép tay là dựng nguồn sự thật thứ hai, đúng bài học **MT-03**.",
        "",
        "---",
        "",
        "## 2. Sơ đồ quan hệ",
        "",
        "```",
        "trades ──1:N──> orders              (orders.ft_trade_id → trades.id)",
        "       └─1:N──> trade_custom_data   (trade_custom_data.ft_trade_id → trades.id)",
        "",
        "wallet_history   pairlocks   KeyValueStore    (độc lập, không khoá ngoại)",
        "```",
        "",
        "---",
        "",
    ]

    for b in bang:
        fk_theo_cot = {fk["cot"]: fk for fk in b["khoa_ngoai"]}
        hang: list[Sequence[str]] = []
        for c in b["cot"]:
            khoa = (b["ten"], c["ten"])
            n = y_nghia.get(khoa)
            hang.append(
                (
                    f"`{c['ten']}`",
                    c["kieu"],
                    f"{n.y_nghia} — _nguồn: `{n.bang_chung}`_" if n else CHUA_TRA,
                    _bat_buoc(c),
                    n.gia_tri_hop_le if n else "—",
                    _rang_buoc(c, fk_theo_cot),
                    " · ".join(f"`{x}`" for x in dung_boi.get(khoa, ())) or "—",
                    PHIEN_BAN_DONG,
                    ngay,
                )
            )
        da_tra = sum(1 for c in b["cot"] if (b["ten"], c["ten"]) in y_nghia)
        d += [
            f"## Bảng: {b['ten']}",
            "",
            f"**{b['so_cot']} cột** · đã tra ý nghĩa: **{da_tra}/{b['so_cot']}**",
            "",
        ]
        d += _bang(COT_BANG_CHINH, hang)
        d.append("")

    d += [
        "---",
        "",
        "## Lịch sử thay đổi Từ điển Dữ liệu",
        "",
    ]
    d += _bang(
        COT_LICH_SU,
        [
            (
                "(toàn bộ)",
                "➕ Thêm mới",
                "—",
                f"Khởi tạo từ schema THẬT: {artifact['so_bang']} bảng / {artifact['so_cot']} cột",
                "TD-0245 — Quy tắc 7 đang chặn TD-0238 và TD-0240; từ điển chưa bao giờ tồn tại ở gốc repo",
                ngay,
            )
        ],
    )
    d += [
        "",
        "---",
        "",
        f"_Bằng chứng ý nghĩa đọc từ: {NGUON_BANG_CHUNG}_",
        "",
    ]
    return "\n".join(d)


def gop_dung_boi(
    cho_doc: Sequence[ChoDoc],
    cot_theo_bang: Mapping[str, frozenset[str]],
    them: Mapping[tuple[str, str], Sequence[str]],
) -> dict[tuple[str, str], list[str]]:
    """Gộp kết quả quét AST với phần khai tay thành cột *Dùng bởi*.

    Một tên cột có thể thuộc nhiều bảng (`id`, `amount`, `leverage`…). Phép quét
    chỉ thấy TÊN thuộc tính, không biết bảng, nên mỗi chỗ đọc được gán cho MỌI
    bảng có cột tên đó. Đây là chỗ phép quét **nói ít hơn sự thật** một cách có
    kiểm soát — nó trả lời *"cái tên này bị đọc ở đâu"*, không phải *"cột của
    bảng nào bị đọc"*; muốn chính xác tới bảng thì khai vào `TOOL_D_DOC_THEM`.
    """
    ket: dict[tuple[str, str], set[str]] = {}
    for c in cho_doc:
        for ten_bang, cot in cot_theo_bang.items():
            if c.cot in cot:
                ket.setdefault((ten_bang, c.cot), set()).add(c.nhan())
    for khoa, nhan in them.items():
        ket.setdefault(khoa, set()).update(nhan)
    return {k: sorted(v) for k, v in ket.items()}
