"""TD-0384 chặng 3 — bộ khởi chạy D10 (`ops/live_d10.py`) và ba service compose profile `d10`.

Mọi key/token là GIẢ; không gọi mạng thật (metadata sàn thay bằng hàm giả)."""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tool_d.ops import live_d10
from tool_d.ops.live_d10 import (
    CAU_HINH_API_SERVER,
    CAU_HINH_FREQTRADE_GOC,
    DB_URL_LIVE,
    RO_D10,
    TEN_CHIEN_LUOC,
    LiveD10Error,
    bien_moi_truong_san,
    chon_ro_va_ghi,
    doc_ro_d10,
    dung_cau_hinh_live_d10,
    kiem_ro_da_commit,
    lenh_freqtrade,
    ung_vien_tu_san,
)
from tool_d.pool_giai_doan import POOL_HOM_NAY

REPO_ROOT = Path(__file__).resolve().parents[2]
NGUON = REPO_ROOT / "src/tool_d/ops/live_d10.py"
RO = ("DOGE/USDT:USDT", "XRP/USDT:USDT")
KHOA_D10 = {"dry_run", "strategy", "db_url", "bot_name", "initial_state", "max_open_trades"}


def _repo_gia(tmp_path: Path, *, sua=None) -> Path:
    goc = tmp_path / "repo"
    (goc / "config/freqtrade").mkdir(parents=True)
    ft = json.loads((REPO_ROOT / CAU_HINH_FREQTRADE_GOC).read_text(encoding="utf-8"))
    if sua is not None:
        sua(ft)
    (goc / CAU_HINH_FREQTRADE_GOC).write_text(json.dumps(ft), encoding="utf-8")
    return goc


class TestDungCauHinh:
    def test_chi_doi_khoa_d10_va_ro(self, tmp_path) -> None:
        kq = dung_cau_hinh_live_d10(ro=RO, repo_dir=REPO_ROOT, thu_muc_ra=tmp_path)
        goc = json.loads((REPO_ROOT / CAU_HINH_FREQTRADE_GOC).read_text(encoding="utf-8"))
        phu = json.loads(kq.duong_dan.read_text(encoding="utf-8"))
        assert phu["dry_run"] is False and phu["strategy"] == TEN_CHIEN_LUOC and phu["db_url"] == DB_URL_LIVE
        assert phu["db_url"] != goc["db_url"]  # DB live TÁCH DB dry-run (N11)
        assert phu["max_open_trades"] == 1
        doi = {k for k in set(goc) | set(phu) if goc.get(k) != phu.get(k)}
        assert doi == KHOA_D10 | {"exchange"}, doi
        assert {k for k in goc["exchange"] if goc["exchange"][k] != phu["exchange"][k]} == {"pair_whitelist"}
        assert phu["exchange"]["pair_whitelist"] == list(RO)

    def test_ban_phu_khong_chua_bi_mat(self, tmp_path) -> None:
        kq = dung_cau_hinh_live_d10(ro=RO, repo_dir=REPO_ROOT, thu_muc_ra=tmp_path)
        phu = json.loads(kq.duong_dan.read_text(encoding="utf-8"))
        assert not phu["exchange"].get("key") and not phu["exchange"].get("secret") and "telegram" not in phu

    def test_tu_choi_file_goc_co_key(self, tmp_path) -> None:
        goc = _repo_gia(tmp_path, sua=lambda ft: ft["exchange"].update(secret="bi-mat-gia"))
        with pytest.raises(LiveD10Error, match="secret"):
            dung_cau_hinh_live_d10(ro=RO, repo_dir=goc, thu_muc_ra=tmp_path / "ra")

    def test_tu_choi_ro_rong(self, tmp_path) -> None:
        with pytest.raises(LiveD10Error, match="rỗng"):
            dung_cau_hinh_live_d10(ro=(), repo_dir=REPO_ROOT, thu_muc_ra=tmp_path)

    def test_lenh_co_ca_cau_hinh_control_api(self, tmp_path) -> None:
        lenh = lenh_freqtrade(dung_cau_hinh_live_d10(ro=RO, repo_dir=REPO_ROOT, thu_muc_ra=tmp_path))
        cau_hinh = [lenh[i + 1] for i, x in enumerate(lenh) if x == "--config"]
        assert lenh[:2] == ["freqtrade", "trade"] and str(CAU_HINH_API_SERVER) in cau_hinh and len(cau_hinh) == 2
        assert lenh[lenh.index("--strategy") + 1] == TEN_CHIEN_LUOC

    def test_key_di_qua_env_dung_ten_freqtrade(self) -> None:
        assert bien_moi_truong_san("k", "s") == {"FREQTRADE__EXCHANGE__KEY": "k", "FREQTRADE__EXCHANGE__SECRET": "s"}


