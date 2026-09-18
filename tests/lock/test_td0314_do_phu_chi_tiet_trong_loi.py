"""TD-0314 (`DR-D1-05` §3b.4) — lõi bộ chạy kiểm ĐỘ PHỦ 5m, không chỉ kiểm file tồn tại.

Tiêu chí đã chốt: *không một giờ 1H nào thiếu nến 5m tương ứng, ở mọi mã* — đủ hoặc TỪ CHỐI.
Chủ dự án chốt 18/09/2026 cách lấy dữ liệu: **nạp hai lần** (lõi tự nạp, không nhận lời khai của
tiến trình con).

Canh năm thứ:

1. 🔴 **Thủng giữa chuỗi bị bắt** — ca mà chốt `is_file()` cũ cho qua. Đây là răng chính.
2. 🔴 **Nạp KHÔNG lấp**: Freqtrade mặc định lấp chỗ thủng bằng nến giả (đo 18/09/2026: thủng 3 giờ,
   lấp ⇒ 576 nến và hàm độ phủ trả rỗng). Đổi `fill_up_missing=False` về mặc định ⇒ ca (1) đỏ.
3. **Không chặt quá mức** — phủ đủ thì đi qua tới bước dựng môi trường; thủng NGOÀI cửa sổ xin
   chạy không chặn. Một chốt không bao giờ thoả được sớm muộn bị gỡ.
4. **Khung chính rỗng trong cửa sổ = KHÔNG ĐO ĐƯỢC**, không phải "đủ" (N6).
5. **Đúng MỘT chốt**: chốt `is_file()` cũ đã xoá khỏi `chay_mot_luot()`.

Dữ liệu tự dựng trong `tmp_path` (tiền lệ `test_td0312_loi_bo_chay.py`): dữ liệu thật bị
`.gitignore` chặn. Không ca nào chạy backtest — mọi ca dừng ở bước 3 hoặc ở lính canh đặt tại
bước 4, nên file này chạy trong vài giây.
"""

from __future__ import annotations

import ast
import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

import tool_d.bo_chay.chay as chay_mod
from tool_d.bo_chay.chay import chay_mot_luot
from tool_d.bo_chay.yeu_cau import BoChayError, GiayPhepChay, YeuCauChay
from tool_d.ledger.registry import TrialLedger

REPO = Path(__file__).resolve().parents[2]
CHIEN_LUOC = "ZoneAbsorptionMinimal"
MA_DU = "BTCUSDT"
MA_THUNG = "ETHUSDT"

TU = date(2025, 1, 1)
DEN_KHONG_GOM = date(2025, 2, 1)
SO_GIO = 400  # 2025-01-01 00:00 → 2025-01-17 15:00

#: Ba giờ thủng giữa chuỗi 5m của `MA_THUNG` — nằm TRONG cửa sổ [TU, DEN_KHONG_GOM).
THUNG_TU, THUNG_DEN = "2025-01-10 05:00", "2025-01-10 08:00"


class _DaQuaBuoc3(Exception):
    """Lính canh đặt thay `dung_moi_truong()`: tới được bước 4 nghĩa là chốt độ phủ đã cho qua."""


