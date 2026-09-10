"""🔴 TD-0201 — `decision_log.py` phân biệt NGUỒN bản ghi (backtest / dry-run
/ live), bắt buộc không mặc định.

Phát hiện khi soát dashboard front-end (`-dc`, 10/09/2026): `TRUONG_KHOA`
chỉ định nghĩa trường DỰNG KHOÁ cho bốn loại sự kiện của §8.3, không có
trường nào mang nguồn. Spec §8.3 cũng KHÔNG định nghĩa trường này — khoảng
trống thật của spec, module này lấp bằng một quyết định dự án (không phải
diễn giải lại spec).

🔴 Vì sao đáng một lớp canh riêng, không gộp vào `test_lz45_*`: `L-Z45`
canh tính chất DEDUP/APPEND-ONLY của sổ; đây là một trục khác — TÍNH ĐẦY ĐỦ
NỘI DUNG của một bản ghi hợp lệ. Trộn hai câu hỏi vào một file test sẽ làm
`test_lz45_*` đỏ vì lý do không liên quan tới dedup mỗi khi ai đó sửa danh
sách nguồn hợp lệ — đúng bài học *"canh đúng chỗ, không lẫn hai câu hỏi"*
đã lặp lại nhiều lần trong repo.

`nguon` KHÔNG tham gia khoá (`TRUONG_KHOA`) — cùng một sự kiện thật (cùng
`exchange_order_id`, v.v.) không đổi khoá chỉ vì đổi nguồn ghi. Nó là một
trường NỘI DUNG bắt buộc, kiểm bởi `dedup_key()` vì đó là điểm nghẽn DUY
NHẤT mọi bản ghi đi qua trước khi chạm file (bài học TD-0150: vá rải rác ở
nhiều hàm để lọt qua điểm chưa vá).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tool_d.ledger.decision_log import (
    NGUON_HOP_LE,
    TRUONG_KHOA,
    DecisionLogError,
    dedup_key,
    ghi_neu_chua_co,
)


def _ban_ghi(nguon: object = "backtest", **ghi_de) -> dict:
    co_ban = {"loai": "VAO_RA_LENH", "nguon": nguon, "exchange_order_id": "OID-1"}
    return {**co_ban, **ghi_de}


class TestBaGiaTriHopLe:
    def test_ba_gia_tri_dung_dinh_nghia(self) -> None:
        assert NGUON_HOP_LE == ("backtest", "dry_run", "live")

    @pytest.mark.parametrize("nguon", ["backtest", "dry_run", "live"])
    def test_moi_gia_tri_hop_le_deu_dung_khoa_duoc(self, nguon: str) -> None:
        assert dedup_key(_ban_ghi(nguon)) == "OID-1"


class TestFailClosed:
    def test_thieu_nguon_thi_raise(self) -> None:
        ban_ghi = {"loai": "VAO_RA_LENH", "exchange_order_id": "OID-1"}
        with pytest.raises(DecisionLogError, match="nguon"):
            dedup_key(ban_ghi)

    @pytest.mark.parametrize("nguon_sai", [None, "", "  ", "BACKTEST", "live ", "paper", 0, 1])
    def test_nguon_khong_thuoc_tap_hop_le_thi_raise(self, nguon_sai: object) -> None:
        with pytest.raises(DecisionLogError, match="nguon"):
            dedup_key(_ban_ghi(nguon_sai))

    def test_khong_mac_dinh_am_tham_ve_backtest(self) -> None:
        """Đây là điểm quan trọng nhất: thiếu `nguon` phải RAISE, KHÔNG được
        lặng lẽ coi là 'chắc là backtest'. Một mặc định ở đây là chỗ để một
        đường ghi live/dry-run quên khai mà vẫn lặng lẽ ghi lẫn vào backtest
        — đúng lỗi Tool A đã dính (đếm phóng đại vì gộp nguồn)."""
        with pytest.raises(DecisionLogError):
            dedup_key({"loai": "PLAN", "pair": "BTC/USDT:USDT", "candle_ts": "T", "block": "b"})

    def test_ghi_neu_chua_co_cung_tu_choi_thieu_nguon(self, tmp_path: Path) -> None:
        so = tmp_path / "s.jsonl"
        with pytest.raises(DecisionLogError, match="nguon"):
            ghi_neu_chua_co(so, {"loai": "VAO_RA_LENH", "exchange_order_id": "OID-1"})
        assert not so.exists(), "TỪ CHỐI phải xảy ra TRƯỚC khi chạm file"


class TestNguonKhongThamGiaKhoa:
    def test_doi_nguon_khong_doi_khoa(self) -> None:
        """Cùng sự kiện thật (cùng `exchange_order_id`), khác nguồn ghi
        (ví dụ tái lập một lệnh dry-run trong backtest để đối chiếu) →
        PHẢI ra cùng khoá. `nguon` là nội dung, không phải một phần khoá."""
        a = dedup_key(_ban_ghi("backtest"))
        b = dedup_key(_ban_ghi("dry_run"))
        c = dedup_key(_ban_ghi("live"))
        assert a == b == c == "OID-1"

    def test_nguon_khong_nam_trong_bat_ky_TRUONG_KHOA_nao(self) -> None:
        for cac_truong in TRUONG_KHOA.values():
            assert "nguon" not in cac_truong


class TestApDungChoCaBonLoai:
    """`nguon` là điều kiện tiên quyết PHỔ QUÁT — không riêng cho
    `VAO_RA_LENH`. PLAN/GATE_CHECK cũng chạy cả ở backtest lẫn live."""

    @pytest.mark.parametrize(
        "ban_ghi_thieu_nguon",
        [
            {"loai": "VAO_RA_LENH", "exchange_order_id": "OID-1"},
            {"loai": "DOI_SL", "sl_order_id_new": "SL-1"},
            {"loai": "PLAN", "pair": "BTC/USDT:USDT", "candle_ts": "T", "block": "b"},
            {"loai": "GATE_CHECK", "trade_id": 1, "candle_ts": "T", "gate": "DG6"},
        ],
    )
    def test_ca_bon_loai_deu_doi_nguon(self, ban_ghi_thieu_nguon: dict) -> None:
        with pytest.raises(DecisionLogError, match="nguon"):
            dedup_key(ban_ghi_thieu_nguon)


class TestKiemTaiNguon:
    """Kiểm AST: bốn caller `TRUONG_KHOA` hiện có trong `decision_log.py`
    không hề đổi — bản vá KHÔNG được lan sang phần dựng khoá, chỉ thêm một
    điều kiện tiên quyết mới song song."""

    def test_TRUONG_KHOA_khong_doi(self) -> None:
        assert TRUONG_KHOA == {
            "VAO_RA_LENH": ("exchange_order_id",),
            "DOI_SL": ("sl_order_id_new",),
            "PLAN": ("pair", "candle_ts", "block"),
            "GATE_CHECK": ("trade_id", "candle_ts", "gate"),
        }

    def test_khong_co_gia_tri_mac_dinh_cho_tham_so_record(self) -> None:
        """`dedup_key(record)` không được có `nguon` mặc định lén qua
        `record.setdefault`/`dict.get(..., "backtest")` — chỉ được đọc
        bằng `.get("nguon")` rồi so với `NGUON_HOP_LE`, không có nhánh
        nào gán giá trị thay cho record."""
        import tool_d.ledger.decision_log as mod

        cay = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        ham = next(
            n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef) and n.name == "dedup_key"
        )
        nguon = [
            n
            for n in ast.walk(ham)
            if isinstance(n, ast.Attribute) and n.attr == "setdefault"
        ]
        assert not nguon, "phát hiện `setdefault` — nghi có mặc định lén cho `nguon`"