class TestDocRo:
    def _ghi(self, tmp_path, noi_dung) -> Path:
        p = tmp_path / "ro.yaml"
        p.write_text(yaml.safe_dump(noi_dung), encoding="utf-8")
        return p

    def test_doc_dung(self, tmp_path) -> None:
        assert doc_ro_d10(self._ghi(tmp_path, {"cap": list(RO)})) == RO

    def test_thieu_file(self, tmp_path) -> None:
        with pytest.raises(LiveD10Error, match="--chon-ro"):
            doc_ro_d10(tmp_path / "khong-co.yaml")

    @pytest.mark.parametrize("noi_dung", [{}, {"cap": []}, {"cap": "DOGE"}, {"cap": ["A", "A"]}, {"cap": [""]}],
                             ids=["thieu-khoa", "rong", "khong-phai-list", "trung", "ten-rong"])
    def test_sai_dang_thi_tu_choi(self, tmp_path, noi_dung) -> None:
        with pytest.raises(LiveD10Error):
            doc_ro_d10(self._ghi(tmp_path, noi_dung))

    def test_qua_tran_so_cap_thi_tu_choi(self, tmp_path) -> None:
        with pytest.raises(LiveD10Error, match="trần"):
            doc_ro_d10(self._ghi(tmp_path, {"cap": [f"C{i}/USDT:USDT" for i in range(11)]}))


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class TestRoDaCommit:
    @pytest.fixture
    def repo(self, tmp_path) -> Path:
        if shutil.which("git") is None:
            pytest.skip("không có git")
        r = tmp_path / "r"
        (r / "config").mkdir(parents=True)
        _git(r, "init", "-q")
        _git(r, "config", "user.email", "t@t")
        _git(r, "config", "user.name", "t")
        return r

    def test_chua_commit_thi_tu_choi(self, repo) -> None:
        (repo / RO_D10).write_text("cap: [A]\n", encoding="utf-8")
        with pytest.raises(LiveD10Error, match="CHƯA được commit"):
            kiem_ro_da_commit(RO_D10, repo_dir=repo)

    def test_da_commit_va_nguyen_ven_thi_qua(self, repo) -> None:
        (repo / RO_D10).write_text("cap: [A]\n", encoding="utf-8")
        _git(repo, "add", str(RO_D10))
        _git(repo, "commit", "-qm", "ro")
        kiem_ro_da_commit(RO_D10, repo_dir=repo)

    def test_sua_sau_commit_thi_tu_choi(self, repo) -> None:
        (repo / RO_D10).write_text("cap: [A]\n", encoding="utf-8")
        _git(repo, "add", str(RO_D10))
        _git(repo, "commit", "-qm", "ro")
        (repo / RO_D10).write_text("cap: [B]\n", encoding="utf-8")
        with pytest.raises(LiveD10Error, match="SỬA sau commit"):
            kiem_ro_da_commit(RO_D10, repo_dir=repo)


EXCHANGE_INFO = {"symbols": [
    {"symbol": "DOGEUSDT", "filters": [{"filterType": "MIN_NOTIONAL", "notional": "5"},
                                       {"filterType": "LOT_SIZE", "stepSize": "1", "minQty": "1"}]},
    {"symbol": "XRPUSDT", "filters": [{"filterType": "MIN_NOTIONAL", "notional": "5"},
                                      {"filterType": "LOT_SIZE", "stepSize": "0.1", "minQty": "0.1"}]},
]}
TICKER_24H = [{"symbol": "DOGEUSDT", "quoteVolume": "9e8"}, {"symbol": "XRPUSDT", "quoteVolume": "5e8"}]
GIA = [{"symbol": "DOGEUSDT", "price": "0.25"}, {"symbol": "XRPUSDT", "price": "2.5"}]


