"""L-Z13 🆕 — sổ truy cập lockbox (spec dòng 3876-3880, §9c.6):

    lockbox_access.log có ĐÚNG 0 bản ghi cho tới sau D9; 🔴 v7 sửa: sau
    đó ĐÚNG 1 bản ghi CHO MỖI ĐOẠN NIÊM PHONG, tối đa 3 đoạn (1 gốc + 2
    gia hạn INCONCLUSIVE, DR-011). Mỗi bản ghi phải trỏ tới một
    `lockbox_seal_<n>.json` KHÁC NHAU với hash khác nhau. Hai bản ghi
    cùng seal = vi phạm.

D0-PRE chưa có lockbox thật (N2) — mọi ca dùng seal GIẢ trong `tmp_path`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tool_d.lockbox.access_log import (
    MAX_SEGMENTS,
    append_access_record,
    make_access_record,
    read_access_log,
    validate_access_log,
    validate_before_d9,
)


def _write_seal(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


class TestTruocD9DungKhongBanGhi:
    def test_so_rong_hop_le(self) -> None:
        assert validate_before_d9([]) == []

    def test_co_ban_ghi_truoc_d9_vi_pham(self) -> None:
        errors = validate_before_d9([{"seal_path": "x", "seal_file_hash": "y"}])
        assert errors != []

    def test_file_chua_ton_tai_doc_thanh_so_rong(self, tmp_path: Path) -> None:
        assert read_access_log(tmp_path / "khong_co.jsonl") == []


class TestSauD9ToiDaBaDoanKhongTrung:
    def test_dung_mot_doan_hop_le(self, tmp_path: Path) -> None:
        seal = _write_seal(tmp_path / "lockbox_seal_1.json", "noi_dung_seal_1")
        rec = make_access_record(
            reason="Xác nhận cuối", config_hash="cfg-abc", seal_path=seal, accessed_at="2026-01-01T00:00:00Z"
        )
        assert validate_access_log([rec.to_dict()]) == []

    def test_ba_doan_khac_seal_hop_le(self, tmp_path: Path) -> None:
        records = []
        for i in range(1, MAX_SEGMENTS + 1):
            seal = _write_seal(tmp_path / f"lockbox_seal_{i}.json", f"noi_dung_{i}")
            rec = make_access_record(
                reason=f"đoạn {i}", config_hash=f"cfg-{i}", seal_path=seal, accessed_at=f"2026-0{i}-01T00:00:00Z"
            )
            records.append(rec.to_dict())
        assert validate_access_log(records) == []

    def test_bon_doan_vuot_tran_vi_pham(self, tmp_path: Path) -> None:
        records = []
        for i in range(1, MAX_SEGMENTS + 2):  # 4 đoạn, spec chỉ cho tối đa 3
            seal = _write_seal(tmp_path / f"lockbox_seal_{i}.json", f"noi_dung_{i}")
            rec = make_access_record(
                reason=f"đoạn {i}", config_hash=f"cfg-{i}", seal_path=seal, accessed_at=f"2026-{i:02d}-01T00:00:00Z"
            )
            records.append(rec.to_dict())
        errors = validate_access_log(records)
        assert errors != []
        assert "tối đa" in errors[0]

    def test_hai_ban_ghi_cung_seal_path_vi_pham(self, tmp_path: Path) -> None:
        seal = _write_seal(tmp_path / "lockbox_seal_1.json", "noi_dung_1")
        rec1 = make_access_record(
            reason="lần 1", config_hash="cfg-1", seal_path=seal, accessed_at="2026-01-01T00:00:00Z"
        ).to_dict()
        rec2 = make_access_record(
            reason="lần 2 (không được phép)", config_hash="cfg-2", seal_path=seal, accessed_at="2026-02-01T00:00:00Z"
        ).to_dict()
        errors = validate_access_log([rec1, rec2])
        assert errors != []
        assert "cùng seal_path" in errors[0] or "cùng seal_path" in "".join(errors)

    def test_hai_ban_ghi_cung_hash_khac_path_van_bi_bat(self, tmp_path: Path) -> None:
        # Hai đường dẫn khác nhau nhưng NỘI DUNG seal giống hệt nhau (hash
        # trùng) — spec đòi "hash khác nhau", không chỉ "path khác nhau".
        seal_a = _write_seal(tmp_path / "lockbox_seal_1.json", "noi_dung_giong_het")
        seal_b = _write_seal(tmp_path / "ban_sao.json", "noi_dung_giong_het")
        rec1 = make_access_record(
            reason="lần 1", config_hash="cfg-1", seal_path=seal_a, accessed_at="2026-01-01T00:00:00Z"
        ).to_dict()
        rec2 = make_access_record(
            reason="lần 2", config_hash="cfg-2", seal_path=seal_b, accessed_at="2026-02-01T00:00:00Z"
        ).to_dict()
        errors = validate_access_log([rec1, rec2])
        assert errors != []
        assert any("seal_file_hash" in e for e in errors)


class TestAppendAccessRecordFailClosed:
    def test_ghi_dung_ba_lan_thanh_cong(self, tmp_path: Path) -> None:
        log_path = tmp_path / "lockbox_access.log"
        for i in range(1, MAX_SEGMENTS + 1):
            seal = _write_seal(tmp_path / f"lockbox_seal_{i}.json", f"noi_dung_{i}")
            rec = make_access_record(
                reason=f"đoạn {i}", config_hash=f"cfg-{i}", seal_path=seal, accessed_at=f"2026-0{i}-01T00:00:00Z"
            )
            append_access_record(log_path, rec)
        assert len(read_access_log(log_path)) == MAX_SEGMENTS

    def test_ghi_lan_thu_tu_bi_tu_choi(self, tmp_path: Path) -> None:
        log_path = tmp_path / "lockbox_access.log"
        for i in range(1, MAX_SEGMENTS + 1):
            seal = _write_seal(tmp_path / f"lockbox_seal_{i}.json", f"noi_dung_{i}")
            append_access_record(
                log_path,
                make_access_record(
                    reason=f"đoạn {i}", config_hash=f"cfg-{i}", seal_path=seal, accessed_at=f"2026-0{i}-01T00:00:00Z"
                ),
            )

        seal_4 = _write_seal(tmp_path / "lockbox_seal_4.json", "noi_dung_4")
        rec_4 = make_access_record(
            reason="đoạn 4 (cấm)", config_hash="cfg-4", seal_path=seal_4, accessed_at="2026-04-01T00:00:00Z"
        )
        with pytest.raises(ValueError):
            append_access_record(log_path, rec_4)
        # Ghi thất bại KHÔNG được để lại dấu vết trong sổ.
        assert len(read_access_log(log_path)) == MAX_SEGMENTS

    def test_ghi_lai_cung_seal_bi_tu_choi(self, tmp_path: Path) -> None:
        log_path = tmp_path / "lockbox_access.log"
        seal = _write_seal(tmp_path / "lockbox_seal_1.json", "noi_dung_1")
        rec1 = make_access_record(
            reason="lần 1", config_hash="cfg-1", seal_path=seal, accessed_at="2026-01-01T00:00:00Z"
        )
        append_access_record(log_path, rec1)

        rec2 = make_access_record(
            reason="lần 2 (cấm)", config_hash="cfg-2", seal_path=seal, accessed_at="2026-02-01T00:00:00Z"
        )
        with pytest.raises(ValueError):
            append_access_record(log_path, rec2)
        assert len(read_access_log(log_path)) == 1

    def test_so_dung_dinh_dang_jsonl_doc_lai_dung(self, tmp_path: Path) -> None:
        log_path = tmp_path / "lockbox_access.log"
        seal = _write_seal(tmp_path / "lockbox_seal_1.json", "noi_dung_1")
        rec = make_access_record(
            reason="Xác nhận cuối, DSR-adjusted expectancy đạt ngưỡng",
            config_hash="cfg-xyz",
            seal_path=seal,
            accessed_at="2026-01-01T00:00:00Z",
        )
        append_access_record(log_path, rec)

        ghi_lai = read_access_log(log_path)
        assert ghi_lai == [rec.to_dict()]


class TestMakeAccessRecordHashNoiDungSeal:
    def test_hai_seal_noi_dung_khac_nhau_ra_hash_khac_nhau(self, tmp_path: Path) -> None:
        seal_a = _write_seal(tmp_path / "a.json", "noi_dung_a")
        seal_b = _write_seal(tmp_path / "b.json", "noi_dung_b")
        rec_a = make_access_record(reason="x", config_hash="c", seal_path=seal_a)
        rec_b = make_access_record(reason="x", config_hash="c", seal_path=seal_b)
        assert rec_a.seal_file_hash != rec_b.seal_file_hash

    def test_doc_lai_seal_giong_het_ra_hash_giong_het(self, tmp_path: Path) -> None:
        seal = _write_seal(tmp_path / "a.json", "noi_dung_khong_doi")
        rec1 = make_access_record(reason="x", config_hash="c1", seal_path=seal)
        rec2 = make_access_record(reason="y", config_hash="c2", seal_path=seal)
        assert rec1.seal_file_hash == rec2.seal_file_hash
