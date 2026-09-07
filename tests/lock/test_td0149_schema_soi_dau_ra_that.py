"""TD-0149 — `trial_event.schema.json` phải soi ĐẦU RA THẬT của sổ trial.

`tests/unit/test_registry_schemas.py` (TD-0050) validate schema bằng
`tests/fixtures/trial_events_valid.jsonl` — một file GÕ TAY. Nó chứng minh
schema tự nó nhất quán, nhưng KHÔNG chứng minh `TrialLedger` ghi ra đúng
hình dạng đó. Hai bên chưa bao giờ nhìn nhau.

🔴 **Lỗ này đã cắn thật, hôm nay.** TD-0130 thêm hai khoá vào sự kiện
   RESERVE (`reproduces_trial_id`, `ctrl_output_whitelist`) mà quên
   `trial_event.schema.json` (`additionalProperties: false`). **735 test
   xanh KHÔNG bắt được**, vì không test nào soi đầu ra thật — sổ thật lúc
   đó chưa có dòng CTRL nào nên cũng chưa nổ. Nó sẽ nổ đúng lần ghi CTRL
   thật đầu tiên, tức lúc đang cần ghi điểm kiểm soát nhất.

   TD-0130 đã vá TRƯỜNG HỢP đó. Bộ test này vá CƠ CHẾ: từ giờ mọi khoá
   thêm vào bất kỳ sự kiện nào mà quên schema đều đỏ NGAY, không chờ tới
   lần ghi thật.

🔑 Nguyên tắc chung, đã tái diễn bốn lần trong ngày: **một lớp bảo vệ
   chưa ai thử xem nó có canh thật không thì nguy hơn không có lớp nào**,
   vì có nó thì người ta thôi cảnh giác. Vì vậy file này không chỉ kiểm
   "đầu ra hợp lệ" mà còn tự chứng minh mình CÓ RĂNG (`TestCoRang`).
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tool_d.ledger.registry import SchemaViolationError, TrialLedger

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads(
    (REPO_ROOT / "registry/schemas/trial_event.schema.json").read_text(encoding="utf-8")
)

# Đúng bộ 7 khoá provenance mà schema đòi (0d.5, L-Z40).
PROVENANCE = {
    "params_source": "yaml",
    "params_effective": {"zss_threshold": 0.5},
    "git_sha": "a" * 40,
    "reproducible_from_sha": True,
    "data_hashes": {"BTC_USDT-1h.feather": "b" * 64},
    "cache_mode": "none",
    "guard_passed": True,
}

OUTCOME = {
    "expectancy": 1.25,
    "sharpe": 0.8,
    "n_trades": 42,
    "max_single_loss_ratio": 0.3,
}


def _duong_dan(tmp_path: Path) -> Path:
    return tmp_path / "trial_registry.jsonl"


def _so(tmp_path: Path) -> TrialLedger:
    """Sổ trên `tmp_path`. Test giữ đường dẫn ở phía mình chứ không đọc
    thuộc tính riêng tư `_path` của `TrialLedger` — thò vào nội bộ để test
    là cách biến một chi tiết cài đặt thành một hợp đồng ngoài ý muốn."""
    return TrialLedger(_duong_dan(tmp_path))


def _reserve(so: TrialLedger, **doi) -> str:
    tham_so = {
        "n_dang_ky": 114,
        "so_lenh_da_dong": 0,
        "tool_id": "D",
        "budget_line": "B1",
        "hypothesis_slot": "A-01",
        "direction": "LONG",
        "dataset": "CALIB",
        "param_under_test": "zss_threshold",
        "param_value": 0.5,
        "params_frozen_hash": "f" * 64,
        "config_hash": "c" * 64,
        "code_commit": "a" * 40,
        "provenance": PROVENANCE,
        "contribution": 1,
    }
    tham_so.update(doi)
    return so.reserve(**tham_so)


def _doc_su_kien(tmp_path: Path) -> list[dict]:
    """Đọc LẠI TỪ ĐĨA, không lấy dict trong bộ nhớ.

    Đây là điểm mấu chốt của cả file: thứ phải hợp lệ là **byte đã nằm
    trên đĩa**, vì đó mới là thứ `audit_checks` và mọi phiên chạy sau đọc.
    Soi một dict trong bộ nhớ sẽ bỏ lọt mọi lỗi ở khâu serialize.
    """
    text = _duong_dan(tmp_path).read_text(encoding="utf-8")
    return [json.loads(d) for d in text.splitlines() if d.strip()]


def _sinh_du_5_loai(tmp_path: Path) -> list[dict]:
    """Ghi thật đủ 5 loại sự kiện bằng chính `TrialLedger`."""
    so = _so(tmp_path)

    # RESERVE + SEAL + CONSUME + CONTAMINATE trên cùng một trial
    t1 = _reserve(so)
    so.seal(t1, seal_path="runs/D-0001/metrics.seal")
    so.consume(t1, outcome=OUTCOME, verdict="KEPT", retest_forbidden=True)
    so.mark_contaminated(t1, reason="nhiễm tham số — DR-014 §6")

    # REFUND cần một trial CHƯA seal (L-Z53: đã seal thì cấm hoàn trả)
    t2 = _reserve(so, config_hash="d" * 64)
    so.refund(t2, cause_machine="exit_code=86 guard chặn")

    return _doc_su_kien(tmp_path)


class TestDauRaThatHopLeTheoSchema:
    def test_du_ca_5_loai_su_kien_duoc_sinh_ra(self, tmp_path: Path) -> None:
        loai = {e["event"] for e in _sinh_du_5_loai(tmp_path)}
        assert loai == {"RESERVE", "SEAL", "CONSUME", "REFUND", "CONTAMINATE"}

    def test_moi_dong_GHI_THAT_deu_hop_le_theo_schema(self, tmp_path: Path) -> None:
        """🔴 Phép kiểm chính. Nếu ai thêm khoá vào một sự kiện mà quên
        schema (`additionalProperties: false`), ca này đỏ NGAY — không chờ
        tới lần ghi thật như TD-0130 đã phải chờ."""
        for e in _sinh_du_5_loai(tmp_path):
            try:
                jsonschema.validate(e, SCHEMA)
            except jsonschema.ValidationError as exc:
                pytest.fail(
                    f"sự kiện {e['event']} do TrialLedger ghi ra KHÔNG khớp "
                    f"trial_event.schema.json — code và schema đã lệch nhau.\n"
                    f"  chỗ sai: {'/'.join(str(x) for x in exc.absolute_path) or '(gốc)'}\n"
                    f"  lý do:   {exc.message}"
                )

    def test_dong_CTRL_khai_tai_lap_cung_hop_le(self, tmp_path: Path) -> None:
        """Đúng hai khoá đã gây ra sự cố TD-0130 (`reproduces_trial_id`).
        Ca này tồn tại để lần sửa đó không lặng lẽ mất đi."""
        so = _so(tmp_path)
        goc = _reserve(so)
        so.reserve(
            n_dang_ky=114, so_lenh_da_dong=0, tool_id="D", budget_line="CTRL",
            hypothesis_slot="A-01", direction="LONG", dataset="CALIB",
            param_under_test="zss_threshold", param_value=0.5,
            params_frozen_hash="f" * 64, config_hash="c" * 64, code_commit="a" * 40,
            provenance=PROVENANCE, contribution=1, reproduces_trial_id=goc,
        )
        ctrl = [e for e in _doc_su_kien(tmp_path) if e.get("budget_line") == "CTRL"]
        assert len(ctrl) == 1
        jsonschema.validate(ctrl[0], SCHEMA)

    def test_dong_CTRL_khai_do_thuoc_cung_hop_le(self, tmp_path: Path) -> None:
        """Khoá thứ hai của TD-0130 (`ctrl_output_whitelist`)."""
        so = _so(tmp_path)
        so.reserve(
            n_dang_ky=114, so_lenh_da_dong=0, tool_id="D", budget_line="CTRL",
            hypothesis_slot="A-01", direction="LONG", dataset="CALIB",
            param_under_test="zss_threshold", param_value=0.5,
            params_frozen_hash="f" * 64, config_hash="c" * 64, code_commit="a" * 40,
            provenance=PROVENANCE, contribution=1,
            ctrl_output_whitelist=["price_delta", "tranche_index"],
        )
        jsonschema.validate(_doc_su_kien(tmp_path)[0], SCHEMA)

    def test_hypothesis_slot_dang_IQ_cung_hop_le(self, tmp_path: Path) -> None:
        """MT-12 nối sổ ý tưởng vào sổ trial bằng `hypothesis_slot = IQ-xxxx`.
        Nếu schema siết `hypothesis_slot` thành dạng `A-xx` thì cả cơ chế đó
        gãy — ca này canh cho khỏi siết nhầm."""
        so = _so(tmp_path)
        _reserve(so, hypothesis_slot="IQ-0007")
        jsonschema.validate(_doc_su_kien(tmp_path)[0], SCHEMA)


class TestKhoangHoDaVA:
    """Ghi nhận một khoảng hở LỘ RA khi viết bộ test này — không sửa ở đây.

    **`TrialLedger` KHÔNG validate đầu vào theo schema của chính nó.**
    Hai ví dụ độc lập, tìm được khi viết bộ test này:

      • `seal_path` — schema đòi mẫu `runs/<...>/metrics.seal`;
        `seal()` nhận bất kỳ chuỗi nào.
      • `verdict` — schema chỉ cho `KEPT|REJECTED|INCONCLUSIVE`;
        `consume()` nhận bất kỳ chuỗi nào.

    Hai trường khác nhau, cùng một hiện tượng — nên đây là tính chất chung
    của cửa ghi, không phải hai chỗ sót lẻ. Chỗ gọi truyền sai thì sổ VẪN
    GHI, và dòng đó không hợp lệ theo chính schema của nó — im lặng, cho
    tới khi có ai validate lại.

    Cùng họ với lỗ mà TD-0149 vá: cửa GHI và schema không nhìn nhau. Khác
    ở chỗ lỗ kia là "schema không biết khoá mới", còn lỗ này là "cửa ghi
    không biết ràng buộc của schema".

    ✅ **ĐÃ VÁ — TD-0150** (chủ dự án duyệt 08/09/2026). `_append()` nay
    đối chiếu schema TRƯỚC khi ghi, nên cả hai ca dưới đây từ "ghi được
    nhưng không hợp lệ" chuyển thành "BỊ TỪ CHỐI, sổ không dài thêm".

    🔑 Hai ca này CỐ Ý được **sửa thành khẳng định ngược, KHÔNG bị xoá**.
    Chúng ghim hiện trạng cũ, nên khi cửa ghi siết lại chúng PHẢI đỏ —
    và người sửa buộc phải đọc lý do trước khi động vào. Xoá một test đỏ
    cho sạch bảng là cách một quyết định biến mất mà không ai ghi lại.
    Vá ở `_append()` (điểm nghẽn duy nhất) chứ không vá từng hàm: khoảng
    hở lộ ra ở HAI trường khác nhau nên nó là tính chất của cửa ghi.
    """

    def test_seal_path_sai_mau_NAY_BI_TU_CHOI_ghi(self, tmp_path: Path) -> None:
        so = _so(tmp_path)
        t = _reserve(so)
        truoc = len(_doc_su_kien(tmp_path))

        with pytest.raises(SchemaViolationError):
            so.seal(t, seal_path="duong/dan/bat/ky.txt")  # cửa ghi NAY CHẶN

        assert len(_doc_su_kien(tmp_path)) == truoc  # sổ không dài thêm dòng nào

    def test_verdict_ngoai_enum_NAY_BI_TU_CHOI_ghi(self, tmp_path: Path) -> None:
        """Cùng khoảng hở, ở một trường KHÁC — nên đây là hiện tượng chung
        của cửa ghi, không phải một chỗ sót lẻ. Schema chỉ cho
        `KEPT|REJECTED|INCONCLUSIVE`; `consume()` nhận mọi chuỗi."""
        so = _so(tmp_path)
        t = _reserve(so)
        truoc = len(_doc_su_kien(tmp_path))

        with pytest.raises(SchemaViolationError):
            so.consume(t, outcome=OUTCOME, verdict="ACCEPTED", retest_forbidden=True)

        assert len(_doc_su_kien(tmp_path)) == truoc


class TestCoRang:
    """Tự chứng minh bộ test này bắt được lệch thật.

    Không có lớp này thì `TestDauRaThatHopLeTheoSchema` có thể xanh vì
    schema quá lỏng chứ không phải vì code đúng — đúng loại "lớp bảo vệ
    giả" mà chính file này sinh ra để chống.
    """

    @pytest.mark.parametrize(
        "loai", ["RESERVE", "SEAL", "CONSUME", "REFUND", "CONTAMINATE"]
    )
    def test_them_mot_khoa_la_vao_su_kien_thi_schema_TU_CHOI(
        self, tmp_path: Path, loai: str
    ) -> None:
        """Mô phỏng đúng sự cố TD-0130: code thêm khoá, schema không biết."""
        e = next(x for x in _sinh_du_5_loai(tmp_path) if x["event"] == loai)
        e["khoa_moi_ai_do_vua_them"] = "giá trị nào đó"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(e, SCHEMA)

    @pytest.mark.parametrize(
        "loai,khoa",
        [
            ("RESERVE", "provenance"),
            ("RESERVE", "budget_line"),
            ("SEAL", "seal_path"),
            ("CONSUME", "outcome"),
            ("REFUND", "refund_cause_machine"),
            ("CONTAMINATE", "reason"),
        ],
    )
    def test_bo_mot_khoa_bat_buoc_thi_schema_TU_CHOI(
        self, tmp_path: Path, loai: str, khoa: str
    ) -> None:
        e = next(x for x in _sinh_du_5_loai(tmp_path) if x["event"] == loai)
        assert khoa in e, f"đầu ra thật của {loai} đã KHÔNG còn khoá {khoa}"
        del e[khoa]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(e, SCHEMA)

    def test_bo_mot_khoa_provenance_thi_schema_TU_CHOI(self, tmp_path: Path) -> None:
        """Khối xuất xứ 7 khoá (0d.5, L-Z40) — thiếu một khoá là mất khả
        năng tái lập, không phải chuyện thẩm mỹ."""
        e = next(x for x in _sinh_du_5_loai(tmp_path) if x["event"] == "RESERVE")
        del e["provenance"]["git_sha"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(e, SCHEMA)

    def test_su_kien_khong_thuoc_5_loai_thi_schema_TU_CHOI(self, tmp_path: Path) -> None:
        e = next(x for x in _sinh_du_5_loai(tmp_path) if x["event"] == "SEAL")
        e["event"] = "MOT_LOAI_MOI"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(e, SCHEMA)


class TestFixtureVaDauRaThatKhongDuocLECH:
    """Fixture gõ tay giờ có một việc rõ ràng: làm ví dụ đọc được. Nhưng nó
    không được MÔ TẢ SAI hình dạng thật — một fixture lạc hậu sẽ dạy người
    đọc sai về sổ, và là cách lỗi TD-0130 đã sống sót qua nhiều vòng."""

    def test_fixture_co_du_khoa_ma_dau_ra_that_co(self, tmp_path: Path) -> None:
        fixture = [
            json.loads(d)
            for d in (REPO_ROOT / "tests/fixtures/trial_events_valid.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if d.strip()
        ]
        that = _sinh_du_5_loai(tmp_path)

        for loai in ("RESERVE", "SEAL", "CONSUME", "REFUND", "CONTAMINATE"):
            f = next((x for x in fixture if x["event"] == loai), None)
            assert f is not None, f"fixture thiếu hẳn loại {loai}"
            t = next(x for x in that if x["event"] == loai)
            thieu = set(t) - set(f)
            assert not thieu, (
                f"fixture {loai} thiếu khoá mà đầu ra THẬT có: {sorted(thieu)} — "
                "fixture đang mô tả sai hình dạng sổ"
            )
