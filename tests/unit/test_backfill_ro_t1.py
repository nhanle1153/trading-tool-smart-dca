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
    i_nhanh = src.index("if args.ro_t1_sao_chep or args.ro_t1_nhap_kho or args.cat_den_t2 or args.ro_t1_kiem:")
    assert i_guard < i_nhanh < src.index("require_d0_pre_complete", i_nhanh)


def test_cat_den_t2_doi_data_dir_tuong_minh() -> None:
    src = inspect.getsource(E8.main)
    assert 'x == "--data-dir" or x.startswith("--data-dir=")' in src
