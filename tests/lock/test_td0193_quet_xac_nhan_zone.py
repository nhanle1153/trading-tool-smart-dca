"""TD-0193 — quét chuỗi lần chạm zone trong toàn vòng đời, thi hành §3.3b
Phương án A (MT-22): cửa sổ chờ xác nhận mở ĐÚNG MỘT LẦN, ở lần chạm đầu
tiên sau khi zone được xác nhận. KHÔNG quay lại tìm xác nhận ở lần chạm
xa hơn — "BỎ LƯỢT" nghĩa là bỏ luôn zone đó cho giao dịch thật.

Kèm ghi PHẢN THỰC cho phương án B (mọi lượt chạm, tới khi thành công) —
CHỈ để đếm, KHÔNG BAO GIỜ dùng để phát tín hiệu thật. Điều kiện mở lại
BẤT ĐỐI XỨNG đã chốt ở MT-22: loại B ra thì 0 trial (chỉ cần đếm); nhận
B vào thì phải trả một suất trial B1, phản thực không phải bằng chứng
expectancy.

════ Diễn giải, ghi ra để cãi lại được ════

1. **"Lần chạm gần nhất trước đó"** (điều kiện (b)): dùng mốc TẠI NẾN
   CHẠM (giá + RSI ở bar bắt đầu lượt chạm), KHÔNG phải tại nến xác nhận
   của lượt đó. Lý do: (b) đo hình dạng giá GIỮA HAI LẦN CHẠM — quan hệ
   đó không đổi theo việc lượt trước có tìm được xác nhận hay không.
2. **"Chạm"** = một lượt/CỤM giá nằm trong `[zone_low, zone_high]`, kết
   thúc khi giá RA khỏi khoảng đó (cùng khái niệm cụm của `touch_count`,
   nhưng dùng VỊ TỪ trần `zone_low <= gia <= zone_high`, không dùng lại
   `touch_count()` — hàm đó cần biết điểm BẬT RA để đếm cụm ĐÃ hoàn tất,
   tức cần đọc nến SAU, sai ngữ cảnh "tại t có phải điểm bắt đầu chạm
   không" mà hàm này cần trả lời tại chỗ, không nhìn về sau).
3. Cửa sổ quét bị CHẶN bởi `den` — do TẦNG GỌI tính, khuyến nghị dùng
   đúng `NGUONG_TUOI_ZONE_TOI_DA` (§1.3, 40 nến 4H) quy đổi sang 1H:
   `zone_hop_le()` hiện gọi với `tuoi_nen=K_XAC_NHAN` (hằng 3) — cùng
   tautology mà MT-19/TD-0189 bắt được ở zone TP — nên KHÔNG có gì khác
   chặn một zone entry sống mãi ngoài `den` mà hàm này nhận được.
"""

from __future__ import annotations

import math

import pytest

from tool_d.entry_confirmation import (
    KetQuaQuetXacNhanZone,
    quet_xac_nhan_zone,
)

# Cấu hình chung: 20 nến 1H, RSI/volume đơn giản để dựng tay các ca.
N = 20
V_MIN = 1.0
ZL, ZH = 90.0, 100.0  # zone đáy


def _phang() -> dict:
    """Nền cho mọi ca: nến DOJI TUYỆT ĐỐI (range=0) NGOÀI zone ở giá 80.0.

    Range=0 khiến `la_nen_rejection` trả `False` NGAY (guard `bien_do <=
    0`) tại MỌI nến nền — tránh đúng lỗi bản đầu của helper này, nơi nến
    nền mo/dong=95 nhưng thap=80 (baseline khác nhau) VÔ TÌNH tạo bóng
    dưới giả 15 điểm, đủ thoả điều kiện (a) ở bất kỳ nến nào trong cửa sổ
    xác nhận mà không chủ ý."""
    mo = [80.0] * N
    cao = [80.0] * N
    thap = [80.0] * N
    dong = [80.0] * N
    rsi = [50.0] * N
    vol = [10.0] * N
    vma = [10.0] * N
    return dict(mo=mo, cao=cao, thap=thap, dong=dong, rsi=rsi, volume=vol, volume_ma=vma)


