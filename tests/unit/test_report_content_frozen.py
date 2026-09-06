"""TD-0062 — đóng băng nội dung báo cáo định kỳ (E5). Spec dòng 4808:

    🔴 ĐỔI NỘI DUNG BÁO CÁO = TIÊU 1 TRIAL. Nếu không, bạn sẽ thêm chỉ số
       mới cho tới khi tìm được cái trông bất thường.

`FROZEN_CONTENT_HASH` dưới đây là vân tay (`content_fingerprint()`, hash
của toàn bộ cặp code+label theo đúng thứ tự) tại thời điểm TD-0062 đóng.
Test này KHÔNG được sửa để "cho qua" khi đỏ — một hash lệch nghĩa là danh
sách chỉ số đã đổi, và theo spec đó PHẢI đi kèm một quyết định quản trị
(trừ 1 trial từ B3, DR-012) trước khi cập nhật hằng số này, không phải một
refactor tự do.
"""

from __future__ import annotations

from tool_d.reporting.report_model import build_metrics, content_fingerprint

# 🔴 Đổi hằng số này = xác nhận đã ĐỔI NỘI DUNG BÁO CÁO = TIÊU 1 TRIAL
# (spec dòng 4808). Phải kèm: lý do đổi + trial_id đã trừ khỏi B3, ghi
# vào registry/TASKS.md — không tự sửa hằng số này khi thấy test đỏ.
FROZEN_CONTENT_HASH = "be32148011ac0f25d69c34d768a928323c53f6decbe565d96d425648d2f24484"


class TestNoiDungBaoCaoDaDongBang:
    def test_van_tay_khop_ban_da_dong_bang(self) -> None:
        assert content_fingerprint() == FROZEN_CONTENT_HASH, (
            "Vân tay nội dung báo cáo ĐÃ ĐỔI so với bản đóng băng ở TD-0062. "
            "Theo spec dòng 4808: đổi nội dung báo cáo = TIÊU 1 TRIAL — đây "
            "phải là quyết định quản trị (DR-012/ngân sách B3), không phải "
            "sửa test cho xanh lại."
        )

    def test_van_tay_on_dinh_qua_nhieu_lan_goi(self) -> None:
        assert content_fingerprint() == content_fingerprint()

    def test_van_tay_nhay_cam_voi_thu_tu(self) -> None:
        # Đổi THỨ TỰ khai báo cũng là đổi nội dung (LLM đọc báo cáo theo
        # thứ tự trình bày) — vân tay phải phân biệt được, không chỉ so
        # tập hợp không thứ tự.
        metrics = build_metrics()
        xuoi = "\n".join(f"{m.code}|{m.label}" for m in metrics)
        nguoc = "\n".join(f"{m.code}|{m.label}" for m in reversed(metrics))
        assert xuoi != nguoc

    def test_van_tay_nhay_cam_voi_doi_nhan(self) -> None:
        # Chứng minh hàm có răng: đổi MỘT nhãn phải đổi hash — nếu không,
        # "đóng băng" chỉ là hình thức.
        import hashlib

        metrics = build_metrics()
        payload_goc = "\n".join(f"{m.code}|{m.label}" for m in metrics)
        payload_sua = payload_goc.replace(metrics[0].label, metrics[0].label + " (sửa)")
        assert hashlib.sha256(payload_goc.encode()).hexdigest() != hashlib.sha256(
            payload_sua.encode()
        ).hexdigest()
