"""🔴 TD-0170 — DG1/DG2/DG5 KHÔNG được nhìn thấy nến tương lai (callback).

Phiên `-d5` phát hiện khi rà tĩnh `ZoneAbsorption` (08/09/2026): trong
backtest, `dp.get_pair_dataframe()` trả **TOÀN BỘ** dữ liệu đã nạp — kể cả
nến chưa xảy ra tại `current_time`. Chỉ `get_analyzed_dataframe()` mới bị
cắt. Bản nháp đầu lấy `iloc[-1]` của khung 4H trong callback, nên cả ba
cổng đều "biết" giá sắp tới.

════ Vì sao `H4-D` không bắt được, và vì sao cần file này ════

`H4-D` (§7.5) canh lookahead ở `populate_*` — nơi zone được phát hiện. Ba
hàm này sống ở **callback** (`adjust_trade_position`, `custom_exit`), một
mặt cắt `H4-D` **không phủ**. Cùng họ lỗi B2, khác chỗ đứng.

Đã vá bằng `_df_4h(pair, current_time)` cắt `date + 4h ≤ now`. File này là
thứ **giữ** phép cắt đó.

════ Ba lớp, và vì sao thiếu lớp nào cũng hở ════

**(a) Hành vi trên MỐC QUYẾT ĐỊNH THẬT.** Không dựng tay: mốc lấy từ
`orders` của một lượt backtest thật, và hàm được gọi là chính `_df_4h` của
production. Đây là bài học TD-0168 (*thứ được canh phải nằm trên đường
chạy*) và TD-0188 (*đường chạy phải đi qua nhánh cần canh* — nên đòi lệnh
đủ **3 tranche**, vì tranche 2/3 mới là lúc ba cổng được hỏi).

**(b) Chốt AST.** Lớp (a) chỉ chứng minh `_df_4h` cắt đúng; nó **không**
chứng minh mọi chỗ đọc khung 4H đều đi qua `_df_4h`. Một callback thêm sau
đọc thẳng `get_pair_dataframe` sẽ lọt sạch. Nên đòi: chuỗi đó xuất hiện
ĐÚNG MỘT lần trong file, và ba helper đều gọi `_df_4h`.

**(c) Có răng.** Bỏ phép cắt → (a) phải đỏ. Một chốt không kiểm được là
một chốt không ai biết còn sống hay không.
"""

from __future__ import annotations

import ast
import importlib.util
from datetime import timezone
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHIEN_LUOC_PATH = REPO_ROOT / "user_data" / "strategies" / "ZoneAbsorption.py"

# ── tái dùng ĐÚNG bộ chạy backtest của TD-0187 ────────────────────────
# `tests/` không phải package nên nạp bằng importlib — cùng cách file
# TD-0187 nạp lại bộ sinh nến của L-Z49. Tái dùng chứ KHÔNG chép: một bộ
# chạy thứ hai sẽ trôi lệch khỏi bộ chạy đang sinh số thật.
_spec = importlib.util.spec_from_file_location(
    "td0187", REPO_ROOT / "tests" / "lock" / "test_td0187_dinh_co_lenh_backtest_that.py"
)
_td0187 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_td0187)  # type: ignore[union-attr]

_chay, _lenh_vao, CAP = _td0187._chay, _td0187._lenh_vao, _td0187.CAP
#: Tên cặp dạng SÀN. `_DpGia` bỏ qua tham số này, nhưng viết đúng vẫn
#: cần: nếu sau này ai thay `_DpGia` bằng `dp` thật thì một chuỗi sai sẽ
#: trả về khung rỗng và MỌI ca lookahead thành xanh-vô-nghĩa.
PAIR = CAP.replace("_USDT_USDT", "/USDT:USDT")
SAN_XUAT = _td0187.SAN_XUAT


