"""TD-0146 — bản ghi fold: đủ xuất xứ (`L-Z40`) + ba trạng thái (`L-Z41`)
+ thi hành sàn số lệnh của DR-D3-01 §5.2.

🔴 **Điểm khác biệt quan trọng nhất của bộ test này so với
`tests/unit/test_registry_schemas.py`:** ở đây schema được đối chiếu với
**ĐẦU RA THẬT của `build_fold_record()`**, không phải với fixture gõ tay.

Vì sao điều đó đáng một dòng chú thích: schema của project đặt
`additionalProperties: false`. Thêm một khoá vào code mà quên thêm vào
schema thì bộ test kiểu-fixture **không bắt được** — fixture và schema do
cùng một người sửa cùng lúc nên chúng luôn khớp nhau, và cùng lệch khỏi
code. Lỗi chỉ nổ đúng lần ghi thật đầu tiên. Phiên song song vừa dính
đúng lỗi đó với `trial_event.schema.json`: **735 test xanh vẫn không bắt
được**. `TestSchemaSoiDauRaThat` tồn tại để bịt đúng khe này.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import jsonschema
import pytest

from tool_d.measurement.provenance import Provenance
from tool_d.measurement.tri_state import Measured
from tool_d.wfo.fold_record import FoldRecordError, build_fold_record, validate_fold_record
from tool_d.wfo.folds import Fold

REPO_ROOT = Path(__file__).resolve().parents[2]
FOLD_RECORD_SCHEMA = json.loads(
    (REPO_ROOT / "registry/schemas/fold_record.schema.json").read_text(encoding="utf-8")
)

FOLD = Fold(
    chi_so=1,
    train_start=date(2025, 6, 12),
    train_end=date(2025, 9, 4),
    test_start=date(2025, 9, 4),
    test_end=date(2025, 10, 23),
)


def _prov(**thay_doi) -> Provenance:
    mac_dinh = dict(
        params_source="yaml",
        params_effective={"tier_b": {"zss_threshold": 0.5}},
        git_sha="a" * 40,
        reproducible_from_sha=True,
        data_hashes={"BTCUSDT-1h.feather": "b" * 64},
        cache_mode="none",
        guard_passed=True,
        runtime_image_digest="sha256:" + "c" * 64,
    )
    mac_dinh.update(thay_doi)
    return Provenance(**mac_dinh)  # type: ignore[arg-type]


def _ban_ghi(*, so_lenh: int = 40, san: int = 30, **thay_doi):
    chi_so = thay_doi.pop(
        "chi_so_do",
        {
            "expectancy_pnl_abs": Measured.ok(12.34),
            "sharpe_r_realized": Measured.pending("chưa chạy phép đo"),
        },
    )
    return build_fold_record(
        fold=thay_doi.pop("fold", FOLD),
        provenance=thay_doi.pop("provenance", _prov()),
        so_lenh=so_lenh,
        san_lenh_moi_fold=san,
        chi_so_do=chi_so,
    )


class TestSchemaSoiDauRaThat:
    """🔴 Đối chiếu ĐẦU RA THẬT với schema — không dùng fixture."""

    def test_ban_ghi_du_lenh_khop_schema(self) -> None:
        jsonschema.validate(_ban_ghi(so_lenh=40), FOLD_RECORD_SCHEMA)

    def test_ban_ghi_mong_khop_schema(self) -> None:
        jsonschema.validate(_ban_ghi(so_lenh=12), FOLD_RECORD_SCHEMA)

    def test_ban_ghi_di_qua_duoc_json_round_trip(self) -> None:
        # Bản ghi phải serialise được thật, không chỉ "trông giống dict".
        d = _ban_ghi()
        jsonschema.validate(json.loads(json.dumps(d, ensure_ascii=False)), FOLD_RECORD_SCHEMA)

    def test_schema_BAT_khoa_la(self) -> None:
        """Đối chứng: nếu `additionalProperties: false` bị nới ở đâu đó
        thì ca này xanh sai và mọi ca trên mất giá trị."""
        d = {**_ban_ghi(), "khoa_khong_khai_bao": 1}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(d, FOLD_RECORD_SCHEMA)

    def test_schema_BAT_value_khac_null_khi_chua_do(self) -> None:
        d = _ban_ghi()
        d["chi_so"]["sharpe_r_realized"]["value"] = 0.0  # bịa 0.0 khi pending
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(d, FOLD_RECORD_SCHEMA)


class TestSanLenhThiHanhDRD301:
    def test_du_lenh_thi_giu_nguyen_chi_so_da_do(self) -> None:
        d = _ban_ghi(so_lenh=30, san=30)  # đúng bằng sàn -> vẫn đủ
        assert d["du_lenh"] is True
        assert d["chi_so"]["expectancy_pnl_abs"] == {
            "status": "ok",
            "value": 12.34,
            "note": None,
        }

    def test_mong_thi_EP_moi_chi_so_thanh_unreadable(self) -> None:
        """🔴 Ép, không phải cảnh báo: một con số đã nằm trong bảng thì sẽ
        được đọc, bất kể chú thích bên cạnh nói gì."""
        d = _ban_ghi(so_lenh=29, san=30)
        assert d["du_lenh"] is False
        for ten, m in d["chi_so"].items():
            assert m["status"] == "unreadable", ten
            assert m["value"] is None, ten
            assert "quá mỏng" in m["note"] and "29" in m["note"] and "30" in m["note"]

    def test_mong_thi_KHONG_gop_thanh_pending(self) -> None:
        """`pending` = chưa chạy phép đo. `unreadable` = ĐÃ chạy nhưng mẫu
        quá mỏng. Gộp hai cái sẽ mất đúng thông tin mà phán quyết cuối của
        D3 cần (DR-D3-01 §5.3)."""
        assert {m["status"] for m in _ban_ghi(so_lenh=5)["chi_so"].values()} == {"unreadable"}

    def test_mong_thi_KHONG_ghi_0_hay_gia_tri_linh_canh(self) -> None:
        d = _ban_ghi(so_lenh=5)
        assert all(m["value"] is None for m in d["chi_so"].values())
        assert "0.0" not in json.dumps(d["chi_so"])
        assert "UNKNOWN" not in json.dumps(d["chi_so"])

    def test_fold_0_lenh_van_dung_duoc_ban_ghi(self) -> None:
        # 0 lệnh là kết quả hợp lệ, không phải lỗi — nhưng mọi chỉ số
        # unreadable.
        d = _ban_ghi(so_lenh=0)
        assert d["so_lenh"] == 0 and d["du_lenh"] is False
        jsonschema.validate(d, FOLD_RECORD_SCHEMA)


class TestDungBanGhiFailClosed:
    def test_so_lenh_am_thi_raise(self) -> None:
        with pytest.raises(FoldRecordError, match="so_lenh"):
            _ban_ghi(so_lenh=-1)

    def test_san_duoi_1_thi_raise(self) -> None:
        with pytest.raises(FoldRecordError, match="san_lenh_moi_fold"):
            _ban_ghi(san=0)

    def test_khong_co_chi_so_nao_thi_raise(self) -> None:
        """Bản ghi rỗng đi qua mọi phép kiểm mà không chứng minh điều gì —
        đúng bẫy PASS RỖNG."""
        with pytest.raises(FoldRecordError, match="PASS RỖNG"):
            _ban_ghi(chi_so_do={})


class TestValidateFoldRecord:
    def test_ban_ghi_dung_thi_khong_loi(self) -> None:
        assert validate_fold_record(_ban_ghi()) == []

    def test_thieu_provenance_thi_bao_loi(self) -> None:
        d = _ban_ghi()
        del d["provenance"]
        assert any("provenance" in e for e in validate_fold_record(d))

    def test_provenance_hong_thi_dung_lai_LZ40_khong_viet_lai_luat(self) -> None:
        # params_source != "yaml" là luật của L-Z40 — nếu module này chép
        # lại luật thay vì gọi validate_provenance() thì hai bản sẽ trôi
        # lệch nhau theo thời gian.
        d = _ban_ghi(provenance=_prov(params_source="env"))
        assert any("params_source" in e for e in validate_fold_record(d))

    def test_git_sha_UNKNOWN_thi_bao_loi(self) -> None:
        d = _ban_ghi(provenance=_prov(git_sha="UNKNOWN"))
        assert any("git_sha" in e for e in validate_fold_record(d))

    def test_chi_so_mang_value_khi_chua_do_thi_bao_loi(self) -> None:
        d = _ban_ghi()
        d["chi_so"]["sharpe_r_realized"]["value"] = 0.0
        assert any("cấm hiện số cũ" in e for e in validate_fold_record(d))

    def test_status_la_thi_bao_loi(self) -> None:
        d = _ban_ghi()
        d["chi_so"]["sharpe_r_realized"]["status"] = "chua_biet"
        assert any("không thuộc" in e for e in validate_fold_record(d))

    def test_du_lenh_khai_sai_thi_bao_loi(self) -> None:
        """Bản ghi khai `du_lenh: true` trong khi mẫu mỏng là bản ghi tự
        cấp cho mình quyền hiển thị số."""
        d = _ban_ghi(so_lenh=5)
        d["du_lenh"] = True
        assert any("du_lenh" in e for e in validate_fold_record(d))

    def test_thieu_chi_so_thi_bao_loi(self) -> None:
        d = _ban_ghi()
        d["chi_so"] = {}
        assert any("chi_so" in e or "chỉ số" in e for e in validate_fold_record(d))


class TestCauNoiTuKetQuaFold:
    """`build_fold_record_tu_ket_qua()` là đường DUY NHẤT từ kết quả trong
    bộ nhớ (`KetQuaFold`, TD-0145) sang bản ghi trên đĩa. Hai thứ đó là
    hai TẦNG khác nhau — nhưng nếu không có đúng một đường nối thì mỗi
    nơi cần ghi sẽ tự dựng lấy, và ta có hai bộ tuần tự hoá trôi lệch."""

    def _ket_qua(self, *, so_lenh: int = 40, tu_cache: bool = False):
        from tool_d.wfo.equity import FoldEquity
        from tool_d.wfo.orchestrator import KetQuaFold

        pnl = tuple(1.0 for _ in range(so_lenh))
        eq = FoldEquity(
            chi_so=1, starting_balance=1000.0, final_balance=1000.0 + so_lenh, pnl_abs=pnl
        )
        he_so = Measured.ok(eq.he_so) if so_lenh >= 30 else Measured.unreadable("mỏng")
        return KetQuaFold(fold=FOLD, equity=eq, tu_cache=tu_cache, he_so=he_so)

    def test_he_so_duoc_dua_vao_chi_so_khong_can_ben_goi_nho(self) -> None:
        from tool_d.wfo.fold_record import build_fold_record_tu_ket_qua

        d = build_fold_record_tu_ket_qua(
            ket_qua=self._ket_qua(), provenance=_prov(), san_lenh_moi_fold=30
        )
        assert d["chi_so"]["he_so_tang_truong"]["status"] == "ok"
        jsonschema.validate(d, FOLD_RECORD_SCHEMA)

    def test_so_lenh_lay_tu_ket_qua_khong_phai_ben_goi_khai(self) -> None:
        from tool_d.wfo.fold_record import build_fold_record_tu_ket_qua

        d = build_fold_record_tu_ket_qua(
            ket_qua=self._ket_qua(so_lenh=7), provenance=_prov(), san_lenh_moi_fold=30
        )
        assert d["so_lenh"] == 7 and d["du_lenh"] is False

    def test_de_len_he_so_tang_truong_thi_RAISE(self) -> None:
        """Đè lên là thay con số đã qua L-Z47 bằng số không rõ nguồn."""
        from tool_d.wfo.fold_record import build_fold_record_tu_ket_qua

        with pytest.raises(FoldRecordError, match="he_so_tang_truong"):
            build_fold_record_tu_ket_qua(
                ket_qua=self._ket_qua(),
                provenance=_prov(),
                san_lenh_moi_fold=30,
                chi_so_do={"he_so_tang_truong": Measured.ok(999.0)},
            )

    @pytest.mark.parametrize("tu_cache", [True, False])
    def test_tu_cache_ghi_vao_ban_ghi(self, tu_cache: bool) -> None:
        """Một fold LẤY LẠI TỪ CACHE là con số do lần chạy TRƯỚC sinh ra.
        Vân tay cache bảo đảm nó khớp cấu hình/code/dữ liệu, nhưng người
        đọc vẫn cần biết số được tính lại hay dùng lại — đó là câu hỏi
        xuất xứ (§0d.5)."""
        from tool_d.wfo.fold_record import build_fold_record_tu_ket_qua

        d = build_fold_record_tu_ket_qua(
            ket_qua=self._ket_qua(tu_cache=tu_cache),
            provenance=_prov(),
            san_lenh_moi_fold=30,
        )
        assert d["tu_cache"] is tu_cache
        jsonschema.validate(d, FOLD_RECORD_SCHEMA)

    def test_xuat_xu_KHONG_nam_trong_payload_cache(self) -> None:
        """🔴 Quyết định của TD-0146: cache chỉ giữ SỐ, không giữ xuất xứ.

        Vân tay cache (`params_hash`/`code_sha`/`data_hash`, TD-0143) đã
        trả lời "kết quả này thuộc về cấu hình/code/dữ liệu nào". Nhét
        thêm provenance vào payload là hai nguồn sự thật cho cùng một
        câu hỏi, và khi chúng lệch nhau thì không có luật nào nói tin
        cái nào."""
        from tool_d.wfo.orchestrator import _thanh_payload

        payload = _thanh_payload(self._ket_qua().equity)
        assert "provenance" not in payload
        assert set(payload) == {"chi_so", "starting_balance", "final_balance", "pnl_abs"}


class TestMocFoldGhiDungVaoBanGhi:
    def test_bon_moc_thoi_gian_ghi_dang_ISO(self) -> None:
        f = _ban_ghi()["fold"]
        assert f["train_start"] == "2025-06-12" and f["test_end"] == "2025-10-23"
        assert f["train_end"] == f["test_start"]  # ranh giới nửa mở
        assert f["chi_so"] == 1
