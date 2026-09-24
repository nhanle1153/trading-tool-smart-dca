"""TD-0382 — `DR-LOCKBOX-04` §2 dòng 3 + §3 có máy: vốn vượt trần D12 ⇒ `load_tool_d_config()` TỪ CHỐI, trừ khi hiện
vật xác nhận trên dữ liệu SAU `T3` đã commit và đạt ngưỡng đã chốt.

Chủ dự án chốt 24/09/2026: trần = giá trị đang chốt; "tăng vốn" = tăng `E_D` HOẶC `rho_pct` HOẶC `L_exchange`; chặn cứng
lúc đọc cấu hình; bằng chứng = file đã commit. Trước việc này tăng vốn chỉ là sửa một số ở `tier_a` ("chỉnh tự do").

Repo git THẬT trong `tmp_path` — không mock `git`, vì "đã commit" chính là thứ đang được kiểm (khuôn `test_td0375`).
"""

from __future__ import annotations

import copy
import json
import math
import subprocess
from pathlib import Path

import pytest
import yaml

from tool_d.config.loader import ConfigError, TranVonError, load_tool_d_config
from tool_d.config.tran_von import KHOA_KHOI, KHOA_VON, cac_khoa_vuot_tran, ly_do_chua_xac_nhan

REPO = Path(__file__).resolve().parents[2]
CONFIG_THAT = REPO / "config" / "tool_d_config.yaml"
HIEN_VAT = "docs/du-lieu-do/xac-nhan-sau-t3.json"
CHI_SO = "mean_r_trien_khai"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _cfg_that() -> dict:
    return yaml.safe_load(CONFIG_THAT.read_text(encoding="utf-8"))


def _repo(tmp_path: Path, cfg: dict, *, hien_vat: dict | None = None, commit_hien_vat: bool = True) -> Path:
    """Repo tạm: `config/tool_d_config.yaml` (+ hiện vật). Config commit, hiện vật tuỳ `commit_hien_vat`."""
    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "config" / "tool_d_config.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "cfg")
    if hien_vat is not None:
        p = repo / HIEN_VAT
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(hien_vat), encoding="utf-8")
        if commit_hien_vat:
            _git(repo, "add", HIEN_VAT)
            _git(repo, "commit", "-qm", "hien vat")
    return repo


def _cfg_vuot(khoa: str = "E_D", *, chi_so: str | None = CHI_SO, nguong: float | None = 0.05) -> dict:
    cfg = copy.deepcopy(_cfg_that())
    cfg["tier_a"][khoa] = cfg["tier_c"][KHOA_KHOI]["tran_d12"][khoa] * 2
    cfg["tier_c"][KHOA_KHOI]["chi_so"] = chi_so
    cfg["tier_c"][KHOA_KHOI]["nguong"] = nguong
    return cfg


def _hv(**doi) -> dict:
    hv = {"dr": "DR-LOCKBOX-04", "hypothesis_slot": "IQ-0003", "tu_ngay": "2026-09-07",
          "n_lenh": 30, "chi_so": CHI_SO, "gia_tri": 0.08}
    hv.update(doi)
    return hv


def _load(repo: Path):
    return load_tool_d_config(repo / "config" / "tool_d_config.yaml")


