"""🔴 TD-0148 — `L-Z55` ĐÚNG NGHĨA cho WFO: bộ chạy phải KHAI PHẠM VI DỮ
LIỆU THẬT ĐÃ ĐỌC, và orchestrator đối chiếu nó với biên đã niêm phong.

Bối cảnh (rà soát độc lập khối D3, 07/09/2026): `kiem_folds()` CÓ gọi
`assert_dataset_timerange()`, nhưng với fold do `sinh_folds()` sinh ra thì
**cả hai vế đều suy từ `wfo.start`** — đúng cái bẫy mà docstring
`DatasetBoundary` tự cảnh báo. Nó gần như luôn đúng theo cấu tạo. Phép
kiểm ở tầng DỮ LIỆU THẬT trước đó **không được gọi ở đâu**.

Mối đe doạ có thật và đã xảy ra một lần — TD-0093: `download-data
--timerange` KHÔNG cắt file, nến vùng LOCKBOX (tới 2026-09-05) đang nằm
sẵn trong đúng thư mục mà WFO sẽ đọc.

🔑 **HAI GIỚI HẠN PHẢI GHI RÕ, KHÔNG ĐƯỢC NGẦM HIỂU** — không viết ra là
lặp lại đúng sai lầm đang sửa:

  1. Tới khi có bộ chạy backtest THẬT (D3.5), phép kiểm này chỉ được nuôi
     bằng **bộ chạy GIẢ** trong chính file test này. **Cơ chế** đã tại chỗ
     và bị khoá; **bảo đảm trên dữ liệu thật** thì D3.5 mới có.
  2. Nó **vẫn tin lời khai của bộ chạy**. Một bộ chạy trả ngày *dự kiến*
     thay vì ngày *thật đọc được từ dataframe* sẽ vô hiệu hoá nó hoàn
     toàn. Khi viết bộ chạy thật, bắt buộc đọc từ dataframe, và phải có
     test khoá riêng cho đúng điều đó.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from tool_d.config.loader import load_tool_d_config  # noqa: E402
from tool_d.ledger.timerange import (  # noqa: E402
    TimerangeViolationError,
    dataset_boundaries_from_config,
)
from tool_d.wfo.equity import FoldEquity  # noqa: E402
from tool_d.wfo.folds import Fold, kiem_pham_vi_du_lieu, sinh_folds  # noqa: E402
from tool_d.wfo.orchestrator import chay_wfo  # noqa: E402

CFG = load_tool_d_config()
BIEN_WFO = dataset_boundaries_from_config(CFG)["WFO"]
FOLDS = sinh_folds(CFG)
FOLD1, FOLD2, FOLD3 = FOLDS


def _kiem(fold: Fold, bd: date, kt: date) -> None:
    kiem_pham_vi_du_lieu(
        observed_start=bd, observed_end=kt, fold=fold, boundary=BIEN_WFO
    )


class TestTruongBatBuocKhongCoMacDinh:
    def test_FoldEquity_thieu_observed_thi_NO_ngay(self) -> None:
        """Không có mặc định là quyết định thiết kế, không phải bất tiện:
        một mặc định (kể cả `None`) sớm muộn sẽ có chỗ quên truyền, và
        chỗ quên đó chính là chỗ phép kiểm im lặng biến mất."""
        with pytest.raises(TypeError, match="observed_start"):
            FoldEquity(  # type: ignore[call-arg]
                chi_so=1, starting_balance=1000.0, final_balance=1100.0, pnl_abs=(100.0,)
            )


class TestTangA_BienWFO:
    def test_trong_bien_thi_khong_raise(self) -> None:
        _kiem(FOLD1, FOLD1.train_start, FOLD1.test_end - timedelta(days=1))

    def test_doc_truoc_T1_thi_raise(self) -> None:
        _kiem_loi = BIEN_WFO.start - timedelta(days=1)
        with pytest.raises(TimerangeViolationError):
            _kiem(FOLD1, _kiem_loi, FOLD1.test_end - timedelta(days=1))

    def test_doc_qua_T2_cham_LOCKBOX_thi_raise(self) -> None:
        """Đây đúng là hình dạng của TD-0093: nến vùng LOCKBOX nằm sẵn
        trong thư mục WFO sẽ đọc."""
        with pytest.raises(TimerangeViolationError):
            _kiem(FOLD3, FOLD3.train_start, BIEN_WFO.end + timedelta(days=1))


class TestTangB_CuaSoCuaChinhFold:
    """🔴 Tầng (b) chặt hơn tầng (a) và bắt thêm RÒ RỈ GIỮA CÁC FOLD —
    thứ mà biên WFO một mình không thấy."""

    def test_fold1_doc_sang_cua_so_test_cua_fold2_thi_RAISE(self) -> None:
        """Ca cốt lõi: phạm vi này vẫn nằm GỌN trong `[T1, T2]` nên tầng
        (a) cho qua — nhưng nó là đọc dữ liệu TƯƠNG LAI."""
        lan_sang = FOLD2.test_end - timedelta(days=1)
        assert BIEN_WFO.start <= lan_sang <= BIEN_WFO.end  # tầng (a) sẽ cho qua
        with pytest.raises(TimerangeViolationError, match="TƯƠNG LAI"):
            _kiem(FOLD1, FOLD1.train_start, lan_sang)

    def test_fold_doc_du_lieu_cu_hon_test_start_la_DUNG_THIET_KE(self) -> None:
        """Neo gốc: train dài dần từ T1, nên đọc dữ liệu cũ hơn `test_start`
        không phải vi phạm. Chiều nguy hiểm chỉ có MỘT — về tương lai."""
        _kiem(FOLD3, FOLD3.train_start, FOLD3.test_end - timedelta(days=1))

    def test_pham_vi_dao_nguoc_thi_raise(self) -> None:
        with pytest.raises(TimerangeViolationError, match="đảo ngược"):
            _kiem(FOLD1, FOLD1.test_start, FOLD1.train_start)


class TestBayLechQuyUocMotNgay:
    """⚠️ Cửa sổ fold NỬA MỞ `[start, end)` vs `observed_*` BAO GỒM hai
    đầu. Trộn hai quy ước là lệch đúng một ngày — và một ngày ở đây là
    MỘT NGÀY DỮ LIỆU TƯƠNG LAI."""

    def test_ngay_cuoi_cho_phep_la_test_end_TRU_MOT(self) -> None:
        _kiem(FOLD1, FOLD1.train_start, FOLD1.test_end - timedelta(days=1))

    def test_doc_DUNG_ngay_test_end_thi_RAISE(self) -> None:
        """Nến tại `test_end` KHÔNG thuộc fold này — nó là nến đầu tiên
        của fold sau. Nếu ai đó viết `observed_end > test_end` thay vì
        `>= test_end` thì đúng ca này đỏ."""
        with pytest.raises(TimerangeViolationError):
            _kiem(FOLD1, FOLD1.train_start, FOLD1.test_end)


class _BoChayGia:
    """Bộ chạy GIẢ — xem giới hạn (1) ở docstring đầu file."""

    def __init__(self, *, lech_ngay: int = 0, so_lenh: int = 40) -> None:
        self.lech_ngay = lech_ngay
        self.so_lenh = so_lenh

    def __call__(self, fold: Fold) -> FoldEquity:
        pnl = (1.0,) * self.so_lenh
        return FoldEquity(
            chi_so=fold.chi_so,
            starting_balance=1000.0,
            final_balance=1000.0 + sum(pnl),
            pnl_abs=pnl,
            observed_start=fold.train_start,
            observed_end=fold.test_end - timedelta(days=1) + timedelta(days=self.lech_ngay),
        )


class TestNoiVaoOrchestrator:
    def test_bo_chay_khai_dung_pham_vi_thi_chay_duoc(self, tmp_path: Path) -> None:
        kq = chay_wfo(
            cfg=CFG,
            chay_mot_fold=_BoChayGia(),
            data_hashes={"x": "h"},
            von_ban_dau=1000.0,
            cache_dir=tmp_path / "cache",
            repo_dir=REPO_ROOT,
        )
        assert len(kq.folds) == len(FOLDS)

    def test_bo_chay_doc_lan_MOT_NGAY_sang_tuong_lai_thi_RAISE(self, tmp_path: Path) -> None:
        """Một ngày — đúng độ lệch mà bẫy quy ước gây ra."""
        with pytest.raises(TimerangeViolationError):
            chay_wfo(
                cfg=CFG,
                chay_mot_fold=_BoChayGia(lech_ngay=1),
                data_hashes={"x": "h"},
                von_ban_dau=1000.0,
                cache_dir=tmp_path / "cache",
                repo_dir=REPO_ROOT,
            )

    def test_ket_qua_doc_sai_pham_vi_KHONG_duoc_ghi_vao_cache(self, tmp_path: Path) -> None:
        """Ghi cache một kết quả đọc sai vùng dữ liệu là chôn nó lại cho
        lần sau HIT thẳng vào, lúc đó phép kiểm không còn cơ hội chạy.

        🔑 Ca này ÉP được thứ nó kiểm: fold 1-2 ĐẠT (cache có thật 2 mục),
        fold 3 mới lệch — nếu chỉ cho fold 1 lệch thì thư mục cache còn
        chưa được tạo và assert "rỗng" đúng một cách vô nghĩa (bài học từ
        TD-0145).
        """

        class LechOFold3(_BoChayGia):
            def __call__(self, fold: Fold) -> FoldEquity:
                self.lech_ngay = 1 if fold.chi_so == 3 else 0
                return super().__call__(fold)

        cache_dir = tmp_path / "cache"
        with pytest.raises(TimerangeViolationError):
            chay_wfo(
                cfg=CFG,
                chay_mot_fold=LechOFold3(),
                data_hashes={"x": "h"},
                von_ban_dau=1000.0,
                cache_dir=cache_dir,
                repo_dir=REPO_ROOT,
            )
        assert len(list(cache_dir.glob("*.json"))) == 2

    def test_muc_cache_cu_thieu_observed_thi_TU_CHOI_dung_lai(self, tmp_path: Path) -> None:
        """Mục cache ghi bởi code TRƯỚC TD-0148 không có ngày để mà kiểm.
        Fail-closed: từ chối dùng lại, buộc chạy lại — KHÔNG đoán ngày,
        KHÔNG bỏ qua phép kiểm."""
        from tool_d.wfo.orchestrator import _tu_payload

        with pytest.raises(ValueError, match="trước TD-0148"):
            _tu_payload(
                {
                    "chi_so": 1,
                    "starting_balance": 1000.0,
                    "final_balance": 1100.0,
                    "pnl_abs": [100.0],
                },
                fold=FOLD1,
            )

    def test_ket_qua_lay_TU_CACHE_cung_bi_kiem_pham_vi(self, tmp_path: Path) -> None:
        """Cùng lý do L-Z47 chạy cho cả nhánh HIT: một mục cache có thể
        được ghi bởi phiên bản code cũ hơn phép kiểm này."""
        import json

        from tool_d.wfo.cache import ghi_cache, van_tay_hien_tai
        from tool_d.wfo.orchestrator import _khoa_cache

        cache_dir = tmp_path / "cache"
        van_tay = van_tay_hien_tai(cfg=CFG, data_hashes={"x": "h"}, repo_dir=REPO_ROOT)
        for fold in FOLDS:
            ghi_cache(
                khoa=_khoa_cache(fold),
                payload={
                    "chi_so": fold.chi_so,
                    "starting_balance": 1000.0,
                    "final_balance": 1040.0,
                    "pnl_abs": [1.0] * 40,
                    "observed_start": fold.train_start.isoformat(),
                    # lệch một ngày sang tương lai, chôn sẵn trong cache
                    "observed_end": fold.test_end.isoformat(),
                },
                van_tay=van_tay,
                cache_dir=cache_dir,
                ghi_luc="2026-09-08T00:00:00Z",
            )
        assert json.loads  # giữ import có ích, tránh hiểu nhầm là thừa

        with pytest.raises(TimerangeViolationError):
            chay_wfo(
                cfg=CFG,
                chay_mot_fold=_BoChayGia(),
                data_hashes={"x": "h"},
                von_ban_dau=1000.0,
                cache_dir=cache_dir,
                repo_dir=REPO_ROOT,
            )