class TestChonRo:
    def test_ung_vien_thieu_bo_loc_thi_san_none(self) -> None:
        uv = ung_vien_tu_san(EXCHANGE_INFO, TICKER_24H, GIA, ["DOGEUSDT", "ABCUSDT"], strategy_stoploss=-0.99)
        assert uv[0].cap == "DOGE/USDT:USDT" and uv[0].san_usdt is not None and uv[0].san_usdt > 0
        assert uv[1].san_usdt is None and uv[1].quote_volume_24h is None

    def test_chon_ro_va_ghi_file_co_nguon(self, tmp_path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        (repo / "config/freqtrade").mkdir(parents=True)
        shutil.copy(REPO_ROOT / CAU_HINH_FREQTRADE_GOC, repo / CAU_HINH_FREQTRADE_GOC)
        shutil.copy(REPO_ROOT / "config/tool_d_config.yaml", repo / "config/tool_d_config.yaml")
        (repo / POOL_HOM_NAY).write_text(yaml.safe_dump({"trading": ["XRPUSDT", "DOGEUSDT"]}), encoding="utf-8")
        monkeypatch.setattr(live_d10, "get_exchange_info", lambda: EXCHANGE_INFO)
        monkeypatch.setattr(live_d10, "get_ticker_24hr", lambda: TICKER_24H)
        monkeypatch.setattr(live_d10, "get_ticker_price", lambda: GIA)
        assert chon_ro_va_ghi(repo_dir=repo) == ("DOGE/USDT:USDT", "XRP/USDT:USDT")
        ghi = yaml.safe_load((repo / RO_D10).read_text(encoding="utf-8"))
        assert ghi["cap"] == ["DOGE/USDT:USDT", "XRP/USDT:USDT"] and "chon_luc_utc" in ghi and "DR-D10-02" in ghi["_nguon"]


class TestThuTuChotTrongMain:
    """Kiểm AST (allow-list, không deny-list tên callback — nợ đã khai ở dòng `D10–D12` của `TASKS.md`)."""

    @staticmethod
    def _goi_trong(ham: ast.FunctionDef) -> list[tuple[int, str]]:
        return sorted(
            (n.lineno, n.func.id if isinstance(n.func, ast.Name) else n.func.attr)
            for n in ast.walk(ham)
            if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))
        )

    def _main(self) -> ast.FunctionDef:
        cay = ast.parse(NGUON.read_text(encoding="utf-8"))
        return next(n for n in cay.body if isinstance(n, ast.FunctionDef) and n.name == "main")

    def test_kiem_credential_nam_trong_main_va_truoc_moi_buoc_khac(self) -> None:
        goi = [ten for _, ten in self._goi_trong(self._main())]
        i = goi.index("validate_credentials_for_live")
        for sau in ("kiem_truoc_khi_bat", "kiem_ro_da_commit", "dung_cau_hinh_live_d10", "execvp"):
            assert goi.index(sau) > i, f"{sau} chạy TRƯỚC validate_credentials_for_live"

    def test_kiem_bao_mat_truoc_khi_exec(self) -> None:
        goi = [ten for _, ten in self._goi_trong(self._main())]
        assert goi.index("kiem_truoc_khi_bat") < goi.index("execvp")
        assert goi.index("kiem_ro_da_commit") < goi.index("execvp")

    def test_chi_main_goi_kiem_credential(self) -> None:
        """Allow-list: trong module, CHỈ `main` gọi `validate_credentials_for_live`; chiến lược CTRL không gọi nó
        (callback bị Freqtrade nuốt exception — MT-16 vii)."""
        cay = ast.parse(NGUON.read_text(encoding="utf-8"))
        noi_goi = {
            ham.name
            for ham in ast.walk(cay)
            if isinstance(ham, ast.FunctionDef)
            for n in ast.walk(ham)
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "validate_credentials_for_live"
        }
        assert noi_goi == {"main"}
        chien_luoc = (REPO_ROOT / "user_data/strategies/CtrlD10.py").read_text(encoding="utf-8")
        assert "validate_credentials_for_live" not in chien_luoc


class TestComposeD10:
    @staticmethod
    def _sv() -> dict:
        return yaml.safe_load((REPO_ROOT / "docker/docker-compose.yml").read_text(encoding="utf-8"))["services"]

    def test_ba_service_sau_profile_rieng_d10(self) -> None:
        sv = self._sv()
        for ten in ("live-d10", "live-d10-watchdog", "risk-supervisor-d10"):
            assert sv[ten]["profiles"] == ["d10"], ten
            assert sv[ten]["env_file"] == [{"path": "../.env.d10", "required": True}], ten

    def test_bot_d10_khong_tu_khoi_dong_lai(self) -> None:
        """Q6: máy khởi động lại thì D10 KHÔNG tự chạy lại."""
        assert "restart" not in self._sv()["live-d10"]

    def test_watchdog_canh_runmode_live(self) -> None:
        assert self._sv()["live-d10-watchdog"]["entrypoint"][-2:] == ["--runmode", "live"]

    def test_supervisor_chung_mang_voi_bot_de_goi_localhost(self) -> None:
        sv = self._sv()["risk-supervisor-d10"]
        assert sv["network_mode"] == "service:live-d10"
        assert sv["entrypoint"][-1] == "http://127.0.0.1:8081"
        api = json.loads((REPO_ROOT / CAU_HINH_API_SERVER).read_text(encoding="utf-8"))["api_server"]
        assert (api["listen_ip_address"], api["listen_port"]) == ("127.0.0.1", 8081)

    def test_dry_run_khong_dung_profile_d10(self) -> None:
        sv = self._sv()
        assert sv["dryrun"]["profiles"] == ["van_hanh"] and "live-d10" not in str(sv["dryrun"])
