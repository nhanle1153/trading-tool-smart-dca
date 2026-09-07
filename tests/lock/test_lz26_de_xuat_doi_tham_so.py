"""L-Z26 🔴 CRITICAL (§12d.4, OQ-13) — mọi thay đổi tham số sau live có:
nguồn kích hoạt ∈ {HEALTH, GATE_FAIL, CONDITIONAL_UNFREEZE}, chỉ số cụ thể,
giá trị cụ thể, và 1 trial đã trừ khỏi B3 (spec dòng 4868-4870).

Trước TD-0125 mã này có **0 dòng code** — luật §12c.3/§12d viết rất chặt
nhưng không máy nào thi hành, và chưa có sổ ghi đề xuất nào.

Hai lớp canh cùng một bộ luật (`kiem_de_xuat`): cửa GHI bịt lỗ "nộp đơn
sai", `check_lz26_*` bịt lỗ "sửa sổ bằng tay". Test dưới đây đòi cả hai lớp
cùng chặn một ca — nếu chúng lệch nhau thì lớp nào cũng có thể là lớp sai.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from tool_d.config.loader import DEFAULT_CONFIG_PATH, load_tool_d_config  # noqa: E402
from tool_d.ledger.audit_checks import (  # noqa: E402
    WARN_ONLY_CODES,
    check_lz26_de_xuat_doi_tham_so,
)
from tool_d.ledger.param_proposals import (  # noqa: E402
    ParamProposalError,
    hash_bao_cao,
    kiem_de_xuat,
    next_de_xuat_id,
    submit_proposal,
)
from trial_ledger_audit import EXIT_AUDIT_FAILED, run_audit  # noqa: E402

CONFIG = REPO_ROOT / DEFAULT_CONFIG_PATH
SCHEMA = REPO_ROOT / "registry/schemas/param_change_proposal.schema.json"
CFG = load_tool_d_config(CONFIG)


@pytest.fixture
def goc(tmp_path: Path) -> Path:
    """Thư mục gốc giả có sẵn một 'bản báo cáo' để đề xuất gắn vào."""
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs/bao_cao.txt").write_text("đã audit 22/22\nH-3: 0.41\n", encoding="utf-8")
    return tmp_path


def _ld(**doi) -> dict:
    d = {
        "chi_so": "H-3 ti le dong bang TIME_STOP",
        "gia_tri": 0.41,
        "dai_ky_vong": "0.05-0.25",
        "tham_so_tro_toi": "tier_b.max_hold_bars_4h",
    }
    d.update(doi)
    return d


def _dx(goc: Path, **doi) -> dict:
    d = {
        "de_xuat_id": "PC-0001",
        "created_at": "2026-10-01T00:00:00Z",
        "source": "LLM",
        "bao_cao_path": "runs/bao_cao.txt",
        "bao_cao_hash": hash_bao_cao(goc / "runs/bao_cao.txt"),
        "nguon_kich_hoat": "HEALTH",
        "tham_so_tro_toi": "tier_b.max_hold_bars_4h",
        "cap_tham_so": "A",
        "tu_khai_hang": "L1",
        "luan_diem": [_ld()],
        "gia_tri_hien_tai": 24,
        "gia_tri_de_xuat": 30,
        "trial_id": None,
        "status": "PROPOSED",
    }
    d.update(doi)
    return d


def _so_dong(path: Path) -> int:
    if not path.exists():
        return 0
    return len([x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()])


def _nop(goc: Path, **doi) -> str:
    return submit_proposal(
        de_xuat=_dx(goc, **doi),
        path=goc / "so.jsonl",
        config_path=CONFIG,
        schema_path=SCHEMA,
        goc=goc,
    )


def _kiem(goc: Path, **doi) -> list[str]:
    return kiem_de_xuat(_dx(goc, **doi), cfg=CFG, schema_path=SCHEMA, goc=goc)


class TestGhiHopLe:
    def test_de_xuat_du_dieu_kien_ghi_duoc(self, goc: Path) -> None:
        assert _nop(goc) == "PC-0001"
        assert _so_dong(goc / "so.jsonl") == 1
        assert _kiem(goc) == []

    def test_may_tu_bam_bao_cao_hash(self, goc: Path) -> None:
        """Máy tự tính, người không có đường nhập liệu (DR-014 §3)."""
        d = _dx(goc)
        d.pop("bao_cao_hash")
        d["de_xuat_id"] = ""
        submit_proposal(
            de_xuat=d, path=goc / "so.jsonl", config_path=CONFIG, schema_path=SCHEMA, goc=goc
        )
        dong = json.loads((goc / "so.jsonl").read_text(encoding="utf-8").splitlines()[0])
        assert dong["bao_cao_hash"] == hash_bao_cao(goc / "runs/bao_cao.txt")
        assert dong["de_xuat_id"] == "PC-0001"

    def test_next_de_xuat_id_lay_max(self, goc: Path) -> None:
        assert next_de_xuat_id(goc / "so.jsonl") == "PC-0001"
        _nop(goc, de_xuat_id="PC-0009")
        assert next_de_xuat_id(goc / "so.jsonl") == "PC-0010"

    def test_trung_id_bi_tu_choi(self, goc: Path) -> None:
        _nop(goc)
        with pytest.raises(ParamProposalError, match="đã có trong sổ"):
            _nop(goc)
        assert _so_dong(goc / "so.jsonl") == 1


class TestTamCaTuChoi:
    """Mỗi ca: cửa ghi raise, file không dài thêm, VÀ `kiem_de_xuat` bắt được."""

    @pytest.mark.parametrize(
        "doi",
        [
            {"nguon_kich_hoat": "THAY_KET_QUA_CHUA_DEP"},
            {"tu_khai_hang": "L9"},
            {"cap_tham_so": "D"},
            {"status": "CHAC_LA_ON"},
            {"bao_cao_hash": "khong-phai-sha256"},
            {"khoa_la_hoac": 1},
        ],
        ids=["nguon-kich-hoat", "hang", "cap", "status", "hash", "khoa-thua"],
    )
    def test_ca1_sai_schema(self, goc: Path, doi: dict) -> None:
        with pytest.raises(ParamProposalError):
            _nop(goc, **doi)
        assert _so_dong(goc / "so.jsonl") == 0
        assert _kiem(goc, **doi) != []

    def test_ca1_thieu_khoa_bat_buoc(self, goc: Path) -> None:
        d = _dx(goc)
        del d["tu_khai_hang"]
        assert kiem_de_xuat(d, cfg=CFG, schema_path=SCHEMA, goc=goc) != []

    def test_ca2_cap_c_khong_co_o_nhap(self, goc: Path) -> None:
        vp = _kiem(goc, cap_tham_so="C")
        assert any("không có ô nhập" in v for v in vp), vp
        with pytest.raises(ParamProposalError):
            _nop(goc, cap_tham_so="C")
        assert _so_dong(goc / "so.jsonl") == 0

    def test_ca2_tham_so_tier_c_bi_chan_du_khai_cap_khac(self, goc: Path) -> None:
        """Khai `cap_tham_so: A` cho một khoá thuộc tier_c cũng không lọt —
        máy đọc config thật, không nhận lời khai."""
        vp = _kiem(
            goc,
            cap_tham_so="A",
            tham_so_tro_toi="tier_c.liq_buffer_min",
            luan_diem=[_ld(tham_so_tro_toi="tier_c.liq_buffer_min")],
        )
        assert any("tier_c" in v for v in vp), vp

    def test_ca3_luan_diem_rong(self, goc: Path) -> None:
        """§12d.2 BƯỚC 3: đề xuất không có số nào → LOẠI TOÀN BỘ.
        (schema `minItems: 1` bắt trước, nên chỉ cần chặn được là đủ)"""
        with pytest.raises(ParamProposalError):
            _nop(goc, luan_diem=[])
        assert _so_dong(goc / "so.jsonl") == 0

    @pytest.mark.parametrize("gt", ["bốn mươi mốt phần trăm", None, True])
    def test_ca4_luan_diem_khong_trich_duoc_so(self, goc: Path, gt) -> None:
        """`gia_tri` phải là SỐ. `True` cũng bị loại: bool là int trong Python
        nhưng "đúng/sai" không phải một con số trích từ báo cáo."""
        vp = _kiem(goc, luan_diem=[_ld(gia_tri=gt)])
        assert vp != [], f"gia_tri={gt!r} vẫn lọt"
        with pytest.raises(ParamProposalError):
            _nop(goc, luan_diem=[_ld(gia_tri=gt)])

    def test_ca5_tham_so_khong_co_that(self, goc: Path) -> None:
        vp = _kiem(
            goc,
            tham_so_tro_toi="tier_b.khong_ton_tai",
            luan_diem=[_ld(tham_so_tro_toi="tier_b.khong_ton_tai")],
        )
        assert any("không có thật" in v for v in vp), vp

    def test_ca6_hai_luan_diem_tro_hai_tham_so_thi_LOAI(self, goc: Path) -> None:
        """🔴 Chốt chống 'hyperopt viết bằng tiếng Việt' — dễ bị nới nhất về sau.

        Đề xuất một BỘ tham số tối ưu là cùng hành vi tìm kiếm với hyperopt,
        nhưng mất phần đếm được số lần thử. Cũng là dấu hiệu L2 đội lốt L1
        (§12d.2 dòng 4832) — cạm bẫy nguy hiểm nhất vì L1 rẻ hơn nhiều.
        """
        vp = _kiem(
            goc,
            luan_diem=[_ld(), _ld(chi_so="H-2", tham_so_tro_toi="tier_b.zss_threshold")],
        )
        assert any("tìm kiếm tham số hàng loạt" in v for v in vp), vp
        with pytest.raises(ParamProposalError, match="tìm kiếm tham số hàng loạt"):
            _nop(goc, luan_diem=[_ld(), _ld(tham_so_tro_toi="tier_b.zss_threshold")])
        assert _so_dong(goc / "so.jsonl") == 0

    def test_ca6_ba_luan_diem_cung_mot_tham_so_thi_duoc(self, goc: Path) -> None:
        """Nhiều bằng chứng cho CÙNG một tham số là điều tốt, không bị phạt."""
        assert _kiem(goc, luan_diem=[_ld(), _ld(chi_so="H-1", gia_tri=0.9), _ld(gia_tri=0.5)]) == []

    def test_ca6_tham_so_tro_toi_khong_khop_luan_diem(self, goc: Path) -> None:
        vp = _kiem(goc, tham_so_tro_toi="tier_b.zss_threshold")
        assert any("không khớp" in v for v in vp), vp

    def test_ca7_bao_cao_khong_ton_tai(self, goc: Path) -> None:
        vp = _kiem(goc, bao_cao_path="runs/khong_co.txt")
        assert any("không thấy bản báo cáo" in v for v in vp), vp

    def test_ca7_bao_cao_bi_sua_sau_khi_nop(self, goc: Path) -> None:
        """Hash không khớp = báo cáo đã bị sửa, hoặc đề xuất trỏ nhầm kỳ.
        Đây là chỗ 'gắn vào ĐÚNG MỘT bản báo cáo' có răng."""
        _nop(goc)
        (goc / "runs/bao_cao.txt").write_text("H-3: 0.09\n", encoding="utf-8")
        ket_qua = check_lz26_de_xuat_doi_tham_so(
            goc / "so.jsonl", goc / "reg.jsonl", CONFIG, goc
        )
        assert ket_qua.is_fail is True
        assert "không khớp bao_cao_hash" in ket_qua.evidence

    def test_ca8_applied_ma_khong_co_trial(self, goc: Path) -> None:
        vp = _kiem(goc, status="APPLIED", trial_id=None)
        assert any("tiêu 1 trial từ B3" in v for v in vp), vp
        with pytest.raises(ParamProposalError):
            _nop(goc, status="APPLIED", trial_id=None)
        assert _so_dong(goc / "so.jsonl") == 0


class TestAuditCanhSoDaGhi:
    """Cửa ghi không phải đường DUY NHẤT tới file — sổ vẫn sửa tay được."""

    @staticmethod
    def _ghi_tay(path: Path, dx: dict) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dx, ensure_ascii=False) + "\n")

    @staticmethod
    def _trial_consumed(reg: Path, trial_id: str) -> None:
        prov = {
            "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
            "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none",
            "guard_passed": True,
        }
        with reg.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "event": "RESERVE", "trial_id": trial_id,
                "registered_at": "2026-10-02T10:00:00Z", "budget_line": "B3",
                "hypothesis_slot": "A-01", "direction": "LONG", "dataset": "CALIB",
                "param_under_test": "max_hold_bars_4h", "param_value": 30,
                "params_frozen_hash": "f", "config_hash": f"c-{trial_id}",
                "code_commit": "a", "provenance": prov, "contribution": 1, "tool_id": "D",
            }, ensure_ascii=False) + "\n")
            f.write(json.dumps({
                "event": "CONSUME", "trial_id": trial_id,
                "executed_at": "2026-10-02T11:00:00Z",
                "outcome": {"expectancy": None, "sharpe": None, "n_trades": None,
                            "max_single_loss_ratio": None},
                "verdict": "INCONCLUSIVE", "rejection_reason": None, "retest_forbidden": True,
            }, ensure_ascii=False) + "\n")

    def test_so_rong_thi_chua_do_duoc(self, goc: Path) -> None:
        so = goc / "so.jsonl"
        so.touch()
        ket_qua = check_lz26_de_xuat_doi_tham_so(so, goc / "reg.jsonl", CONFIG, goc)
        assert ket_qua.measured.status.name == "PENDING"

    def test_dong_sua_tay_vi_pham_thi_so_ban_va_chan_chay(self, goc: Path) -> None:
        so = goc / "so.jsonl"
        self._ghi_tay(so, _dx(goc, cap_tham_so="C"))
        reg = goc / "reg.jsonl"
        reg.touch()

        ket_qua = check_lz26_de_xuat_doi_tham_so(so, reg, CONFIG, goc)
        assert ket_qua.is_fail is True

        exit_code, text = run_audit(
            registry_path=reg, idea_queue_path=goc / "iq.jsonl", proposals_path=so
        )
        assert exit_code == EXIT_AUDIT_FAILED, text
        assert "L-Z26" in text

    def test_applied_khai_trial_khong_co_that_thi_so_ban(self, goc: Path) -> None:
        """Không nhận lời khai suông — cùng khuôn nối hai sổ của TD-0119b."""
        so = goc / "so.jsonl"
        self._ghi_tay(so, _dx(goc, status="APPLIED", trial_id="D-9999"))
        reg = goc / "reg.jsonl"
        reg.touch()
        ket_qua = check_lz26_de_xuat_doi_tham_so(so, reg, CONFIG, goc)
        assert ket_qua.is_fail is True
        assert "D-9999" in ket_qua.evidence

    def test_applied_voi_trial_co_that_consumed_thi_dat(self, goc: Path) -> None:
        so = goc / "so.jsonl"
        self._ghi_tay(so, _dx(goc, status="APPLIED", trial_id="D-0001"))
        reg = goc / "reg.jsonl"
        reg.touch()
        self._trial_consumed(reg, "D-0001")
        assert check_lz26_de_xuat_doi_tham_so(so, reg, CONFIG, goc).ok is True

    def test_trial_moi_RESERVE_chua_du_cho_APPLIED(self, goc: Path) -> None:
        """Đặt chỗ không phải là đã tiêu — trial phải CONSUMED."""
        so = goc / "so.jsonl"
        self._ghi_tay(so, _dx(goc, status="APPLIED", trial_id="D-0001"))
        reg = goc / "reg.jsonl"
        prov = {
            "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
            "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none",
            "guard_passed": True,
        }
        reg.write_text(json.dumps({
            "event": "RESERVE", "trial_id": "D-0001",
            "registered_at": "2026-10-02T10:00:00Z", "budget_line": "B3",
            "hypothesis_slot": "A-01", "direction": "LONG", "dataset": "CALIB",
            "param_under_test": "x", "param_value": 1, "params_frozen_hash": "f",
            "config_hash": "c", "code_commit": "a", "provenance": prov,
            "contribution": 1, "tool_id": "D",
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        assert check_lz26_de_xuat_doi_tham_so(so, reg, CONFIG, goc).is_fail is True

    def test_lz26_CHAN_CUNG_khong_phai_canh_bao(self) -> None:
        """🔴 CRITICAL — nếu ai đó về sau đưa L-Z26 vào WARN_ONLY_CODES thì
        test này phải đỏ."""
        assert "L-Z26" not in WARN_ONLY_CODES
        assert WARN_ONLY_CODES == frozenset({"L-Z17"})
