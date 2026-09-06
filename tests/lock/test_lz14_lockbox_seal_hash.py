"""L-Z14 🆕 — SHA-256 dữ liệu lockbox khớp `lockbox_seal_<n>.json` ở MỌI
lần kiểm (spec dòng 3881, DR-011).

D0-PRE chưa có dữ liệu lockbox thật (N2) — mọi ca dưới đây dùng dữ liệu
GIẢ trong `tmp_path`, kiểm CƠ CHẾ niêm phong/xác nhận, không phải nội
dung lockbox thật (đó là việc của TD-0084, sau khi gate D0-PRE đóng).
"""

from __future__ import annotations

import json
from pathlib import Path

from tool_d.lockbox.seal import (
    Seal,
    build_seal,
    discover_seals,
    verify_all_seals,
    verify_seal,
    write_seal,
)


def _make_data_files(tmp_path: Path, contents: dict[str, str]) -> dict[str, Path]:
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    paths: dict[str, Path] = {}
    for name, text in contents.items():
        p = data_dir / name
        p.write_text(text, encoding="utf-8")
        paths[name] = p
    return paths


class TestBuildVaVerifySeal:
    def test_seal_khop_du_lieu_khong_doi(self, tmp_path: Path) -> None:
        data_files = _make_data_files(tmp_path, {"btc.csv": "aaa", "eth.csv": "bbb"})
        seal = build_seal(
            segment=1,
            sealed_at="2026-01-01T00:00:00Z",
            date_range={"t0": "2023-01-01", "t1": "2023-06-01", "t2": "2023-11-01", "t3": "2024-02-01"},
            data_files=data_files,
        )
        seal_path = tmp_path / "lockbox_seal_1.json"
        write_seal(seal, seal_path)

        assert verify_seal(seal_path, tmp_path / "data") == []

    def test_lech_mot_byte_du_lieu_bi_bat(self, tmp_path: Path) -> None:
        data_files = _make_data_files(tmp_path, {"btc.csv": "aaa"})
        seal = build_seal(
            segment=1, sealed_at="2026-01-01T00:00:00Z", date_range={}, data_files=data_files
        )
        seal_path = tmp_path / "lockbox_seal_1.json"
        write_seal(seal, seal_path)

        # Sửa ĐÚNG một byte sau khi đã niêm phong.
        (tmp_path / "data" / "btc.csv").write_text("aab", encoding="utf-8")

        errors = verify_seal(seal_path, tmp_path / "data")
        assert len(errors) == 1
        assert "btc.csv" in errors[0]

    def test_file_bi_xoa_sau_niem_phong_bi_bat(self, tmp_path: Path) -> None:
        data_files = _make_data_files(tmp_path, {"btc.csv": "aaa"})
        seal = build_seal(
            segment=1, sealed_at="2026-01-01T00:00:00Z", date_range={}, data_files=data_files
        )
        seal_path = tmp_path / "lockbox_seal_1.json"
        write_seal(seal, seal_path)

        (tmp_path / "data" / "btc.csv").unlink()

        errors = verify_seal(seal_path, tmp_path / "data")
        assert len(errors) == 1
        assert "MISSING" in errors[0]

    def test_seal_khong_ton_tai(self, tmp_path: Path) -> None:
        errors = verify_seal(tmp_path / "khong_co.json", tmp_path / "data")
        assert errors != []
        assert "không đọc được" in errors[0]

    def test_seal_hong_json(self, tmp_path: Path) -> None:
        seal_path = tmp_path / "lockbox_seal_1.json"
        seal_path.write_text("{ khong phai json hop le", encoding="utf-8")
        errors = verify_seal(seal_path, tmp_path / "data")
        assert errors != []
        assert "hỏng JSON" in errors[0]

    def test_seal_thieu_khoa_data_hashes(self, tmp_path: Path) -> None:
        seal_path = tmp_path / "lockbox_seal_1.json"
        seal_path.write_text(json.dumps({"segment": 1}), encoding="utf-8")
        errors = verify_seal(seal_path, tmp_path / "data")
        assert errors != []
        assert "data_hashes" in errors[0]

    def test_khong_hash_file_ngoai_danh_sach_seal(self, tmp_path: Path) -> None:
        # Seal chỉ liệt kê btc.csv — file eth.csv thêm sau KHÔNG được kiểm,
        # KHÔNG được coi là vi phạm (seal là danh sách ĐÓNG, không phải
        # "mọi file trong thư mục").
        data_files = _make_data_files(tmp_path, {"btc.csv": "aaa"})
        seal = build_seal(
            segment=1, sealed_at="2026-01-01T00:00:00Z", date_range={}, data_files=data_files
        )
        seal_path = tmp_path / "lockbox_seal_1.json"
        write_seal(seal, seal_path)

        (tmp_path / "data" / "eth.csv").write_text("moi them", encoding="utf-8")

        assert verify_seal(seal_path, tmp_path / "data") == []


