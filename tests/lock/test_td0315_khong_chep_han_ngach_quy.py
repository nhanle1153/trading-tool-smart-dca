"""TD-0315 — đầu ra lúc chạy của cửa NỘP không được chép hạn ngạch của MỘT quý.

Bản trước, thông báo Ca 2 (`status` không hợp lệ) ghi cứng *"quý 3/2026 khai
`HAN_NGACH_CHON: 0`"*. Nguồn sự thật là `docs/decisions/DR-Q{n}-{năm}-tieu-chi-
chon-y-tuong.md` của đúng quý, và máy vốn đã đọc động (`HAN_NGACH_RE`,
`_tieu_chi_path()`), nên câu đó chỉ là một bản chép — rồi quý đổi, bản chép ở lại.

🔑 Vì sao nó nguy hơn một chú thích lỗi thời: nó nằm trong **chuỗi in ra lúc chạy**,
   nên người đọc thấy máy đang nói, không thấy một dòng văn bản cũ. Một phiên IDEA
   sạch điền nhầm `status: SELECTED` sẽ đọc nó và tin cửa chọn đang đóng — trong khi
   `DR-Q4-2026` khai hạn ngạch 1. Cùng lớp lỗi với `docs/mau-don-y-tuong.yaml`
   (TD-0304) và với bảng `102/102` của TD-0082: một con số đúng MỘT LẦN rồi được đọc
   như thể LUÔN đúng.

Chốt theo **VẮNG MẶT MỘT MẪU**, không theo vắng mặt chuỗi "quý 3/2026": chép số quý
nào cũng đỏ, kể cả quý chưa tồn tại lúc viết test này.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from tool_d.ledger import idea_queue as iq_mod  # noqa: E402
from tool_d.ledger.idea_queue import IdeaQueueError, submit_idea  # noqa: E402

# "quý 3/2026", "quy 3/2026", "Quý 04/2026" — mọi cách chép một quý cụ thể.
MAU_CHEP_QUY = re.compile(r"qu[ýy]\s*0?[1-4]\s*/\s*\d{4}", re.IGNORECASE)

# Bản chép hạn ngạch kèm số, kiểu "HAN_NGACH_CHON: 0".
MAU_CHEP_HAN_NGACH = re.compile(r"HAN_NGACH_CHON\s*:\s*\d+")


def _don_selected() -> dict:
    """Tờ đơn hợp lệ mọi mặt TRỪ `status` — để chạm đúng Ca 2, không ca khác."""
    return {
        "source": "LLM",
        "data_source": "MECHANISM",
        "title": "don thu td0315 cham ca 2",
        "mechanism": "khong mo ta co che that, chi de cham ca 2 cua cua nop",
        "who_pays": "khong ai, day la don thu",
        "durability": "khong ap dung, don thu",
        "phep_thu_du_kien": "khong ap dung, don thu",
        "filter_verdict": "PASS",
        "status": "SELECTED",  # ← cửa NỘP phải từ chối
    }


def _thong_bao_ca_2(tmp_path: Path) -> str:
    so = tmp_path / "idea_queue.jsonl"
    with pytest.raises(IdeaQueueError) as exc:
        submit_idea(don=_don_selected(), path=so)
    assert not so.exists(), "Ca 2 phải từ chối TRƯỚC khi mở file — sổ append-only không có đường lùi"
    return str(exc.value)


class TestKhongChepHanNgachCuaMotQuy:
    def test_thong_bao_ca_2_van_chan_selected(self, tmp_path: Path) -> None:
        """Chốt này chỉ có nghĩa nếu Ca 2 còn chặn — kiểm trước, kẻo canh một nhánh đã chết."""
        tb = _thong_bao_ca_2(tmp_path)
        assert "SELECTED" in tb
        assert "QUEUED" in tb

    def test_khong_chep_so_quy_nao(self, tmp_path: Path) -> None:
        tb = _thong_bao_ca_2(tmp_path)
        assert not MAU_CHEP_QUY.search(tb), (
            "Thông báo Ca 2 đang chép hạn ngạch của MỘT quý cụ thể. Nguồn sự thật là "
            "docs/decisions/DR-Q<n>-<năm>-tieu-chi-chon-y-tuong.md và máy đã đọc động — "
            f"chép vào đây là tạo bản thứ hai sẽ lỗi thời khi sang quý mới.\nThông báo: {tb}"
        )

    def test_khong_chep_con_so_han_ngach(self, tmp_path: Path) -> None:
        tb = _thong_bao_ca_2(tmp_path)
        assert not MAU_CHEP_HAN_NGACH.search(tb), (
            f"Thông báo Ca 2 đang chép một con số HAN_NGACH_CHON.\nThông báo: {tb}"
        )

    def test_van_tro_toi_nguon_su_that(self, tmp_path: Path) -> None:
        """Bỏ con số mà không trỏ đi đâu thì người đọc mất luôn đường tra — tệ hơn bản cũ."""
        tb = _thong_bao_ca_2(tmp_path)
        assert "tieu-chi-chon-y-tuong" in tb, (
            "Đã bỏ con số nhưng không trỏ tới DR tiêu chí chọn — người đọc không còn đường tra."
        )


class TestDocstringModuleCungKhongChep:
    """Docstring nhẹ hơn (phiên sạch không cần đọc code) nhưng cùng một lớp lỗi."""

    def test_docstring_khong_chep_so_quy(self) -> None:
        doc = iq_mod.__doc__ or ""
        assert not MAU_CHEP_QUY.search(doc), (
            f"Docstring module đang chép hạn ngạch của một quý cụ thể.\n{doc}"
        )
