"""🔴 L-Z56 CRITICAL (TD-0165) — bộ chạy ablation TỪ CHỐI khi chưa có Δ_R
của cổng D3.5 **đã commit**.

Spec: *"Chạy bất kỳ arm ablation nào khi chưa có kết quả Δ_R của cổng
D3.5 (cả ba bước, cả hai hướng) đã commit → bộ chạy TỪ CHỐI (DR-015 §1)."*

Ba thứ bộ test canh, xếp theo mức dễ bị bỏ sót:

1. **"Đã commit" ≠ "có file trên đĩa".** Một con số chưa commit vẫn sửa
   được sau khi nhìn thấy kết quả ablation, và sửa xong không để lại dấu
   vết. Có ca riêng cho: chưa theo dõi, và đã theo dõi nhưng bị sửa.
2. **Artifact trôi khỏi code.** Một file commit từ tháng trước vẫn "đã
   commit" hoàn hảo trong khi công thức tính Δ_R đã đổi.
3. **Chốt phải NỐI THẬT vào E3**, không chỉ tồn tại. Có ca soi AST của
   `run_ablation.py` — cùng bài học L-Z36: một phép kiểm không được gọi
   là một phép kiểm không tồn tại.
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from types import MappingProxyType

import pytest

from tool_d.config.loader import ToolDConfig
from tool_d.dr015.cong_d35 import (
    EXIT_CHUA_CO_DELTA_R,
    FILE_KET_QUA_D35,
    CongD35ChuaDongError,
    kiem_cong_d35,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DELTA_THAT = 0.16120552895757337  # số niêm phong của TD-0161


def _cfg(*, long: bool = True, short: bool = False) -> ToolDConfig:
    trong = MappingProxyType({})
    return ToolDConfig(
        tier_a=MappingProxyType({"enable_long": long, "enable_short": short}),
        tier_b=trong, tier_frozen=trong, tier_c=trong, raw_text="", sha256="",
    )


def _repo_gia(tmp_path: Path, *, delta_long=DELTA_THAT, commit=True, tho=None) -> Path:
    """Repo git thật, nhỏ — không mock `git`, vì chính hành vi của git là
    thứ đang được kiểm."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)

    goc = json.loads((REPO_ROOT / "docs/du-lieu-do/dr015-luot-khop-tranche.json").read_text("utf-8"))
    (tmp_path / "docs/du-lieu-do").mkdir(parents=True)
    (tmp_path / "docs/du-lieu-do/dr015-luot-khop-tranche.json").write_text(
        json.dumps(tho if tho is not None else goc, ensure_ascii=False), encoding="utf-8"
    )
    b1 = {"delta_r": {
        "LONG": {"gia_tri": delta_long, "trang_thai": "ok", "so_lenh": 35, "dung_p90": True},
        "SHORT": {"gia_tri": None, "trang_thai": "unreadable", "so_lenh": 0, "dung_p90": False},
    }}
    for i, (_, p) in enumerate(FILE_KET_QUA_D35):
        (tmp_path / p).write_text(json.dumps(b1 if i == 0 else {"x": 1}), encoding="utf-8")
    if commit:
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-qm", "seed"], cwd=tmp_path, check=True)
    return tmp_path


class TestDaCommitKhongPhaiChiCoFile:
    def test_du_dieu_kien_thi_KHONG_raise(self, tmp_path: Path) -> None:
        delta = kiem_cong_d35(repo_dir=_repo_gia(tmp_path), cfg=_cfg())
        assert delta["LONG"]["gia_tri"] == pytest.approx(DELTA_THAT)

    def test_file_CHUA_COMMIT_thi_TU_CHOI_du_da_co_tren_dia(self, tmp_path: Path) -> None:
        """🔴 Ca cốt lõi: file có đủ, nội dung đúng, nhưng chưa commit —
        vẫn sửa được sau khi thấy kết quả ablation."""
        with pytest.raises(CongD35ChuaDongError, match="CHƯA COMMIT"):
            kiem_cong_d35(repo_dir=_repo_gia(tmp_path, commit=False), cfg=_cfg())

    def test_da_commit_roi_SUA_LAI_thi_TU_CHOI(self, tmp_path: Path) -> None:
        """Con số đang chạy KHÁC con số niêm phong."""
        repo = _repo_gia(tmp_path)
        p = repo / FILE_KET_QUA_D35[0][1]
        d = json.loads(p.read_text("utf-8"))
        d["delta_r"]["LONG"]["gia_tri"] = 0.001  # nới cho DCA dễ thắng
        p.write_text(json.dumps(d), encoding="utf-8")
        with pytest.raises(CongD35ChuaDongError, match="ĐÃ SỬA SAU KHI COMMIT"):
            kiem_cong_d35(repo_dir=repo, cfg=_cfg())

    def test_thieu_mot_file_bat_ky_thi_TU_CHOI(self, tmp_path: Path) -> None:
        repo = _repo_gia(tmp_path)
        (repo / FILE_KET_QUA_D35[2][1]).unlink()
        with pytest.raises(CongD35ChuaDongError, match="Bước 3|KHÔNG TỒN TẠI|ĐÃ SỬA"):
            kiem_cong_d35(repo_dir=repo, cfg=_cfg())

    def test_doi_ba_file_cua_ca_ba_buoc(self) -> None:
        """"Cả ba bước" — không được rút xuống hai."""
        assert len(FILE_KET_QUA_D35) == 3


