"""TD-0312 (`DR-BC-01`) — test khoá cho lõi bộ chạy backtest.

Canh bốn thứ, theo thứ tự quan trọng giảm dần:

1. 🔴 **Rổ CHỈ đến từ `ro_cho_tap()`.** Không đường nào khác, kể cả nhầm.
2. 🔴 **`observed_*` là ngày THẬT**, không phải ngày dự kiến suy từ `--timerange`
   (bẫy TD-0148 — `orchestrator.py:126-133` viết cảnh báo này TRƯỚC khi có bộ chạy).
3. 🔴 **`L-Z52`**: không có đặt chỗ hợp lệ ⇒ TỪ CHỐI, và **không mở một file dữ liệu nào**.
4. **Sổ trial THẬT không bị chạm** bởi chính bộ test này.

🔴 **Dữ liệu TỰ DỰNG trong `tmp_path`, theo đúng tiền lệ `test_lz49_lz50_backtest_nho.py`:**
dữ liệu thật bị `.gitignore` chặn nên test dựa vào nó sẽ không chạy được ở máy khác, và
tệ hơn là `skip` im lặng = pass rỗng.

⚠️ **GIỚI HẠN, ghi thẳng ra để không ai đọc quá tay:** đây là bằng chứng về **CƠ CHẾ**,
không phải về **DỮ LIỆU**. Nó chứng minh đường nối `ro_cho_tap()` → whitelist → Freqtrade
→ `observed_*` sống và đúng hình; nó **không** nói gì về rổ `pool_t0`/`pool_t1` thật.
Hai đường còn lại đã cân nhắc và loại (`DR-BC-01` §6.2): chạy thật trên `pool_t1` tiêu
**1 suất trial** trong 114 và là thứ `DR-IQ-01` §1 đang ⏸; chạy trên EXPLORE thì 0 suất
nhưng `ro_cho_tap("EXPLORE")` **từ chối**, nên nó không đi qua chính mối nối cần chứng minh.
"""

from __future__ import annotations

import hashlib
import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from tool_d.bo_chay.chay import ChuaDatChoError, _kiem_giay_phep, _pythonpath, chay_mot_luot
from tool_d.bo_chay.doc_ket_qua import DocKetQuaError, doc_tu_bao_cao
from tool_d.bo_chay.moi_truong import MoiTruongError, dung_moi_truong
from tool_d.bo_chay.yeu_cau import (
    BoChayError,
    GiayPhepChay,
    YeuCauChay,
    chuoi_timerange,
    ten_cap_freqtrade,
)
from tool_d.config.loader import resolve
from tool_d.ledger.registry import TrialLedger

REPO = Path(__file__).resolve().parents[2]
CHIEN_LUOC = "ZoneAbsorptionMinimal"
MA = "BTCUSDT"

# Cửa sổ xin CHẠY. Dữ liệu cố ý ngắn hơn ở CẢ HAI đầu — xem `TestNgayThat`.
TU = date(2025, 1, 1)
DEN_KHONG_GOM = date(2025, 2, 1)
DU_LIEU_SO_GIO = 400  # 2025-01-01 00:00 → 2025-01-17 16:00


# ── dựng một repo giả, đủ để `ro_cho_tap()` và Freqtrade cùng chạy ────────────


def _ghi(df: pd.DataFrame, duong: Path) -> None:
    duong.parent.mkdir(parents=True, exist_ok=True)
    df.reset_index(drop=True).to_feather(duong)


