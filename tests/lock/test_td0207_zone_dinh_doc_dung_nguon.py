"""TD-0207 — `_zone_dinh_tren` / `_tuoi_zone_dinh_nen` phải đọc ĐÚNG NGUỒN.

Lỗi được vá (TD-0206 đo được, 88 mã / 22 lệnh thật, 0 trial): hai hàm này
đọc cột `zone_dinh_gia` từ `_df_4h()`, nhưng `_df_4h` gọi
`dp.get_pair_dataframe()` — trả **OHLCV thô, đúng 6 cột**
(`date,open,high,low,close,volume`). Cột chỉ báo sinh trong
`populate_indicators` không có mặt ở đó; sau `merge_informative_pair` tên
thật của nó là `zone_dinh_gia_4h` và nó sống trên khung 1H.

⇒ `_zone_dinh_tren` rơi `return []` **22/22 lần**, TP1 **luôn** dùng nạng,
H-4 = 100% là defect chứ không phải cấu trúc thị trường. `_tuoi_zone_dinh_nen`
chết theo ⇒ `tp_zone_age_bars` luôn `None` ⇒ ràng buộc 1 của `DR-D4-06`
chưa bao giờ thoả được.

🔑 **Vì sao suite 1648 xanh vẫn không bắt được:** `return []` không phân biệt
được với *"quét được nhưng không có zone nào"*. Không exception, không ca đỏ.
Và `_quet_zone_dinh` — BÊN SINH — thì hoạt động đúng thật (4.775 zone), nên
mọi phép kiểm chĩa vào nó đều xanh. Đây là *hình dạng lỗi thứ năm* đã ghi ở
`research-log` 10/09: **kiểm BÊN SINH không kiểm được ĐƯỜNG ĐI.**

Hai lớp canh dưới đây nhắm đúng hai nửa của lớp lỗi đó:
  · `TestKhongDocCotVangMat` — canh ĐƯỜNG ĐỌC (cấu trúc, AST).
  · `TestTuoiLayLanXacNhanDauTien` — canh cái bẫy ffill mà bản vá suýt dính.
"""

from __future__ import annotations

import ast
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHIEN_LUOC = REPO_ROOT / "user_data" / "strategies" / "ZoneAbsorption.py"


def _than_ham(nguon: str, ten: str) -> ast.FunctionDef:
    cay = ast.parse(nguon)
    for nut in ast.walk(cay):
        if isinstance(nut, ast.FunctionDef) and nut.name == ten:
            return nut
    raise AssertionError(f"không tìm thấy hàm {ten} — đổi tên thì phải cập nhật lớp canh này")