class TestArtifactTroiKhoiCode:
    def test_delta_r_niem_phong_LECH_voi_tinh_lai_thi_TU_CHOI(self, tmp_path: Path) -> None:
        """🔴 Một artifact commit từ tháng trước vẫn 'đã commit' hoàn hảo
        trong khi công thức tính Δ_R đã đổi — lúc đó ablation chạy với một
        con số không còn là thứ code hiện tại sinh ra."""
        repo = _repo_gia(tmp_path, delta_long=0.999)
        with pytest.raises(CongD35ChuaDongError, match="TRÔI khỏi code"):
            kiem_cong_d35(repo_dir=repo, cfg=_cfg())

    def test_tinh_lai_dung_du_lieu_tho_DA_COMMIT(self, tmp_path: Path) -> None:
        """Đổi dữ liệu thô → Δ_R tính lại đổi theo → lệch artifact → từ
        chối. Chốt này canh cả hai đầu, không chỉ artifact."""
        goc = json.loads(
            (REPO_ROOT / "docs/du-lieu-do/dr015-luot-khop-tranche.json").read_text("utf-8")
        )
        bot = dict(goc, luot_khop=[r for r in goc["luot_khop"] if r["trade_idx"] < 20])
        with pytest.raises(CongD35ChuaDongError, match="TRÔI khỏi code"):
            kiem_cong_d35(repo_dir=_repo_gia(tmp_path, tho=bot), cfg=_cfg())


class TestCaHaiHuong:
    def test_bat_SHORT_ma_thieu_delta_SHORT_thi_TU_CHOI(self, tmp_path: Path) -> None:
        """Bật Short thì phải có Δ_R(Short) — KHÔNG dùng Δ_R(Long) thay."""
        with pytest.raises(CongD35ChuaDongError, match="SHORT"):
            kiem_cong_d35(repo_dir=_repo_gia(tmp_path), cfg=_cfg(short=True))

    def test_tat_SHORT_thi_khong_doi_delta_SHORT(self, tmp_path: Path) -> None:
        """Diễn giải đã chọn (xem docstring module): đòi Δ_R cho mọi hướng
        ablation THỰC SỰ chạy. Đọc theo chữ 'cả hai hướng' thì cổng không
        bao giờ mở được với chiến lược LONG-only — và một chốt không bao
        giờ thoả được sẽ bị gỡ bỏ."""
        kiem_cong_d35(repo_dir=_repo_gia(tmp_path), cfg=_cfg(short=False))

    def test_tat_CA_HAI_huong_thi_TU_CHOI(self, tmp_path: Path) -> None:
        with pytest.raises(CongD35ChuaDongError, match="CẢ hai hướng"):
            kiem_cong_d35(repo_dir=_repo_gia(tmp_path), cfg=_cfg(long=False, short=False))

    def test_huong_doc_tu_CAU_HINH_khong_nhan_loi_khai(self) -> None:
        import inspect

        import tool_d.dr015.cong_d35 as mod

        src = inspect.getsource(mod._huong_can_co)
        assert "tier_a.enable_long" in src and "tier_a.enable_short" in src


class TestNoiThatVaoE3:
    """🔴 Cùng bài học L-Z36: một phép kiểm không được gọi là một phép
    kiểm không tồn tại."""

    def test_E3_co_goi_kiem_cong_d35(self) -> None:
        cay = ast.parse((REPO_ROOT / "entrypoints/run_ablation.py").read_text("utf-8"))
        goi = {
            n.func.id
            for n in ast.walk(cay)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        assert "kiem_cong_d35" in goi

    def test_E3_tra_dung_exit_code_rieng(self) -> None:
        src = (REPO_ROOT / "entrypoints/run_ablation.py").read_text("utf-8")
        assert "EXIT_CHUA_CO_DELTA_R" in src
        assert EXIT_CHUA_CO_DELTA_R not in (86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97)

    def test_chot_dung_TRUOC_verify_seal(self) -> None:
        """Từ chối sớm: chốt này rẻ, `verify_all_seals()` thì không."""
        src = (REPO_ROOT / "entrypoints/run_ablation.py").read_text("utf-8")
        than = src.split("def main(")[1]
        assert than.index("kiem_cong_d35()") < than.index("verify_all_seals(")