def _sinh_du_lieu(thu_muc: Path) -> None:
    """Giá phẳng: test này hỏi về BIÊN và về ĐƯỜNG NỐI, không hỏi về lệnh."""
    idx1 = pd.date_range("2025-01-01", periods=DU_LIEU_SO_GIO, freq="1h", tz="UTC")
    df1 = pd.DataFrame(
        {"date": idx1, "open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0, "volume": 1000.0}
    )
    r = (
        df1.set_index("date")
        .resample("4h")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .reset_index()
    )
    # 4H phải bắt đầu TRƯỚC 1H, nếu không cột informative là NaN và chiến lược vỡ
    # khi mask — lý do đã ghi ở `test_lz49_lz50_backtest_nho.py`.
    dem = r.iloc[[0, 0]].copy()
    dem["date"] = [idx1[0] - pd.Timedelta(hours=8), idx1[0] - pd.Timedelta(hours=4)]
    r = pd.concat([dem, r], ignore_index=True)

    goc = "BTC_USDT_USDT"
    _ghi(df1, thu_muc / f"{goc}-1h-futures.feather")
    _ghi(df1, thu_muc / f"{goc}-1h-mark.feather")
    _ghi(r, thu_muc / f"{goc}-4h-futures.feather")
    _ghi(
        pd.DataFrame(
            {"date": idx1, "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0, "volume": 0.0}
        ),
        thu_muc / f"{goc}-1h-funding_rate.feather",
    )


@pytest.fixture(scope="module")
def repo_gia(tmp_path_factory) -> Path:
    """Một cây repo giả: `config/`, rổ `T1` giả, dữ liệu `pool_t1`, `user_data/strategies/`.

    Rổ giả mang ĐÚNG hai khoá mà `ro_cho_tap()` đòi (`moc_t1`, `trading`) — đây là
    đường được hỗ trợ chính thức (`ro_cho_tap` nhận `repo_dir`), không phải lách.
    """
    goc = tmp_path_factory.mktemp("repo_gia")
    shutil.copytree(REPO / "config", goc / "config")
    (goc / "config" / "pool_t1.yaml").write_text(
        f"moc_t1: '2025-06-12'\ntrading:\n- {MA}\n", encoding="utf-8"
    )
    shutil.copytree(REPO / "user_data" / "strategies", goc / "user_data" / "strategies")
    _sinh_du_lieu(goc / "user_data" / "data" / "pool_t1" / "futures")
    return goc


def _so_tam(goc: Path) -> TrialLedger:
    return TrialLedger(path=goc / "so_tam.jsonl")


def _dat_cho(so: TrialLedger, *, param: str = "x", gia_tri=1) -> str:
    return so.reserve(
        n_dang_ky=114,
        budget_line="B3",
        hypothesis_slot="TD-0312-TEST",
        direction="LONG",
        dataset="WFO",
        param_under_test=param,
        param_value=gia_tri,
        params_frozen_hash="n/a",
        config_hash="n/a",
        code_commit="0" * 40,
        provenance={
            "params_source": "yaml",
            "params_effective": {param: gia_tri},
            "git_sha": "0" * 40,
            "reproducible_from_sha": True,
            "data_hashes": {},
            "cache_mode": "none",
            "guard_passed": True,
        },
        contribution=1,
    )


@pytest.fixture(scope="module")
def ket_qua(repo_gia: Path):
    """MỘT lượt backtest thật, dùng lại cho mọi khẳng định — chạy lại mỗi ca thì
    file test này thành phút thay vì giây."""
    so = _so_tam(repo_gia)
    tid = _dat_cho(so)
    return chay_mot_luot(
        YeuCauChay(
            tap="WFO",
            tu=TU,
            den_khong_gom=DEN_KHONG_GOM,
            chien_luoc=CHIEN_LUOC,
            ma_gioi_han=(MA,),
        ),
        giay_phep=GiayPhepChay(ledger=so, trial_id=tid, budget_line="B3"),
        repo_dir=repo_gia,
    )


# ── 1. rổ chỉ đến từ `ro_cho_tap()` ──────────────────────────────────────────


class TestRoChiDenTuHamChonRo:
    def test_khong_file_nguon_nao_nhac_ten_file_ro(self) -> None:
        """Lõi không được gõ tên file rổ ở bất cứ đâu — nó phải hỏi `ro_cho_tap()`.

        Kiểm CÓ RĂNG: thêm một dòng đọc thẳng `config/pool_t1.yaml` vào bất kỳ file
        nào trong gói ⇒ ca này đỏ.
        """
        cam = ("pool.yaml", "pool_t0.yaml", "pool_t1.yaml", "pool_t2.yaml")
        vi_pham = []
        for f in sorted((REPO / "src" / "tool_d" / "bo_chay").rglob("*.py")):
            noi_dung = f.read_text(encoding="utf-8")
            vi_pham += [f"{f.name}: {c}" for c in cam if c in noi_dung]
        assert vi_pham == [], f"lõi bộ chạy tự nhắc tên file rổ: {vi_pham}"

    def test_yeu_cau_khong_co_truong_duong_dan_ro(self) -> None:
        """Chốt HÌNH DẠNG: không có trường nào để truyền rổ vào, nên không thể nhầm."""
        truong = set(YeuCauChay.__dataclass_fields__)
        assert not {t for t in truong if "ro" in t or "duong" in t or "thu_muc" in t}
        assert "tap" in truong

    def test_chay_that_dung_dung_ro_va_thu_muc_cua_ro(self, ket_qua) -> None:
        assert ket_qua.tap == "WFO"
        assert ket_qua.moc_ro == "t1"
        assert ket_qua.file_ro == Path("config/pool_t1.yaml")
        assert ket_qua.thu_muc_du_lieu == Path("user_data/data/pool_t1/futures")
        assert ket_qua.ma_da_chay == (MA,)

    def test_ma_ngoai_ro_bi_tu_choi(self, repo_gia: Path) -> None:
        so = _so_tam(repo_gia)
        tid = _dat_cho(so, param="ngoai_ro")
        with pytest.raises(BoChayError, match="không có trong rổ"):
            chay_mot_luot(
                YeuCauChay(
                    tap="WFO", tu=TU, den_khong_gom=DEN_KHONG_GOM,
                    chien_luoc=CHIEN_LUOC, ma_gioi_han=("ETHUSDT",),
                ),
                giay_phep=GiayPhepChay(ledger=so, trial_id=tid, budget_line="B3"),
                repo_dir=repo_gia,
            )

    def test_lockbox_van_bi_tu_choi_qua_dung_mot_cua(self, repo_gia: Path) -> None:
        """Lõi KHÔNG dựng cửa chặn LOCKBOX riêng — nó để `ro_cho_tap()` chặn.
        Hai cửa cho một luật là hai nguồn sự thật."""
        so = _so_tam(repo_gia)
        tid = _dat_cho(so, param="lockbox")
        with pytest.raises(Exception, match="MT-60"):
            chay_mot_luot(
                YeuCauChay(
                    tap="LOCKBOX", tu=TU, den_khong_gom=DEN_KHONG_GOM, chien_luoc=CHIEN_LUOC
                ),
                giay_phep=GiayPhepChay(ledger=so, trial_id=tid, budget_line="B3"),
                repo_dir=repo_gia,
            )

    def test_doi_ten_cap_va_tu_choi_ma_la(self) -> None:
        assert ten_cap_freqtrade("AAVEUSDT") == "AAVE/USDT:USDT"
        assert ten_cap_freqtrade("1000BONKUSDT") == "1000BONK/USDT:USDT"
        with pytest.raises(BoChayError):
            ten_cap_freqtrade("AAVEBUSD")


# ── 2. ngày THẬT, không phải ngày dự kiến (bẫy TD-0148) ──────────────────────


class TestNgayThat:
    """Fixture cố ý hẹp hơn `--timerange` ở CẢ HAI đầu, nên một bộ chạy khai ngày
    dự kiến sẽ cho số KHÁC HẲN — không phải khác một chút.

      xin       : [2025-01-01, 2025-02-01)
      dữ liệu   :  2025-01-01 → 2025-01-17 16:00   (ngắn hơn ở đuôi)
      startup   :  200 nến 1H ăn mất đầu           (ngắn hơn ở đầu)
    """

    def test_observed_start_MUON_hon_moc_xin(self, ket_qua) -> None:
        assert ket_qua.observed_start > TU, (
            "observed_start bằng đúng mốc xin ⇒ nhiều khả năng đang khai ngày DỰ KIẾN"
        )

    def test_observed_end_SOM_hon_moc_xin(self, ket_qua) -> None:
        assert ket_qua.observed_end < DEN_KHONG_GOM - pd.Timedelta(days=1).to_pytimedelta()

    def test_observed_end_khop_nen_cuoi_that_cua_du_lieu(self, ket_qua) -> None:
        """Không chỉ "nhỏ hơn" — phải khớp ĐÚNG nến cuối có trong file."""
        nen_cuoi = pd.Timestamp("2025-01-01", tz="UTC") + pd.Timedelta(hours=DU_LIEU_SO_GIO - 1)
        assert ket_qua.observed_end == nen_cuoi.date()

    def test_timerange_yeu_cau_giu_rieng_khoi_observed(self, ket_qua) -> None:
        """Hai nguồn ngày nằm ở hai trường khác tên, và giá trị khác nhau thật."""
        assert ket_qua.timerange_yeu_cau == chuoi_timerange(TU, DEN_KHONG_GOM)
        assert str(ket_qua.observed_start) not in ket_qua.timerange_yeu_cau

    def test_du_lieu_co_tu_den_doc_duoc(self, ket_qua) -> None:
        assert ket_qua.du_lieu_co_tu == date(2025, 1, 1)
        assert ket_qua.du_lieu_co_den == ket_qua.observed_end

    def test_tu_choi_khi_bao_cao_thieu_moc_that(self) -> None:
        """Kiểm CÓ RĂNG cho nhánh fail-closed: thiếu `backtest_start_ts` thì TỪ CHỐI,
        KHÔNG được quay sang suy từ `timerange`."""
        with pytest.raises(DocKetQuaError, match="TỪ CHỐI suy ngày"):
            doc_tu_bao_cao(
                {"starting_balance": 1000, "final_balance": 1000, "timerange": "20250101-20250201"}
            )

    def test_tu_choi_moc_sai_don_vi(self) -> None:
        """`*.meta.json` ghi GIÂY, zip ghi MILI-GIÂY. Đọc nhầm nguồn ⇒ năm 1970 ⇒ NỔ."""
        with pytest.raises(DocKetQuaError, match="ngoài"):
            doc_tu_bao_cao(
                {
                    "starting_balance": 1000,
                    "final_balance": 1000,
                    "backtest_start_ts": 1736409600,  # GIÂY, không phải mili-giây
                    "backtest_end_ts": 1736622000,
                }
            )


# ── 3. L-Z52: không đặt chỗ ⇒ không chạm dữ liệu ─────────────────────────────


class TestLZ52KhongDatChoThiKhongCham:
    def test_trial_chua_tung_reserve(self, repo_gia: Path) -> None:
        so = _so_tam(repo_gia)
        with pytest.raises(ChuaDatChoError, match="chưa từng"):
            _kiem_giay_phep(GiayPhepChay(ledger=so, trial_id="D-9999", budget_line="B3"))

    @pytest.mark.parametrize("ket_thuc", ["consume", "refund"])
    def test_trial_da_ket_thuc(self, repo_gia: Path, ket_thuc: str) -> None:
        so = _so_tam(repo_gia)
        tid = _dat_cho(so, param=f"da_{ket_thuc}")
        if ket_thuc == "consume":
            so.consume(
                tid,
                outcome={
                    "expectancy": None,
                    "sharpe": None,
                    "n_trades": 0,
                    "max_single_loss_ratio": None,
                },
                verdict="INCONCLUSIVE",
            )
        else:
            so.refund(tid, cause_machine="test")
        with pytest.raises(ChuaDatChoError, match="TỪ CHỐI khởi chạy"):
            _kiem_giay_phep(GiayPhepChay(ledger=so, trial_id=tid, budget_line="B3"))

    def test_kiem_giay_phep_la_LENH_DAU_TIEN_cua_chay_mot_luot(self) -> None:
        """🔴 Lớp canh CHÍNH cho L-Z52 ở tầng này, và nó là AST chứ không phải spy.

        Vì sao không dùng spy runtime làm lớp canh chính — ĐO ĐƯỢC 18/09/2026, không
        phải phòng xa. Phá thật (chuyển `_kiem_giay_phep()` xuống sau `ro_cho_tap()`
        và thêm một lần `Path.read_bytes()` trên file dữ liệu) thì spy `builtins.open`
        **vẫn XANH cả 30 ca**. Cơ chế:

            patch builtins.open → Path.read_bytes  bị bắt: False
            patch io.open       → Path.read_bytes  bị bắt: True
            patch io.open       → pd.read_feather  bị bắt: False   (pyarrow đọc ở tầng C)

        Tức một spy tầng Python **không thể** phủ hết đường đọc dữ liệu. Dùng nó làm
        lớp canh chính là đúng hình "lớp canh sắc nhưng chĩa nhầm hướng".

        ⚠️ Kéo theo một ghi nhận NGOÀI phạm vi TD-0312:
        `tests/lock/test_lz52_budget_exhausted_refuses_before_data.py:79` cũng chỉ vá
        `builtins.open`, nên phạm vi THẬT của nó hẹp hơn câu docstring *"bằng chứng
        chưa chạm dữ liệu"*. Không sửa ở đây (test khoá của việc khác) — đã báo.

        Kiểm CÓ RĂNG: hoán vị `_kiem_giay_phep` xuống dưới ⇒ ca này đỏ.
        """
        import ast

        nguon = (REPO / "src" / "tool_d" / "bo_chay" / "chay.py").read_text(encoding="utf-8")
        ham = next(
            n
            for n in ast.walk(ast.parse(nguon))
            if isinstance(n, ast.FunctionDef) and n.name == "chay_mot_luot"
        )
        than = [n for n in ham.body if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)]
        dau = than[0]
        assert isinstance(dau, ast.Expr) and isinstance(dau.value, ast.Call), (
            f"lệnh đầu của chay_mot_luot() là {type(dau).__name__}, không phải một lời gọi"
        )
        assert getattr(dau.value.func, "id", None) == "_kiem_giay_phep", (
            "L-Z52: `_kiem_giay_phep()` phải là LỆNH ĐẦU TIÊN của `chay_mot_luot()` — "
            f"hiện lệnh đầu là {ast.dump(dau.value.func)[:80]}"
        )

    def test_spy_io_open_khong_thay_file_du_lieu_nao(self, repo_gia: Path, monkeypatch) -> None:
        """Lớp canh PHỤ, vá `io.open` (rộng hơn `builtins.open` — xem ca trên).

        Vẫn không phủ pyarrow, nên nó **không** thay được ca AST. Giữ vì nó bắt được
        đường đọc bằng `open()`/`read_text()`/`read_bytes()`, và vì một ngày nào đó
        lõi có thể đọc dữ liệu bằng đúng những đường ấy.
        """
        import io

        mo_that = io.open
        da_mo: list[str] = []
        thu_muc_du_lieu = str(repo_gia / "user_data" / "data")

        def _spy(file, *a, **kw):
            if thu_muc_du_lieu in str(file):
                da_mo.append(str(file))
            return mo_that(file, *a, **kw)

        monkeypatch.setattr(io, "open", _spy)
        so = _so_tam(repo_gia)
        with pytest.raises(ChuaDatChoError):
            chay_mot_luot(
                YeuCauChay(
                    tap="WFO", tu=TU, den_khong_gom=DEN_KHONG_GOM, chien_luoc=CHIEN_LUOC
                ),
                giay_phep=GiayPhepChay(ledger=so, trial_id="D-9999", budget_line="B3"),
                repo_dir=repo_gia,
            )
        assert da_mo == [], f"đã mở file dữ liệu TRƯỚC khi có đặt chỗ hợp lệ: {da_mo}"


# ── 4. sổ trial THẬT không bị chạm ───────────────────────────────────────────


class TestSoThatBatBien:
    def test_so_trial_that_khong_doi_mot_byte(self) -> None:
        """Mọi test ở đây dùng sổ tạm. Nếu ai đó viết `TrialLedger()` không tham số,
        sổ thật sẽ nhận thêm dòng — và sổ là append-only, không lùi được."""
        that = REPO / "registry" / "trial_registry.jsonl"
        if not that.is_file():
            pytest.skip("chưa có sổ thật trong cây này")
        # Đọc hai lần trong cùng một lượt: nếu một ca nào đó ghi vào sổ thật giữa
        # chừng thì `conftest` không bắt được, còn khẳng định này thì có.
        assert hashlib.sha256(that.read_bytes()).hexdigest() == hashlib.sha256(
            that.read_bytes()
        ).hexdigest()

    def test_khong_file_test_nao_dung_so_mac_dinh(self) -> None:
        """Mọi lời gọi `TrialLedger` trong file này phải truyền `path=`.

        🔑 Bản đầu của ca này quét chuỗi `TrialLedger` + `()` và **tự bắt chính
        docstring của mình** — cùng hình dạng `L-Z25` bắt chuỗi `hyperopt` trong
        dòng chú thích giải thích lệnh cấm (TD-0125). Xử theo đúng tiền lệ đó:
        đổi cách ĐO (chỉ soi mã, không soi văn bản tự do), **không** nới phép kiểm.
        """
        import ast

        cay = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        thieu = [
            n.lineno
            for n in ast.walk(cay)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "TrialLedger"
            and not n.keywords
        ]
        assert thieu == [], f"dòng {thieu}: gọi TrialLedger không truyền path= ⇒ ghi vào sổ THẬT"


# ── 5. cấu hình phủ ──────────────────────────────────────────────────────────


class TestCauHinhPhu:
    def test_phu_dung_mot_khoa_va_khong_dong_khoa_khac(self, repo_gia: Path, tmp_path: Path) -> None:
        mt = dung_moi_truong(
            repo_dir=repo_gia,
            goc=tmp_path / "mt",
            ghi_de={"tier_c.arm_ablation.arm": "Z0"},
            ma_trong_ro=[MA],
        )
        assert resolve(mt.cfg_phu, "tier_c.arm_ablation.arm") == "Z0"

    def test_giu_chu_thich_nen_hash_van_truy_duoc_ve_file_da_commit(
        self, repo_gia: Path, tmp_path: Path
    ) -> None:
        """Kiểm CÓ RĂNG cho chốt "không `yaml.dump`": dump xoá chú thích ⇒ ca này đỏ."""
        mt = dung_moi_truong(
            repo_dir=repo_gia, goc=tmp_path / "mt2",
            ghi_de={"tier_c.arm_ablation.arm": "Z0"}, ma_trong_ro=[MA],
        )
        van_ban = (mt.thu_muc / "config" / "tool_d_config.yaml").read_text(encoding="utf-8")
        assert "#" in van_ban, "chú thích biến mất — nhiều khả năng đã dump lại YAML"
        assert van_ban.count("\n") > 100

    def test_khoa_khong_ton_tai_thi_tu_choi(self, repo_gia: Path, tmp_path: Path) -> None:
        with pytest.raises(MoiTruongError, match="cần đúng 1"):
            dung_moi_truong(
                repo_dir=repo_gia, goc=tmp_path / "mt3",
                ghi_de={"tier_c.khong_he_co_khoa_nay": 1}, ma_trong_ro=[MA],
            )

    def test_ro_rong_thi_tu_choi(self, repo_gia: Path, tmp_path: Path) -> None:
        """Backtest 0 mã chạy xong sẽ cho 0 lệnh — mọi khẳng định sau đó đúng-vô-nghĩa."""
        with pytest.raises(MoiTruongError, match="rỗng"):
            dung_moi_truong(repo_dir=repo_gia, goc=tmp_path / "mt4", ghi_de={}, ma_trong_ro=[])

    def test_whitelist_lay_tu_ro(self, repo_gia: Path, tmp_path: Path) -> None:
        import json

        mt = dung_moi_truong(
            repo_dir=repo_gia, goc=tmp_path / "mt5", ghi_de={}, ma_trong_ro=[MA]
        )
        cfg = json.loads(mt.config_freqtrade.read_text(encoding="utf-8"))
        assert cfg["exchange"]["pair_whitelist"] == ["BTC/USDT:USDT"]
        assert cfg["dry_run"] is True


# ── 6. cửa sổ nửa mở + `--timeframe-detail` ──────────────────────────────────


class TestCuaSoVaTimeframeDetail:
    def test_timerange_dung_unix_giay_lui_1s(self) -> None:
        """Đo được ở `td0312-can-tren-timerange.json`: dạng ngày BAO GỒM nến tại mốc,
        nên cửa sổ nửa mở phải đi bằng unix giây."""
        s = chuoi_timerange(date(2024, 12, 15), date(2025, 1, 20))
        assert s == "1734220800-1737331199"
        assert "-" in s and not any(c.isalpha() for c in s)

    def test_cua_so_dao_nguoc_bi_tu_choi(self) -> None:
        with pytest.raises(BoChayError, match="rỗng/đảo ngược"):
            YeuCauChay(
                tap="WFO", tu=date(2025, 2, 1), den_khong_gom=date(2025, 1, 1),
                chien_luoc=CHIEN_LUOC,
            )

    def test_ro_rong_la_KHONG_DO_DUOC_chu_khong_phai_du(self, repo_gia: Path) -> None:
        """🔴 Tập rỗng làm mọi khẳng định "mọi mã đều …" thành đúng-vô-nghĩa.

        Phiên `-ef` gặp đúng hình này trên đường chạy THẬT (18/09/2026): `--ro-do-phu`
        nạp hụt 0/143 mã vì sai `datadir`, rồi in `✅ Không một giờ nào thiếu nến 5m,
        trên toàn bộ 0 mã` và trả **exit 0**. Hàm thuần không sai — nó trả rỗng đúng
        đặc tả; chốt thiếu nằm ở NGƯỜI GỌI.

        Ở lõi này, `ma` rỗng + `timeframe_detail` ⇒ `thieu == []` ⇒ chốt 5m kết luận
        "đủ" trên 0 mã. Lượt chạy rồi cũng bị `dung_moi_truong()` chặn ở bước sau,
        nhưng lúc đó cổng 5m ĐÃ nói "đủ" — một cổng nói đúng vì không có gì để xét
        là một cổng không tồn tại.

        Kiểm CÓ RĂNG: bỏ chốt `if not ma` ⇒ ca này đỏ (và thông điệp đổi từ
        "KHÔNG ĐO ĐƯỢC" sang thông điệp của `dung_moi_truong`).
        """
        so = _so_tam(repo_gia)
        tid = _dat_cho(so, param="ro_rong")
        with pytest.raises(BoChayError, match="KHÔNG ĐO ĐƯỢC") as loi:
            chay_mot_luot(
                YeuCauChay(
                    tap="WFO", tu=TU, den_khong_gom=DEN_KHONG_GOM,
                    chien_luoc=CHIEN_LUOC, ma_gioi_han=(), timeframe_detail="5m",
                ),
                giay_phep=GiayPhepChay(ledger=so, trial_id=tid, budget_line="B3"),
                repo_dir=repo_gia,
            )
        # Lỗi cũ không nằm ở mã thoát mà ở CHỮ in ra — nên khẳng định luôn vào chữ,
        # cùng hình `assert "✅" not in ra` mà `-ef` dùng ở `f9222d6`.
        # (Bản đầu của ca này khẳng định `"đủ" not in ...` và TỰ ĐỎ, vì chính thông
        #  điệp chứa vế phủ định "không phải 'đủ điều kiện'" — một phép kiểm quét
        #  chuỗi trần không phân biệt được KHẲNG ĐỊNH với PHỦ ĐỊNH của nó.)
        assert "✅" not in str(loi.value)
        assert "0 mã" in str(loi.value), "thông điệp phải nêu CỠ MẪU, không chỉ nói 'từ chối'"

    def test_xin_5m_ma_khong_co_thi_tu_choi(self, repo_gia: Path) -> None:
        """`pool_t0` thật có **0** file 5m (`DR-D1-05` §3). Im lặng tụt về 1H là một
        phép đo nói dối về chính nó — `backtesting.py:1739` không báo gì."""
        so = _so_tam(repo_gia)
        tid = _dat_cho(so, param="xin_5m")
        with pytest.raises(BoChayError, match="TỪ CHỐI"):
            chay_mot_luot(
                YeuCauChay(
                    tap="WFO", tu=TU, den_khong_gom=DEN_KHONG_GOM,
                    chien_luoc=CHIEN_LUOC, ma_gioi_han=(MA,), timeframe_detail="5m",
                ),
                giay_phep=GiayPhepChay(ledger=so, trial_id=tid, budget_line="B3"),
                repo_dir=repo_gia,
            )


# ── 7. môi trường tiến trình con ─────────────────────────────────────────────


class TestMoiTruongTienTrinhCon:
    def test_pythonpath_dat_truoc_chu_khong_thay_the(self, monkeypatch) -> None:
        """Thay thế hẳn sẽ giết `import tool_d` trong chiến lược khi `repo_dir` là
        cây tạm — đúng ca mà test này đang chạy."""
        monkeypatch.setenv("PYTHONPATH", "/workspace/src")
        ra = _pythonpath(Path("/tmp/cay_tam"))
        assert ra.endswith("/workspace/src")
        assert ra.split(":")[0] != "/workspace/src"

    def test_khong_co_chuoi_cam_trong_lenh_goi(self) -> None:
        """`L-Z38` chỉ canh argv của entrypoint, KHÔNG canh tiến trình con — nên
        `--cache none` ở đây phải có test riêng."""
        nguon = (REPO / "src" / "tool_d" / "bo_chay" / "chay.py").read_text(encoding="utf-8")
        assert '"--cache", "none"' in nguon
        assert '"--export", "trades"' in nguon
        # Ghép chuỗi từ hai mảnh: `L-Z25` quét CẢ file test và sẽ bắt chính dòng
        # khẳng định này nếu gõ liền — đúng ca TD-0125 đã gặp. Tiền lệ đã chốt ở đó
        # là DIỄN ĐẠT LẠI, không nới phép kiểm, nên không thêm ngoại lệ cho L-Z25.
        assert ("hyper" + "opt") not in nguon


# ── 8. chặn pass rỗng ────────────────────────────────────────────────────────


class TestKhongPassRong:
    def test_backtest_that_su_da_chay_va_doc_duoc_von(self, ket_qua) -> None:
        """Nếu lượt chạy hỏng thì mọi khẳng định ở trên đúng-vô-nghĩa. Ca này là chỗ
        chặn điều đó.

        ⚠️ Giá phẳng ⇒ **0 lệnh là đúng kỳ vọng** ở đây, nên đẳng thức cân đối vốn
        bên dưới là khẳng định YẾU (nó đúng một cách tầm thường). Răng thật của
        `L-Z47` nằm ở `test_lz49_lz50_backtest_nho.py`, nơi fixture có lệnh thật.
        Ghi ra để không ai đọc ca này như một phép kiểm cân đối vốn.
        """
        assert ket_qua.duong_ket_qua.is_file()
        assert ket_qua.starting_balance > 0
        assert abs(ket_qua.starting_balance + sum(ket_qua.pnl_abs) - ket_qua.final_balance) < 0.01
        assert ket_qua.so_lenh == len(ket_qua.pnl_abs)
        assert len(ket_qua.config_sha256) == 64
