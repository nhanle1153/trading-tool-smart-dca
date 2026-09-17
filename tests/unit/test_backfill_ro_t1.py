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
    from tool_d.data.pool_t1_du_lieu import KE_HOACH_THEO_RO, NAM_LOAI_FILE_T0, SAU_LOAI_FILE

    assert set(E8.CAU_HINH_RO) == {"t0", "t1"}
    assert E8.CAU_HINH_RO["t0"][0] == Path("user_data/data/pool_t0/futures")
    assert E8.CAU_HINH_RO["t0"][1] == Path("config/pool_t0.yaml")
    assert E8.CAU_HINH_RO["t0"][2] != E8.MOC_NGUNG_JSON  # artifact mốc ngừng RIÊNG cho rổ T0
    assert E8.CAU_HINH_RO["t0"][3] == (E8.DEFAULT_DATA_DIR, E8.POOL_T1_DATA_DIR)
    assert KE_HOACH_THEO_RO["t0"] == (NAM_LOAI_FILE_T0, "t1")
    assert KE_HOACH_THEO_RO["t1"] == (SAU_LOAI_FILE, "t2")
    assert all(lf.khung != "5m" for lf in NAM_LOAI_FILE_T0) and len(NAM_LOAI_FILE_T0) == 5


def test_sao_chep_t0_uu_tien_nguon_dau_va_tu_choi_mot_phan(tmp_path: Path, monkeypatch) -> None:
    from tool_d.data.pool_t1_du_lieu import NAM_LOAI_FILE_T0, ten_file

    n1, n2, dich = tmp_path / "binance", tmp_path / "pool_t1", tmp_path / "pool_t0"
    for d in (n1, n2):
        d.mkdir()
    for lf in NAM_LOAI_FILE_T0:
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
    assert (dich / ten_file("AUSDT", NAM_LOAI_FILE_T0[0])).read_bytes() == b"n1-A"  # nguồn ĐẦU thắng
    assert (dich / ten_file("BUSDT", NAM_LOAI_FILE_T0[0])).read_bytes() == b"n2-B"
    assert not any(dich.glob("*5m*"))
    # Mã có MỘT PHẦN file ở nguồn đầu ⇒ từ chối, không lấy nguồn sau.
    (n1 / ten_file("CUSDT", NAM_LOAI_FILE_T0[0])).write_bytes(b"le")
    for lf in NAM_LOAI_FILE_T0:
        (n2 / ten_file("CUSDT", lf)).write_bytes(b"n2-C")
    dich2 = tmp_path / "pool_t0_b"
    monkeypatch.setitem(E8.CAU_HINH_RO, "t0", (dich2, ro_yaml, tmp_path / "moc.json", (n1, n2)))
    assert E8.do_ro_sao_chep("t0") == E8.EXIT_RO_T1_LOI
    assert not dich2.exists()


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
