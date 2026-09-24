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
CHI_SO = "mean_r"
SLOT = "IQ-0003"
NGAY_CHON = "2026-10-01T10:00:00Z"
HASH_CHAM = "c" * 64
SO_Y_TUONG = "registry/idea_queue.jsonl"
SO_TRUY_CAP = "lockbox/lockbox_access.log"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _dong_y_tuong(*, voided: bool = False) -> list[dict]:
    """TD-0387 — sổ ý tưởng tối thiểu: `SLOT` QUEUED → SELECTED (→ VOIDED nếu `voided`)."""
    dong = [{"idea_id": SLOT, "status": "QUEUED", "selected_at": None},
            {"idea_id": SLOT, "status": "SELECTED", "selected_at": NGAY_CHON}]
    if voided:
        dong.append({"idea_id": SLOT, "status": "VOIDED", "selected_at": NGAY_CHON})
    return dong


def _ban_ghi_cham(hash_cham: str = HASH_CHAM) -> dict:
    return {"accessed_at": "2026-12-01T00:00:00Z", "reason": "D9.5", "config_hash": hash_cham,
            "seal_path": "lockbox/lockbox_seal_1.json", "seal_file_hash": "d" * 64}


def _cfg_that() -> dict:
    return yaml.safe_load(CONFIG_THAT.read_text(encoding="utf-8"))


def _repo(
    tmp_path: Path,
    cfg: dict,
    *,
    hien_vat: dict | None = None,
    commit_hien_vat: bool = True,
    y_tuong: list[dict] | None = None,
    cham: list[dict] | None = None,
) -> Path:
    """Repo tạm: config + sổ ý tưởng (mặc định `SLOT` đã CHỌN) + sổ truy cập lockbox (mặc định một lần chạm
    `HASH_CHAM`), đều commit; hiện vật tuỳ `commit_hien_vat`. Truyền `[]` để bỏ sổ."""
    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "config" / "tool_d_config.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    for rel, dong in ((SO_Y_TUONG, _dong_y_tuong() if y_tuong is None else y_tuong),
                      (SO_TRUY_CAP, [_ban_ghi_cham()] if cham is None else cham)):
        if dong:
            p = repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("".join(json.dumps(d) + "\n" for d in dong), encoding="utf-8")
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
    if cfg["tier_c"][KHOA_KHOI]["tran_d12"][khoa] is None:  # TD-0404: trần vốn rổ chưa điền ⇒ dựng một trần số
        cfg["tier_c"][KHOA_KHOI]["tran_d12"][khoa] = 1000
    cfg["tier_a"][khoa] = cfg["tier_c"][KHOA_KHOI]["tran_d12"][khoa] * 2
    cfg["tier_c"][KHOA_KHOI]["chi_so"] = chi_so
    cfg["tier_c"][KHOA_KHOI]["nguong"] = nguong
    return cfg


def _hv(**doi) -> dict:
    hv = {"dr": "DR-LOCKBOX-04", "hypothesis_slot": SLOT, "tu_ngay": NGAY_CHON[:10],
          "n_lenh": 30, "chi_so": CHI_SO, "gia_tri": 0.08, "config_sha256": HASH_CHAM}
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
        # 🔄 24/09/2026 (TD-0404, `DR-LOCKBOX-04` bổ sung, ngoại lệ trong kế hoạch chủ dự án duyệt): thêm `von_ro_usdt: None`
        # — vốn rổ `IQ-0003` chưa chốt (`DR-D0-IQ0003` §10 c), trần điền CÙNG commit. Ba số cũ giữ nguyên.
        assert cfg["tier_c"][KHOA_KHOI]["tran_d12"] == {"E_D": 750, "rho_pct": 0.375, "L_exchange": 3, "von_ro_usdt": None}
        assert {k: cfg["tier_a"][k] for k in KHOA_VON} == cfg["tier_c"][KHOA_KHOI]["tran_d12"]

    def test_config_that_chua_the_xac_nhan(self) -> None:
        """TD-0386: ô ký đã điền nhưng CHƯA có hiện vật đo ⇒ lớp xác nhận KHÔNG đạt được hôm nay (N6: chưa đo không
        phải đạt). Lý do chưa đạt phải là thiếu hiện vật, không còn là ô trống."""
        cfg = _cfg_that()
        ly_do = ly_do_chua_xac_nhan(cfg["tier_c"], REPO)
        assert ly_do, "không có hiện vật mà lớp xác nhận lại đạt"
        assert any("KHÔNG TỒN TẠI" in x for x in ly_do)
        assert not any("chưa điền" in x or "+inf" in x for x in ly_do)

    def test_o_ky_dung_quyet_dinh_chu_du_an(self) -> None:
        """🔴 Ghim QUYẾT ĐỊNH (TD-0386, ô ký DR-LOCKBOX-04 §3 `fe1da36`, 24/09/2026): `mean_r` ≥ 0,10 R, n ≥ 30.
        Trước TD-0386 test này ghim trạng thái ⏳ (`null`); đổi thành ghim quyết định khi ô được điền."""
        khoi = _cfg_that()["tier_c"][KHOA_KHOI]
        assert khoi["chi_so"] == "mean_r"
        assert khoi["nguong"] == 0.10
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


