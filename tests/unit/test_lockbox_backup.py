"""TD-0085 — src/tool_d/lockbox/backup.py: sao chép seal + data ra ngoài
git, dùng `tmp_path` (không đụng lockbox thật của repo)."""

from __future__ import annotations

import pytest

from tool_d.lockbox.backup import backup_lockbox
from tool_d.lockbox.seal import verify_seal


def _fake_lockbox(tmp_path, name="lockbox"):
    src = tmp_path / name
    (src / "data" / "futures").mkdir(parents=True)
    (src / "data" / "futures" / "BTC_USDT_USDT-1d-futures.feather").write_bytes(b"fake-ohlcv")
    seal_path = src / "lockbox_seal_1.json"
    from tool_d.lockbox.seal import build_seal, write_seal

    seal = build_seal(
        segment=1,
        sealed_at="2026-09-06T00:00:00.000000Z",
        date_range={"T2": "2026-01-29", "T3": "2026-09-06"},
        data_files={"BTC_USDT_USDT-1d-futures.feather": src / "data" / "futures" / "BTC_USDT_USDT-1d-futures.feather"},
    )
    write_seal(seal, seal_path)
    (src / "lockbox_access.log").write_text("khong duoc backup\n", encoding="utf-8")
    return src


class TestBackupLockbox:
    def test_khong_co_lockbox_nguon_thi_raise(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            backup_lockbox(source_lockbox_dir=tmp_path / "khong_ton_tai", dest_dir=tmp_path / "dest")

    def test_backup_roi_khoi_phuc_thi_verify_seal_pass(self, tmp_path) -> None:
        src = _fake_lockbox(tmp_path, "lockbox")
        dest_dir = tmp_path / "backup_dest"

        dest_lockbox = backup_lockbox(source_lockbox_dir=src, dest_dir=dest_dir)

        assert (dest_lockbox / "lockbox_seal_1.json").exists()
        assert (dest_lockbox / "data" / "futures" / "BTC_USDT_USDT-1d-futures.feather").exists()

        # "khôi phục thật" = verify_seal chạy trên chính bản backup, coi
        # backup như một bản khôi phục vào một thư mục khác — đúng kịch
        # bản mất ổ đĩa gốc rồi phục hồi từ backup.
        errors = verify_seal(dest_lockbox / "lockbox_seal_1.json", dest_lockbox / "data" / "futures")
        assert errors == []

    def test_khong_sao_chep_access_log(self, tmp_path) -> None:
        src = _fake_lockbox(tmp_path, "lockbox")
        dest_lockbox = backup_lockbox(source_lockbox_dir=src, dest_dir=tmp_path / "backup_dest")
        assert not (dest_lockbox / "lockbox_access.log").exists()

    def test_ghi_de_ban_backup_cu(self, tmp_path) -> None:
        src = _fake_lockbox(tmp_path, "lockbox")
        dest_dir = tmp_path / "backup_dest"
        backup_lockbox(source_lockbox_dir=src, dest_dir=dest_dir)

        # đổi dữ liệu nguồn rồi backup lại — bản backup phải phản ánh MỚI
        (src / "data" / "futures" / "extra.feather").write_bytes(b"them-file-moi")
        dest_lockbox = backup_lockbox(source_lockbox_dir=src, dest_dir=dest_dir)
        assert (dest_lockbox / "data" / "futures" / "extra.feather").exists()

    def test_khong_co_thu_muc_data_van_backup_duoc_seal(self, tmp_path) -> None:
        # Trường hợp lockbox chỉ có seal, chưa từng có data/ (VD chạy trên
        # máy khác, hoặc D0-PRE trước TD-0084) — không raise.
        src = tmp_path / "lockbox_khong_data"
        src.mkdir()
        (src / "lockbox_seal_1.json").write_text('{"segment": 1}', encoding="utf-8")
        dest_lockbox = backup_lockbox(source_lockbox_dir=src, dest_dir=tmp_path / "dest2")
        assert (dest_lockbox / "lockbox_seal_1.json").exists()
        assert not (dest_lockbox / "data").exists()