class TestKhongDocCotVangMat:
    """Không hàm nào được đọc cột `zone_dinh_gia` trần từ kết quả `_df_4h()`.

    Đây là chốt CẤU TRÚC, không phải chốt giá trị: nó cấm chính *đường đọc*
    đã sai, nên một bản viết lại vô tình quay về cách cũ sẽ đỏ ngay — kể cả
    khi backtest vẫn chạy trơn và không lệnh nào lỗi.
    """

    @pytest.mark.parametrize("ten", ["_zone_dinh_tren", "_tuoi_zone_dinh_nen"])
    def test_khong_nhac_ten_cot_tran(self, ten: str) -> None:
        nguon = CHIEN_LUOC.read_text(encoding="utf-8")
        than = ast.get_source_segment(nguon, _than_ham(nguon, ten)) or ""
        # Bỏ docstring: nó CÓ nhắc tên cột để giải thích chính lỗi này.
        than_khong_doc = than.replace(ast.get_docstring(_than_ham(nguon, ten)) or "", "")
        assert '"zone_dinh_gia"' not in than_khong_doc, (
            f"{ten} đọc lại cột `zone_dinh_gia` từ `_df_4h()` — cột đó KHÔNG BAO GIỜ "
            "có mặt ở đó (TD-0206 đo được 22/22 lần vắng). Dùng "
            "`_zone_dinh_da_xac_nhan()` (tính lại bằng `_quet_zone_dinh`)."
        )

    @pytest.mark.parametrize("ten", ["_zone_dinh_tren", "_tuoi_zone_dinh_nen"])
    def test_di_qua_ham_tinh_lai(self, ten: str) -> None:
        """Đối chứng DƯƠNG — thiếu ca này thì một hàm rỗng cũng qua ca trên."""
        nguon = CHIEN_LUOC.read_text(encoding="utf-8")
        than = ast.get_source_segment(nguon, _than_ham(nguon, ten)) or ""
        assert "_zone_dinh_da_xac_nhan" in than, (
            f"{ten} phải lấy zone qua `_zone_dinh_da_xac_nhan()` — nếu không thì "
            "ca `test_khong_nhac_ten_cot_tran` xanh một cách vô nghĩa"
        )

    def test_ham_tinh_lai_dung_quet_zone_dinh_chu_khong_viet_lai(self) -> None:
        """MT-03 — cùng một hàm quét, không phải bản sao thứ hai sẽ trôi lệch."""
        nguon = CHIEN_LUOC.read_text(encoding="utf-8")
        than = ast.get_source_segment(nguon, _than_ham(nguon, "_zone_dinh_da_xac_nhan")) or ""
        assert "_quet_zone_dinh" in than
        assert "la_diem_swing" not in than, (
            "chép lại vòng quét là dựng nguồn sự thật thứ hai (MT-03) — gọi "
            "`_quet_zone_dinh` thay vì viết lại"
        )


class TestTuoiLayLanXacNhanDauTien:
    """`_tuoi_zone_dinh_nen` phải neo vào lần xác nhận ĐẦU TIÊN.

    🔴 Cái bẫy mà bản vá suýt dính: nếu ai đó vá bằng cách đọc cột đã merge
    (`zone_dinh_gia_4h`), `merge_informative_pair(..., ffill=True)` **kéo dài**
    giá zone qua các nến sau ⇒ một giá khớp cả một DẢI. Bản cũ lấy
    `khop.iloc[-1]` (lần cuối) ⇒ tuổi ra **≈ 0 ở MỌI lệnh**, sai im lặng đúng
    lớp `L-Z48c` — và `DR-D4-06` §2.3 lại dựa vào đúng con số đó để xét lại
    quyết định bỏ hạn dùng §1.3.

    Ca dưới đây mô phỏng chính tình huống lặp đó và đòi lấy mốc ĐẦU.
    """

    @staticmethod
    def _chien_luoc():
        spec = importlib.util.spec_from_file_location("za_td0207", CHIEN_LUOC)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod.ZoneAbsorption.__new__(mod.ZoneAbsorption)

    def test_lay_moc_dau_tien_khi_gia_zone_lap_lai(self, monkeypatch) -> None:
        s = self._chien_luoc()
        now = datetime(2025, 7, 1, tzinfo=timezone.utc)
        dau = now - timedelta(hours=40)  # 10 nến 4H trước
        lap = [(dau + timedelta(hours=4 * k), 100.0) for k in range(10)]
        monkeypatch.setattr(type(s), "_zone_dinh_da_xac_nhan", lambda self, p, t: lap)
        assert s._tuoi_zone_dinh_nen("X/USDT:USDT", now, 100.0) == 10, (
            "lấy mốc CUỐI sẽ ra 0 — đó chính là hình dạng lỗi ffill mà ca này canh"
        )

    def test_khong_tim_thay_thi_None_chu_khong_phai_0(self) -> None:
        """N6 — 'không tra được tuổi' khác hẳn 'zone vừa xác nhận nến này'."""
        s = self._chien_luoc()
        now = datetime(2025, 7, 1, tzinfo=timezone.utc)
        type(s)._zone_dinh_da_xac_nhan = lambda self, p, t: [(now, 55.0)]
        assert s._tuoi_zone_dinh_nen("X/USDT:USDT", now, 100.0) is None
