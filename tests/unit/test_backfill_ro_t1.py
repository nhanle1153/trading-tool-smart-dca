"""TD-0247 (`DR-D1-03` §4–§5) — các cờ rổ T1 trên E8 `backfill_data.py`.

🔴 Test này sinh ra sau một lỗi thật: commit `cf86276` làm E8 KHÔNG nạp được (chuỗi
`"\\n"` bị bản vá ghi thành xuống dòng thật ⇒ `SyntaxError`), trong khi 65 test đơn vị
của module dữ liệu vẫn xanh vì không test nào nạp E8. Nạp module ở đây là phép kiểm đầu tiên.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _nap_e8():
    spec = importlib.util.spec_from_file_location("backfill_ro_t1", REPO / "entrypoints" / "backfill_data.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E8 = _nap_e8()


def test_ghi_moc_ngung_gop_va_TU_CHOI_ghi_de_moc_khac(tmp_path: Path, monkeypatch) -> None:
    dich = tmp_path / "moc.json"
    monkeypatch.setattr(E8, "MOC_NGUNG_JSON", dich)
    E8._ghi_moc_ngung("MKRUSDT", {"moc_ngung": "2025-09-08T08:00:00+00:00", "gia_dong_nen_cuoi": 1650.1})
    E8._ghi_moc_ngung("FLMUSDT", {"moc_ngung": "2025-11-21T08:00:00+00:00", "gia_dong_nen_cuoi": 0.0082})
    # Ghi lại đúng mốc cũ: được (chạy lại không đổi gì).
    E8._ghi_moc_ngung("MKRUSDT", {"moc_ngung": "2025-09-08T08:00:00+00:00", "gia_dong_nen_cuoi": 1650.1})
    du_lieu = json.loads(dich.read_text(encoding="utf-8"))
    assert set(du_lieu["ma"]) == {"MKRUSDT", "FLMUSDT"}
    assert dich.read_text(encoding="utf-8").endswith("}\n")
    with pytest.raises(RuntimeError):
        E8._ghi_moc_ngung("MKRUSDT", {"moc_ngung": "2025-09-09T08:00:00+00:00", "gia_dong_nen_cuoi": 1.0})
    assert E8._doc_moc_ngung.__code__  # hàm đọc tồn tại


def test_doc_moc_ngung_chua_co_file_thi_rong(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(E8, "MOC_NGUNG_JSON", tmp_path / "khong-co.json")
    assert E8._doc_moc_ngung() == {}


def test_cac_co_ro_t1_di_SAU_guard_va_gate_d0_pre() -> None:
    src = inspect.getsource(E8.main)
    i_guard = src.index("measurement_guard(")
    i_nhanh = src.index("args.ro_t1_sao_chep or args.ro_t1_nhap_kho or args.cat_den_t2 or args.ro_t1_kiem")
    assert i_guard < i_nhanh < src.index("require_d0_pre_complete", i_nhanh)


def test_cat_den_t2_doi_data_dir_tuong_minh() -> None:
    src = inspect.getsource(E8.main)
    assert 'x == "--data-dir" or x.startswith("--data-dir=")' in src


# ─── TD-0301 (DR-D1-05) — cùng thao tác theo mốc rổ ───


def test_cau_hinh_ro_t0_t1() -> None:
    from tool_d.data.pool_t1_du_lieu import (
        KE_HOACH_THEO_RO,
        LOAI_5M_T0,
        NAM_LOAI_FILE_T0,
        SAU_LOAI_FILE,
        SAU_LOAI_FILE_T0,
    )

    assert set(E8.CAU_HINH_RO) == {"t0", "t1"}
    assert E8.CAU_HINH_RO["t0"][0] == Path("user_data/data/pool_t0/futures")
    assert E8.CAU_HINH_RO["t0"][1] == Path("config/pool_t0.yaml")
    assert E8.CAU_HINH_RO["t0"][2] != E8.MOC_NGUNG_JSON  # artifact mốc ngừng RIÊNG cho rổ T0
    assert E8.CAU_HINH_RO["t0"][3] == (E8.DEFAULT_DATA_DIR, E8.POOL_T1_DATA_DIR)
    # TD-0252 (DR-D1-05 §3b.1): rổ T0 nay SÁU loại, 5m tính từ T0.
    assert KE_HOACH_THEO_RO["t0"] == (SAU_LOAI_FILE_T0, "t1")
    assert KE_HOACH_THEO_RO["t1"] == (SAU_LOAI_FILE, "t2")
    assert LOAI_5M_T0.khung == "5m" and LOAI_5M_T0.tu_moc == "t0"
    assert LOAI_5M_T0 in SAU_LOAI_FILE_T0 and len(SAU_LOAI_FILE_T0) == 6
    # Vế cũ VẪN ĐÚNG và vẫn có nghĩa: NAM_LOAI_FILE_T0 mô tả 715 file TD-0301 đã đặt trên đĩa.
    assert all(lf.khung != "5m" for lf in NAM_LOAI_FILE_T0) and len(NAM_LOAI_FILE_T0) == 5
    # 🔴 Bất biến giữ cho 107 mã rổ T1 KHỎI phải tải lại: 5m của rổ T1 vẫn tính từ T1.
    assert next(lf for lf in SAU_LOAI_FILE if lf.khung == "5m").tu_moc == "t1"
    # 1h futures vẫn đứng đầu MỌI kế hoạch — nhap_ma_tu_kho() đo mốc ngừng bằng phần tử 0.
    for ke_hoach, _ in KE_HOACH_THEO_RO.values():
        assert (ke_hoach[0].khung, ke_hoach[0].hau_to) == ("1h", "futures")


def test_sao_chep_t0_uu_tien_nguon_dau_va_tu_choi_mot_phan(tmp_path: Path, monkeypatch) -> None:
    from tool_d.data.pool_t1_du_lieu import SAU_LOAI_FILE_T0, ten_file

    n1, n2, dich = tmp_path / "binance", tmp_path / "pool_t1", tmp_path / "pool_t0"
    for d in (n1, n2):
        d.mkdir()
    for lf in SAU_LOAI_FILE_T0:
        (n1 / ten_file("AUSDT", lf)).write_bytes(b"n1-A")
        (n2 / ten_file("AUSDT", lf)).write_bytes(b"n2-A")
        (n2 / ten_file("BUSDT", lf)).write_bytes(b"n2-B")
    ro_yaml = tmp_path / "pool_t0.yaml"
    ro_yaml.write_text("moc_t0: x\ntrading:\n- AUSDT\n- BUSDT\n- CUSDT\n", encoding="utf-8")
    td0230 = tmp_path / "td0230.json"
    td0230.write_text('{"khoang_ton_tai": {}}', encoding="utf-8")
    monkeypatch.setitem(E8.CAU_HINH_RO, "t0", (dich, ro_yaml, tmp_path / "moc.json", (n1, n2)))
    monkeypatch.setattr(E8, "NGUON_TD0230", td0230)
    assert E8.do_ro_sao_chep("t0") == 0
    assert (dich / ten_file("AUSDT", SAU_LOAI_FILE_T0[0])).read_bytes() == b"n1-A"  # nguồn ĐẦU thắng
    assert (dich / ten_file("BUSDT", SAU_LOAI_FILE_T0[0])).read_bytes() == b"n2-B"
    # TD-0252: đảo vế cũ (`not any(dich.glob("*5m*"))`) — rổ T0 nay CÓ 5m trong kế hoạch.
    assert (dich / ten_file("AUSDT", SAU_LOAI_FILE_T0[-1])).is_file()
    assert len(list(dich.glob("*-5m-futures.feather"))) == 2
    # Mã có MỘT PHẦN file ở nguồn đầu ⇒ từ chối, không lấy nguồn sau.
    (n1 / ten_file("CUSDT", SAU_LOAI_FILE_T0[0])).write_bytes(b"le")
    for lf in SAU_LOAI_FILE_T0:
        (n2 / ten_file("CUSDT", lf)).write_bytes(b"n2-C")
    dich2 = tmp_path / "pool_t0_b"
    monkeypatch.setitem(E8.CAU_HINH_RO, "t0", (dich2, ro_yaml, tmp_path / "moc.json", (n1, n2)))
    assert E8.do_ro_sao_chep("t0") == E8.EXIT_RO_T1_LOI
    assert not dich2.exists()


def test_sao_chep_t0_thieu_dung_5m_o_nguon_thi_TU_CHOI(tmp_path: Path, monkeypatch) -> None:
    """TD-0252 — ca THẬT của dữ liệu trên đĩa: 66 mã có đủ 5 loại cũ ở nguồn nhưng KHÔNG có 5m
    kỷ nguyên CALIB. Phải rơi nhánh "một phần", không được lặng lẽ chép 5 file rồi báo thành công."""
    from tool_d.data.pool_t1_du_lieu import NAM_LOAI_FILE_T0, ten_file

    nguon, dich = tmp_path / "binance", tmp_path / "pool_t0"
    nguon.mkdir()
    for lf in NAM_LOAI_FILE_T0:  # đúng 5 loại, thiếu 5m
        (nguon / ten_file("AUSDT", lf)).write_bytes(b"x")
    ro_yaml = tmp_path / "pool_t0.yaml"
    ro_yaml.write_text("moc_t0: x\ntrading:\n- AUSDT\n", encoding="utf-8")
    td0230 = tmp_path / "td0230.json"
    td0230.write_text('{"khoang_ton_tai": {}}', encoding="utf-8")
    monkeypatch.setitem(E8.CAU_HINH_RO, "t0", (dich, ro_yaml, tmp_path / "moc.json", (nguon,)))
    monkeypatch.setattr(E8, "NGUON_TD0230", td0230)
    assert E8.do_ro_sao_chep("t0") == E8.EXIT_RO_T1_LOI
    assert not dich.exists()


def test_co_chung_doi_moc_tuong_minh_va_co_t1_khong_nhan_moc_t0() -> None:
    src = inspect.getsource(E8.main)
    assert "cần --moc TƯỜNG MINH" in src
    assert 'args.moc not in (None, "t1")' in src


def test_ghi_moc_ngung_t0_vao_file_rieng(tmp_path: Path, monkeypatch) -> None:
    rieng = tmp_path / "t0.json"
    chung = tmp_path / "t1.json"
    monkeypatch.setattr(E8, "MOC_NGUNG_JSON", chung)
    monkeypatch.setitem(E8.CAU_HINH_RO, "t0", (tmp_path, tmp_path / "r.yaml", rieng, ()))
    E8._ghi_moc_ngung("FTMUSDT", {"moc_ngung": "2025-01-13T08:00:00+00:00"}, "t0")
    assert rieng.is_file() and not chung.exists()
    assert set(E8._doc_moc_ngung("t0")) == {"FTMUSDT"} and E8._doc_moc_ngung("t1") == {}


# ─── TD-0252 (DR-D1-05 §3b) — cờ --chi-loai / --ro-con-thieu / --ro-do-phu ───


def test_chi_loai_khung_la_thi_TU_CHOI_khong_thanh_tap_rong() -> None:
    """Khung không có trong kế hoạch phải TỪ CHỐI. Nếu nó lặng lẽ thành tuple rỗng thì mọi thao
    tác chạy xong trên 0 file và in dấu thành công — đúng hình PASS RỖNG."""
    from tool_d.data.pool_t1_du_lieu import DuLieuRoError

    with pytest.raises(DuLieuRoError, match="không có trong kế hoạch"):
        E8._loai_file_cho("t0", "15m")
    loai, moc_cuoi = E8._loai_file_cho("t0", "5m")
    assert len(loai) == 1 and loai[0].khung == "5m" and loai[0].tu_moc == "t0" and moc_cuoi == "t1"
    assert len(E8._loai_file_cho("t0", None)[0]) == 6


def test_chi_loai_khung_la_qua_cac_ham_thi_exit_98(tmp_path: Path, monkeypatch) -> None:
    ro_yaml = tmp_path / "pool_t0.yaml"
    ro_yaml.write_text("moc_t0: x\ntrading:\n- AUSDT\n", encoding="utf-8")
    td0230 = tmp_path / "td0230.json"
    td0230.write_text('{"khoang_ton_tai": {"AUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08"}}}', encoding="utf-8")
    monkeypatch.setitem(E8.CAU_HINH_RO, "t0", (tmp_path / "d", ro_yaml, tmp_path / "moc.json", ()))
    monkeypatch.setattr(E8, "NGUON_TD0230", td0230)
    assert E8.do_ro_con_thieu("t0", "15m") == E8.EXIT_RO_T1_LOI
    assert E8.do_ro_sao_chep("t0", "15m") == E8.EXIT_RO_T1_LOI
    assert E8.do_ro_kiem("t0", "15m") == E8.EXIT_RO_T1_LOI
    assert not (tmp_path / "d").exists()


def test_nhap_kho_chi_loai_ma_VANG_artifact_moc_ngung_thi_exit_98(tmp_path: Path, monkeypatch, capsys) -> None:
    """🔴 Chặn cứng: thiếu artifact thì 18 mã đã ngừng giao dịch trong CALIB bị cắt tại T1 và
    nhận đuôi nến phẳng volume 0 — và nhánh mã-có-mốc-ngừng của kiem_du_lieu_ro() không chạy,
    nên không phép kiểm nào báo đỏ. Phải dừng TRƯỚC khi gọi mạng."""
    ro_yaml = tmp_path / "pool_t0.yaml"
    ro_yaml.write_text("moc_t0: x\ntrading:\n- AUSDT\n", encoding="utf-8")
    td0230 = tmp_path / "td0230.json"
    td0230.write_text('{"khoang_ton_tai": {"AUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08"}}}', encoding="utf-8")
    vang = tmp_path / "khong-ton-tai.json"
    monkeypatch.setitem(E8.CAU_HINH_RO, "t0", (tmp_path / "d", ro_yaml, vang, ()))
    monkeypatch.setattr(E8, "NGUON_TD0230", td0230)

    # 🔴 Ca này TỪNG là PASS vì lý do khác: bỏ chặn đi thì code chạy tiếp, gọi mạng, lỗi ở đó
    # và CŨNG trả exit 98 — phá thật không làm nó đỏ. Phải khẳng định KHÔNG một lời gọi mạng nào
    # xảy ra, đó mới là thứ phân biệt "chặn trước" với "chết dọc đường".
    import tool_d.api_client.binance_public as bp

    da_goi: list[tuple] = []

    def _cam(**kw):
        da_goi.append(tuple(sorted(kw)))
        raise AssertionError("KHÔNG được gọi mạng khi thiếu artifact mốc ngừng")

    monkeypatch.setattr(bp, "doc_csv_thang_kho", _cam)
    ma_thoat = E8.do_ro_nhap_kho("t0", "AUSDT", "5m")
    ra = capsys.readouterr().out
    assert ma_thoat == E8.EXIT_RO_T1_LOI
    assert da_goi == []  # chặn TRƯỚC khi chạm mạng
    assert "artifact mốc ngừng giao dịch" in ra
    assert not (tmp_path / "d").exists()


def test_ro_con_thieu_chi_doc_khong_ghi(tmp_path: Path, monkeypatch, capsys) -> None:
    from tool_d.data.pool_t1_du_lieu import LOAI_5M_T0, ten_file

    dich = tmp_path / "d"
    dich.mkdir()
    (dich / ten_file("AUSDT", LOAI_5M_T0)).write_bytes(b"x")
    ro_yaml = tmp_path / "pool_t0.yaml"
    ro_yaml.write_text("moc_t0: x\ntrading:\n- AUSDT\n- BUSDT\n", encoding="utf-8")
    td0230 = tmp_path / "td0230.json"
    td0230.write_text('{"khoang_ton_tai": {}}', encoding="utf-8")
    monkeypatch.setitem(E8.CAU_HINH_RO, "t0", (dich, ro_yaml, tmp_path / "moc.json", ()))
    monkeypatch.setattr(E8, "NGUON_TD0230", td0230)
    truoc = sorted(p.name for p in dich.iterdir())
    assert E8.do_ro_con_thieu("t0", "5m") == 0
    ra = capsys.readouterr().out
    assert "BUSDT" in ra and "AUSDT" not in ra.split("\n")[-2]
    assert sorted(p.name for p in dich.iterdir()) == truoc  # không ghi gì


def test_cac_co_moi_di_SAU_guard_va_gate_d0_pre() -> None:
    src = inspect.getsource(E8.main)
    vi_tri_guard = src.index("measurement_guard(")
    vi_tri_co = min(src.index("args.ro_con_thieu"), src.index("args.ro_do_phu"))
    assert vi_tri_guard < vi_tri_co
    assert "--chi-loai chỉ đi kèm" in src


def test_do_phu_nap_duoc_0_ma_thi_KHONG_DO_DUOC_chu_khong_phai_DU(tmp_path: Path, monkeypatch, capsys) -> None:
    """🔴 Bẫy PASS RỖNG đã XẢY RA THẬT 18/09/2026, không phải giả định: `datadir` truyền thiếu
    một tầng (Freqtrade tự nối `futures/` cho candle_type FUTURES) ⇒ `load_data` trả 0 mã ⇒
    `cho_thieu_khung_chi_tiet({}, {})` trả rỗng ⇒ hàm in "✅ không giờ nào thiếu, trên toàn bộ
    0 mã nạp được" và trả **exit 0**. Khẳng định ĐÚNG-VÔ-NGHĨA trên tập rỗng.

    "Không đo được" phải KHÁC "đo ra đủ" (N6) — trước bản vá, hai ca đó cho cùng mã thoát."""
    ro_yaml = tmp_path / "pool_t0.yaml"
    ro_yaml.write_text("moc_t0: x\ntrading:\n- AUSDT\n- BUSDT\n", encoding="utf-8")
    td0230 = tmp_path / "td0230.json"
    td0230.write_text('{"khoang_ton_tai": {}}', encoding="utf-8")
    monkeypatch.setitem(E8.CAU_HINH_RO, "t0", (tmp_path / "trong" / "futures", ro_yaml, tmp_path / "m.json", ()))
    monkeypatch.setattr(E8, "NGUON_TD0230", td0230)
    out = tmp_path / "do-phu.json"
    ma_thoat = E8.do_ro_do_phu("t0", "5m", out)
    ra = capsys.readouterr().out
    assert ma_thoat == E8.EXIT_RO_T1_LOI, "0 mã nạp được PHẢI là lỗi, không phải 'đủ'"
    assert "KHÔNG ĐO ĐƯỢC" in ra
    assert "✅" not in ra


def test_do_phu_ma_qua_ro_kiem_ma_khong_nap_duoc_thi_TU_CHOI(tmp_path: Path, monkeypatch, capsys) -> None:
    """Mẫu số không được lặng lẽ thu nhỏ: `--ro-kiem` đã khẳng định mọi mã có file 1h hợp lệ,
    nên `load_data` bỏ sót mã là mâu thuẫn giữa hai đường đọc — phải truy, không báo 'đủ'."""
    import tool_d.data.do_phu_chi_tiet as dp

    ro_yaml = tmp_path / "pool_t0.yaml"
    ro_yaml.write_text("moc_t0: x\ntrading:\n- AUSDT\n- BUSDT\n", encoding="utf-8")
    td0230 = tmp_path / "td0230.json"
    td0230.write_text('{"khoang_ton_tai": {}}', encoding="utf-8")
    monkeypatch.setitem(E8.CAU_HINH_RO, "t0", (tmp_path / "d" / "futures", ro_yaml, tmp_path / "m.json", ()))
    monkeypatch.setattr(E8, "NGUON_TD0230", td0230)

    import pandas as pd

    def _nap_gia(**kw):  # chỉ nạp được A, vắng B
        d = pd.date_range("2024-04-09", "2024-04-10", freq="1h", tz="UTC")
        return {"A/USDT:USDT": pd.DataFrame({"date": d})}

    import freqtrade.data.history as ft_history

    monkeypatch.setattr(ft_history, "load_data", _nap_gia)
    ma_thoat = E8.do_ro_do_phu("t0", "5m", tmp_path / "o.json")
    ra = capsys.readouterr().out
    assert ma_thoat == E8.EXIT_RO_T1_LOI
    assert "B/USDT:USDT" in ra and "KHÔNG nạp được" in ra
    assert dp.cho_thieu_khung_chi_tiet({}, {}) == []  # hàm thuần vẫn đúng; chốt nằm ở người gọi