def _dung_cham(d: dict, t: int, *, gia: float = 95.0) -> None:
    """Đặt nến `t` nằm TRONG zone (chạm), không phải rejection, không (b).

    Bóng dưới CHỈ 10% range (< 50% ngưỡng (a)) — tránh đúng cạnh biên
    `>=` của `la_nen_rejection` (0,5×range đúng bằng ngưỡng thì VẪN thoả
    điều kiện, một bản đầu của helper này dính đúng lỗi đó)."""
    d["thap"][t] = gia
    d["cao"][t] = gia + 1.0
    d["mo"][t] = gia + 0.1
    d["dong"][t] = gia + 0.1


def _dung_rejection(d: dict, t: int, *, gia_thap: float = 92.0) -> None:
    """Đặt nến `t` là rejection: bóng dưới >=50% range, đóng cửa nửa trên."""
    d["thap"][t] = gia_thap
    d["cao"][t] = gia_thap + 10.0
    d["mo"][t] = gia_thap + 6.0
    d["dong"][t] = gia_thap + 8.0  # đóng cửa ở 80% range -> nửa trên
    d["vol"] = d.get("vol")


def _goi(d: dict, *, tu: int, den: int, lct=None) -> KetQuaQuetXacNhanZone:
    return quet_xac_nhan_zone(
        d["mo"], d["cao"], d["thap"], d["dong"], d["rsi"], d["volume"], d["volume_ma"],
        zone_low=ZL, zone_high=ZH, tu=tu, den=den, v_min=V_MIN, loai="day",
        lan_cham_truoc_khi_xac_nhan=lct,
    )


class TestKhongCoLanChamNao:
    def test_gia_khong_bao_gio_vao_zone_thi_ca_hai_deu_none(self) -> None:
        d = _phang()
        kq = _goi(d, tu=0, den=N)
        assert kq.nen_xac_nhan_that is None
        assert kq.nen_xac_nhan_phan_thuc is None
        assert kq.lan_cham_phan_thuc == 0


class TestPhuongAnA_LanChamDauXacNhanNgay:
    def test_lan_cham_dau_xac_nhan_bang_rejection_thi_A_va_B_cung_mot_nen(self) -> None:
        d = _phang()
        _dung_cham(d, 5)          # nến chạm
        _dung_rejection(d, 5)     # xác nhận NGAY tại nến chạm (a VÀ c)
        d["volume"][5], d["volume_ma"][5] = 20.0, 10.0  # v_r=2.0 >= v_min
        kq = _goi(d, tu=0, den=N)
        assert kq.nen_xac_nhan_that == 5
        assert kq.nen_xac_nhan_phan_thuc == 5
        assert kq.lan_cham_phan_thuc == 1


class TestPhuongAnA_BoLuotKhongQuayLai:
    def test_lan_cham_dau_khong_xac_nhan_thi_A_la_None_du_lan_sau_co(self) -> None:
        """Cốt lõi của Phương án A: lần chạm đầu trượt (không a/b/c trong
        3 nến) -> zone BỊ BỎ VĨNH VIỄN cho giao dịch thật, dù lần chạm
        sau đó có xác nhận ngon lành."""
        d = _phang()
        _dung_cham(d, 5)                      # chạm nhưng KHÔNG xác nhận
        # nến 6,7 vẫn phẳng -> cửa sổ 3 nến (5,6,7) của lượt 1 trượt hết
        # giá ra khỏi zone ở nến 8, rồi chạm lại ở nến 12 với xác nhận thật
        d["thap"][8] = 80.0  # ra khỏi zone
        _dung_cham(d, 12)
        _dung_rejection(d, 12)
        d["volume"][12], d["volume_ma"][12] = 20.0, 10.0

        kq = _goi(d, tu=0, den=N)
        assert kq.nen_xac_nhan_that is None, "Phương án A phải BỎ LƯỢT, không quay lại"
        assert kq.nen_xac_nhan_phan_thuc == 12, "phản thực (B) phải thấy lượt 2 xác nhận"
        assert kq.lan_cham_phan_thuc == 2


