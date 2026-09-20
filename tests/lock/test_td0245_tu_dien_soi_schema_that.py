"""TD-0245 — `tu-dien-du-lieu.md` phải soi SCHEMA THẬT, và Quy tắc 7 phải có răng.

Hai lớp canh, đóng hai lỗ khác nhau:

**A — từ điển không được trôi khỏi database.** Quy tắc 8 (`CLAUDE.md:27`):
*"Database thật luôn là chân lý — nếu lệch, sửa từ điển theo database, không
phải ngược lại."* Test A sinh lại nội dung trong bộ nhớ từ artifact rồi so
từng ký tự với file trên đĩa. Bắt được cả hai chiều: ai đó sửa tay từ điển,
và Freqtrade nâng cấp thêm/bớt cột (sau khi đo lại).

**B — Quy tắc 7 thành máy.** Không được đọc một cột chưa tra. Trước TD-0245
luật này **không có một dòng mã nào** thi hành — đúng hình dạng `MT-08`
(chính sách chốt ở năm chỗ trong spec mà mã vẫn làm sai) và `L-Z26` (luật
chặt, 0 dòng code).

🔑 **Cả hai test gọi ĐÚNG hàm mà đường sản xuất gọi** (`dung_noi_dung()`,
`kiem_quy_tac_7()`), không chép lại logic. Đây là bài học `TD-0168`: hôm đó
33 phép kiểm canh một hàm mà **đường chạy thật chưa từng gọi** — *"thứ được
canh không nằm trên đường chạy"*. Một bản sao logic trong test sẽ xanh mãi
ngay cả khi bản thật đã hỏng.

🔴 **`TestCoRang` tự chứng minh mình có răng.** Bài học lặp bốn lần trong
ngày 08/09: *"một lớp bảo vệ chưa ai thử xem nó có canh thật không thì nguy
hơn không có lớp nào"* — vì có nó thì người ta thôi cảnh giác.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tool_d.tu_dien.ghi_tu_dien import (
    FILE_ARTIFACT,
    FILE_TU_DIEN,
    doc_artifact,
    dung_noi_dung,
    quet_tat_ca,
    quet_va_phan_loai,
)
from tool_d.tu_dien.kiem_quy_tac_7 import kiem_quy_tac_7
from tool_d.tu_dien.quet_cot import ChoDoc, la_ten_dac_trung
from tool_d.tu_dien.sinh_tu_dien import COT_BANG_CHINH, LoiSinhTuDien, _hang
from tool_d.tu_dien.y_nghia_cot import (
    KHONG_PHAI_DOC_DB,
    TOOL_D_DOC_THEM,
    NghiaCot,
    Y_NGHIA,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

LENH_SINH_LAI = (
    "docker compose -f docker/docker-compose.yml run --rm freqtrade "
    "-m tool_d.tu_dien.ghi_tu_dien"
)
LENH_DO_LAI = (
    "docker compose -f docker/docker-compose.yml run --rm freqtrade "
    "docs/du-lieu-do/do_td0245_schema_sqlite_freqtrade.py"
)


@pytest.fixture(scope="module")
def artifact() -> dict:
    return doc_artifact(FILE_ARTIFACT)


class TestArtifactLaBangChung:
    """Artifact phải là bằng chứng của một lần chạy THẬT trong Docker."""

    def test_artifact_ton_tai(self) -> None:
        assert FILE_ARTIFACT.is_file(), (
            f"thiếu {FILE_ARTIFACT} — từ điển KHÔNG được viết từ trí nhớ "
            f"(Quy tắc 8). Chạy: {LENH_DO_LAI}"
        )

    def test_so_dem_khop_noi_dung(self, artifact: dict) -> None:
        """`so_bang`/`so_cot` phải là phép đếm THẬT, không phải số gõ tay.

        Con số "6 bảng / 109 cột" lưu hành trước TD-0245 không có xuất xứ nào
        trong repo. Test này giữ cho nó mãi là số đo, không trở lại thành lời khai.
        """
        assert artifact["so_bang"] == len(artifact["bang"])
        assert artifact["so_cot"] == sum(b["so_cot"] for b in artifact["bang"])
        for b in artifact["bang"]:
            assert b["so_cot"] == len(b["cot"]), f"bảng {b['ten']} lệch số cột"

    def test_co_du_xuat_xu(self, artifact: dict) -> None:
        """Thiếu xuất xứ ⇒ không truy lại được "lúc đó chạy Freqtrade bản nào"."""
        for khoa in ("freqtrade_version", "freqtrade_source_commit", "runtime_image_digest"):
            assert artifact.get(khoa), f"artifact thiếu {khoa}"
        assert artifact["runtime_image_digest"].startswith("sha256:")
        assert artifact["trial"] == 0

    def test_khong_sinh_file_sqlite_LA_trong_repo(self) -> None:
        """Phép đo dùng DB tạm trong `/tmp` của container, không rơi vào repo.

        Một `*.sqlite` LẠ nằm trong repo sẽ bị `.gitignore` nuốt im lặng, rồi sau này có người tưởng đó
        là DB thật của một lần chạy thật.

        🔴 **THU HẸP 20/09/2026 (TD-0350, chủ dự án duyệt sửa khẳng định).** Bản cũ cấm MỌI `*.sqlite`
        trong repo. Từ khi có service dry-run (`DR-TRIEN-KHAI-01` §4), bot vận hành LUÔN sinh đúng file
        DB mà `config/freqtrade/config.json` đã ghim có chủ đích (`TD-0201`/`TD-0202`) — hai quyết định
        đã chốt va nhau, và bản cũ làm suite đỏ mỗi khi dry-run chạy. Ý định gốc của ca này là *"phép ĐO
        không được để lại DB"*, không phải *"bot vận hành không được có DB"*: nay cấm đúng file LẠ, và
        đường DB hợp lệ đọc THẲNG từ config — không chép tay thành hằng số thứ hai (LD-09).
        """
        hop_le = set()
        for khoa in ("db_url",):
            url = json.loads(
                (REPO_ROOT / "config/freqtrade/config.json").read_text(encoding="utf-8")
            ).get(khoa, "")
            if url.startswith("sqlite:///"):
                hop_le.add(Path(url.replace("sqlite:////", "/").replace("sqlite:///", "")).name)
        assert hop_le, "config không khai db_url sqlite nào — đường DB hợp lệ phải đọc được từ config"

        thay = [
            p.relative_to(REPO_ROOT).as_posix()
            for p in REPO_ROOT.rglob("*.sqlite*")
            if ".git" not in p.parts and not p.name.startswith(tuple(hop_le))
        ]
        assert thay == [], f"có file sqlite LẠ lọt vào repo: {thay}"


class TestATuDienSoiSchemaThat:
    def test_tu_dien_ton_tai(self) -> None:
        assert FILE_TU_DIEN.is_file(), (
            f"thiếu {FILE_TU_DIEN.name} — Quy tắc 7 chặn mọi việc đọc trường "
            f"database khi chưa có từ điển. Chạy: {LENH_SINH_LAI}"
        )

    def test_khop_tung_ky_tu_voi_ban_sinh_lai(self) -> None:
        """File trên đĩa == bản sinh lại từ artifact. Lệch một ký tự là đỏ."""
        tren_dia = FILE_TU_DIEN.read_text(encoding="utf-8")
        sinh_lai = dung_noi_dung(REPO_ROOT)
        assert tren_dia == sinh_lai, (
            "tu-dien-du-lieu.md đã trôi khỏi schema thật. KHÔNG sửa tay file .md — "
            "sửa nguồn của nó (đo lại schema, hoặc thêm nghĩa vào "
            f"src/tool_d/tu_dien/y_nghia_cot.py) rồi chạy: {LENH_SINH_LAI}"
        )

    def test_moi_bang_do_duoc_deu_co_mat(self, artifact: dict) -> None:
        noi_dung = FILE_TU_DIEN.read_text(encoding="utf-8")
        for b in artifact["bang"]:
            assert f"## Bảng: {b['ten']}" in noi_dung, f"từ điển thiếu bảng {b['ten']}"

    def test_moi_cot_do_duoc_deu_co_mat(self, artifact: dict) -> None:
        noi_dung = FILE_TU_DIEN.read_text(encoding="utf-8")
        for b in artifact["bang"]:
            for c in b["cot"]:
                assert f"| `{c['ten']}` |" in noi_dung, (
                    f"từ điển thiếu cột {b['ten']}.{c['ten']}"
                )

    def test_moi_hang_dung_9_o(self) -> None:
        """`TD-0233`: markdown BỎ IM LẶNG mọi ô vượt quá số cột của header.

        Một dòng thừa ô không làm hỏng file — nó chỉ **biến mất ở bản render**,
        tức từ điển nói thiếu mà không ai biết.
        """
        so_cot = len(COT_BANG_CHINH)
        for i, dong in enumerate(FILE_TU_DIEN.read_text(encoding="utf-8").splitlines(), 1):
            if not dong.startswith("| `"):
                continue
            o = dong.split("|")[1:-1]
            assert len(o) == so_cot, f"dòng {i} có {len(o)} ô, phải đúng {so_cot}"


class TestBQuyTac7CoMay:
    def test_khong_co_vi_pham(self, artifact: dict) -> None:
        vi_pham = kiem_quy_tac_7(
            artifact=artifact,
            y_nghia=Y_NGHIA,
            tool_d_doc_them=TOOL_D_DOC_THEM,
            khong_phai_doc_db=KHONG_PHAI_DOC_DB,
            cho_doc=quet_tat_ca(artifact, REPO_ROOT),
        )
        assert vi_pham == [], "vi phạm Quy tắc 7:\n" + "\n".join(f"  {v}" for v in vi_pham)

    def test_moi_nghia_deu_co_bang_chung(self) -> None:
        """Không có nghĩa nào được phép thiếu `file:line`.

        Đây là ranh giới giữa "đã tra" và "đoán từ tên trường" — thứ Quy tắc 7
        cấm bằng chữ. Không có bằng chứng thì thuộc về `⏳`, không thuộc về đây.
        """
        for (bang, cot), n in sorted(Y_NGHIA.items()):
            assert n.bang_chung.strip(), f"{bang}.{cot} có nghĩa mà không có bằng chứng"
            assert ":" in n.bang_chung, (
                f"{bang}.{cot} bằng chứng {n.bang_chung!r} không có dạng file:line"
            )
            assert n.y_nghia.strip(), f"{bang}.{cot} có mục nhưng nghĩa rỗng"

    def test_cot_tool_d_dang_doc_deu_da_tra(self, artifact: dict) -> None:
        """Mọi cột mã sản xuất ĐANG đọc đều phải đã tra — đây chính là Quy tắc 7."""
        doc_db, _ = quet_va_phan_loai(artifact, REPO_ROOT)
        theo_bang = {b["ten"]: {c["ten"] for c in b["cot"]} for b in artifact["bang"]}
        chua_tra = {
            f"{bang}.{c.cot}"
            for c in doc_db
            for bang, cot in theo_bang.items()
            if c.cot in cot and (bang, c.cot) not in Y_NGHIA
        }
        assert chua_tra == set(), f"đang đọc cột chưa tra từ điển: {sorted(chua_tra)}"


class TestCoRang:
    """Tự chứng minh hai lớp canh trên CÓ RĂNG.

    Mọi ca ở đây gọi **đúng hàm** mà test thật gọi, chỉ đổi ĐẦU VÀO — nên nó
    chứng minh chính lớp canh đang chạy, không phải một bản sao.
    """

    def test_thieu_nghia_thi_bao_do(self, artifact: dict) -> None:
        """Hạ một cột đang đọc về `⏳` ⇒ phải có vi phạm DOC-COT-CHUA-TRA."""
        doc_db, _ = quet_va_phan_loai(artifact, REPO_ROOT)
        assert doc_db, "phép quét không thấy chỗ đọc nào — ca này mất ý nghĩa"
        nan_nhan = doc_db[0]
        bot_di = {k: v for k, v in Y_NGHIA.items() if k[1] != nan_nhan.cot}
        vi_pham = kiem_quy_tac_7(
            artifact=artifact,
            y_nghia=bot_di,
            tool_d_doc_them={},
            khong_phai_doc_db=KHONG_PHAI_DOC_DB,
            cho_doc=quet_tat_ca(artifact, REPO_ROOT),
        )
        assert any(v.ma == "DOC-COT-CHUA-TRA" for v in vi_pham), (
            f"bỏ nghĩa của {nan_nhan.cot} mà lớp canh vẫn im — nó không có răng"
        )

    def test_cot_bia_ra_thi_bao_do(self, artifact: dict) -> None:
        """Tên cột không tồn tại trong schema ⇒ KHONG-CO-COT.

        Đây là ca Quy tắc 7 sợ nhất: một cái tên nhớ nhầm, hoặc tên Freqtrade
        đã đổi ở bản mới, mà mã vẫn đọc.
        """
        vi_pham = kiem_quy_tac_7(
            artifact=artifact,
            y_nghia={
                **Y_NGHIA,
                ("trades", "loi_nhuan_rong"): NghiaCot("cột bịa", "khong_co_that.py:1"),
            },
            tool_d_doc_them={},
            khong_phai_doc_db=KHONG_PHAI_DOC_DB,
            cho_doc=[],
        )
        assert any(v.ma == "KHONG-CO-COT" for v in vi_pham)

    def test_khai_doc_ma_chua_tra_thi_bao_do(self, artifact: dict) -> None:
        vi_pham = kiem_quy_tac_7(
            artifact=artifact,
            y_nghia={},
            tool_d_doc_them={("trades", "close_date"): ("bat_ky.py",)},
            khong_phai_doc_db={},
            cho_doc=[],
        )
        assert any(v.ma == "KHAI-DOC-CHUA-TRA" for v in vi_pham)

    def test_mien_tru_chet_thi_bao_do(self, artifact: dict) -> None:
        """Miễn trừ không còn khớp chỗ nào phải bị bắt.

        Một danh sách miễn trừ không ai dọn sẽ lớn dần rồi che mất một ca thật
        — đúng lý do `CTRL_OUTPUT_ALLOWED` của `TD-0130` chọn danh sách CHO
        PHÉP thay vì danh sách cấm.
        """
        vi_pham = kiem_quy_tac_7(
            artifact=artifact,
            y_nghia=Y_NGHIA,
            tool_d_doc_them={},
            khong_phai_doc_db={("khong_ton_tai", "khong/co/file.py"): "lý do gì đó"},
            cho_doc=[],
        )
        assert any(v.ma == "MIEN-TRU-CHET" for v in vi_pham)

    def test_mien_tru_khong_ly_do_thi_bao_do(self, artifact: dict) -> None:
        cho = ChoDoc(cot="close_profit_abs", duong_dan="x.py", ham="f", dong=1)
        vi_pham = kiem_quy_tac_7(
            artifact=artifact,
            y_nghia=Y_NGHIA,
            tool_d_doc_them={},
            khong_phai_doc_db={("close_profit_abs", "x.py"): "   "},
            cho_doc=[cho],
        )
        assert any(v.ma == "MIEN-TRU-THIEU-LY-DO" for v in vi_pham)

    def test_truyen_ban_da_loc_thi_mien_tru_bao_chet(self, artifact: dict) -> None:
        """Hồi quy cho một lỗi THẬT đã xảy ra lúc viết TD-0245.

        `kiem_quy_tac_7()` phải nhận **toàn bộ** chỗ quét được. Lần đầu nối, tôi
        truyền bản ĐÃ LỌC (`quet_va_phan_loai()[0]`) nên không mục miễn trừ nào
        được đánh dấu "đã dùng" ⇒ mục nào cũng bị báo `MIEN-TRU-CHET`.

        Ca này ghim đúng cái sai đó: truyền bản đã lọc **phải** ra `MIEN-TRU-CHET`.
        Nó vừa chống lỗi quay lại, vừa chứng minh `MIEN-TRU-CHET` không phải một
        phép kiểm trang trí — nó đã bắt người viết ra chính nó.
        """
        doc_db, khong_phai = quet_va_phan_loai(artifact, REPO_ROOT)
        assert khong_phai, "không còn mục miễn trừ nào — ca này mất ý nghĩa"
        vi_pham = kiem_quy_tac_7(
            artifact=artifact,
            y_nghia=Y_NGHIA,
            tool_d_doc_them=TOOL_D_DOC_THEM,
            khong_phai_doc_db=KHONG_PHAI_DOC_DB,
            cho_doc=doc_db,
        )
        assert any(v.ma == "MIEN-TRU-CHET" for v in vi_pham)

    def test_bo_sinh_tu_choi_dong_sai_so_o(self) -> None:
        """Bộ sinh phải raise TRƯỚC khi ghi, không ghi ra một dòng sẽ tàng hình."""
        with pytest.raises(LoiSinhTuDien):
            _hang(("chỉ", "có", "ba"), len(COT_BANG_CHINH))

    def test_o_chua_dau_ong_duoc_escape(self) -> None:
        """Dấu `|` trong nội dung phải được escape, nếu không nó tự tách thêm ô."""
        dong = _hang(tuple(["a|b"] + ["x"] * (len(COT_BANG_CHINH) - 1)), len(COT_BANG_CHINH))
        assert dong.count("|") == len(COT_BANG_CHINH) + 1 + 1  # viền + 1 dấu đã escape
        assert r"a\|b" in dong

    def test_ten_chung_khong_bi_khop_nham(self) -> None:
        """Phép quét cố ý BỎ QUA tên cột quá chung — và đó là chủ ý, không phải lỗi.

        `self.timeframe` của chiến lược KHÔNG phải cột `trades.timeframe`. Khớp
        mù theo tên sẽ dựng một từ điển nói sai về ai đọc cái gì (bài học
        08/09: *"đừng đo tính chất NGỮ NGHĨA bằng dấu hiệu CÚ PHÁP"*).
        """
        for ten in ("id", "amount", "status", "pair", "price", "side", "timeframe", "leverage"):
            assert not la_ten_dac_trung(ten), f"{ten} quá chung, không được khớp theo tên"
        for ten in ("close_profit_abs", "realized_profit", "funding_fees", "order_update_date"):
            assert la_ten_dac_trung(ten), f"{ten} là tên đặc trưng, phải được canh"


class TestArtifactKhopFileTuDien:
    def test_artifact_json_hop_le(self) -> None:
        json.loads(FILE_ARTIFACT.read_text(encoding="utf-8"))
