"""L-Z44 🔴 CRITICAL — Risk Supervisor khai lại hằng số, và hai bản khai
PHẢI bằng nhau (§6.6 ràng buộc 2, spec dòng 1959-1964).

Spec cho Supervisor một ngoại lệ mà nó không cho ai khác:

    "vài hằng số (E_D, thang dd 5/8/20, trần margin 0.85) bị KHAI LẠI CÓ
     CHỦ ĐÍCH — đây là ngoại lệ HỢP LỆ DUY NHẤT của nguyên tắc 'một nguồn
     sự thật' (LD-09), và phải ghi chú tường minh tại chỗ khai lại + có
     test L-Z44 đối chiếu hai bản khai bằng nhau."

🔑 Đọc kỹ mệnh đề đó: ngoại lệ KHÔNG hợp lệ vì spec cho phép nó tồn tại —
nó hợp lệ vì **có phép đối chiếu**. Bỏ phép đối chiếu đi thì thứ còn lại
không phải "một ngoại lệ hợp lệ", mà là đúng cái LD-09 cấm: hai nguồn sự
thật cho cùng một con số, trôi khỏi nhau trong im lặng. Vì thế file này
canh hai thứ KHÁC NHAU, và thứ hai mới là thứ đáng giá:

  (A) Năm hằng số khai lại KHỚP bản gốc — phép đối chiếu chạy đúng.
  (B) 🔴 Phép đối chiếu PHỦ ĐỦ mọi trường của `HangSoKhaiLai` — tức
      không tồn tại một hằng số khai lại nào đứng ngoài tầm canh.

Vì sao (B) tồn tại, bằng một ca THẬT chứ không phải lo xa: từ TD-0196
(09/09/2026) `HANG_SO_KHAI_LAI` mang đủ **năm** trường, nhưng bảng
`doi_chieu` chỉ liệt kê **bốn** — `tran_margin_ty_le` (0,85) được khai
lại mà **chưa bao giờ được đối chiếu**, suốt bốn ngày, trong khi §6.6(2)
gọi đích danh "trần margin 0.85". Không phép kiểm nào đỏ, vì mọi phép
kiểm đều hỏi *"bốn cái kia có khớp không"*, không cái nào hỏi *"có phải
chỉ có bốn cái không"*. Đây đúng hình dạng lỗi mà dự án đã đặt tên: lớp
canh sắc nhưng **chĩa nhầm hướng** — và ở dạng lặng nhất của nó, vì cái
thiếu không để lại triệu chứng nào.

(C) canh ràng buộc còn lại của §6.6(2) — *"SUPERVISOR KHÔNG IMPORT CODE
BOT"* — bằng **AST**, không bằng lời hứa trong docstring. Cùng lý do N5
chọn AST cho `L-Z36`: một ràng buộc chỉ sống trong chú thích là một
ràng buộc không có máy thi hành.

⚠️ PHẠM VI, đừng đọc quá tay: file này canh **tầng hằng số + tầng import**
của Supervisor. Nó KHÔNG chứng nhận Supervisor đã chạy như một tiến trình
riêng — việc đó chưa có (xem docstring `risk_supervisor.py`: cách nó chạy
thật là câu CHƯA CHỐT, và TD-0241 để nguyên câu đó cho chủ dự án).
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.risk_supervisor import (
    HANG_SO_KHAI_LAI,
    HangSoKhaiLai,
    kiem_khai_lai_khop_ban_goc,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FILE_SUPERVISOR = REPO_ROOT / "src" / "tool_d" / "risk_supervisor.py"

#: Đường dẫn bản GỐC cho từng trường khai lại. Giữ ở đây MỘT BẢN ĐỘC LẬP
#: với bảng `doi_chieu` trong code sản xuất — nếu test đọc chính bảng đó
#: rồi so với chính nó thì phép kiểm luôn xanh, đúng lỗi "hai vế cùng một
#: nguồn" mà `L-Z55` đã dính một lần (xem research-log 08/09/2026).
DUONG_DAN_GOC: dict[str, str] = {
    "e_d": "tier_a.E_D",
    "dd_soft_pct": "tier_c.dd_ladder_pct.soft",
    "dd_halt_pct": "tier_c.dd_ladder_pct.halt",
    "dd_abort_pct": "tier_c.dd_ladder_pct.abort",
    # §6.8f là GỐC của 0,85; `mult_deploy_thr` là bên MƯỢN — xem
    # `admission.py:80-88`. KHÔNG thêm khoá YAML thứ ba cho cùng con số.
    "tran_margin_ty_le": "tier_frozen.mult_deploy_thr.value",
}

#: Tiền tố module bị CẤM xuất hiện trong `import` cấp cao nhất của
#: Supervisor. Đây là danh sách CẤM chứ không phải danh sách CHO PHÉP, và
#: đó là lựa chọn có ý thức: ca (C) chỉ cần chặn đúng thứ §6.6(2) gọi tên
#: là "code bot". Phần CHO PHÉP được canh bằng ca `chi_dung_thu_vien_chuan`
#: bên dưới, nên hai ca cộng lại vẫn fail-closed với một import lạ.
CAM_IMPORT = ("freqtrade", "user_data", "tool_d.config", "tool_d.strategy")


class TestKhaiLaiKhopBanGoc:
    """(A) — năm hằng số khai lại khớp bản gốc trong `tool_d_config.yaml`."""

    def test_khop_tren_config_that(self) -> None:
        cfg = load_tool_d_config()
        lech = kiem_khai_lai_khop_ban_goc(cfg, doc_resolve=resolve)
        assert lech == [], f"hai bản khai đã trôi khỏi nhau: {lech}"

    @pytest.mark.parametrize("truong", sorted(DUONG_DAN_GOC))
    def test_tung_truong_khop_duong_doc_doc_lap(self, truong: str) -> None:
        """Đọc lại bản gốc bằng đường của TEST, không mượn bảng của code.

        Ca này và `kiem_khai_lai_khop_ban_goc()` đi hai đường khác nhau
        tới cùng một kết luận — nên nếu ai đó sửa bảng `doi_chieu` trỏ
        sang một khoá YAML khác cho tiện, ca này vẫn bắt được.
        """
        cfg = load_tool_d_config()
        goc = float(resolve(cfg, DUONG_DAN_GOC[truong]))
        khai = float(getattr(HANG_SO_KHAI_LAI, truong))
        assert khai == pytest.approx(goc), (
            f"{truong}: Supervisor khai {khai}, bản gốc "
            f"{DUONG_DAN_GOC[truong]} = {goc}"
        )


class TestPhepDoiChieuPhuDuMoiTruong:
    """(B) 🔴 — không hằng số khai lại nào được đứng ngoài tầm canh."""

    def test_moi_truong_cua_dataclass_deu_co_duong_goc(self) -> None:
        """Thêm một hằng số khai lại mà quên đối chiếu ⇒ ca này ĐỎ.

        Đây là ca đã bắt `tran_margin_ty_le` (khai lại từ TD-0196, chưa
        bao giờ được đối chiếu tới TD-0241).
        """
        truong_dataclass = {f.name for f in dataclasses.fields(HangSoKhaiLai)}
        thieu = truong_dataclass - set(DUONG_DAN_GOC)
        assert not thieu, (
            f"hằng số khai lại KHÔNG có đường đối chiếu: {sorted(thieu)}. "
            "§6.6(2) chỉ hợp lệ KHI có phép đối chiếu — thêm đường gốc "
            "vào DUONG_DAN_GOC và vào `doi_chieu` của risk_supervisor.py."
        )

    def test_khong_co_duong_goc_thua(self) -> None:
        """Chiều ngược lại: một đường gốc trỏ tới trường đã bị xoá là một
        phép kiểm chạy trên hư không — nó xanh mà không canh gì cả."""
        truong_dataclass = {f.name for f in dataclasses.fields(HangSoKhaiLai)}
        thua = set(DUONG_DAN_GOC) - truong_dataclass
        assert not thua, f"đường gốc trỏ tới trường không còn tồn tại: {sorted(thua)}"

    def test_ham_doi_chieu_that_su_cham_TUNG_truong(self) -> None:
        """KIỂM CÓ RĂNG — không tin bảng, bắt hàm tự khai.

        Với MỖI trường, dựng một `doc_resolve` giả trả đúng bản khai cho
        mọi đường TRỪ đường của trường đang xét (lệch đi 1.0). Nếu
        `kiem_khai_lai_khop_ban_goc()` thật sự đối chiếu trường đó thì
        phải báo đúng 1 chỗ lệch và nêu đúng tên trường.
        """
        for truong, duong_dan_lech in DUONG_DAN_GOC.items():
            def resolve_gia(_cfg: object, duong_dan: str, _lech: str = duong_dan_lech) -> float:
                nguoc = {v: k for k, v in DUONG_DAN_GOC.items()}
                gia_tri = float(getattr(HANG_SO_KHAI_LAI, nguoc[duong_dan]))
                return gia_tri + 1.0 if duong_dan == _lech else gia_tri

            lech = kiem_khai_lai_khop_ban_goc({"cfg": "gia"}, doc_resolve=resolve_gia)
            assert len(lech) == 1, (
                f"làm lệch {truong} mà hàm báo {len(lech)} chỗ — "
                "trường này nhiều khả năng KHÔNG nằm trong bảng đối chiếu"
            )
            assert truong in lech[0], f"báo lệch nhưng không nêu tên {truong}: {lech[0]}"


class TestSupervisorKhongImportCodeBot:
    """(C) — §6.6(2) *"SUPERVISOR KHÔNG IMPORT CODE BOT"*, kiểm bằng AST."""

    def _import_cap_cao_nhat(self) -> list[str]:
        cay = ast.parse(FILE_SUPERVISOR.read_text(encoding="utf-8"))
        ten: list[str] = []
        for nut in cay.body:  # CHỈ cấp cao nhất — import trong hàm là chuyện khác
            if isinstance(nut, ast.Import):
                ten.extend(bidanh.name for bidanh in nut.names)
            elif isinstance(nut, ast.ImportFrom) and nut.module:
                ten.append(nut.module)
        return ten

    def test_khong_import_code_bot(self) -> None:
        vi_pham = [
            ten
            for ten in self._import_cap_cao_nhat()
            if any(ten == cam or ten.startswith(cam + ".") for cam in CAM_IMPORT)
        ]
        assert not vi_pham, (
            f"risk_supervisor.py import code bot ở cấp cao nhất: {vi_pham}. "
            "§6.6(2) đòi Supervisor sống độc lập với bot — giá trị cần từ "
            "bot phải NHẬN QUA THAM SỐ (khuôn `doc_resolve`), không import."
        )

    def test_chi_dung_thu_vien_chuan(self) -> None:
        """Chặn cả import LẠ, không chỉ import đã nghĩ ra trước.

        `CAM_IMPORT` là danh sách cấm nên nó chỉ chặn tên đã biết; ca này
        bù lại bằng phía CHO PHÉP — cùng lập luận đã dùng cho
        `CTRL_OUTPUT_ALLOWED` (MT-08): blocklist một mình không fail-closed.
        """
        cho_phep = {
            "__future__", "math", "os", "collections.abc",
            "dataclasses", "datetime", "typing", "enum",
        }
        la = [ten for ten in self._import_cap_cao_nhat() if ten not in cho_phep]
        assert not la, (
            f"import ngoài thư viện chuẩn trong risk_supervisor.py: {la}. "
            "Nếu đây là thay đổi có chủ đích, thêm vào danh sách CHO PHÉP "
            "của ca này — việc đó buộc người sửa phải đọc §6.6(2)."
        )