class TestDieuKienB_MocLaGiaRsiTaiNenCham:
    def test_dieu_kien_b_lay_moc_tu_NEN_CHAM_khong_phai_nen_xac_nhan(self) -> None:
        """Diễn giải #1: mốc cho (b) ở lượt sau = (giá, RSI) tại NẾN CHẠM
        của lượt trước, không phải tại nến nào đó bên trong cửa sổ chờ
        xác nhận của lượt trước (dù lượt đó có tìm được xác nhận hay
        không). Ca này dựng lượt 1 KHÔNG xác nhận (chỉ để lại mốc), rồi
        lượt 2 xác nhận ĐÚNG NHỜ (b) so với giá/RSI tại nến chạm của
        lượt 1 — không phải bất kỳ giá nào khác trong cửa sổ đó."""
        d = _phang()
        d["rsi"][5] = 30.0
        _dung_cham(d, 5, gia=95.0)   # lượt 1: chạm tại giá 95, RSI 30 -- KHÔNG xác nhận
        d["thap"][8] = 80.0          # ra khỏi zone

        # lượt 2: chạm tại giá THẤP HƠN (94 <= 95) với RSI CAO HƠN (35 > 30)
        # -> đúng công thức phan_ky_momentum khi so với mốc lượt 1 (95, 30).
        # Range rộng + đóng cửa gần đáy -> KHÔNG thoả (a), cô lập đúng (b)
        # (một bản đầu dùng range hẹp vô tình thoả CẢ (a VÀ c), khiến ca
        # này xanh vì sai lý do — không thật sự kiểm chứng (b)).
        d["thap"][12], d["cao"][12] = 94.0, 98.0
        d["mo"][12], d["dong"][12] = 94.2, 94.4
        d["rsi"][12] = 35.0

        kq = _goi(d, tu=0, den=N)
        assert kq.nen_xac_nhan_phan_thuc == 12
        assert kq.lan_cham_phan_thuc == 2


class TestMocTruocKhiXacNhanZone_ChoLanChamDau:
    def test_lan_cham_dau_dung_moc_truyen_vao_tu_ben_ngoai(self) -> None:
        """MT-22 xác nhận: mọi zone hợp lệ đã có >=1 lần chạm TRƯỚC nến
        xác nhận zone (zone_hop_le đòi so_touch>=1) -- mốc đó do TẦNG GỌI
        cung cấp qua `lan_cham_truoc_khi_xac_nhan`, hàm này không tự suy
        ra. Ca này xác nhận lượt chạm ĐẦU TIÊN trong cửa sổ [tu, den]
        cũng dùng đúng mốc ngoài đó cho (b), không coi là None."""
        d = _phang()
        # giá đáy 94 <= mốc trước (95); RSI 40 > mốc trước (30). Range
        # rộng + đóng cửa gần đáy -> KHÔNG thoả (a), cô lập đúng vế (b).
        d["thap"][3], d["cao"][3] = 94.0, 98.0
        d["mo"][3], d["dong"][3] = 94.2, 94.4
        d["rsi"][3] = 40.0

        kq_khong_moc = _goi(d, tu=0, den=N, lct=None)
        assert kq_khong_moc.nen_xac_nhan_that is None, "không mốc thì (b) không có gì để so"

        kq_co_moc = _goi(d, tu=0, den=N, lct=(95.0, 30.0))
        assert kq_co_moc.nen_xac_nhan_that == 3


class TestMotCumChamKhongTinhNhieuLan:
    def test_gia_nam_lien_nhieu_nen_trong_zone_van_la_MOT_luot(self) -> None:
        """Giá vào zone và NẰM LẠI nhiều nến (không ra rồi vào lại) vẫn
        là MỘT lượt chạm -- không tính lại 'lượt mới' ở mỗi nến trong
        cùng một lần ghé."""
        d = _phang()
        for t in (5, 6, 7, 8, 9):
            _dung_cham(d, t)  # 5 nến liên tiếp trong zone, không xác nhận
        kq = _goi(d, tu=0, den=N)
        assert kq.nen_xac_nhan_that is None
        assert kq.nen_xac_nhan_phan_thuc is None
        assert kq.lan_cham_phan_thuc == 0, "chỉ được tính 1 lượt, không phải 5"