class TestTD0387SietChot:
    """TD-0387 — ba điều kiện của quyết định "backtest từ ngày CHỌN, đo một lần" (ô ký DR-LOCKBOX-04 §3, DR-XAC-NHAN-01)."""

    def test_tu_ngay_truoc_ngay_chon_thi_TU_CHOI(self, tmp_path) -> None:
        repo = _repo(tmp_path, _cfg_vuot(), hien_vat=_hv(tu_ngay="2026-09-30"))
        with pytest.raises(TranVonError, match="trước ngày CHỌN 2026-10-01"):
            _load(repo)

    def test_tu_ngay_dung_ngay_chon_thi_qua(self, tmp_path) -> None:
        """Biên nửa mở `[ngày CHỌN, …)` của DR-XAC-NHAN-01 §2: đúng ngày CHỌN được nhận."""
        _load(_repo(tmp_path, _cfg_vuot(), hien_vat=_hv(tu_ngay="2026-10-01")))

    def test_lan_chon_da_huy_thi_khong_con_hieu_luc(self, tmp_path) -> None:
        repo = _repo(tmp_path, _cfg_vuot(), hien_vat=_hv(), y_tuong=_dong_y_tuong(voided=True))
        with pytest.raises(TranVonError, match="không có lần CHỌN còn hiệu lực"):
            _load(repo)

    def test_slot_khac_chua_duoc_chon_thi_TU_CHOI(self, tmp_path) -> None:
        repo = _repo(tmp_path, _cfg_vuot(), hien_vat=_hv(hypothesis_slot="IQ-0009"))
        with pytest.raises(TranVonError, match="IQ-0009 không có lần CHỌN còn hiệu lực"):
            _load(repo)

    def test_thieu_so_y_tuong_thi_TU_CHOI(self, tmp_path) -> None:
        repo = _repo(tmp_path, _cfg_vuot(), hien_vat=_hv(), y_tuong=[])
        with pytest.raises(TranVonError, match="sổ ý tưởng .* đọc không được"):
            _load(repo)

    def test_hien_vat_commit_hai_lan_thi_TU_CHOI(self, tmp_path) -> None:
        """Đo lại rồi commit đè = "đo tới khi đẹp" — cấm kể cả khi bản mới vẫn đạt ngưỡng."""
        repo = _repo(tmp_path, _cfg_vuot(), hien_vat=_hv(gia_tri=0.06))
        (repo / HIEN_VAT).write_text(json.dumps(_hv(gia_tri=0.09)), encoding="utf-8")
        _git(repo, "add", HIEN_VAT)
        _git(repo, "commit", "-qm", "do lai")
        with pytest.raises(TranVonError, match="ĐÚNG MỘT commit.*nhận 2"):
            _load(repo)

    def test_chua_cham_lockbox_thi_TU_CHOI(self, tmp_path) -> None:
        repo = _repo(tmp_path, _cfg_vuot(), hien_vat=_hv(), cham=[])
        with pytest.raises(TranVonError, match="chưa có lần chạm lockbox nào"):
            _load(repo)

    @pytest.mark.parametrize("cfg_hv", ["e" * 64, None])
    def test_config_khong_khop_lan_cham_thi_TU_CHOI(self, tmp_path, cfg_hv) -> None:
        repo = _repo(tmp_path, _cfg_vuot(), hien_vat=_hv(config_sha256=cfg_hv))
        with pytest.raises(TranVonError, match="không khớp cấu hình nào đã chạm lockbox"):
            _load(repo)

    def test_khop_mot_trong_nhieu_lan_cham_thi_qua(self, tmp_path) -> None:
        _load(_repo(tmp_path, _cfg_vuot(), hien_vat=_hv(), cham=[_ban_ghi_cham("f" * 64), _ban_ghi_cham()]))


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


