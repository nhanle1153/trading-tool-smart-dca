"""TD-0229 — khoá xuất xứ thứ 8 `runtime_image_digest` (MT-07) phải có RĂNG.

Trước TD-0229 khoá này là một **PASS RỖNG**: có kiểu dữ liệu, có schema, nhưng
**không nơi gọi nào truyền giá trị** (`dr015/buoc1_lech_tranche.py:261` và
`entrypoints/periodic_report.py:55` đều bỏ trống ⇒ luôn `None`), bản ghi thật duy
nhất mang nó là `registry/trial_registry.jsonl` dòng 13 với `null`, không test nào
ghim, không gate nào so, và `cache_key()` **cố ý loại nó ra**.

⇒ Đổi `docker/Dockerfile:21` là một thao tác **im lặng hoàn toàn**: full suite vẫn
xanh, 5 cổng vẫn đóng, cache vẫn trúng, không bản ghi nào ghi nhận môi trường đã đổi.

🔴 File này **KHÔNG sửa một ca nào của `L-Z40`**. `REQUIRED_PROVENANCE_KEYS` giữ đúng
7 — đó là tập **spec §0d.5** đòi (dòng 597-616) và phải giữ nguyên nghĩa đó (N1).
Ràng buộc thứ 8 là của **riêng Tool D** (MT-07) nên nó có tập riêng, hàm kiểm riêng,
và test riêng — để khi một trong hai đổi thì người đọc phân biệt được.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tool_d.measurement.provenance import (
    KHOA_XUAT_XU_TOOL_D,
    REQUIRED_PROVENANCE_KEYS,
    ImageDigestError,
    Provenance,
    cache_key,
    doc_runtime_image_digest,
    validate_provenance,
    validate_provenance_tool_d,
)

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def _prov(digest: str | None = DIGEST_A) -> Provenance:
    return Provenance(
        params_source="yaml",
        params_effective={"zss_threshold": 0.5},
        git_sha="deadbeef",
        reproducible_from_sha=True,
        data_hashes={"x": "sha256:" + "0" * 64},
        cache_mode="none",
        guard_passed=True,
        runtime_image_digest=digest,
    )


class TestHaiTapTachBiet:
    """Tập spec (7) và tập Tool D (8) phải là HAI thứ, không phải một."""

    def test_tap_spec_van_dung_bay(self) -> None:
        # Ghim lại ở đây nữa, cạnh tập Tool D — nếu ai đó nhập hai tập làm một
        # thì ca này đỏ ngay cả khi họ đã sửa L-Z40 cho khớp.
        assert len(REQUIRED_PROVENANCE_KEYS) == 7
        assert "runtime_image_digest" not in REQUIRED_PROVENANCE_KEYS

    def test_tap_tool_d_la_tap_spec_cong_dung_mot_khoa(self) -> None:
        assert KHOA_XUAT_XU_TOOL_D == REQUIRED_PROVENANCE_KEYS | {
            "runtime_image_digest"
        }
        assert len(KHOA_XUAT_XU_TOOL_D) == 8


class TestValidateToolDCoRang:
    def test_ban_ghi_du_digest_thi_hop_le(self) -> None:
        assert validate_provenance_tool_d(_prov().to_dict()) == []

    def test_thieu_han_khoa_thi_bi_tu_choi(self) -> None:
        d = _prov().to_dict()
        del d["runtime_image_digest"]
        loi = validate_provenance_tool_d(d)
        assert any("runtime_image_digest" in e for e in loi)

    def test_null_BI_TU_CHOI_chu_khong_bo_qua(self) -> None:
        """`null` chính là trạng thái khoá này nằm suốt từ MT-07 tới TD-0229.

        Nếu `null` qua được thì bản vá không vá gì cả — bản ghi thật ở
        `trial_registry.jsonl` dòng 13 vẫn sẽ "hợp lệ".
        """
        loi = validate_provenance_tool_d(_prov(None).to_dict())
        assert any("runtime_image_digest" in e for e in loi)

    @pytest.mark.parametrize("xau", ["", "UNKNOWN", "sha256:xyz", "a" * 64])
    def test_gia_tri_linh_canh_bi_tu_choi(self, xau: str) -> None:
        """N6 cấm giá trị lính canh — `""`/`"UNKNOWN"` phải đỏ như `null`."""
        loi = validate_provenance_tool_d(_prov(xau).to_dict())
        assert any("runtime_image_digest" in e for e in loi)

    def test_ban_SPEC_van_cho_qua_khi_thieu_digest(self) -> None:
        """Ranh giới hai hàm: `validate_provenance()` thi hành SPEC (7 khoá).

        Nó KHÔNG được đỏ vì thiếu khoá thứ 8 — nếu đỏ thì nó đã thôi mang nghĩa
        "tập spec đòi", đúng lớp trôi ngữ nghĩa TD-0229 sinh ra để tránh.
        """
        assert validate_provenance(_prov(None).to_dict()) == []


class TestCacheKeyCoRang:
    """Phần có răng THẬT: đổi ảnh ⇒ khoá cache đổi ⇒ không thể dùng lại kết quả."""

    def test_doi_digest_thi_doi_khoa_cache(self) -> None:
        assert cache_key(_prov(DIGEST_A)) != cache_key(_prov(DIGEST_B))

    def test_cung_digest_thi_khoa_cache_on_dinh(self) -> None:
        assert cache_key(_prov(DIGEST_A)) == cache_key(_prov(DIGEST_A))

    def test_none_khac_voi_co_digest(self) -> None:
        assert cache_key(_prov(None)) != cache_key(_prov(DIGEST_A))


class TestBoSinhFailClosed:
    """Đọc không ra ⇒ RAISE, không trả `""`/`"UNKNOWN"` (N6)."""

    def test_ngoai_docker_thi_tu_choi(self, tmp_path: Path) -> None:
        with pytest.raises(ImageDigestError, match="không chạy trong ảnh Docker"):
            doc_runtime_image_digest(
                tmp_path, dau_hieu_anh=tmp_path / "khong-ton-tai.txt"
            )

    def test_thieu_dockerfile_thi_tu_choi(self, tmp_path: Path) -> None:
        dau_hieu = tmp_path / "dau_hieu.txt"
        dau_hieu.write_text("x", encoding="utf-8")
        with pytest.raises(ImageDigestError, match="digest ghim"):
            doc_runtime_image_digest(tmp_path, dau_hieu_anh=dau_hieu)

    def test_doc_dung_digest_tu_dockerfile(self, tmp_path: Path) -> None:
        dau_hieu = tmp_path / "dau_hieu.txt"
        dau_hieu.write_text("x", encoding="utf-8")
        (tmp_path / "docker").mkdir()
        (tmp_path / "docker" / "Dockerfile").write_text(
            f"# ghi chú\nFROM freqtradeorg/freqtrade@{DIGEST_A}\nUSER root\n",
            encoding="utf-8",
        )
        assert doc_runtime_image_digest(tmp_path, dau_hieu_anh=dau_hieu) == DIGEST_A

    def test_hai_dong_FROM_thi_tu_choi(self, tmp_path: Path) -> None:
        """Mơ hồ thì DỪNG, không đoán dòng nào là dòng đúng."""
        dau_hieu = tmp_path / "dau_hieu.txt"
        dau_hieu.write_text("x", encoding="utf-8")
        (tmp_path / "docker").mkdir()
        (tmp_path / "docker" / "Dockerfile").write_text(
            f"FROM a@{DIGEST_A}\nFROM b@{DIGEST_B}\n", encoding="utf-8"
        )
        with pytest.raises(ImageDigestError, match="ĐÚNG MỘT"):
            doc_runtime_image_digest(tmp_path, dau_hieu_anh=dau_hieu)


class TestDockerfileThatVanDocDuoc:
    """Canh chính `docker/Dockerfile` của repo — không chỉ canh file dựng tay."""

    def test_dockerfile_that_co_dung_mot_dong_from_digest(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        dau_hieu = repo / "docker" / "Dockerfile"  # file chắc chắn tồn tại
        digest = doc_runtime_image_digest(repo, dau_hieu_anh=dau_hieu)
        assert digest.startswith("sha256:")
        assert len(digest) == len("sha256:") + 64
