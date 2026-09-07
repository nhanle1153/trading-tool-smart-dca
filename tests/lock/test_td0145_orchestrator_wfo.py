"""TD-0145 — orchestrator WFO: nối folds + cache + equity, và nối vào E2.

Bộ chạy backtest được TIÊM VÀO, nên toàn bộ logic điều phối kiểm được TẤT
ĐỊNH mà không cần dữ liệu thị trường. Đó là lý do chính của thiết kế đó:
nếu logic này chỉ chạy được khi có backtest thật thì nó chỉ được kiểm ở D9,
tức sau khi đã tin nó suốt nhiều tháng.

🔑 Nguyên tắc áp cho từng ca ở đây (học từ ca PASS RỖNG phiên -e8 tự bắt
   được: 4 tiến trình thật vẫn xanh sau khi gỡ hẳn `flock`): mỗi test phải
   ÉP ĐƯỢC điều kiện nó nói là đang kiểm. Cụ thể — dùng bộ chạy ĐẾM SỐ LẦN
   GỌI, nên "cache HIT nên không chạy lại" là một khẳng định đo được, chứ
   không phải một suy đoán từ việc test xanh.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from tool_d.config.loader import DEFAULT_CONFIG_PATH, load_tool_d_config  # noqa: E402
from tool_d.measurement.tri_state import Status  # noqa: E402
from tool_d.wfo.cache import TrangThai, doc_cache, van_tay_hien_tai  # noqa: E402
from tool_d.wfo.equity import CanDoiFoldError, FoldEquity  # noqa: E402
from tool_d.wfo.folds import Fold, san_lenh_moi_fold, sinh_folds  # noqa: E402
from tool_d.wfo.orchestrator import chay_wfo  # noqa: E402

CFG = load_tool_d_config(REPO_ROOT / DEFAULT_CONFIG_PATH)
SAN = san_lenh_moi_fold(CFG)


class BoChayDem:
    """Bộ chạy giả có ĐẾM — biến 'không chạy lại' thành thứ đo được."""

    def __init__(self, *, so_lenh: int = 40, lai_moi_lenh: float = 1.0) -> None:
        self.so_lan_goi = 0
        self.fold_da_chay: list[int] = []
        self.so_lenh = so_lenh
        self.lai = lai_moi_lenh

    def __call__(self, fold: Fold) -> FoldEquity:
        self.so_lan_goi += 1
        self.fold_da_chay.append(fold.chi_so)
        pnl = tuple([self.lai] * self.so_lenh)
        return FoldEquity(
            chi_so=fold.chi_so,
            starting_balance=1000.0,
            final_balance=1000.0 + sum(pnl),
            pnl_abs=pnl,
        )


def _chay(thu_muc: Path, bo_chay: BoChayDem, **doi):
    return chay_wfo(
        cfg=CFG,
        chay_mot_fold=bo_chay,
        data_hashes=doi.pop("data_hashes", {"BTC": "abc"}),
        von_ban_dau=1000.0,
        cache_dir=thu_muc,
        repo_dir=REPO_ROOT,
        in_ra=doi.pop("in_ra", lambda _: None),
        **doi,
    )


@pytest.fixture
def thu_muc(tmp_path: Path) -> Path:
    return tmp_path / "wfo_cache"


class TestChayDuChuoiFold:
    def test_chay_dung_so_fold_cua_DR_D3_01(self, thu_muc: Path) -> None:
        bo = BoChayDem()
        kq = _chay(thu_muc, bo)
        assert bo.so_lan_goi == len(sinh_folds(CFG)) == 3
        assert bo.fold_da_chay == [1, 2, 3]
        assert len(kq.folds) == 3

    def test_duong_von_ghep_bang_NHAN_khong_phai_CONG(self, thu_muc: Path) -> None:
        """Bug Tool A số (6). Mỗi fold tự reset vốn 1000 -> 1040, hệ số 1.04.
        Ghép NHÂN: 1000 · 1.04³. Ghép CỘNG sẽ ra 1000 + 3·40 = 1120."""
        kq = _chay(thu_muc, BoChayDem(so_lenh=40, lai_moi_lenh=1.0))
        assert kq.duong_von[-1] == pytest.approx(1000.0 * 1.04**3)
        assert kq.duong_von[-1] != pytest.approx(1120.0)

    def test_he_so_gop_doc_duoc_khi_moi_fold_tren_san(self, thu_muc: Path) -> None:
        kq = _chay(thu_muc, BoChayDem(so_lenh=SAN + 10))
        assert kq.he_so_gop.status is Status.OK
        assert kq.so_fold_doc_duoc == 3


class TestCacheKhongChayLai:
    """'Không chạy lại' là khẳng định ĐO ĐƯỢC nhờ bộ chạy có đếm."""

    def test_lan_hai_lay_tu_cache_va_KHONG_goi_bo_chay(self, thu_muc: Path) -> None:
        bo1 = BoChayDem()
        _chay(thu_muc, bo1)
        assert bo1.so_lan_goi == 3

        bo2 = BoChayDem()
        kq2 = _chay(thu_muc, bo2)
        assert bo2.so_lan_goi == 0, "cache HIT mà vẫn chạy lại backtest"
        assert all(f.tu_cache for f in kq2.folds)

    def test_ket_qua_tu_cache_giong_het_lan_chay_dau(self, thu_muc: Path) -> None:
        kq1 = _chay(thu_muc, BoChayDem())
        kq2 = _chay(thu_muc, BoChayDem())
        assert kq1.duong_von == kq2.duong_von
        assert [f.equity for f in kq1.folds] == [f.equity for f in kq2.folds]

    def test_cache_ghi_ra_doc_lai_duoc_bang_van_tay_that(self, thu_muc: Path) -> None:
        _chay(thu_muc, BoChayDem())
        vt = van_tay_hien_tai(cfg=CFG, data_hashes={"BTC": "abc"}, repo_dir=REPO_ROOT)
        f1 = sinh_folds(CFG)[0]
        khoa = f"fold1_{f1.test_start:%Y%m%d}_{f1.test_end:%Y%m%d}"
        assert doc_cache(khoa=khoa, van_tay=vt, cache_dir=thu_muc).trang_thai is TrangThai.HIT


class TestSTALEKhongBiGopVaoMISS:
    """🔴 Bất biến chính của TD-0143 phải sống sót qua chỗ nối này.

    Gộp STALE vào MISS thì kết quả cuối vẫn ĐÚNG (đằng nào cũng chạy lại)
    nên không test nào đỏ — mất đúng tín hiệu 'có gì đó đổi ngoài ý muốn'.
    """

    def test_doi_data_hash_thi_CHAY_LAI_va_CO_canh_bao(self, thu_muc: Path) -> None:
        _chay(thu_muc, BoChayDem())

        bo2 = BoChayDem()
        da_in: list[str] = []
        kq = _chay(thu_muc, bo2, data_hashes={"BTC": "DOI_ROI"}, in_ra=da_in.append)

        assert bo2.so_lan_goi == 3, "vân tay lệch mà vẫn dùng lại cache"
        assert kq.canh_bao != (), "chạy lại IM LẶNG — mất tín hiệu, đúng lỗi cần chặn"
        assert len(da_in) == 3, "cảnh báo phải được IN RA, không chỉ gom vào kết quả"
        assert "LỆCH VÂN TAY" in kq.canh_bao[0]
        assert "data_hash" in kq.canh_bao[0]

    def test_MISS_lan_dau_thi_IM_LANG(self, thu_muc: Path) -> None:
        """Chưa có cache là bình thường — cảnh báo ở đây sẽ dạy người đọc
        bỏ qua cảnh báo, làm hỏng cả ca STALE ở trên."""
        da_in: list[str] = []
        kq = _chay(thu_muc, BoChayDem(), in_ra=da_in.append)
        assert kq.canh_bao == ()
        assert da_in == []


class TestSanSoLenhKhongBiaSo:
    """DR-D3-01 §5.2 + N6: dưới sàn thì `unreadable`, KHÔNG phải 0.0."""

    def test_duoi_san_thi_unreadable_chu_KHONG_phai_0(self, thu_muc: Path) -> None:
        kq = _chay(thu_muc, BoChayDem(so_lenh=SAN - 1))
        for f in kq.folds:
            assert f.he_so.status is Status.UNREADABLE
            assert f.he_so.value is None, "🔴 bịa số cho fold chưa đủ lệnh"
            assert str(SAN) in (f.he_so.note or "")

    def test_dung_bang_san_thi_doc_duoc(self, thu_muc: Path) -> None:
        """Ranh giới: sàn là '< san' chứ không phải '<= san'."""
        kq = _chay(thu_muc, BoChayDem(so_lenh=SAN))
        assert all(f.he_so.status is Status.OK for f in kq.folds)

    def test_mot_fold_duoi_san_thi_HE_SO_GOP_cung_khong_doc_duoc(self, thu_muc: Path) -> None:
        """Bỏ qua fold unreadable rồi nhân các fold còn lại sẽ cho một con
        số trông bình thường nhưng đo một KHOẢNG THỜI GIAN KHÁC với khoảng
        người đọc tưởng — sai lặng lẽ, đúng thứ PHẦN 0d chặn."""

        class MotFoldMong(BoChayDem):
            def __call__(self, fold: Fold) -> FoldEquity:
                self.so_lenh = 2 if fold.chi_so == 2 else SAN + 5
                return super().__call__(fold)

        kq = _chay(thu_muc, MotFoldMong())
        assert kq.folds[1].he_so.status is Status.UNREADABLE
        assert kq.he_so_gop.status is Status.UNREADABLE
        assert kq.he_so_gop.value is None
        assert "2" in (kq.he_so_gop.note or "")
        assert kq.so_fold_doc_duoc == 2


class TestLZ47FailClosed:
    def test_fold_lech_can_doi_thi_RAISE(self, thu_muc: Path) -> None:
        class BoChayLech(BoChayDem):
            def __call__(self, fold: Fold) -> FoldEquity:
                self.so_lan_goi += 1
                return FoldEquity(
                    chi_so=fold.chi_so,
                    starting_balance=1000.0,
                    final_balance=9999.0,  # không khớp Σ pnl_abs
                    pnl_abs=(1.0,) * 40,
                )

        with pytest.raises(CanDoiFoldError):
            _chay(thu_muc, BoChayLech())

    def test_fold_lech_KHONG_duoc_ghi_vao_cache(self, thu_muc: Path) -> None:
        """Ghi cache một kết quả chưa qua L-Z47 nghĩa là lần sau HIT thẳng
        vào con số sai, và phép kiểm không còn cơ hội chạy nữa.

        🔑 Ca này phải ÉP được thứ nó kiểm. Bản đầu của tôi cho fold 1 lỗi
        ngay rồi assert "thư mục cache rỗng" — nhưng lúc đó thư mục còn
        CHƯA ĐƯỢC TẠO, nên assert đúng một cách vô nghĩa: nó xanh kể cả khi
        thứ tự kiểm-rồi-ghi bị đảo. Sửa: cho fold 1 và 2 chạy ĐẠT (cache có
        thật 2 mục), fold 3 mới lệch — rồi đòi đúng 2 mục, không phải 3.
        """

        class LechOFold3(BoChayDem):
            def __call__(self, fold: Fold) -> FoldEquity:
                self.so_lan_goi += 1
                if fold.chi_so < 3:
                    pnl = (1.0,) * 40
                    return FoldEquity(
                        chi_so=fold.chi_so, starting_balance=1000.0,
                        final_balance=1000.0 + sum(pnl), pnl_abs=pnl,
                    )
                return FoldEquity(
                    chi_so=fold.chi_so, starting_balance=1000.0,
                    final_balance=9999.0, pnl_abs=(1.0,) * 40,  # lệch cân đối
                )

        with pytest.raises(CanDoiFoldError):
            _chay(thu_muc, LechOFold3())

        da_ghi = sorted(p.name for p in thu_muc.glob("*.json"))
        assert len(da_ghi) == 2, f"fold lệch vẫn lọt vào cache: {da_ghi}"
        assert not any(n.startswith("fold3_") for n in da_ghi)

    def test_cache_ban_van_bi_LZ47_bat_khi_doc_lai(self, thu_muc: Path) -> None:
        """Mục cache có thể được ghi bởi phiên bản code CŨ HƠN phép kiểm.
        Vì vậy L-Z47 chạy cho cả kết quả lấy từ cache, không chỉ kết quả mới."""
        import json

        _chay(thu_muc, BoChayDem())
        f = sorted(thu_muc.glob("*.json"))[0]
        muc = json.loads(f.read_text(encoding="utf-8"))
        muc["payload"]["final_balance"] = 12345.0  # phá cân đối
        f.write_text(json.dumps(muc), encoding="utf-8")

        with pytest.raises(CanDoiFoldError):
            _chay(thu_muc, BoChayDem())


class TestNoiVaoE2:
    def test_e2_van_la_mot_trong_8_entrypoint(self) -> None:
        from tool_d.measurement.entrypoint_registry import CLOSED_ENTRYPOINTS

        assert CLOSED_ENTRYPOINTS["E2"] == "run_wfo.py"
        assert len(CLOSED_ENTRYPOINTS) == 8

    def test_khong_con_NotImplementedError_trong_E2(self) -> None:
        nguon = (REPO_ROOT / "entrypoints/run_wfo.py").read_text(encoding="utf-8")
        assert "raise NotImplementedError" not in nguon

    def test_so_do_fold_in_ra_dung_3_fold_va_neu_san(self) -> None:
        from run_wfo import in_so_do_fold

        text = in_so_do_fold()
        for i in (1, 2, 3):
            assert f"fold {i}:" in text
        assert f"sàn số lệnh mỗi fold: {SAN}" in text
        assert "unreadable" in text

    def test_so_do_fold_neu_ro_CAI_GI_CON_THIEU(self) -> None:
        """Một cổng có thông báo, không phải traceback — và phải nói rõ
        mảnh còn thiếu, kèm ràng buộc L-Z52 cho người viết mảnh đó."""
        from run_wfo import in_so_do_fold

        text = in_so_do_fold()
        assert "CHƯA CHẠY ĐƯỢC" in text
        assert "L-Z52" in text

    def test_ma_thoat_rieng_khac_moi_ma_loi_khac(self) -> None:
        from run_backtest import EXIT_GUARD_BLOCKED
        from run_wfo import EXIT_CHUA_CO_BO_CHAY
        from trial_ledger_audit import EXIT_AUDIT_FAILED

        assert EXIT_CHUA_CO_BO_CHAY not in (0, EXIT_GUARD_BLOCKED, EXIT_AUDIT_FAILED)