def _cfg_von_ro(von: object, tran: object = "khong_doi") -> dict:
    """TD-0404 — config thật, chỉ đổi vốn rổ (và trần nếu truyền). `tran = "xoa"` ⇒ bỏ hẳn khoá khỏi `tran_d12`."""
    cfg = copy.deepcopy(_cfg_that())
    cfg["tier_a"]["von_ro_usdt"] = von
    t = cfg["tier_c"][KHOA_KHOI]["tran_d12"]
    if tran == "xoa":
        del t["von_ro_usdt"]
    elif tran != "khong_doi":
        t["von_ro_usdt"] = tran
    return cfg


class TestVonRoTD0404:
    """`DR-LOCKBOX-04` bổ sung 24/09/2026: vốn rổ `IQ-0003` vào trần D12. `null` ⇒ bỏ qua; có số mà trần trống ⇒ VƯỢT."""

    def test_von_ro_null_thi_bo_qua(self, tmp_path) -> None:
        _load(_repo(tmp_path, _cfg_von_ro(None)))

    def test_von_ro_co_so_ma_tran_trong_thi_TU_CHOI(self, tmp_path) -> None:
        with pytest.raises(TranVonError, match="von_ro_usdt: 500 mà trần tran_d12.von_ro_usdt còn trống"):
            _load(_repo(tmp_path, _cfg_von_ro(500)))

    def test_von_ro_bang_tran_thi_qua(self, tmp_path) -> None:
        _load(_repo(tmp_path, _cfg_von_ro(500, 500)))

    def test_von_ro_vuot_tran_mot_don_vi_thi_TU_CHOI(self, tmp_path) -> None:
        with pytest.raises(TranVonError, match="von_ro_usdt: 501 > trần 500"):
            _load(_repo(tmp_path, _cfg_von_ro(501, 500)))

    def test_von_ro_thieu_khoa_tran_thi_TU_CHOI(self, tmp_path) -> None:
        with pytest.raises(TranVonError, match="thiếu trần tran_d12.von_ro_usdt"):
            _load(_repo(tmp_path, _cfg_von_ro(500, "xoa")))

    @pytest.mark.parametrize("hong", ["500", math.inf, True])
    def test_tran_von_ro_hong_thi_TU_CHOI(self, tmp_path, hong) -> None:
        with pytest.raises(TranVonError, match="tran_d12.von_ro_usdt"):
            _load(_repo(tmp_path, _cfg_von_ro(500, hong)))

    def test_von_ro_null_khong_can_khoa_tran(self, tmp_path) -> None:
        """Rổ chưa cấp vốn thì không đòi trần — config cũ thiếu khoá vẫn đọc được."""
        _load(_repo(tmp_path, _cfg_von_ro(None, "xoa")))

    def test_tran_trong_nhung_da_xac_nhan_thi_qua(self, tmp_path) -> None:
        """Như ba khoá cũ: lớp xác nhận ĐẠT thì trần thôi áp."""
        cfg = _cfg_von_ro(500)
        cfg["tier_c"][KHOA_KHOI]["nguong"] = 0.05
        _load(_repo(tmp_path, cfg, hien_vat=_hv()))
