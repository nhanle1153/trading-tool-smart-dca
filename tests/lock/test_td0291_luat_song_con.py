"""🔒 TD-0291 — luật cổng sống còn (`DR-SONG-CON-01` §4), hàm `gates/song_con.danh_gia_song_con`.

Mỗi nhánh luật một ca, đáp án TÍNH TAY. Dữ liệu dựng:
- `_xen(m, d, n)` = n lệnh `m ± d` xen kẽ ⇒ mean = m (n chẵn), std mẫu = d·√(n/(n−1)).
- Tham số gốc: ma_nam = 100, so_ma_pool = 102, nam_test = 147/365, N = 114.
"""

from __future__ import annotations

import math

import pytest

from tool_d.config.loader import load_tool_d_config
from tool_d.gates import thresholds
from tool_d.gates.dsr import N_DANG_KY, dsr_hurdle
from tool_d.gates.song_con import (
    SAN_N,
    KetLuanSongCon,
    SongConError,
    danh_gia_song_con,
    thong_ke,
)
from tool_d.measurement.tri_state import Status
from tool_d.wfo.folds import sinh_folds

NAM_TEST = 147 / 365


def _xen(m: float, d: float, n: int) -> list[float]:
    return [m + (d if i % 2 else -d) for i in range(n)]


def _goi(r_calib, r_wfo, *, ma_nam=100.0, so_ma_pool=102, nam_test=NAM_TEST, n_trials=N_DANG_KY):
    return danh_gia_song_con(
        r_calib=r_calib, r_wfo=r_wfo, ma_nam=ma_nam, so_ma_pool=so_ma_pool, nam_test=nam_test, n_trials=n_trials,
    )


class TestThongKe:
    def test_tinh_tay(self) -> None:
        tk = thong_ke(_xen(0.2, 1.0, 100))
        s = math.sqrt(100 / 99)
        assert math.isclose(tk.mean.value, 0.2) and math.isclose(tk.std.value, s)
        assert math.isclose(tk.ci_tren.value, 0.2 + 1.96 * s / 10)

    def test_duoi_hai_lenh_unreadable_khong_phai_0(self) -> None:
        tk = thong_ke([])
        assert tk.mean.status is Status.UNREADABLE and tk.std.value is None