class TestConfigThat:
    def test_config_that_doc_duoc(self) -> None:
        load_tool_d_config(CONFIG_THAT)

    def test_tran_bang_dung_gia_tri_dang_chot(self) -> None:
        """🔴 Ghim QUYẾT ĐỊNH (DR-LOCKBOX-04, chủ dự án 24/09/2026): trần = đúng tier_a lúc chốt. Nâng trần hay nâng vốn
        đều phải sửa dòng này — tức phải nhìn thấy DR."""
        cfg = _cfg_that()
        assert cfg["tier_c"][KHOA_KHOI]["tran_d12"] == {"E_D": 750, "rho_pct": 0.375, "L_exchange": 3}
        assert {k: cfg["tier_a"][k] for k in KHOA_VON} == cfg["tier_c"][KHOA_KHOI]["tran_d12"]

    def test_config_that_chua_the_xac_nhan(self) -> None:
        """Ô ngưỡng còn ⏳ ⇒ lớp xác nhận KHÔNG đạt được hôm nay (N6: chưa đo không phải đạt)."""
        cfg = _cfg_that()
        ly_do = ly_do_chua_xac_nhan(cfg["tier_c"], REPO)
        assert any("chi_so chưa điền" in x for x in ly_do)
        assert any("+inf" in x for x in ly_do)

    def test_hai_o_cho_chu_du_an_dang_trong(self) -> None:
        khoi = _cfg_that()["tier_c"][KHOA_KHOI]
        assert khoi["chi_so"] is None and khoi["nguong"] is None
        assert khoi["n_lenh_toi_thieu"] == 30


class TestChanKhiVuotTran:
    @pytest.mark.parametrize("khoa", KHOA_VON)
    def test_tang_bat_ky_khoa_von_nao_khong_hien_vat_thi_TU_CHOI(self, tmp_path, khoa) -> None:
        repo = _repo(tmp_path, _cfg_vuot(khoa))
        with pytest.raises(TranVonError, match=f"{khoa}: .* > trần"):
            _load(repo)

    def test_vuot_tran_mot_don_vi_cung_TU_CHOI(self, tmp_path) -> None:
        """Biên: 751 > 750. Các ca trên nhân đôi nên không phân biệt được một trần bị nới lề."""
        cfg = _cfg_vuot()
        cfg["tier_a"]["E_D"] = cfg["tier_c"][KHOA_KHOI]["tran_d12"]["E_D"] + 1
        with pytest.raises(TranVonError, match="E_D: 751 > trần 750"):
            _load(_repo(tmp_path, cfg))

    def test_TranVonError_la_ConfigError(self) -> None:
        assert issubclass(TranVonError, ConfigError)

    def test_bang_tran_thi_qua(self, tmp_path) -> None:
        cfg = _cfg_vuot()
        cfg["tier_a"]["E_D"] = cfg["tier_c"][KHOA_KHOI]["tran_d12"]["E_D"]
        _load(_repo(tmp_path, cfg))

    def test_giam_von_thi_qua_khong_can_hien_vat(self, tmp_path) -> None:
        cfg = copy.deepcopy(_cfg_that())
        cfg["tier_a"]["E_D"] = 500
        cfg["tier_a"]["rho_pct"] = 0.2
        _load(_repo(tmp_path, cfg))

    def test_khai_von_ma_thieu_khoi_thi_TU_CHOI(self, tmp_path) -> None:
        cfg = copy.deepcopy(_cfg_that())
        del cfg["tier_c"][KHOA_KHOI]
        with pytest.raises(TranVonError, match="thiếu khối"):
            _load(_repo(tmp_path, cfg))

    @pytest.mark.parametrize("hong", [None, "750", math.inf, True])
    def test_tran_hong_thi_TU_CHOI_khong_doc_thanh_khong_co_tran(self, tmp_path, hong) -> None:
        cfg = copy.deepcopy(_cfg_that())
        cfg["tier_c"][KHOA_KHOI]["tran_d12"]["E_D"] = hong
        with pytest.raises(TranVonError, match="tran_d12.E_D"):
            _load(_repo(tmp_path, cfg))

    def test_tier_a_khong_khai_von_thi_khong_co_gi_de_vuot(self) -> None:
        """Fixture dựng tay (`tier_a: {}`) — không khoá vốn nào để so; thiếu khối cũng không raise."""
        assert cac_khoa_vuot_tran({}, {}) == []


