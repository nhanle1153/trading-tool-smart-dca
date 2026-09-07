"""TD-0141 — `src/tool_d/wfo/folds.py`.

Bộ test này canh hai thứ khác nhau, đừng gộp:

1. **Sơ đồ sinh ra đúng DR-D3-01** — neo gốc, 3 fold, train khởi tạo 12
   tuần, test 7 tuần, nằm trọn `[T1, T2]`. Đọc từ `config/tool_d_config.yaml`
   THẬT (không phải config giả) — nếu ai sửa con số trong YAML mà quên sửa
   DR, ca `test_khop_dung_so_do_da_niem_phong` đỏ.
2. **`kiem_folds()` từ chối fold hỏng** — dựng TAY các danh sách fold sai
   (chồng lấn, vượt ranh giới, train đi sau test). Không dựng được qua
   `sinh_folds()` vì nó luôn sinh đúng; nếu chỉ test qua `sinh_folds()`
   thì mọi phép kiểm trong `kiem_folds()` sẽ xanh mà chưa bao giờ chạy
   vào nhánh raise — đúng bẫy PASS RỖNG.
"""

from __future__ import annotations

from datetime import date, timedelta
from types import MappingProxyType

import pytest

from tool_d.config.loader import ToolDConfig, load_tool_d_config
from tool_d.ledger.timerange import (
    DatasetBoundary,
    TimerangeViolationError,
    dataset_boundaries_from_config,
)
from tool_d.wfo.folds import (
    Fold,
    FoldConfigError,
    kiem_folds,
    san_lenh_moi_fold,
    sinh_folds,
)

T1 = date(2025, 6, 12)
T2 = date(2026, 1, 29)
WFO = DatasetBoundary("WFO", T1, T2)


def _cfg(**wfo_folds) -> ToolDConfig:
    """Config tối thiểu: chỉ `tier_c` với `data_split` thật + khối fold
    truyền vào. Các tầng khác rỗng — module này không đọc chúng."""
    mac_dinh = {
        "so_fold": 3,
        "train_khoi_tao_tuan": 12,
        "test_tuan": 7,
        "san_lenh_moi_fold": 30,
    }
    mac_dinh.update(wfo_folds)
    tier_c = MappingProxyType(
        {
            "data_split": MappingProxyType(
                {"t0": "2024-04-09", "t1": "2025-06-12", "t2": "2026-01-29", "t3": "2026-09-06"}
            ),
            "wfo_folds": MappingProxyType(mac_dinh),
        }
    )
    trong = MappingProxyType({})
    return ToolDConfig(
        tier_a=trong, tier_b=trong, tier_frozen=trong, tier_c=tier_c, raw_text="", sha256=""
    )


class TestKhopDRDaNiemPhong:
    def test_config_that_khop_dung_so_do_da_niem_phong(self) -> None:
        """Đọc `config/tool_d_config.yaml` THẬT — đây là ca canh việc ai
        đó đổi số trong YAML mà quên rằng DR-D3-01 đã niêm phong sơ đồ."""
        folds = sinh_folds(load_tool_d_config())
        assert len(folds) == 3
        for f in folds:
            assert f.train_start == T1  # neo gốc: MỌI fold bắt đầu tại T1
            assert f.test_ngay == 7 * 7  # test 7 tuần
        assert folds[0].train_ngay == 12 * 7  # train khởi tạo 12 tuần
        # train dài dần đúng một cửa sổ test mỗi fold
        assert folds[1].train_ngay == folds[0].train_ngay + 7 * 7
        assert folds[2].train_ngay == folds[0].train_ngay + 2 * 7 * 7

    def test_san_lenh_moi_fold_doc_tu_config_that(self) -> None:
        assert san_lenh_moi_fold(load_tool_d_config()) == 30


class TestBoCucFold:
    def test_test_noi_duoi_nhau_khong_ho_khong_chong(self) -> None:
        folds = sinh_folds(_cfg())
        for truoc, sau in zip(folds, folds[1:]):
            assert sau.test_start == truoc.test_end

    def test_train_end_bang_test_start_ranh_gioi_nua_mo(self) -> None:
        # Chồng lấn dù chỉ một nến giữa train và test là rò rỉ IS->OOS —
        # loại lỗi không bao giờ báo lỗi.
        for f in sinh_folds(_cfg()):
            assert f.train_end == f.test_start

    def test_moi_fold_nam_tron_trong_T1_T2(self) -> None:
        folds = sinh_folds(_cfg())
        assert all(f.train_start >= T1 and f.test_end <= T2 for f in folds)

    def test_khong_fold_nao_cham_lockbox(self) -> None:
        # T2 là ranh giới LOCKBOX tuyệt đối — vượt qua là sai phạm CRITICAL
        # và không có lockbox thứ hai.
        lockbox_start = dataset_boundaries_from_config(_cfg())["LOCKBOX"].start
        assert max(f.test_end for f in sinh_folds(_cfg())) <= lockbox_start

    def test_chi_so_fold_dem_tu_1(self) -> None:
        assert [f.chi_so for f in sinh_folds(_cfg())] == [1, 2, 3]