def _nen(idx: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(
        {"date": idx, "open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0, "volume": 1000.0}
    )


def _ghi(df: pd.DataFrame, duong: Path) -> None:
    duong.parent.mkdir(parents=True, exist_ok=True)
    df.reset_index(drop=True).to_feather(duong)


def _dung_repo(goc: Path, *, thung: tuple[str, str] | None, co_5m_thung: bool = True) -> Path:
    """Repo giả, rổ `T1` hai mã. `MA_DU` phủ đủ 5m; `MA_THUNG` mang chỗ thủng `thung` (hoặc
    không có file 5m nào nếu `co_5m_thung=False`)."""
    shutil.copytree(REPO / "config", goc / "config")
    (goc / "config" / "pool_t1.yaml").write_text(
        f"moc_t1: '2025-06-12'\ntrading:\n- {MA_DU}\n- {MA_THUNG}\n", encoding="utf-8"
    )
    thu_muc = goc / "user_data" / "data" / "pool_t1" / "futures"
    idx1 = pd.date_range("2025-01-01", periods=SO_GIO, freq="1h", tz="UTC")
    idx5 = pd.date_range("2025-01-01", periods=SO_GIO * 12, freq="5min", tz="UTC")
    for ma in (MA_DU, MA_THUNG):
        ten = f"{ma[:-4]}_USDT_USDT"
        _ghi(_nen(idx1), thu_muc / f"{ten}-1h-futures.feather")
        df5 = _nen(idx5)
        if ma == MA_THUNG:
            if not co_5m_thung:
                continue
            if thung is not None:
                bo = (df5["date"] >= pd.Timestamp(thung[0], tz="UTC")) & (
                    df5["date"] < pd.Timestamp(thung[1], tz="UTC")
                )
                df5 = df5[~bo]
        _ghi(df5, thu_muc / f"{ten}-5m-futures.feather")
    return goc


def _giay_phep(goc: Path) -> GiayPhepChay:
    so = TrialLedger(path=goc / "so_tam.jsonl")
    tid = so.reserve(
        n_dang_ky=114,
        budget_line="B3",
        hypothesis_slot="TD-0314-TEST",
        direction="LONG",
        dataset="WFO",
        param_under_test="x",
        param_value=1,
        params_frozen_hash="n/a",
        config_hash="n/a",
        code_commit="0" * 40,
        provenance={
            "params_source": "yaml",
            "params_effective": {"x": 1},
            "git_sha": "0" * 40,
            "reproducible_from_sha": True,
            "data_hashes": {},
            "cache_mode": "none",
            "guard_passed": True,
        },
        contribution=1,
    )
    return GiayPhepChay(ledger=so, trial_id=tid, budget_line="B3")


def _chay(goc: Path, *, tu: date = TU, den: date = DEN_KHONG_GOM, detail: str | None = "5m"):
    return chay_mot_luot(
        YeuCauChay(
            tap="WFO", tu=tu, den_khong_gom=den, chien_luoc=CHIEN_LUOC, timeframe_detail=detail
        ),
        giay_phep=_giay_phep(goc),
        repo_dir=goc,
        goc_tam=goc / "moi_truong_tam",
    )


@pytest.fixture
def linh_canh_buoc4(monkeypatch) -> None:
    def _dung(**_kw):
        raise _DaQuaBuoc3

    monkeypatch.setattr(chay_mod, "dung_moi_truong", _dung)


# ── 1 + 2. thủng giữa chuỗi bị bắt (và chỉ bắt được khi nạp KHÔNG lấp) ────────


class TestThungGiuaChuoi:
    def test_thung_giua_chuoi_bi_tu_choi_truoc_khi_dung_moi_truong(self, tmp_path: Path) -> None:
        """Ca chốt `is_file()` cũ cho QUA: file 5m của `MA_THUNG` tồn tại, chỉ thủng 3 giờ.

        Kiểm CÓ RĂNG (đã làm 18/09/2026): đổi `fill_up_missing=False` → mặc định (lấp) ⇒ ca này
        đỏ, vì Freqtrade lấp 3 giờ thủng bằng nến giả và hàm độ phủ trả rỗng.
        """
        goc = _dung_repo(tmp_path, thung=(THUNG_TU, THUNG_DEN))
        file_5m = goc / "user_data/data/pool_t1/futures/ETH_USDT_USDT-5m-futures.feather"
        assert file_5m.is_file(), "tiền đề: file 5m TỒN TẠI — tức chốt cũ sẽ cho qua"

        with pytest.raises(BoChayError) as loi:
            _chay(goc)
        chu = str(loi.value)
        assert "TỪ CHỐI" in chu
        assert "ETH/USDT:USDT: thủng 3/" in chu, chu
        assert "1/2 mã" in chu, "phải nêu cỡ mẫu và chỉ đích danh mã thủng, không gộp mã đủ"
        assert "BTC/USDT:USDT" not in chu, "mã phủ đủ không được bị kể là thiếu"
        assert not (goc / "moi_truong_tam").exists(), "phải từ chối TRƯỚC khi dựng môi trường"

    def test_khong_co_file_5m_bi_tu_choi(self, tmp_path: Path) -> None:
        """Ca cũ vẫn phải bị bắt: một mã không có file 5m nào. Freqtrade tự nó không báo gì
        (`fail_without_data=True` chỉ nổ khi MỌI mã đều thiếu)."""
        goc = _dung_repo(tmp_path, thung=None, co_5m_thung=False)
        with pytest.raises(BoChayError, match="TỪ CHỐI") as loi:
            _chay(goc)
        assert "ETH/USDT:USDT: KHÔNG nạp được khung chi tiết" in str(loi.value)


# ── 3. không chặt quá mức ─────────────────────────────────────────────────────


class TestKhongChatQuaMuc:
    def test_phu_du_thi_di_qua_toi_buoc_dung_moi_truong(self, tmp_path: Path, linh_canh_buoc4) -> None:
        """"Ảnh trong gương của PASS RỖNG": một chốt luôn từ chối vẫn làm mọi ca ở trên xanh.
        Ca này chặn điều đó — đi đúng đường `chay_mot_luot()`, tới được bước 4."""
        goc = _dung_repo(tmp_path, thung=None)
        with pytest.raises(_DaQuaBuoc3):
            _chay(goc)

    def test_thung_ngoai_cua_so_khong_chan(self, tmp_path: Path, linh_canh_buoc4) -> None:
        """Phép kiểm dùng CÙNG `timerange` sẽ truyền cho Freqtrade, không quét cả file: chỗ
        thủng ngày 02/01 không liên quan tới lượt chạy bắt đầu 05/01."""
        goc = _dung_repo(tmp_path, thung=("2025-01-02 05:00", "2025-01-02 08:00"))
        with pytest.raises(_DaQuaBuoc3):
            _chay(goc, tu=date(2025, 1, 5))

    def test_khong_xin_detail_thi_khong_kiem(self, tmp_path: Path, linh_canh_buoc4) -> None:
        """Không xin `--timeframe-detail` thì không có gì để phủ — kể cả khi 5m thiếu hẳn."""
        goc = _dung_repo(tmp_path, thung=None, co_5m_thung=False)
        with pytest.raises(_DaQuaBuoc3):
            _chay(goc, detail=None)


# ── 4. tập rỗng ───────────────────────────────────────────────────────────────


class TestTapRong:
    def test_khung_chinh_rong_trong_cua_so_la_KHONG_DO_DUOC(self, tmp_path: Path) -> None:
        """Dữ liệu hết ngày 17/01; xin chạy từ 20/01 ⇒ 0 giờ 1H để phủ. `cho_thieu_khung_chi_tiet`
        trả rỗng đúng đặc tả — chốt thiếu nằm ở người gọi, cùng bẫy `--ro-do-phu` 0/143 mã."""
        goc = _dung_repo(tmp_path, thung=None)
        with pytest.raises(BoChayError, match="KHÔNG ĐO ĐƯỢC") as loi:
            _chay(goc, tu=date(2025, 1, 20))
        assert "0/2 mã" in str(loi.value)
        assert "✅" not in str(loi.value)


# ── 5. đúng MỘT chốt ──────────────────────────────────────────────────────────


class TestMotChot:
    def test_chot_is_file_cu_da_xoa_va_chot_moi_duoc_goi_dung_mot_lan(self) -> None:
        """Giữ cả hai chốt là giữ hai nguồn sự thật cho một việc. Soi AST của
        `chay_mot_luot()`, không soi văn bản (chú thích được phép nhắc tới chốt cũ)."""
        nguon = (REPO / "src" / "tool_d" / "bo_chay" / "chay.py").read_text(encoding="utf-8")
        ham = next(
            n
            for n in ast.walk(ast.parse(nguon))
            if isinstance(n, ast.FunctionDef) and n.name == "chay_mot_luot"
        )
        goi = [n for n in ast.walk(ham) if isinstance(n, ast.Call)]
        is_file = [n.lineno for n in goi if getattr(n.func, "attr", None) == "is_file"]
        kiem = [n for n in goi if getattr(n.func, "id", None) == "_kiem_do_phu_chi_tiet"]
        assert is_file == [], f"chay_mot_luot() còn gọi .is_file() ở dòng {is_file}"
        assert len(kiem) == 1, f"_kiem_do_phu_chi_tiet() được gọi {len(kiem)} lần, cần đúng 1"
