"""TD-0350/TD-0353 (`DR-TRIEN-KHAI-01`) — dry-run D11 chạy song song: cấu hình phủ, heartbeat, service Docker.

Ba thứ được khoá, mỗi thứ qua ĐƯỜNG SẢN XUẤT THẬT (không dựng lại logic trong test):
1. `dung_cau_hinh_dry_run()` đọc đúng `config/freqtrade/config.json` + `config/pool.yaml` của repo, chỉ đổi các
   khoá vận hành, và TỪ CHỐI mọi đường lọt sang tiền thật.
2. `ZoneAbsorption.bot_loop_start()` ghi heartbeat ở live/dry_run, KHÔNG ghi ở backtest, giữ `trang_thai_tu_luc`
   qua các vòng; `bot_start()` chọn file đỉnh equity theo runmode (dry-run và live không ghi đè nhau — N11).
3. Mọi service không phải `lockbox` trong `docker-compose.yml` — kể cả hai service vận hành mới — CHE
   `lockbox/data/` (ARCHITECTURE 3.1). Thêm một service quên che là mở lockbox cho một tiến trình chạy nền.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from tool_d.equity_peak import duong_dan_theo_runmode
from tool_d.ledger.decision_log import DEFAULT_DECISION_LOG_PATH, duong_dan_decision_log
from tool_d.ops.dry_run import (
    CAU_HINH_FREQTRADE_GOC,
    TEN_CHIEN_LUOC,
    DryRunError,
    bien_moi_truong_telegram,
    dung_cau_hinh_dry_run,
    lenh_freqtrade,
)
from tool_d.ops.heartbeat import HeartbeatError, doc_heartbeat, duong_dan_heartbeat, ghi_heartbeat
from tool_d.ops.heartbeat_watchdog import phan_tich_tham_so
from tool_d.pool_giai_doan import POOL_HOM_NAY

REPO_ROOT = Path(__file__).resolve().parents[2]
NGUON_CHIEN_LUOC = REPO_ROOT / "user_data/strategies/ZoneAbsorption.py"
KHOA_VAN_HANH = {"strategy", "initial_state", "bot_name"}


def _repo_gia(tmp_path: Path, *, sua=None, trading=None) -> Path:
    """Bản sao tối thiểu của repo: config Freqtrade THẬT (có thể sửa một khoá) + rổ."""
    goc = tmp_path / "repo"
    (goc / "config/freqtrade").mkdir(parents=True)
    ft = json.loads((REPO_ROOT / CAU_HINH_FREQTRADE_GOC).read_text(encoding="utf-8"))
    if sua is not None:
        sua(ft)
    (goc / CAU_HINH_FREQTRADE_GOC).write_text(json.dumps(ft), encoding="utf-8")
    if trading is None:
        shutil.copy(REPO_ROOT / POOL_HOM_NAY, goc / POOL_HOM_NAY)
    else:
        (goc / POOL_HOM_NAY).write_text(yaml.safe_dump({"trading": trading}), encoding="utf-8")
    return goc


class TestCauHinhDryRun:
    def test_chi_doi_khoa_van_hanh_va_ro(self, tmp_path) -> None:
        kq = dung_cau_hinh_dry_run(repo_dir=REPO_ROOT, thu_muc_ra=tmp_path)
        goc = json.loads((REPO_ROOT / CAU_HINH_FREQTRADE_GOC).read_text(encoding="utf-8"))
        phu = json.loads(kq.duong_dan.read_text(encoding="utf-8"))

        assert phu["dry_run"] is True
        assert phu["strategy"] == TEN_CHIEN_LUOC
        assert phu["initial_state"] == "running"
        assert phu["db_url"] == goc["db_url"]  # DB dry-run riêng (N11), không đổi
        doi = {k for k in set(goc) | set(phu) if goc.get(k) != phu.get(k)}
        assert doi == KHOA_VAN_HANH | {"exchange"}, doi
        doi_san = {k for k in goc["exchange"] if goc["exchange"][k] != phu["exchange"][k]}
        assert doi_san == {"pair_whitelist"}, doi_san

    def test_ro_la_pool_hom_nay_du_ma(self, tmp_path) -> None:
        kq = dung_cau_hinh_dry_run(repo_dir=REPO_ROOT, thu_muc_ra=tmp_path)
        trading = yaml.safe_load((REPO_ROOT / POOL_HOM_NAY).read_text(encoding="utf-8"))["trading"]
        cap = json.loads(kq.duong_dan.read_text(encoding="utf-8"))["exchange"]["pair_whitelist"]
        assert kq.so_cap == len(trading) == len(cap) > 2  # không còn 2 cặp giữ chỗ BTC/ETH
        assert cap == [f"{m[:-4]}/USDT:USDT" for m in trading]

    def test_tu_choi_cau_hinh_goc_khong_phai_dry_run(self, tmp_path) -> None:
        goc = _repo_gia(tmp_path, sua=lambda ft: ft.update(dry_run=False))
        with pytest.raises(DryRunError, match="dry_run"):
            dung_cau_hinh_dry_run(repo_dir=goc, thu_muc_ra=tmp_path / "ra")
        assert not (tmp_path / "ra").exists()

    def test_tu_choi_khi_file_goc_co_key(self, tmp_path) -> None:
        goc = _repo_gia(tmp_path, sua=lambda ft: ft["exchange"].update(api_key="abc"))
        with pytest.raises(DryRunError, match="api_key"):
            dung_cau_hinh_dry_run(repo_dir=goc, thu_muc_ra=tmp_path / "ra")

    def test_tu_choi_ro_rong(self, tmp_path) -> None:
        goc = _repo_gia(tmp_path, trading=[])
        with pytest.raises(DryRunError, match="rỗng"):
            dung_cau_hinh_dry_run(repo_dir=goc, thu_muc_ra=tmp_path / "ra")

    def test_lenh_freqtrade_la_trade_tren_cau_hinh_phu(self, tmp_path) -> None:
        kq = dung_cau_hinh_dry_run(repo_dir=REPO_ROOT, thu_muc_ra=tmp_path)
        lenh = lenh_freqtrade(kq)
        assert lenh[:2] == ["freqtrade", "trade"]
        assert lenh[lenh.index("--config") + 1] == str(kq.duong_dan)
        assert lenh[lenh.index("--strategy") + 1] == TEN_CHIEN_LUOC
        assert lenh.count("trade") == 1  # đúng một lệnh con, không nối thêm lệnh con nào khác


class TestHeartbeatTheoRunmode:
    def test_duong_dan_tach_dry_run_khoi_live(self) -> None:
        assert duong_dan_heartbeat("dry_run") != duong_dan_heartbeat("live")
        assert duong_dan_heartbeat("dry_run").parts[:3] == ("runs", "van_hanh", "dry_run")

    def test_backtest_khong_co_heartbeat(self) -> None:
        with pytest.raises(HeartbeatError):
            duong_dan_heartbeat("backtest")

    def test_ghi_tra_dung_ban_doc_lai(self, tmp_path) -> None:
        now = datetime(2026, 9, 20, tzinfo=timezone.utc)
        hb = ghi_heartbeat(tmp_path / "hb.json", trang_thai="RUNNING", now=now)
        assert doc_heartbeat(tmp_path / "hb.json").heartbeat == hb

    def test_watchdog_bat_buoc_khai_runmode(self) -> None:
        with pytest.raises(SystemExit):
            phan_tich_tham_so([])
        duong, ten = phan_tich_tham_so(["--runmode", "dry_run"])
        assert duong == duong_dan_heartbeat("dry_run") and ten == "tool_d_dry_run"


def _chien_luoc(runmode: str):
    """Dựng chiến lược THẬT (đọc `config/` theo cwd) — gọi TRƯỚC khi test đổi thư mục làm việc."""
    if str(REPO_ROOT / "user_data/strategies") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "user_data/strategies"))
    spec = importlib.util.spec_from_file_location("ZoneAbsorptionTD0350", NGUON_CHIEN_LUOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    s = m.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
    s.dp = SimpleNamespace(runmode=SimpleNamespace(value=runmode))
    return s


class TestBotLoopStartGhiHeartbeat:
    def test_dry_run_ghi_va_giu_moc_trang_thai(self, tmp_path, monkeypatch) -> None:
        s = _chien_luoc("dry_run")
        monkeypatch.chdir(tmp_path)
        s.bot_start()
        t0 = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
        s.bot_loop_start(current_time=t0)
        s.bot_loop_start(current_time=t0 + timedelta(seconds=5))

        kq = doc_heartbeat(tmp_path / duong_dan_heartbeat("dry_run"))
        assert kq.doc_duoc, kq.loi
        assert kq.heartbeat.thoi_diem == t0 + timedelta(seconds=5)
        assert kq.heartbeat.trang_thai == "RUNNING"
        assert kq.heartbeat.trang_thai_tu_luc == t0  # không bị đặt lại mỗi vòng

    def test_backtest_khong_ghi_gi(self, tmp_path, monkeypatch) -> None:
        s = _chien_luoc("backtest")
        monkeypatch.chdir(tmp_path)
        s.bot_start()
        s.bot_loop_start(current_time=datetime(2026, 9, 20, tzinfo=timezone.utc))
        assert not (tmp_path / "runs").exists()


class TestDinhEquityTachTheoRunmode:
    """TD-0353 — dry-run D11 và lệnh live tối thiểu D10 chạy song song không được ghi chung một đỉnh equity."""

    def test_dry_run_va_live_hai_file_khac_nhau(self, tmp_path, monkeypatch) -> None:
        dr, lv = _chien_luoc("dry_run"), _chien_luoc("live")
        monkeypatch.chdir(tmp_path)  # `bot_start()` đọc file đỉnh theo cwd — không đụng runs/ của repo
        dr.bot_start()
        lv.bot_start()
        assert dr._duong_dan_dinh_equity == duong_dan_theo_runmode("dry_run")
        assert lv._duong_dan_dinh_equity == duong_dan_theo_runmode("live")
        assert dr._duong_dan_dinh_equity != lv._duong_dan_dinh_equity

    def test_backtest_khong_co_duong_dan_dinh(self, tmp_path, monkeypatch) -> None:
        s = _chien_luoc("backtest")
        monkeypatch.chdir(tmp_path)
        s.bot_start()
        assert s._duong_dan_dinh_equity is None

    def test_duong_dan_gan_tuong_minh_duoc_giu(self, tmp_path, monkeypatch) -> None:
        s = _chien_luoc("dry_run")
        s._duong_dan_dinh_equity = tmp_path / "rieng.json"
        monkeypatch.chdir(tmp_path)
        s.bot_start()
        assert s._duong_dan_dinh_equity == tmp_path / "rieng.json"


class TestDecisionLogTachTheoRunmode:
    """TD-0390 — dry-run D11 và live D10 không ghi chung MỘT sổ Decision Log; backtest giữ nguyên đường cũ."""

    @staticmethod
    def _lenh_khop(so: str):
        trade = SimpleNamespace(id=1, nr_of_successful_entries=1)
        order = SimpleNamespace(
            order_id=f"oid-{so}", order_filled_date=datetime(2026, 9, 24, tzinfo=timezone.utc),
            ft_order_side="buy", safe_price=2.0, safe_amount_after_fee=11.0,
        )
        return trade, order

    def test_dry_run_va_live_hai_so_khac_nhau(self) -> None:
        assert duong_dan_decision_log("dry_run") != duong_dan_decision_log("live")
        assert duong_dan_decision_log("dry_run").parent == duong_dan_heartbeat("dry_run").parent

    def test_backtest_giu_duong_cu(self) -> None:
        assert duong_dan_decision_log("backtest") == DEFAULT_DECISION_LOG_PATH

    def test_chien_luoc_dry_run_ghi_vao_so_runmode(self, tmp_path, monkeypatch) -> None:
        s = _chien_luoc("dry_run")
        monkeypatch.chdir(tmp_path)  # đường sổ tương đối — không đụng runs/ hay registry/ của repo
        s._ghi_vao_lenh("TRUMP/USDT:USDT", *self._lenh_khop("1"))
        so = tmp_path / duong_dan_decision_log("dry_run")
        assert [json.loads(d)["nguon"] for d in so.read_text(encoding="utf-8").splitlines()] == ["dry_run"]
        assert not (tmp_path / DEFAULT_DECISION_LOG_PATH).exists()


class TestTelegramTichHopFreqtrade:
    """TD-0393 — Telegram tích hợp của Freqtrade bật bằng env, chỉ khi có ĐỦ cả hai biến; bí mật không vào `cfg.json`.

    Mọi giá trị dưới đây là GIẢ — không đọc `.env.telegram` thật."""

    TOKEN_GIA, CHAT_GIA = "111111111:TOKEN-GIA-CHI-DE-TEST", "222222222"

    def test_du_hai_bien_thi_bat(self) -> None:
        kq = bien_moi_truong_telegram({"TELEGRAM_BOT_TOKEN": self.TOKEN_GIA, "TELEGRAM_CHAT_ID": self.CHAT_GIA})
        assert kq == {
            "FREQTRADE__TELEGRAM__ENABLED": "true",
            "FREQTRADE__TELEGRAM__TOKEN": self.TOKEN_GIA,
            "FREQTRADE__TELEGRAM__CHAT_ID": self.CHAT_GIA,
            # TD-0405 — tin vào lệnh mặc định tắt, chiến lược tự gửi tin lúc khớp.
            "FREQTRADE__TELEGRAM__NOTIFICATION_SETTINGS__ENTRY": "off",
            "FREQTRADE__TELEGRAM__NOTIFICATION_SETTINGS__ENTRY_FILL": "off",
            "FREQTRADE__TELEGRAM__NOTIFICATION_SETTINGS__ENTRY_CANCEL": "off",
        }

    def test_freqtrade_doc_env_thanh_notification_settings(self) -> None:
        """TD-0405 — đi qua bộ gộp env THẬT của Freqtrade: khoá lồng phải ra đúng `notification_settings` mà
        `rpc/telegram.py` đọc, và `strategy_msg` (kênh tin của chiến lược) KHÔNG bị tắt."""
        from freqtrade.configuration.environment_vars import _flat_vars_to_nested_dict

        env = bien_moi_truong_telegram({"TELEGRAM_BOT_TOKEN": self.TOKEN_GIA, "TELEGRAM_CHAT_ID": self.CHAT_GIA})
        cfg = _flat_vars_to_nested_dict(env, "FREQTRADE__")
        assert cfg["telegram"]["notification_settings"] == {"entry": "off", "entry_fill": "off", "entry_cancel": "off"}

    @pytest.mark.parametrize(
        "env",
        [
            {},
            {"TELEGRAM_BOT_TOKEN": "111111111:TOKEN-GIA"},
            {"TELEGRAM_CHAT_ID": "222222222"},
            {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": "222222222"},
            {"TELEGRAM_BOT_TOKEN": "111111111:TOKEN-GIA", "TELEGRAM_CHAT_ID": ""},
        ],
        ids=["trong", "thieu-chat_id", "thieu-token", "token-rong", "chat_id-rong"],
    )
    def test_thieu_mot_trong_hai_thi_khong_bat(self, env) -> None:
        """Bật nửa chừng làm schema freqtrade 2026.8 từ chối khởi động — phải là `{}`, không phải một nửa."""
        assert bien_moi_truong_telegram(env) == {}

    def test_cfg_json_khong_chua_bi_mat(self, tmp_path) -> None:
        kq = dung_cau_hinh_dry_run(repo_dir=REPO_ROOT, thu_muc_ra=tmp_path)
        noi_dung = kq.duong_dan.read_text(encoding="utf-8")
        # Kiểm MỤC `telegram` (khoá), không kiểm chữ "telegram" trong cả file: `cfg.json` sao nguyên khoá chú thích
        # `_comment_telegram_api_server` của `config.json`, nên tìm chuỗi thô luôn thấy.
        assert "telegram" not in json.loads(noi_dung)
        assert self.TOKEN_GIA not in noi_dung and self.CHAT_GIA not in noi_dung

    def test_compose_hai_service_nap_env_file_khong_bat_buoc(self) -> None:
        sv = TestComposeCachLyLockbox._services()
        for ten in ("dryrun", "dryrun-watchdog"):
            assert sv[ten]["env_file"] == [{"path": "../.env.telegram", "required": False}], ten
        # Tên biến không còn truyền trần qua `environment` (đó là chỗ phải nhớ `--env-file`).
        moi_truong = sv["dryrun-watchdog"].get("environment") or []
        assert not any(str(d).startswith("TELEGRAM_") for d in moi_truong), moi_truong


class TestComposeCachLyLockbox:
    @staticmethod
    def _services() -> dict:
        return yaml.safe_load((REPO_ROOT / "docker/docker-compose.yml").read_text(encoding="utf-8"))["services"]

    def test_moi_service_tru_lockbox_deu_che_lockbox_data(self) -> None:
        for ten, sv in self._services().items():
            if ten == "lockbox":
                continue
            assert "/workspace/lockbox/data" in (sv.get("volumes") or []), f"service {ten} KHÔNG che lockbox/data"

    def test_service_van_hanh_sau_profile(self) -> None:
        sv = self._services()
        for ten in ("dryrun", "dryrun-watchdog"):
            assert sv[ten].get("profiles") == ["van_hanh"], ten
        assert sv["dryrun"]["entrypoint"][-1] == "tool_d.ops.dry_run"
        assert sv["dryrun-watchdog"]["entrypoint"][-2:] == ["--runmode", "dry_run"]
        for ten in ("tests", "freqtrade", "lockbox"):
            assert "profiles" not in sv[ten], f"{ten} không được rơi vào profile (sẽ biến mất khỏi run --rm)"

    def test_khong_them_file_vao_entrypoints(self) -> None:
        """`L-Z36` khoá đúng 8 file; service vận hành gọi module trong `src/`, không phải entrypoint thứ 9."""
        assert len(sorted((REPO_ROOT / "entrypoints").glob("*.py"))) == 8