class TestFailClosedCauHinh:
    def test_thieu_khoi_wfo_folds_thi_raise(self) -> None:
        tier_c = MappingProxyType(
            {
                "data_split": MappingProxyType(
                    {"t0": "2024-04-09", "t1": "2025-06-12", "t2": "2026-01-29", "t3": "2026-09-06"}
                )
            }
        )
        trong = MappingProxyType({})
        cfg = ToolDConfig(
            tier_a=trong, tier_b=trong, tier_frozen=trong, tier_c=tier_c, raw_text="", sha256=""
        )
        with pytest.raises(FoldConfigError, match="wfo_folds"):
            sinh_folds(cfg)

    @pytest.mark.parametrize("thieu", ["so_fold", "train_khoi_tao_tuan", "test_tuan"])
    def test_thieu_tung_khoa_thi_raise(self, thieu: str) -> None:
        cfg = _cfg()
        khoi = dict(cfg.tier_c["wfo_folds"])
        del khoi[thieu]
        tier_c = MappingProxyType({**cfg.tier_c, "wfo_folds": MappingProxyType(khoi)})
        trong = MappingProxyType({})
        hong = ToolDConfig(
            tier_a=trong, tier_b=trong, tier_frozen=trong, tier_c=tier_c, raw_text="", sha256=""
        )
        with pytest.raises(FoldConfigError, match=thieu):
            sinh_folds(hong)

    @pytest.mark.parametrize("xau", [0, -1, 2.5, "3", True])
    def test_gia_tri_khong_hop_le_thi_raise(self, xau) -> None:
        # `True` nằm trong danh sách có chủ đích: `isinstance(True, int)`
        # là True trong Python, nên nếu quên chặn bool thì `so_fold: true`
        # sẽ lặng lẽ chạy như `so_fold = 1`.
        with pytest.raises(FoldConfigError):
            sinh_folds(_cfg(so_fold=xau))

    def test_so_do_khong_vua_cua_so_thi_RAISE_khong_tu_giam_fold(self) -> None:
        """🔴 Ca quan trọng: sơ đồ đã niêm phong không vừa dữ liệu thì phải
        TỪ CHỐI, không được lặng lẽ co lại cho chạy được."""
        with pytest.raises(FoldConfigError, match="TỪ CHỐI"):
            sinh_folds(_cfg(so_fold=10))  # 12 + 10x7 = 82 tuần > 33 tuần

    def test_thieu_san_lenh_thi_raise_khong_mac_dinh_ngam(self) -> None:
        cfg = _cfg()
        khoi = dict(cfg.tier_c["wfo_folds"])
        del khoi["san_lenh_moi_fold"]
        tier_c = MappingProxyType({**cfg.tier_c, "wfo_folds": MappingProxyType(khoi)})
        trong = MappingProxyType({})
        hong = ToolDConfig(
            tier_a=trong, tier_b=trong, tier_frozen=trong, tier_c=tier_c, raw_text="", sha256=""
        )
        with pytest.raises(FoldConfigError, match="san_lenh_moi_fold"):
            san_lenh_moi_fold(hong)


def _fold(i: int, train_ngay: int, test_ngay: int, *, lech: int = 0) -> Fold:
    ts = T1 + timedelta(days=train_ngay + lech)
    return Fold(
        chi_so=i,
        train_start=T1,
        train_end=ts,
        test_start=ts,
        test_end=ts + timedelta(days=test_ngay),
    )


class TestKiemFoldsTuChoiFoldHong:
    """Dựng TAY fold hỏng — `sinh_folds()` không bao giờ sinh ra được
    những ca này, nên nếu không test trực tiếp `kiem_folds()` thì các
    nhánh raise của nó không bao giờ chạy."""

    def test_danh_sach_rong_thi_raise(self) -> None:
        with pytest.raises(FoldConfigError, match="rỗng"):
            kiem_folds((), boundary=WFO)

    def test_test_chong_lan_nhau_thi_raise(self) -> None:
        a = _fold(1, 84, 49)
        b = _fold(2, 84 + 20, 49)  # bắt đầu trước khi fold 1 kết thúc
        with pytest.raises(FoldConfigError, match="chồng lấn"):
            kiem_folds((a, b), boundary=WFO)

    def test_vuot_ranh_gioi_WFO_thi_raise_qua_LZ55(self) -> None:
        # Lỗi này do `assert_dataset_timerange()` (L-Z55) ném ra, KHÔNG
        # phải phép so sánh tự viết trong module fold — nếu ai đó thay
        # bằng phép kiểm riêng thì loại lỗi ở đây sẽ đổi và ca này đỏ.
        qua_xa = _fold(1, 84, 400)
        with pytest.raises(TimerangeViolationError):
            kiem_folds((qua_xa,), boundary=WFO)

    def test_train_rong_thi_raise(self) -> None:
        rong = Fold(1, T1, T1, T1, T1 + timedelta(days=49))
        with pytest.raises(FoldConfigError, match="thứ tự thời gian"):
            kiem_folds((rong,), boundary=WFO)

    def test_train_lan_sang_test_thi_raise(self) -> None:
        # train_end > test_start: một đoạn thời gian nằm trong CẢ train
        # lẫn test — rò rỉ in-sample sang out-of-sample.
        ts = T1 + timedelta(days=84)
        lan = Fold(1, T1, ts + timedelta(days=5), ts, ts + timedelta(days=49))
        with pytest.raises(FoldConfigError, match="thứ tự thời gian"):
            kiem_folds((lan,), boundary=WFO)

    def test_fold_dung_thi_khong_raise(self) -> None:
        # Đối chứng: nếu ca này cũng raise thì `kiem_folds()` đang chặn
        # nhầm, và mọi ca raise ở trên không chứng minh được gì.
        kiem_folds((_fold(1, 84, 49), _fold(2, 84 + 49, 49)), boundary=WFO)