class TestDoiChungAmKhongDungXaHonDen:
    def test_xac_nhan_ngoai_pham_vi_den_khong_duoc_thay(self) -> None:
        """`den` là biên CỨNG do tầng gọi truyền — hàm không được đọc gì
        từ `den` trở đi, kể cả khi mảng vẫn còn dữ liệu (an toàn lookahead
        khi tầng gọi cắt `den` theo tuổi zone §1.3)."""
        d = _phang()
        _dung_cham(d, 5)  # không xác nhận trong 3 nến (5,6,7)
        d["thap"][8] = 80.0
        _dung_cham(d, 12)
        _dung_rejection(d, 12)
        d["volume"][12], d["volume_ma"][12] = 20.0, 10.0

        kq_bi_cat = _goi(d, tu=0, den=10)  # den=10 < 12 -> không thấy lượt 2
        assert kq_bi_cat.nen_xac_nhan_phan_thuc is None

        kq_du = _goi(d, tu=0, den=N)
        assert kq_du.nen_xac_nhan_phan_thuc == 12


class TestBatBienKhongDungLai:
    def test_ket_qua_A_khong_doi_bat_ke_co_quet_tiep_cho_B_hay_khong(self) -> None:
        """Bất biến bắt buộc (chốt bởi -f4): việc quét tiếp để ghi phản
        thực KHÔNG được làm thay đổi `nen_xac_nhan_that` -- nó phải
        được xác định XONG ngay ở lượt chạm đầu tiên và không đổi nữa dù
        hàm có tiếp tục quét bao xa."""
        d = _phang()
        _dung_cham(d, 5)  # lượt 1: KHÔNG xác nhận
        d["thap"][8] = 80.0
        _dung_cham(d, 12)
        _dung_rejection(d, 12)
        d["volume"][12], d["volume_ma"][12] = 20.0, 10.0

        # so hai lượt gọi: den ngắn (chỉ đủ lượt 1) vs den dài (thấy cả B)
        kq_ngan = _goi(d, tu=0, den=8)
        kq_dai = _goi(d, tu=0, den=N)
        assert kq_ngan.nen_xac_nhan_that == kq_dai.nen_xac_nhan_that == None


class TestDauVaoHong:
    def test_lan_cham_truoc_thieu_rsi_thi_khong_raise_chi_khong_dung_duoc_b(self) -> None:
        """NaN RSI tại nến chạm -> không cập nhật được mốc cho lượt sau,
        nhưng KHÔNG raise (đây là quét lịch sử dài hạn, một nến NaN giữa
        chừng không nên làm hỏng toàn bộ vòng quét)."""
        d = _phang()
        d["rsi"][5] = float("nan")
        _dung_cham(d, 5)  # không xác nhận
        d["thap"][8] = 80.0
        d["rsi"][12] = 50.0
        # Range rộng + đóng cửa gần đáy -> KHÔNG thoả (a), chỉ còn (b)
        # để mà thiếu mốc (do rsi[5] NaN) làm hỏng xác nhận.
        d["thap"][12], d["cao"][12] = 94.0, 98.0
        d["mo"][12], d["dong"][12] = 94.2, 94.4
        # không cho lct trước đó vì rsi[5] la NaN -> (b) ở lượt 2 không có mốc từ lượt 1
        kq = _goi(d, tu=0, den=N, lct=None)
        assert kq.nen_xac_nhan_that is None
        # lượt 2 không xác nhận được qua (b) vì thiếu mốc (không raise)
        assert kq.nen_xac_nhan_phan_thuc is None


