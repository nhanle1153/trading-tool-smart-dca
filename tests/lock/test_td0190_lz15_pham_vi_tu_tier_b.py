"""🔴 TD-0190 — `L-Z15` lấy DANH SÁCH tham số từ `tier_b`, không từ danh
sách tự khai.

DR-D4-03 §6 đã siết `L-Z15` một lần (mọi mục ĐÃ KHAI đều bị soi, kể cả khi
đã có giá trị) và bản siết đó đúng. Nhưng nó đặt `param_status.yaml` làm
*"nguồn sự thật cho DANH SÁCH"*, nên phép kiểm chỉ soi những mục **có
người tự khai**. Kiểm kê TD-0190 đo được hậu quả: danh sách có ĐÚNG MỘT
mục, trong khi **11/12** tham số `tier_b` mang giá trị mà không trial,
không `frozen_rationale`.

🔑 **Hình dạng lỗi thứ ba của dự án, khác hai cái đã ghi.** Không phải
*lớp canh cùn* (rà 19/19 phép phá đều bị bắt), cũng không phải *chĩa nhầm
hướng* (ca sai chỉ đi qua mẫu dựng tay). Đây là: **người bị canh tự chọn
phạm vi bị canh.** Một danh sách tự khai thì bỏ trống luôn là hợp lệ, và
phép kiểm xanh vĩnh viễn mà không ai nói dối câu nào.

Bộ test này canh đúng một tính chất: **phạm vi không co lại được.**
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tool_d.ledger.audit_checks import check_lz15_calibrate_params_have_status

REPO_ROOT = Path(__file__).resolve().parents[2]


def _cfg(tmp_path: Path, **tier_b: str) -> Path:
    dong = "\n".join(f"  {k}: {v}" for k, v in tier_b.items())
    p = tmp_path / "cfg.yaml"
    p.write_text(
        f"tier_a: {{}}\ntier_b:\n  _budget_remaining_B3: null\n{dong}\n"
        "tier_frozen: {}\ntier_c: {}\n",
        encoding="utf-8",
    )
    return p


def _status(tmp_path: Path, noi_dung: str) -> Path:
    p = tmp_path / "status.yaml"
    p.write_text(noi_dung, encoding="utf-8")
    return p


class TestPhamViKhongCoLaiDuoc:
    def test_tham_so_CO_GIA_TRI_ma_khong_khai_thi_FAIL(self, tmp_path: Path) -> None:
        """🔴 Ca cốt lõi của TD-0190 — chính xác ca bản DR-D4-03 bỏ lọt.
        Nó chỉ soi mục ĐÃ KHAI, nên một tham số không khai thì vô hình,
        dù nó đang mang một con số hệ thống dùng thật."""
        r = check_lz15_calibrate_params_have_status(
            _cfg(tmp_path, zss_threshold="0.5"),
            _status(tmp_path, "params: {}\n"),
        )
        assert r.is_fail
        assert "zss_threshold" in r.evidence
        assert "đang mang giá trị" in r.evidence

    def test_khai_MOT_trong_HAI_van_FAIL_vi_con_cai_kia(self, tmp_path: Path) -> None:
        """Khai đủ một mục không làm phép kiểm hài lòng — đó đúng là cách
        danh sách một dòng đã giữ nó xanh suốt."""
        r = check_lz15_calibrate_params_have_status(
            _cfg(tmp_path, v_min="1.0", zss_threshold="0.5"),
            _status(
                tmp_path,
                "params:\n  v_min:\n    status: FROZEN\n    frozen_rationale: có lý do\n",
            ),
        )
        assert r.is_fail
        assert "zss_threshold" in r.evidence
        assert "v_min:" not in r.evidence

    def test_khai_DU_moi_khoa_tier_b_thi_DAT(self, tmp_path: Path) -> None:
        """Chốt phải THOẢ ĐƯỢC — một chốt không bao giờ thoả được thì tệ
        hơn không có chốt, sớm muộn bị gỡ (bài học cổng D3)."""
        r = check_lz15_calibrate_params_have_status(
            _cfg(tmp_path, v_min="1.0", zss_threshold="0.5"),
            _status(
                tmp_path,
                "params:\n"
                "  v_min:\n    status: FROZEN\n    frozen_rationale: lý do A\n"
                "  zss_threshold:\n    status: FROZEN\n    frozen_rationale: lý do B\n",
            ),
        )
        assert r.ok, r.evidence

    def test_khoa_gach_duoi_KHONG_bi_doi_khai(self, tmp_path: Path) -> None:
        """`_budget_remaining_B3` là khoá dẫn xuất (MT-03), không phải
        tham số — đòi nó khai trạng thái là siết quá tay."""
        r = check_lz15_calibrate_params_have_status(
            _cfg(tmp_path, v_min="1.0"),
            _status(
                tmp_path,
                "params:\n  v_min:\n    status: FROZEN\n    frozen_rationale: lý do\n",
            ),
        )
        assert r.ok, r.evidence
        assert "_budget_remaining_B3" not in r.evidence

    def test_thieu_HAN_file_status_thi_FAIL_du_khong_co_khoa_null_nao(
        self, tmp_path: Path
    ) -> None:
        """Bản cũ trả ĐẠT khi không khoá nào `null` — tức một hệ thống đã
        điền hết số nhưng chưa khai gì cả sẽ đi qua sạch sẽ."""
        r = check_lz15_calibrate_params_have_status(
            _cfg(tmp_path, v_min="1.0", zss_threshold="0.5"),
            tmp_path / "khong-ton-tai.yaml",
        )
        assert r.is_fail
        assert "thiếu" in r.evidence


class TestBaLuatCuGiuNguyenKhongNoi:
    """Đổi NGUỒN danh sách, không đổi luật nào của DR-D4-03."""

    def test_FROZEN_thieu_frozen_rationale_van_FAIL(self, tmp_path: Path) -> None:
        r = check_lz15_calibrate_params_have_status(
            _cfg(tmp_path, v_min="1.0"),
            _status(tmp_path, "params:\n  v_min:\n    status: FROZEN\n"),
        )
        assert r.is_fail
        assert "frozen_rationale" in r.evidence

    def test_TUNED_PENDING_khi_da_co_gia_tri_van_FAIL(self, tmp_path: Path) -> None:
        r = check_lz15_calibrate_params_have_status(
            _cfg(tmp_path, v_min="1.0"),
            _status(tmp_path, "params:\n  v_min:\n    status: TUNED_PENDING\n"),
        )
        assert r.is_fail
        assert "TUNED_PENDING" in r.evidence

    def test_TUNED_PENDING_khi_con_null_van_DAT(self, tmp_path: Path) -> None:
        r = check_lz15_calibrate_params_have_status(
            _cfg(tmp_path, v_min="null"),
            _status(tmp_path, "params:\n  v_min:\n    status: TUNED_PENDING\n"),
        )
        assert r.ok, r.evidence

    def test_status_la_thi_FAIL(self, tmp_path: Path) -> None:
        r = check_lz15_calibrate_params_have_status(
            _cfg(tmp_path, v_min="1.0"),
            _status(tmp_path, "params:\n  v_min:\n    status: DA_XEM_QUA\n"),
        )
        assert r.is_fail


class TestHienTrangTrenFileTHAT:
    """Ghim con số kiểm kê TD-0190, trên file THẬT của project.

    📌 **Ca này đã được LẬT NGƯỢC một lần, cố ý.** Bản đầu khẳng định
    `r.is_fail` và ghim *"đúng 11 tham số chưa khai"* — đúng tại thời
    điểm đó. Khi chủ dự án duyệt 12 trạng thái (08/09/2026) thì nó phải
    đảo chiều, **không được xoá**: xoá một ca đỏ cho sạch bảng là cách
    một quyết định biến mất mà không ai ghi (tiền lệ TD-0150 xử hai ca
    của TD-0149).
    """

    def test_du_12_muc_va_KHONG_muc_nao_da_calibrate(self) -> None:
        """🔴 Con số phải đọc kèm mọi kết quả D4: cả 12 tham số `tier_b`
        là CHỖ GIỮ, không tham số nào từng được tune bằng một trial."""
        r = check_lz15_calibrate_params_have_status()
        assert r.ok, r.evidence
        assert "12/12" in r.evidence, r.evidence
        assert "12 ở CHỖ GIỮ chưa calibrate" in r.evidence, r.evidence
        assert "0 đã TUNED" in r.evidence, r.evidence

    def test_moi_muc_deu_khai_chua_calibrate_dang_MAY_DOC_DUOC(self) -> None:
        """Không đủ nếu sự thật đó chỉ nằm trong văn xuôi `frozen_rationale`
        — máy phải đọc được thì nó mới đi vào bằng chứng cổng."""
        import yaml

        ps = yaml.safe_load(
            (REPO_ROOT / "config/param_status.yaml").read_text(encoding="utf-8")
        )["params"]
        assert len(ps) == 12
        khong_khai = [k for k, v in ps.items() if not v.get("chua_calibrate")]
        assert not khong_khai, (
            f"{khong_khai} không khai `chua_calibrate` — nếu một tham số THẬT SỰ đã "
            "calibrate thì nó phải là `status: TUNED` kèm trial, không phải FROZEN "
            "im lặng bỏ trường này"
        )

    def test_khong_tham_so_tier_b_nao_tung_duoc_TUNE_that(self) -> None:
        """Nền của kết luận trên: nếu có trial nào từng tune một khoá
        `tier_b` thì mục đó đáng ra phải khai `TUNED`, và con số 11 sẽ
        khác. Đọc sổ THẬT thay vì tin bảng."""
        import json

        repo = Path(__file__).resolve().parents[2]
        duoi_test = set()
        for dong in (repo / "registry/trial_registry.jsonl").read_text(
            encoding="utf-8"
        ).splitlines():
            if dong.strip():
                if (p := json.loads(dong).get("param_under_test")):
                    duoi_test.add(p)

        from tool_d.config.loader import load_tool_d_config, tunable_param_names

        assert not (duoi_test & set(tunable_param_names(load_tool_d_config()))), (
            f"có tham số tier_b đã được tune thật: {duoi_test} — cập nhật lại kiểm kê"
        )
