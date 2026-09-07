"""TD-0150 — cửa ghi sổ trial phải TỰ ĐỐI CHIẾU SCHEMA trước khi append.

Phiên `trading-tool-smart-dca-91` phát hiện khi làm TD-0149; phiên này tái
hiện độc lập trước khi nhận việc. Chủ dự án duyệt siết 08/09/2026.

**Khoảng hở:** `TrialLedger` không đối chiếu đầu vào với schema của chính
nó. Hai ví dụ ĐỘC LẬP:

  • `seal_path` — schema đòi mẫu `^runs/.+/metrics\\.seal$`;
    `seal()` nhận mọi chuỗi.
  • `verdict`   — schema chỉ cho `KEPT|REJECTED|INCONCLUSIVE`;
    `consume()` nhận mọi chuỗi.

Hai TRƯỜNG khác nhau, cùng một hiện tượng → đây là tính chất chung của cửa
ghi, không phải hai chỗ sót lẻ. Vì vậy chỗ vá là **`_append()`** — điểm
nghẽn DUY NHẤT mà mọi sự kiện phải đi qua — chứ không phải vá từng hàm.
Vá ở `_append()` thì cửa ghi nào viết SAU NÀY cũng tự động được kiểm, không
phụ thuộc ai nhớ; vá từng hàm là mời lỗi thứ ba xuất hiện ở hàm thứ bảy.

🔴 **Vì sao phải kiểm TRƯỚC khi ghi, không phải sau:** sổ append-only không
có đường lùi (MT-01). Một dòng sai đã ghi là sai vĩnh viễn; báo lỗi sau khi
ghi chỉ cho ta biết mình vừa làm hỏng sổ chứ không sửa được gì. Cùng khuôn
`submit_idea()` (TD-0124) và `submit_proposal()` (TD-0125).

Cùng họ với lỗ TD-0149 vừa vá, nhưng **ngược chiều**: lỗ kia là *schema
không biết khoá mới*, lỗ này là *cửa ghi không biết ràng buộc của schema*.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from tool_d.ledger.registry import (
    DEFAULT_REGISTRY_PATH,
    SchemaViolationError,
    TrialLedger,
)

GOC = Path(__file__).resolve().parents[2]
SCHEMA_PATH = GOC / "registry/schemas/trial_event.schema.json"


def _prov() -> dict[str, Any]:
    return {
        "params_source": "yaml",
        "params_effective": {},
        "git_sha": "a" * 40,
        "reproducible_from_sha": True,
        "data_hashes": {},
        "cache_mode": "none",
        "guard_passed": True,
    }


def _reserve(so: TrialLedger, **thay) -> str:
    kw: dict[str, Any] = dict(
        n_dang_ky=114,
        budget_line="B1",
        hypothesis_slot="A-01",
        direction="LONG",
        dataset="CALIB",
        param_under_test="zss_threshold",
        param_value=0.55,
        params_frozen_hash="f" * 8,
        config_hash="c" * 8,
        code_commit="d" * 8,
        provenance=_prov(),
        contribution=1,
    )
    kw.update(thay)
    return so.reserve(**kw)


def _outcome() -> dict[str, Any]:
    """Đúng bốn khoá schema đòi, không hơn (`additionalProperties: false`).

    📌 Bản đầu của test này truyền `{"pnl_abs": 1.0}` và làm ca "đường đúng"
    ĐỎ — tôi suýt báo đó là bug của cửa ghi. Đọc schema mới thấy dữ liệu
    test của mình sai. Ghi lại vì đây đúng loại nhầm mà cả hai phiên cùng
    mắc trong ngày: thấy kết quả hợp giả thuyết thì dễ kết luận vội.
    """
    return {
        "expectancy": 0.12,
        "sharpe": 1.1,
        "n_trades": 40,
        "max_single_loss_ratio": 0.3,
    }


def _so_dong(p: Path) -> int:
    if not p.exists():
        return 0
    return len([d for d in p.read_text(encoding="utf-8").splitlines() if d.strip()])


# ── Cửa ghi TỪ CHỐI dòng không hợp lệ, và KHÔNG ghi gì ────────────────


class TestTuChoiTruocKhiGhi:
    def test_seal_path_sai_mau_thi_raise_va_so_khong_dai_them(self, tmp_path: Path) -> None:
        p = tmp_path / "r.jsonl"
        so = TrialLedger(p)
        t = _reserve(so)
        truoc = _so_dong(p)

        with pytest.raises(SchemaViolationError):
            so.seal(t, seal_path="duong/dan/bat/ky.txt")

        assert _so_dong(p) == truoc  # 🔴 không có đường lùi -> không được ghi

    def test_verdict_ngoai_enum_thi_raise_va_so_khong_dai_them(self, tmp_path: Path) -> None:
        """Trường KHÁC, cùng cửa — chứng minh vá ở điểm nghẽn có tác dụng
        chung, không phải vá riêng `seal_path`."""
        p = tmp_path / "r.jsonl"
        so = TrialLedger(p)
        t = _reserve(so)
        so.seal(t, seal_path="runs/2026-09-08/metrics.seal")
        truoc = _so_dong(p)

        with pytest.raises(SchemaViolationError):
            so.consume(t, outcome=_outcome(), verdict="BIA-DAT", retest_forbidden=False)

        assert _so_dong(p) == truoc

    def test_dataset_ngoai_enum_ngay_tu_reserve_thi_raise(self, tmp_path: Path) -> None:
        """Trường thứ BA, ở cửa ghi ĐẦU TIÊN — nếu chỉ vá `seal`/`consume`
        thì ca này vẫn lọt."""
        p = tmp_path / "r.jsonl"
        so = TrialLedger(p)

        with pytest.raises(SchemaViolationError):
            _reserve(so, dataset="TAP-BIA")

        assert _so_dong(p) == 0

    def test_provenance_thieu_khoa_thi_raise(self, tmp_path: Path) -> None:
        """L-Z40 đòi đủ 7+1 khoá xuất xứ. Thiếu một khoá là dòng không tái
        lập được — không được vào sổ."""
        p = tmp_path / "r.jsonl"
        so = TrialLedger(p)
        thieu = _prov()
        del thieu["git_sha"]

        with pytest.raises(SchemaViolationError):
            _reserve(so, provenance=thieu)

        assert _so_dong(p) == 0


# ── Đường đúng KHÔNG bị chặn nhầm ─────────────────────────────────────


class TestKhongChanNhamDuongDung:
    def test_du_nam_loai_su_kien_hop_le_van_ghi_binh_thuong(self, tmp_path: Path) -> None:
        p = tmp_path / "r.jsonl"
        so = TrialLedger(p)

        t = _reserve(so)
        so.seal(t, seal_path="runs/2026-09-08/metrics.seal")
        so.consume(t, outcome=_outcome(), verdict="KEPT", retest_forbidden=True)
        so.mark_contaminated(t, reason="tham số đổi giữa chừng")

        t2 = _reserve(so)
        so.refund(t2, cause_machine="exit_code=86")

        loai = {json.loads(d)["event"] for d in p.read_text(encoding="utf-8").splitlines() if d.strip()}
        assert loai == {"RESERVE", "SEAL", "CONSUME", "REFUND", "CONTAMINATE"}

    def test_so_that_cua_repo_van_ghi_tiep_duoc(self) -> None:
        """Sổ THẬT 12 dòng đang hợp lệ — siết cửa ghi không được làm nó
        thành sổ không ghi tiếp được."""
        assert DEFAULT_REGISTRY_PATH.exists()
        import jsonschema

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        dong = [
            json.loads(d)
            for d in DEFAULT_REGISTRY_PATH.read_text(encoding="utf-8").splitlines()
            if d.strip()
        ]
        for e in dong:
            jsonschema.validate(e, schema)


# ── Điểm nghẽn phải là DUY NHẤT ───────────────────────────────────────


class TestDiemNghenDuyNhat:
    def test_khong_cua_ghi_nao_di_vong_qua_append(self) -> None:
        """Quét AST `registry.py`: mọi lần ghi ra file đều phải đi qua
        `self._append(...)`. Nếu có hàm nào tự `write`/`open(...,'a')` thì
        phép kiểm schema ở `_append()` không phủ nó, và khoảng hở này sẽ
        quay lại ở đúng chỗ đó."""
        nguon = (GOC / "src/tool_d/ledger/registry.py").read_text(encoding="utf-8")
        cay = ast.parse(nguon)

        ghi_thang: list[str] = []
        for node in ast.walk(cay):
            if not isinstance(node, ast.FunctionDef) or node.name == "_append":
                continue
            for con in ast.walk(node):
                if isinstance(con, ast.Call):
                    ten = getattr(con.func, "attr", "")
                    if ten in ("write", "write_text", "writelines"):
                        ghi_thang.append(f"{node.name}:{con.lineno}")

        assert ghi_thang == [], (
            f"Có chỗ ghi file KHÔNG qua _append(): {ghi_thang} — phép kiểm "
            "schema đặt ở _append() sẽ không phủ được chúng"
        )

    def test_schema_hong_thi_cua_ghi_TU_CHOI_chu_khong_bo_qua(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fail-closed cho chính phép kiểm: schema không đọc được thì cửa
        ghi phải TỪ CHỐI, không được lặng lẽ bỏ qua bước kiểm rồi ghi tiếp
        — bỏ qua nghĩa là mất lớp canh đúng lúc nó hỏng."""
        import tool_d.ledger.registry as reg

        monkeypatch.setattr(reg, "TRIAL_EVENT_SCHEMA_PATH", tmp_path / "khong-ton-tai.json")
        reg._doc_schema.cache_clear()

        p = tmp_path / "r.jsonl"
        so = TrialLedger(p)
        with pytest.raises(SchemaViolationError):
            _reserve(so)

        assert _so_dong(p) == 0
        reg._doc_schema.cache_clear()