class TestCuaSoXacNhanKhongVuotDen:
    """🔴 Bắt bởi `-f4`: `tim_xac_nhan_entry` tự nó chỉ chặn theo
    `len(dong)`, KHÔNG theo `den` mà `quet_xac_nhan_zone` nhận. Một lượt
    chạm bắt đầu gần `den` có thể có cửa sổ xác nhận LẤN QUA khỏi `den`
    — đọc dữ liệu của một zone đã hết hạn (§1.3), và không ca nào trong
    bộ test trước bắt được vì `den` trong các ca đó luôn đủ xa so với
    `so_nen_cho_toi_da`."""

    def test_luot_cham_bat_dau_sat_den_khong_duoc_doc_qua_den(self) -> None:
        d = _phang()
        # zone chỉ "sống" tới den=6. Lượt chạm bắt đầu ở t=5 (còn hợp lệ,
        # 5 < 6), nhưng cửa sổ 3 nến mặc định sẽ là 5,6,7 — nến 6,7 NẰM
        # NGOÀI `den`. Đặt xác nhận rejection thật ở nến 7 (ngoài den).
        _dung_cham(d, 5)
        _dung_rejection(d, 7)
        d["volume"][7], d["volume_ma"][7] = 20.0, 10.0

        kq = _goi(d, tu=0, den=6)
        assert kq.nen_xac_nhan_that is None, (
            "xác nhận ở nến 7 nằm NGOÀI den=6 — không được tính, dù "
            "tim_xac_nhan_entry() một mình sẽ tìm thấy nó"
        )
        assert kq.nen_xac_nhan_phan_thuc is None


class TestMocLaDayThatCuaCum_KhongPhaiNenDau:
    """🔴 Bắt bởi `-f4`: spec dòng 1081-1082 nói (b) so với **"giá tạo
    đáy"** của lần chạm trước — "đáy" tự nhiên là ĐIỂM THẤP NHẤT trong cả
    cụm chạm, không phải giá tại nến ĐẦU TIÊN chạm vào. Lấy nến đầu (nông
    hơn đáy thật) làm (b) DỄ kích hoạt hơn thiết kế — lệch về chiều NHIỀU
    LỆNH HƠN, tức chiều lạc quan mà dự án luôn nghi ngờ trước.

    RSI phải lấy TẠI ĐÚNG NẾN đáy đó — phân kỳ momentum so RSI và giá
    CÙNG một mốc thời gian, không phải RSI thấp nhất độc lập với giá."""

    def test_dung_diem_thap_nhat_cua_cum_khong_phai_nen_dau_cum(self) -> None:
        d = _phang()
        # Lượt 1: cụm chạm 3 nến liên tiếp (5,6,7), giá giảm dần rồi hồi:
        # nến 5 (đầu cụm) = 96, nến 6 (ĐÁY THẬT của cụm) = 93, nến 7 = 95.
        # Không nến nào xác nhận (a)/(c) -> chỉ để lại mốc cho lượt sau.
        for t, gia, r in ((5, 96.0, 20.0), (6, 93.0, 20.0), (7, 95.0, 20.0)):
            _dung_cham(d, t, gia=gia)
            d["rsi"][t] = r
        d["thap"][8] = 80.0  # ra khỏi zone hẳn

        # Lượt 2, CẢ CỬA SỔ 3 nến (12,13,14) giống hệt nhau: giá 94 --
        # THẤP HƠN đáy thật của cụm 1 (93)? KHÔNG (94 > 93) -- nếu mốc là
        # ĐÁY THẬT (93) thì "giá thấp hơn hoặc bằng" SAI ở CẢ BA nến ->
        # (b) KHÔNG xác nhận trong toàn cửa sổ. Nhưng nếu mốc SAI là nến
        # ĐẦU cụm (96) thì 94 <= 96 -> (b) xác nhận NHẦM ngay nến đầu
        # cửa sổ. Đặt GIỐNG HỆT ở cả ba nến để không dính lại đúng lỗi đã
        # sửa hai lần trước trong file này: nến NỀN sau cụm 1 (rsi=50,
        # gia=80) vô tình thoả (b) một cách không chủ ý.
        for j in (12, 13, 14):
            d["thap"][j], d["cao"][j] = 94.0, 98.0
            d["mo"][j], d["dong"][j] = 94.2, 94.4
            d["rsi"][j] = 25.0  # > 20 (mốc) -- đủ "RSI cao hơn"

        kq = _goi(d, tu=0, den=N)
        assert kq.nen_xac_nhan_phan_thuc is None, (
            "mốc phải là ĐÁY THẬT của cụm (93), không phải nến đầu cụm "
            "(96) -- dùng nến đầu sẽ xác nhận NHẦM ở lượt 2"
        )