class TestBonLuat:
    def test_luat1_duoi_san_khong_ket_luan(self) -> None:
        kq = _goi(_xen(-5.0, 0.1, 14), _xen(-5.0, 0.1, 14))  # n = 28 < 30, dù lỗ rất rõ
        assert kq.ket_luan is KetLuanSongCon.KHONG_KET_LUAN and "luật 1" in kq.ly_do

    def test_luat2_lo_ro_thi_dung(self) -> None:
        """200 lệnh −0,3 ± 1: cận trên = −0,3 + 1,96·1,0025/√200 ≈ −0,161 < 0."""
        kq = _goi(_xen(-0.3, 1.0, 100), _xen(-0.3, 1.0, 100))
        assert kq.ket_luan is KetLuanSongCon.DUNG
        assert kq.gop.ci_tren.value < 0

    def test_khoang_tin_cay_cat_qua_0_KHONG_duoc_dung(self) -> None:
        """🔴 Canh lỗi nặng nhất của cổng: DỪNG chiến lược vì NHIỄU. 200 lệnh 0,05 ± 1:
        KTC95 ≈ 0,05 ± 1,96·1,0025/√200 ≈ [−0,089; +0,189] — cận DƯỚI < 0 nhưng cận TRÊN > 0.
        Luật 2 đòi cận TRÊN < 0 ⇒ không DỪNG; dưới M ⇒ KHÔNG TIÊU SUẤT.
        (Bản đầu bộ test thiếu ca này: đổi luật 2 sang so cận dưới mà 22/22 vẫn xanh.)"""
        kq = _goi(_xen(0.05, 1.0, 100), _xen(0.05, 1.0, 100))
        assert kq.gop.ci_duoi.value < 0 < kq.gop.ci_tren.value
        assert kq.ket_luan is KetLuanSongCon.KHONG_TIEU_SUAT

    def test_luat2_dung_truoc_luat3(self) -> None:
        """Âm rõ thì DỪNG kể cả khi M không tính được (n_cong < 2)."""
        kq = _goi(_xen(-0.3, 1.0, 100), _xen(-0.3, 1.0, 100), ma_nam=1e6)
        assert kq.ket_luan is KetLuanSongCon.DUNG

    def test_luat3_du_manh_va_hai_cua_so_duong_thi_di(self) -> None:
        """400 lệnh 0,6 ± 1 (mỗi cửa sổ 200). n_cong = 400/100·102·147/365 ≈ 164,3;
        M = 0,10 + 3,0777·1,00125/√164,3 ≈ 0,340 ≤ 0,6 ⇒ ĐI."""
        kq = _goi(_xen(0.6, 1.0, 200), _xen(0.6, 1.0, 200))
        n_cong = 400 / 100 * 102 * NAM_TEST
        m = thresholds.DSR_ADJ_EXPECTANCY_MIN + dsr_hurdle(N_DANG_KY) * math.sqrt(400 / 399) / math.sqrt(n_cong)
        assert math.isclose(kq.n_cong.value, n_cong) and math.isclose(kq.m_can.value, m)
        assert kq.ket_luan is KetLuanSongCon.DI

    def test_luat4_duong_nhung_duoi_M(self) -> None:
        """400 lệnh 0,2 ± 1: cận trên > 0 (không DỪNG) nhưng 0,2 < M ≈ 0,340 ⇒ KHÔNG TIÊU SUẤT."""
        kq = _goi(_xen(0.2, 1.0, 200), _xen(0.2, 1.0, 200))
        assert kq.ket_luan is KetLuanSongCon.KHONG_TIEU_SUAT and "< M" in kq.ly_do

    def test_luat4_du_M_nhung_mot_cua_so_am(self) -> None:
        """Gộp: (1,4·200 + (−0,2)·200)/400 = 0,6 ≥ M, nhưng WFO âm ⇒ không ĐI."""
        kq = _goi(_xen(1.4, 1.0, 200), _xen(-0.2, 1.0, 200))
        assert kq.gop.mean.value > kq.m_can.value
        assert kq.ket_luan is KetLuanSongCon.KHONG_TIEU_SUAT and "cả hai cửa sổ" in kq.ly_do

    def test_n_lon_hon_thi_M_cao_hon_khi_rao_dsr_tang(self) -> None:
        """DR-007 union đổi N ⇒ cùng số liệu, N lớn hơn có thể lật ĐI thành KHÔNG TIÊU SUẤT."""
        du_lieu = (_xen(0.36, 1.0, 200), _xen(0.36, 1.0, 200))
        assert _goi(*du_lieu, n_trials=114).ket_luan is KetLuanSongCon.DI
        assert _goi(*du_lieu, n_trials=10**12).ket_luan is KetLuanSongCon.KHONG_TIEU_SUAT


class TestDauVao:
    @pytest.mark.parametrize("xau", [True, 1, 2.0, "114"])
    def test_n_trials_xau(self, xau) -> None:
        with pytest.raises(SongConError):
            _goi(_xen(0.1, 1, 20), _xen(0.1, 1, 20), n_trials=xau)

    def test_n_trials_khong_co_mac_dinh(self) -> None:
        with pytest.raises(TypeError):
            danh_gia_song_con(r_calib=[], r_wfo=[], ma_nam=1.0, so_ma_pool=1, nam_test=1.0)  # type: ignore[call-arg]

    @pytest.mark.parametrize("sua", [{"ma_nam": 0.0}, {"nam_test": -1.0}, {"so_ma_pool": 0}, {"ma_nam": math.inf}])
    def test_mau_so_xau(self, sua) -> None:
        with pytest.raises(SongConError):
            _goi(_xen(0.1, 1, 20), _xen(0.1, 1, 20), **sua)

    def test_tri_khong_huu_han(self) -> None:
        with pytest.raises(SongConError):
            _goi([0.1, math.nan] * 20, [0.1] * 20)


class TestKhongGoLaiHangSo:
    def test_san_n_la_moc_dr011(self) -> None:
        assert SAN_N == 30

    def test_nam_test_suy_tu_fold_that_bang_147_ngay(self) -> None:
        """`nam_test` mà script truyền vào phải suy từ `sinh_folds` — ghim quan hệ với fold thật."""
        folds = sinh_folds(load_tool_d_config())
        ngay = sum((f.test_end - f.test_start).days for f in folds)
        assert ngay == 147

    def test_nguong_doc_tu_thresholds_luc_goi(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(thresholds, "DSR_ADJ_EXPECTANCY_MIN", 5.0)
        kq = _goi(_xen(0.6, 1.0, 200), _xen(0.6, 1.0, 200))
        assert kq.m_can.value > 5.0 and kq.ket_luan is KetLuanSongCon.KHONG_TIEU_SUAT