class TestGhiSealBatBien:
    def test_ghi_de_seal_da_ton_tai_bi_tu_choi(self, tmp_path: Path) -> None:
        seal_path = tmp_path / "lockbox_seal_1.json"
        seal1 = build_seal(segment=1, sealed_at="2026-01-01T00:00:00Z", date_range={}, data_files={})
        write_seal(seal1, seal_path)

        seal2 = build_seal(segment=1, sealed_at="2026-06-01T00:00:00Z", date_range={}, data_files={})
        try:
            write_seal(seal2, seal_path)
            assert False, "phải raise FileExistsError"
        except FileExistsError:
            pass

    def test_gia_han_tao_file_moi_khong_dung_den_file_cu(self, tmp_path: Path) -> None:
        data1 = _make_data_files(tmp_path, {"a.csv": "1"})
        seal1 = build_seal(segment=1, sealed_at="2026-01-01T00:00:00Z", date_range={}, data_files=data1)
        path1 = tmp_path / "lockbox_seal_1.json"
        write_seal(seal1, path1)
        noi_dung_goc = path1.read_text(encoding="utf-8")

        data2 = _make_data_files(tmp_path, {"b.csv": "2"})
        seal2 = build_seal(segment=2, sealed_at="2026-06-01T00:00:00Z", date_range={}, data_files=data2)
        path2 = tmp_path / "lockbox_seal_2.json"
        write_seal(seal2, path2)

        assert path1.read_text(encoding="utf-8") == noi_dung_goc  # file cũ KHÔNG đổi
        assert verify_seal(path1, tmp_path / "data") == []
        assert verify_seal(path2, tmp_path / "data") == []

    def test_hai_seal_khac_doan_co_data_hashes_khac_nhau(self, tmp_path: Path) -> None:
        # Nội dung dữ liệu khác nhau ở mỗi đoạn -> hash khác nhau -> file
        # seal khác nhau. Đây là cơ sở để access_log.py phân biệt "khác
        # đoạn" bằng seal_file_hash (L-Z13).
        data1 = _make_data_files(tmp_path, {"a.csv": "goc"})
        seal1 = build_seal(segment=1, sealed_at="t1", date_range={}, data_files=data1)
        (tmp_path / "data" / "a.csv").write_text("gia_han", encoding="utf-8")
        data2 = _make_data_files(tmp_path, {"a.csv": "gia_han"})
        seal2 = build_seal(segment=2, sealed_at="t2", date_range={}, data_files=data2)

        assert seal1.data_hashes != seal2.data_hashes


class TestDiscoverVaVerifyAllSeals:
    """H17 (spec dòng 4348) — kiểm TOÀN BỘ đoạn niêm phong hiện có, dùng
    chung cho E4 `--verify-seal` (TD-0071) và sẽ dùng lại ở đầu E1/E2/E3
    (TD-0072)."""

    def test_thu_muc_lockbox_chua_ton_tai_khong_loi(self, tmp_path: Path) -> None:
        # D0-PRE: chưa niêm phong đoạn nào — "không có gì để xác nhận"
        # không phải lỗi, để pipeline chạy được TRƯỚC TD-0084.
        assert discover_seals(tmp_path / "khong_ton_tai") == []
        assert verify_all_seals(tmp_path / "khong_ton_tai", tmp_path / "data") == []

    def test_thu_muc_lockbox_rong_khong_loi(self, tmp_path: Path) -> None:
        lockbox_dir = tmp_path / "lockbox"
        lockbox_dir.mkdir()
        assert discover_seals(lockbox_dir) == []
        assert verify_all_seals(lockbox_dir, tmp_path / "data") == []

    def test_mot_seal_hop_le_pass(self, tmp_path: Path) -> None:
        lockbox_dir = tmp_path / "lockbox"
        data_files = _make_data_files(tmp_path, {"a.csv": "aaa"})
        seal = build_seal(segment=1, sealed_at="t1", date_range={}, data_files=data_files)
        write_seal(seal, lockbox_dir / "lockbox_seal_1.json")

        assert discover_seals(lockbox_dir) == [lockbox_dir / "lockbox_seal_1.json"]
        assert verify_all_seals(lockbox_dir, tmp_path / "data") == []

    def test_hai_seal_mot_dung_mot_sai_bat_dung_doan_sai(self, tmp_path: Path) -> None:
        lockbox_dir = tmp_path / "lockbox"
        data_files = _make_data_files(tmp_path, {"a.csv": "aaa", "b.csv": "bbb"})
        seal1 = build_seal(
            segment=1, sealed_at="t1", date_range={}, data_files={"a.csv": data_files["a.csv"]}
        )
        write_seal(seal1, lockbox_dir / "lockbox_seal_1.json")
        seal2 = build_seal(
            segment=2, sealed_at="t2", date_range={}, data_files={"b.csv": data_files["b.csv"]}
        )
        write_seal(seal2, lockbox_dir / "lockbox_seal_2.json")

        # Làm hỏng dữ liệu của ĐÚNG đoạn 2, sau khi cả hai đã niêm phong.
        (tmp_path / "data" / "b.csv").write_text("da_bi_sua", encoding="utf-8")

        errors = verify_all_seals(lockbox_dir, tmp_path / "data")
        assert len(errors) == 1
        assert errors[0].startswith("lockbox_seal_2.json:")


class TestSealToDict:
    def test_to_dict_giu_nguyen_date_range(self) -> None:
        seal = Seal(
            segment=1,
            sealed_at="2026-01-01T00:00:00Z",
            date_range={"t0": "2023-01-01"},
            data_hashes={"a.csv": "deadbeef"},
        )
        d = seal.to_dict()
        assert d["segment"] == 1
        assert d["date_range"] == {"t0": "2023-01-01"}
        assert d["data_hashes"] == {"a.csv": "deadbeef"}
