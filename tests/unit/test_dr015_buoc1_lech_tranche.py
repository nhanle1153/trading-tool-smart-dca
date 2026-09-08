"""TD-0161 — DR-015 Bước 1: quy đổi lệch khớp tranche sang đơn vị R.

Dữ liệu vào là 91 lượt khớp THẬT của TD-0115 (`docs/du-lieu-do/
dr015-luot-khop-tranche.json`) — không dựng tay, không mock. Cùng bài
học "ca sai chỉ đi qua mẫu dựng tay" đã rút ra hôm nay: mọi phép kiểm ở
đây chạy trên chính dữ liệu thật đó, không phải một fixture đẹp tự bịa.
"""

from __future__ import annotations

from pathlib import Path

import jsonschema
import pytest

from tool_d.dr015.buoc1_lech_tranche import (
    SAN_N_CHO_P90,
    Buoc1Error,
    _doc_du_lieu_tho,
    _gia_ke_hoach_ca_ba_tranche,
    _p90,
    _uoc_luong_cost_tranche,
    chay,
    ghi_dong_ctrl,
    kiem_timerange_calib,
    tinh_buoc1,
)
from tool_d.ledger.registry import DEFAULT_REGISTRY_PATH, TrialLedger
from tool_d.ledger.timerange import TimerangeViolationError

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = __import__("json").loads(
    (REPO_ROOT / "registry/schemas/trial_event.schema.json").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def du_lieu_that():
    return _doc_du_lieu_tho()


class TestDuLieuThoDungHinhDang:
    """Xác nhận lại các con số research-log TD-0115 — không tin suông."""

    def test_91_luot_khop_35_32_24(self, du_lieu_that) -> None:
        rows = du_lieu_that["luot_khop"]
        assert len(rows) == 91
        from collections import Counter

        c = Counter(r["tranche"] for r in rows)
        assert c == {1: 35, 2: 32, 3: 24}

    def test_chi_co_long(self, du_lieu_that) -> None:
        assert {r["huong"] for r in du_lieu_that["luot_khop"]} == {"long"}


class TestUocLuongCostTranche:
    """Mẫu hình cấp-luỹ-thừa đã xác minh trên chính dữ liệu (8/8 trade)."""

    def test_du_ca_ba_thi_dung_so_that(self) -> None:
        assert _uoc_luong_cost_tranche({1: 10.0, 2: 9.9, 3: 19.8}) == {1: 10.0, 2: 9.9, 3: 19.8}

    def test_chi_co_tranche1_thi_uoc_luong_2_bang_1_va_3_bang_gap_doi(self) -> None:
        ket_qua = _uoc_luong_cost_tranche({1: 10.0})
        assert ket_qua[1] == 10.0
        assert ket_qua[2] == 10.0  # ước lượng = cost1 (mẫu hình quan sát được)
        assert ket_qua[3] == 20.0  # ước lượng = cost1 + cost2_ước = 2×cost1

    def test_co_tranche1_va_2_thi_tranche3_uoc_luong_bang_tong(self) -> None:
        ket_qua = _uoc_luong_cost_tranche({1: 10.0, 2: 9.9})
        assert ket_qua[3] == pytest.approx(19.9)  # cost1 + cost2 THẬT

    def test_thieu_tranche1_thi_raise(self) -> None:
        with pytest.raises(Buoc1Error):
            _uoc_luong_cost_tranche({2: 9.9})

    def test_mau_hinh_khop_voi_8_trade_du_3_tranche_that(self, du_lieu_that) -> None:
        """Kiểm có răng: đối chiếu chính giả định 'cấp luỹ thừa' với TOÀN
        BỘ trade đủ 3 tranche trong dữ liệu thật, không chỉ một mẫu tay."""
        from collections import defaultdict

        theo_trade: dict[int, dict[int, dict]] = defaultdict(dict)
        for r in du_lieu_that["luot_khop"]:
            theo_trade[r["trade_idx"]][r["tranche"]] = r

        so_kiem = 0
        for tid, fills in theo_trade.items():
            if len(fills) != 3:
                continue
            so_kiem += 1
            c1, c2, c3 = fills[1]["cost"], fills[2]["cost"], fills[3]["cost"]
            assert c2 == pytest.approx(c1, rel=0.005), f"trade {tid}: cost2 lệch mẫu hình"
            assert c3 == pytest.approx(c1 + c2, rel=0.005), f"trade {tid}: cost3 lệch mẫu hình"
        assert so_kiem == 24, "phải kiểm đủ 24 trade 3-tranche, không được bỏ sót"


class TestGiaKeHoachCaBaTranche:
    def test_p2_p3_tinh_lai_khop_du_lieu_that_cua_MOI_trade_du_3_tranche(self, du_lieu_that) -> None:
        """Không chỉ một mẫu tay — đối chiếu công thức với TẤT CẢ trade có
        tranche 2 VÀ 3 đã khớp thật, để chắc công thức dùng cho tranche
        CHƯA khớp (không thể đối chiếu trực tiếp) là đáng tin."""
        from collections import defaultdict

        theo_trade: dict[int, dict[int, dict]] = defaultdict(dict)
        for r in du_lieu_that["luot_khop"]:
            theo_trade[r["trade_idx"]][r["tranche"]] = r

        so_kiem = 0
        for tid, fills in theo_trade.items():
            if 2 not in fills and 3 not in fills:
                continue
            so_kiem += 1
            p1 = fills[1]["p_ke_hoach"]
            p = _gia_ke_hoach_ca_ba_tranche(fills[1], p1)
            if 2 in fills:
                assert p[2] == pytest.approx(fills[2]["p_ke_hoach"]), f"trade {tid}: p2 lệch"
            if 3 in fills:
                assert p[3] == pytest.approx(fills[3]["p_ke_hoach"]), f"trade {tid}: p3 lệch"
        assert so_kiem >= 32


class TestP90:
    def test_toan_bo_bang_nhau_thi_tra_dung_gia_tri_do(self) -> None:
        assert _p90([5.0] * 10) == 5.0

    def test_mot_phan_tu_thi_tra_chinh_no(self) -> None:
        assert _p90([7.0]) == 7.0

    def test_p90_cua_0_den_99_xap_xi_89_1(self) -> None:
        # numpy.percentile([0..99], 90) = 89.1 (nội suy tuyến tính chuẩn)
        assert _p90(list(range(100))) == pytest.approx(89.1)


class TestTinhBuoc1:
    def test_long_co_35_lenh_dung_p90(self, du_lieu_that) -> None:
        kq = tinh_buoc1(du_lieu_that)
        assert kq["LONG"].so_lenh == 35
        assert kq["LONG"].dung_p90 is True  # 35 >= SAN_N_CHO_P90
        assert kq["LONG"].delta_r.is_ok()
        assert kq["LONG"].delta_r.value > 0

    def test_short_unreadable_KHONG_phai_0(self, du_lieu_that) -> None:
        kq = tinh_buoc1(du_lieu_that)
        assert not kq["SHORT"].delta_r.is_ok()
        assert kq["SHORT"].so_lenh == 0
        assert kq["SHORT"].lech_moi_lenh == ()

    def test_3_trade_chi_1_tranche_co_lech_bang_0(self, du_lieu_that) -> None:
        """3 trade chỉ khớp tranche 1 -> không có tranche >=2 để lệch ->
        đúng 0.0 (không phải 'thiếu dữ liệu'), và spec nói MỖI lệnh đều
        có một lệch-mỗi-lệnh, kể cả bằng 0.

        Không assert ĐÚNG BẰNG 3: dữ liệu thật có thêm 2 trade khác (đủ 2
        tranche) mà lệnh limit khớp CHÍNH XÁC tại giá kế hoạch (fill_price
        == p_ke_hoach từng chữ số) -> lệch-mỗi-lệnh của chúng cũng hợp lệ
        bằng 0.0. Đây là kết quả THẬT của lệnh giới hạn, không phải lỗi
        code hay lỗi test — assert >= 3 mới đúng bất biến cần giữ (3 trade
        một-tranche CHẮC CHẮN phải có mặt trong tập bằng 0)."""
        kq = tinh_buoc1(du_lieu_that)
        so_bang_0 = sum(1 for x in kq["LONG"].lech_moi_lenh if x == 0.0)
        assert so_bang_0 >= 3

    def test_du_lieu_huong_la_thi_raise(self) -> None:
        with pytest.raises(Buoc1Error):
            tinh_buoc1({"luot_khop": [{"huong": "ngang", "trade_idx": 0, "tranche": 1}]})

    def test_tranche1_KHONG_duoc_tinh_vao_lech(self, du_lieu_that) -> None:
        """🔴 Kiểm có răng cho ràng buộc spec §3: tranche 1 loại khỏi
        Σ|lệch|. Dựng MỘT trade giả có lệch tranche1 RẤT LỚN nhưng
        tranche 2/3 khớp đúng kế hoạch -> lệch-mỗi-lệnh phải ~ 0, không
        bị tranche 1 kéo lên."""
        gia = {"zone_low": 100.0, "zone_high": 110.0, "sl": 95.0}
        rows = [
            {**gia, "trade_idx": 999, "tranche": 1, "huong": "long",
             "p_ke_hoach": 110.0, "fill_price": 50.0,  # lệch KHỔNG LỒ, cố tình
             "amount": 1.0, "cost": 110.0},
            {**gia, "trade_idx": 999, "tranche": 2, "huong": "long",
             "p_ke_hoach": 105.0, "fill_price": 105.0,  # khớp ĐÚNG kế hoạch
             "amount": 1.0, "cost": 105.0},
        ]
        kq = tinh_buoc1({"luot_khop": rows})
        assert kq["LONG"].lech_moi_lenh[0] == pytest.approx(0.0, abs=1e-9)


class TestKiemTimerangeCalib:
    def test_du_lieu_that_nam_trong_CALIB(self, du_lieu_that) -> None:
        kiem_timerange_calib(du_lieu_that["luot_khop"])  # không raise

    def test_du_lieu_ngoai_CALIB_thi_raise(self) -> None:
        """Ngày quan sát cố tình đặt vào tương lai xa (giả lập chạm LOCKBOX
        hoặc dữ liệu chưa tồn tại) -> phải bị chặn, không phải bị bỏ qua."""
        rows = [{"fill_ts_ms": 4102444800000}]  # năm 2100
        with pytest.raises(TimerangeViolationError):
            kiem_timerange_calib(rows)


class TestGhiDongCTRL:
    def test_dong_ghi_ra_hop_le_theo_schema(self, tmp_path: Path) -> None:
        """Đúng bài học TD-0149: soi ĐẦU RA THẬT, đọc lại từ đĩa."""
        reg_path = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg_path)
        trial_id = ghi_dong_ctrl(ledger=ledger, repo_dir=REPO_ROOT)
        assert trial_id == "D-0001"

        dong = [
            __import__("json").loads(x)
            for x in reg_path.read_text(encoding="utf-8").splitlines()
            if x.strip()
        ]
        assert len(dong) == 1
        jsonschema.validate(dong[0], SCHEMA)
        assert dong[0]["budget_line"] == "CTRL"
        assert dong[0]["direction"] == "LONG"
        assert dong[0]["dataset"] == "CALIB"

    def test_dong_CTRL_KHONG_tinh_vao_N(self, tmp_path: Path) -> None:
        reg_path = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg_path)
        ghi_dong_ctrl(ledger=ledger, repo_dir=REPO_ROOT)
        assert ledger.n_used() == 0
        assert ledger.n_reserved() == 0

    def test_ghi_hai_lan_khong_bi_chan_ngan_sach(self, tmp_path: Path) -> None:
        """CTRL đứng ngoài kiểm ngân sách — chạy lại phép đo Bước 1 nhiều
        lần (VD sau khi có dữ liệu mới) không bị BudgetExhaustedError,
        đúng thiết kế MT-08."""
        reg_path = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg_path)
        ghi_dong_ctrl(ledger=ledger, repo_dir=REPO_ROOT)
        ghi_dong_ctrl(ledger=ledger, repo_dir=REPO_ROOT)
        assert ledger.n_used() == 0


class TestChayTronVen:
    def test_chay_tra_ca_ket_qua_lan_trial_id(self, tmp_path: Path) -> None:
        reg_path = tmp_path / "reg.jsonl"
        kq, trial_id = chay(registry_path=reg_path, repo_dir=REPO_ROOT)
        assert kq["LONG"].delta_r.is_ok()
        assert trial_id.startswith("D-")

    def test_khong_dung_duong_dan_that_cua_repo_neu_khong_truyen(self) -> None:
        """Mặc định phải trỏ đúng file thật trong repo — không phải một
        đường dẫn giả nào khác, vì spec bắt 'KHÔNG đo lại'."""
        assert DEFAULT_REGISTRY_PATH == Path("registry/trial_registry.jsonl")