@pytest.fixture(scope="module")
def tmp_module(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("td0170")


@pytest.fixture(scope="module")
def kq(tmp_module) -> dict:
    return _chay(tmp_module, SAN_XUAT)


@pytest.fixture(scope="module")
def df_4h_day_du(tmp_module) -> pd.DataFrame:
    """ĐÚNG thứ `dp.get_pair_dataframe()` trả trong backtest: toàn bộ khung
    4H đã nạp, KHÔNG cắt. Đọc từ chính datadir lượt chạy vừa rồi."""
    p = tmp_module / "data" / "futures" / f"{CAP}-4h-futures.feather"
    assert p.exists(), f"không thấy {p} — bộ sinh dữ liệu của TD-0187 đã đổi?"
    df = pd.read_feather(p)
    assert len(df) > 50, f"chỉ {len(df)} nến 4H — quá ít để phân biệt cắt hay không cắt"
    return df


class _DpGia:
    """`dp` giả trả về TOÀN BỘ khung 4H — mô phỏng đúng hành vi backtest
    (đó chính là điều khiến lookahead xảy ra được)."""

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def get_pair_dataframe(self, pair: str, timeframe: str) -> pd.DataFrame:
        return self._df


class _SelfGia:
    """Đủ thuộc tính để gọi hàm `_df_4h` THẬT như một hàm không ràng buộc."""

    informative_timeframe = "4h"

    def __init__(self, df: pd.DataFrame) -> None:
        self.dp = _DpGia(df)


def _df_4h_that():
    """Hàm `_df_4h` THẬT, nạp từ file chiến lược sản xuất."""
    spec = importlib.util.spec_from_file_location("zone_absorption", CHIEN_LUOC_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.ZoneAbsorption._df_4h


def _moc_vao_lenh(kq: dict) -> list[pd.Timestamp]:
    """Mốc THẬT của từng lần vào lệnh, từ lệnh đủ BA tranche.

    Đòi đủ ba vì tranche 2/3 mới là lúc DG1/DG2/DG5 được hỏi — một lệnh
    một tranche đi qua file này mà không chạm cổng nào (bài học TD-0188:
    đường chạy phải đi qua đúng nhánh cần canh).
    """
    du_ba = [t for t in kq["trades"] if len(_lenh_vao(t)) == 3]
    assert du_ba, f"không lệnh nào đủ 3 tranche: {[len(_lenh_vao(t)) for t in kq['trades']]}"
    # `order_filled_timestamp` là epoch MS — tên khoá thật của Freqtrade,
    # đọc từ chính file kết quả backtest chứ không đoán (bản đầu tôi đoán
    # `order_filled_date` và ba ca nổ `KeyError`).
    moc = [
        pd.Timestamp(o["order_filled_timestamp"], unit="ms", tz=timezone.utc)
        for o in _lenh_vao(du_ba[0])
    ]
    assert len(set(moc)) == 3, f"ba tranche trùng mốc thời gian: {moc}"
    return moc


class TestCatTaiMocQuyetDinhThat:
    """(a) — đường chạy thật, mốc thật, hàm thật."""

    def test_khong_nen_NAO_chua_dong_lot_qua(self, kq, df_4h_day_du) -> None:
        """🔴 Bất biến cốt lõi: tại `t`, chỉ nến đã ĐÓNG (`date + 4h ≤ t`)
        được nhìn thấy. Một nến `date + 4h > t` là nến còn đang chạy hoặc
        chưa xảy ra — dùng `close` của nó là biết trước tương lai."""
        df_4h = _df_4h_that()
        for t in _moc_vao_lenh(kq):
            cat = df_4h(_SelfGia(df_4h_day_du), PAIR, t)
            assert len(cat) > 0, f"cắt rỗng tại {t} — cổng sẽ không có dữ liệu để xét"
            muon_nhat = cat["date"].max()
            assert muon_nhat + pd.Timedelta(hours=4) <= t, (
                f"tại {t} lọt nến đóng lúc {muon_nhat + pd.Timedelta(hours=4)} — LOOKAHEAD"
            )

    def test_so_nen_TANG_theo_thoi_gian_khong_phai_hang_so(self, kq, df_4h_day_du) -> None:
        """🔴 Ca này bịt lỗ mà ca trên không thấy: một cài đặt trả về **rỗng**
        hoặc trả về **cùng một lát cắt** cũng thoả bất biến trên. Phải chứng
        minh lát cắt LỚN DẦN theo mốc — tức nó thật sự bám `current_time`.

        Cùng khuôn phép phá của TD-0188: đòi bằng chứng SỐ HỌC rằng đầu vào
        đổi, không chỉ bằng chứng "có được gọi"."""
        df_4h = _df_4h_that()
        moc = _moc_vao_lenh(kq)
        so_nen = [
            len(df_4h(_SelfGia(df_4h_day_du), PAIR, t))
            for t in moc
        ]
        assert so_nen == sorted(so_nen), f"số nến không tăng theo mốc: {list(zip(moc, so_nen))}"
        assert so_nen[-1] > so_nen[0], (
            f"số nến KHÔNG đổi giữa tranche 1 và tranche 3 ({so_nen}) — lát cắt không "
            "bám current_time, hoặc ba tranche rơi cùng một nến 4H"
        )

    def test_cat_BO_that_su_mot_phan_du_lieu(self, kq, df_4h_day_du) -> None:
        """Nếu lát cắt luôn bằng toàn bộ dữ liệu thì phép cắt là vô hiệu —
        và hai ca trên vẫn xanh nếu mốc cuối nằm sau nến cuối cùng."""
        df_4h = _df_4h_that()
        moc = _moc_vao_lenh(kq)
        cat_dau = df_4h(_SelfGia(df_4h_day_du), PAIR, moc[0])
        assert len(cat_dau) < len(df_4h_day_du), (
            f"tại tranche 1 lát cắt = {len(cat_dau)} = TOÀN BỘ {len(df_4h_day_du)} nến — "
            "phép cắt không bỏ đi gì cả"
        )


class TestDoiChungAmPhepCatCoRang:
    """(c) — kiểm có răng, dưới dạng ĐỐI CHỨNG ÂM THƯỜNG TRỰC.

    🔴 **Vì sao KHÔNG phá file sản xuất tại chỗ.** Lần đầu tôi ghi thẳng
    `return df` vào `ZoneAbsorption.py` để phá. Phiên song song ghi đè file
    đó giữa chừng, phép phá biến mất, và lượt chạy báo "12 passed" — một
    phép đo HỎNG trông y hệt một phép đo đạt. Với file thuộc sân phiên
    khác thì `cp` sao lưu cũng không cứu được, vì người kia có thể ghi đè
    trước khi mình hoàn nguyên.

    Nên phép phá nằm ngay đây, cô lập trong bộ nhớ, chạy MỖI LẦN: dựng một
    `_df_4h` KHÔNG cắt rồi đòi nó **làm đỏ** đúng bất biến ở trên. Nếu một
    ngày nào đó bản không-cắt cũng đi qua được, thì bất biến đó đã mất
    răng — và ca này báo, không cần ai nhớ đi phá tay.
    """

    @staticmethod
    def _khong_cat(tu_than, pair: str, current_time):
        """Đúng `_df_4h` NHƯNG bỏ phép cắt — tức bản trước khi vá."""
        return tu_than.dp.get_pair_dataframe(pair=pair, timeframe="4h")

    def test_ban_KHONG_CAT_phai_lam_do_bat_bien_lookahead(self, kq, df_4h_day_du) -> None:
        moc = _moc_vao_lenh(kq)
        lot = []
        for t in moc:
            cat = self._khong_cat(_SelfGia(df_4h_day_du), PAIR, t)
            muon_nhat = cat["date"].max()
            if muon_nhat + pd.Timedelta(hours=4) > t:
                lot.append(t)
        assert lot, (
            "bản KHÔNG CẮT vẫn thoả bất biến — nghĩa là dữ liệu kết thúc trước mọi mốc "
            "quyết định, nên phép kiểm lookahead ở trên KHÔNG phân biệt được gì. Phải "
            "sinh thêm nến SAU tranche cuối thì bộ test này mới có nghĩa."
        )

    def test_ban_KHONG_CAT_cho_so_nen_KHONG_DOI(self, kq, df_4h_day_du) -> None:
        """Vế thứ hai: bản không cắt trả cùng một số nến ở mọi mốc — đúng
        thứ `test_so_nen_TANG_theo_thoi_gian` bắt."""
        so_nen = {
            len(self._khong_cat(_SelfGia(df_4h_day_du), PAIR, t)) for t in _moc_vao_lenh(kq)
        }
        assert len(so_nen) == 1, f"bản không cắt lẽ ra trả hằng số, nhận {so_nen}"


class TestMoiDuongDocKhung4HDeuQuaMotCua:
    """(b) — chốt AST. Lớp (a) không nói gì về một callback THÊM SAU."""

    @staticmethod
    def _cay() -> ast.Module:
        return ast.parse(CHIEN_LUOC_PATH.read_text(encoding="utf-8"))

    #: Hai chỗ ĐƯỢC PHÉP đọc thẳng `get_pair_dataframe`, và vì sao:
    #:  • `populate_indicators` — đây là mặt cắt `H4-D` CÓ phủ; Freqtrade
    #:    tự cắt dataframe theo nhịp nến khi gọi populate, nên đọc thẳng ở
    #:    đó không phải lookahead.
    #:  • `_df_4h` — cửa duy nhất cho phía CALLBACK, và nó tự cắt.
    #: Mọi hàm khác đọc thẳng đều là lookahead.
    #: 📌 Bản đầu của ca này đòi "đúng MỘT lần trong file" và đỏ ngay —
    #: siết quá tay, vì nó cấm luôn cả đường hợp lệ ở `populate_indicators`.
    #: Một chốt không bao giờ thoả được thì tệ hơn không có chốt (bài học
    #: cổng D3): sớm muộn bị gỡ, và gỡ rồi mất luôn phần đúng của nó.
    CHO_PHEP = {"populate_indicators", "_df_4h"}

    def test_KHONG_callback_nao_doc_thang_get_pair_dataframe(self) -> None:
        goi_tu = {
            n.name for n in ast.walk(self._cay())
            if isinstance(n, ast.FunctionDef)
            and any(
                isinstance(x, ast.Attribute) and x.attr == "get_pair_dataframe"
                for x in ast.walk(n)
            )
        }
        la = goi_tu - self.CHO_PHEP
        assert not la, (
            f"{sorted(la)} đọc thẳng `get_pair_dataframe` — trong backtest hàm đó trả "
            "TOÀN BỘ dữ liệu kể cả nến tương lai. Phía callback phải đi qua `_df_4h`."
        )

    def test_df_4h_van_la_mot_trong_nhung_cho_goi(self) -> None:
        """Đối chứng cho ca trên: nếu `_df_4h` thôi gọi `get_pair_dataframe`
        thì tập `goi_tu` co lại và ca kia vẫn xanh một cách rỗng."""
        goi_tu = {
            n.name for n in ast.walk(self._cay())
            if isinstance(n, ast.FunctionDef)
            and any(
                isinstance(x, ast.Attribute) and x.attr == "get_pair_dataframe"
                for x in ast.walk(n)
            )
        }
        assert "_df_4h" in goi_tu, "_df_4h không còn đọc khung 4H — cửa cắt đã biến mất"

    @pytest.mark.parametrize(
        "ham", ["_close_4h_ke_tu", "_trend_4h_hien_tai", "_zss_hien_tai"]
    )
    def test_ba_helper_cua_DG1_DG2_DG5_deu_goi_df_4h(self, ham: str) -> None:
        """Ba hàm này dựng ĐẦU VÀO cho DG1/DG2/DG5. Một cái không đi qua
        `_df_4h` là một cổng nhìn thấy tương lai."""
        node = next(
            n for n in ast.walk(self._cay())
            if isinstance(n, ast.FunctionDef) and n.name == ham
        )
        assert any(
            isinstance(x, ast.Attribute) and x.attr == "_df_4h" for x in ast.walk(node)
        ), f"{ham}() không gọi _df_4h"

    def test_df_4h_nhan_current_time_khong_tu_doan(self) -> None:
        """Cắt theo `current_time` truyền vào, không theo `datetime.now()` —
        trong backtest `now()` là thời gian THẬT, không phải thời gian mô
        phỏng, nên nó sẽ không cắt gì cả."""
        node = next(
            n for n in ast.walk(self._cay())
            if isinstance(n, ast.FunctionDef) and n.name == "_df_4h"
        )
        assert "current_time" in [a.arg for a in node.args.args], "thiếu tham số current_time"
        assert not any(
            isinstance(x, ast.Attribute) and x.attr in ("now", "utcnow")
            for x in ast.walk(node)
        ), "_df_4h dùng thời gian hệ thống — trong backtest đó không phải mốc mô phỏng"


class TestDG5NaNPhaiRaise:
    """🐛 Lỗi TD-0170 phát hiện trong `dg1_dg5_tranche_gates`, không phải
    trong chiến lược.

    `_zss_hien_tai()` trả `float("nan")` khi `volume_ratio`/`compression`
    thiếu dữ liệu. Bản đầu của `dg5_zss_khong_suy_yeu()` **im lặng trả
    `False`** (vì `NaN >= x` là `False` theo IEEE-754) — tức gộp *"không đo
    được"* vào *"cổng đóng"*, đúng hai thứ `TrancheGateError` sinh ra để
    tách và `N6` cấm gộp.

    Nguy hơn một ô trống: một cổng "đóng" trông giống một quyết định đã cân
    nhắc, nên không ai đi hỏi vì sao.
    """

    def test_zss_hien_tai_NaN_thi_RAISE(self) -> None:
        from tool_d.dg1_dg5_tranche_gates import TrancheGateError, dg5_zss_khong_suy_yeu

        with pytest.raises(TrancheGateError, match="không đo được"):
            dg5_zss_khong_suy_yeu(
                zss_tai_tranche1=0.6, zss_hien_tai=float("nan"), nguong_giam_toi_da=0.30
            )

    def test_zss_tai_tranche1_NaN_thi_RAISE(self) -> None:
        from tool_d.dg1_dg5_tranche_gates import TrancheGateError, dg5_zss_khong_suy_yeu

        with pytest.raises(TrancheGateError, match="không đo được"):
            dg5_zss_khong_suy_yeu(
                zss_tai_tranche1=float("nan"), zss_hien_tai=0.6, nguong_giam_toi_da=0.30
            )

    def test_chu_thich_trong_chien_luoc_KHOP_voi_hanh_vi_that(self) -> None:
        """`ZoneAbsorption.py` ghi *"dg5 fail-closed với NaN
        (TrancheGateError)"*. Trước TD-0170 câu đó SAI — chú thích mô tả
        theo Ý ĐỊNH chứ không theo thứ code làm, cùng hạng
        `_comment_stake_amount` của MT-16. Ca này giữ cho hai thứ đó khớp
        nhau: nếu ai gỡ chốt `NaN` thì câu chú thích lại thành lời hứa
        suông, và ca `test_zss_hien_tai_NaN_thi_RAISE` bên trên sẽ đỏ."""
        src = CHIEN_LUOC_PATH.read_text(encoding="utf-8")
        assert "TrancheGateError" in src, (
            "chiến lược không còn nhắc TrancheGateError — nếu đã đổi cách xử NaN "
            "thì cập nhật ca này cùng lượt, đừng để chú thích và code lệch nhau"
        )