class TestHienVatXacNhan:
    def test_hien_vat_dat_da_commit_thi_DUOC_vuot_tran(self, tmp_path) -> None:
        _load(_repo(tmp_path, _cfg_vuot(), hien_vat=_hv()))

    def test_hien_vat_chua_commit_thi_TU_CHOI(self, tmp_path) -> None:
        repo = _repo(tmp_path, _cfg_vuot(), hien_vat=_hv(), commit_hien_vat=False)
        with pytest.raises(TranVonError, match="CHƯA COMMIT"):
            _load(repo)

    def test_hien_vat_sua_sau_commit_thi_TU_CHOI(self, tmp_path) -> None:
        repo = _repo(tmp_path, _cfg_vuot(), hien_vat=_hv())
        (repo / HIEN_VAT).write_text(json.dumps(_hv(gia_tri=0.5)), encoding="utf-8")
        with pytest.raises(TranVonError, match="ĐÃ SỬA SAU KHI COMMIT"):
            _load(repo)

    def test_nguong_chua_dien_la_inf_nen_khong_bao_gio_dat(self, tmp_path) -> None:
        repo = _repo(tmp_path, _cfg_vuot(nguong=None), hien_vat=_hv(gia_tri=1e9))
        with pytest.raises(TranVonError, match=r"\+inf"):
            _load(repo)

    def test_chi_so_chua_dien_thi_TU_CHOI(self, tmp_path) -> None:
        repo = _repo(tmp_path, _cfg_vuot(chi_so=None), hien_vat=_hv())
        with pytest.raises(TranVonError, match="chi_so chưa điền"):
            _load(repo)

    @pytest.mark.parametrize(
        ("doi", "khop"),
        [
            ({"n_lenh": 29}, "n_lenh 29 < 30"),
            ({"n_lenh": 30.0}, "n_lenh phải là số nguyên"),
            ({"n_lenh": True}, "n_lenh phải là số nguyên"),
            ({"tu_ngay": "2026-09-06"}, "không nằm SAU T3"),
            ({"tu_ngay": "2026-02-01"}, "không nằm SAU T3"),
            ({"tu_ngay": None}, "tu_ngay phải dạng"),
            ({"chi_so": "dsr_adjusted_expectancy"}, "khác chỉ số đã chốt"),
            ({"gia_tri": 0.049}, "< ngưỡng 0.05"),
            ({"gia_tri": None}, "gia_tri phải là số hữu hạn"),
            ({"gia_tri": math.nan}, "gia_tri phải là số hữu hạn"),
            ({"hypothesis_slot": "A-01"}, "hypothesis_slot"),
            ({"dr": "DR-LOCKBOX-03"}, "dr phải là"),
        ],
    )
    def test_hien_vat_sai_tung_diem_thi_TU_CHOI(self, tmp_path, doi, khop) -> None:
        repo = _repo(tmp_path, _cfg_vuot(), hien_vat=_hv(**doi))
        with pytest.raises(TranVonError, match=khop):
            _load(repo)

    def test_n_lenh_toi_thieu_duoi_san_DR011_thi_TU_CHOI(self, tmp_path) -> None:
        cfg = _cfg_vuot()
        cfg["tier_c"][KHOA_KHOI]["n_lenh_toi_thieu"] = 10
        with pytest.raises(TranVonError, match="n_lenh_toi_thieu"):
            _load(_repo(tmp_path, cfg, hien_vat=_hv(n_lenh=12)))


class TestNoiDuongSanXuat:
    def test_chien_luoc_doc_config_trong_init(self) -> None:
        """Chốt chỉ CHẶN CỨNG nếu lỗi không bị Freqtrade nuốt: `__init__` nằm ngoài `strategy_safe_wrapper` (TD-0187)."""
        import ast

        cay = ast.parse((REPO / "user_data" / "strategies" / "ZoneAbsorption.py").read_text(encoding="utf-8"))
        init = next(
            n for n in ast.walk(cay)
            if isinstance(n, ast.FunctionDef) and n.name == "__init__"
        )
        goi = [n for n in ast.walk(init) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "load_tool_d_config"]
        assert goi, "ZoneAbsorption.__init__ phải gọi load_tool_d_config()"
