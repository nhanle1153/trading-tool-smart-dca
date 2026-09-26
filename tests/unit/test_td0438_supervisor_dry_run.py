"""TD-0438 (`DR-TANG-CHAN-01` §4 điều 6, parity N11) — Risk Supervisor cho dry-run.

Không có nó thì lần ĐẦU HALT thật được thi hành rơi vào lúc có tiền (D12). Và từ `TD-0435`, bot dry-run KHÔNG mở lệnh nếu
không có Supervisor sống ⇒ việc này là điều kiện để dry-run chạy lại.

Nguồn equity (`TD-0433`): `/balance.starting_capital` + `/profit.profit_all_coin` — KHÔNG `/balance.total` (rơi lặng lẽ
lãi/lỗ khi lấy giá lỗi). `profit_all_coin` thành NaN khi lấy giá lỗi ⇒ `None` (N6), không bịa.
"""

from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from tool_d.api_client.freqtrade_control import FreqtradeAuthError, FreqtradeControlError, doc_json_get
from tool_d.ops.dry_run import CAU_HINH_API_SERVER, CauHinhDryRun, lenh_freqtrade
from tool_d.ops.risk_supervisor_daemon import (
    _boc_loi_freqtrade,
    chay_mot_vong_giam_sat,
    dd_tu_account,
    duong_dan_dinh_supervisor,
    duong_dan_theo_runmode,
    equity_dry_run,
)
from tool_d.risk_supervisor import HALT, RiskSupervisorError, TrangThaiBenVung, TrangThaiBreaker

REPO_ROOT = Path(__file__).resolve().parents[2]
T0 = datetime(2026, 9, 27, 0, 0, 0, tzinfo=timezone.utc)


class TestEquityDryRun:
    def test_von_cong_lai_lo_gom_chua_chot(self) -> None:
        assert equity_dry_run({"starting_capital": 1000}, {"profit_all_coin": -42.5}) == 957.5

    @pytest.mark.parametrize(
        "balance,profit",
        [({"starting_capital": 1000}, {"profit_all_coin": float("nan")}),  # có vị thế lấy giá lỗi
         ({"starting_capital": 1000}, {"profit_all_coin": None}),  # NaN có thể ra JSON là null
         ({}, {"profit_all_coin": 1.0}), ({"starting_capital": 1000}, {}),
         ({"starting_capital": True}, {"profit_all_coin": 1.0}), (None, None)],
    )
    def test_khong_doc_duoc_thi_None_khong_bia(self, balance, profit) -> None:
        assert equity_dry_run(balance, profit) is None

    def test_di_qua_duong_do_sut_von_that(self, tmp_path) -> None:
        """Account dựng từ ví giấy ⇒ `dd_tu_account` dùng lại NGUYÊN (đỉnh bền vững + sổ sự kiện)."""
        dinh = duong_dan_dinh_supervisor(tmp_path / "dry_run" / "state.json")
        eq = equity_dry_run({"starting_capital": 1000}, {"profit_all_coin": 100.0})
        assert dd_tu_account({"totalMarginBalance": eq}, duong_dan_dinh=dinh) == 0.0
        eq = equity_dry_run({"starting_capital": 1000}, {"profit_all_coin": 0.0})
        assert dd_tu_account({"totalMarginBalance": eq}, duong_dan_dinh=dinh) == pytest.approx(100 / 1100 * 100)


class TestBocLoi:
    def test_loi_mang_thanh_chua_doc_duoc(self) -> None:
        def loi():
            raise FreqtradeControlError("x")

        with pytest.raises(RiskSupervisorError):
            _boc_loi_freqtrade(loi)()

    def test_401_KHONG_boc_de_lo_ra(self) -> None:
        def loi():
            raise FreqtradeAuthError("sai mật khẩu")

        with pytest.raises(FreqtradeAuthError):
            _boc_loi_freqtrade(loi)()


class TestVongDryRun:
    def test_vi_giay_sut_qua_8_thi_HALT_goi_stopentry(self, tmp_path) -> None:
        dinh = duong_dan_dinh_supervisor(tmp_path / "state.json")
        profit = {"profit_all_coin": 0.0}
        goi: list[str] = []

        def vong(tt):
            return chay_mot_vong_giam_sat(
                tt, now=T0,
                doc_account_fn=_boc_loi_freqtrade(lambda: {"totalMarginBalance": equity_dry_run(
                    {"starting_capital": 1000}, profit)}),
                doc_position_fn=lambda: [], doc_force_orders_fn=lambda: [], doc_breaker_hien_tai_fn=TrangThaiBreaker,
                tu_thoi_diem_ms=0, dung_bot_fn=lambda: goi.append("stop"),
                tinh_dd_fn=lambda acc: dd_tu_account(acc, duong_dan_dinh=dinh),
                tam_ngung_fn=lambda: goi.append("stopentry"), ghi_abort_fn=lambda: None, luu_truoc_fn=lambda _t: None,
            )

        tt, _ = vong(TrangThaiBenVung(breaker=TrangThaiBreaker()))
        profit["profit_all_coin"] = -90.0
        tt, dung = vong(tt)
        assert (tt.muc_tang_chan, dung, goi) == (HALT, False, ["stopentry"])
        assert tt.dd_pct_cuoi == pytest.approx(9.0)


def _resp(payload) -> MagicMock:
    r = MagicMock()
    r.read.return_value = json.dumps(payload).encode("utf-8")
    r.__enter__.return_value = r
    return r


class TestDocJsonGet:
    @pytest.mark.parametrize("path", ["/api/v1/balance", "/api/v1/profit"])
    def test_GET_hai_duong_da_khai(self, path) -> None:
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as m:
            m.return_value = _resp({"ok": 1})
            assert doc_json_get("http://127.0.0.1:8081", path, username="u", password="p") == {"ok": 1}
        req = m.call_args[0][0]
        assert req.full_url.endswith(path) and req.get_method() == "GET"

    def test_duong_chua_khai_thi_tu_choi_khong_goi_mang(self) -> None:
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as m:
            with pytest.raises(ValueError, match="chưa khai"):
                doc_json_get("http://127.0.0.1:8081", "/api/v1/forceexit", username="u", password="p")
        m.assert_not_called()

    def test_khong_phai_object_thi_raise(self) -> None:
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as m:
            m.return_value = _resp([1, 2])
            with pytest.raises(FreqtradeControlError):
                doc_json_get("http://127.0.0.1:8081", "/api/v1/profit", username="u", password="p")


class TestMainNhanhDryRun:
    @staticmethod
    def _main() -> ast.FunctionDef:
        cay = ast.parse((REPO_ROOT / "src/tool_d/ops/risk_supervisor_daemon.py").read_text(encoding="utf-8"))
        return next(n for n in cay.body if isinstance(n, ast.FunctionDef) and n.name == "main")

    def test_kiem_key_Binance_chi_o_nhanh_live(self) -> None:
        """Dry-run là ví giấy — đòi key Binance ở đây là bắt người vận hành cấp key thật cho một bot không tiền."""
        main = self._main()  # MỘT cây — so danh tính nút giữa hai lần parse luôn sai
        goi = [n for n in ast.walk(main) if isinstance(n, ast.Call)
               and getattr(n.func, "id", "") == "validate_credentials_for_live"]
        assert len(goi) == 1
        nhanh = [n for n in ast.walk(main) if isinstance(n, ast.If) and ast.unparse(n.test) == "not la_dry_run"]
        assert nhanh and any(goi[0] in ast.walk(n) for n in nhanh)

    def test_dry_run_doc_dung_hai_duong_va_equity_dry_run(self) -> None:
        nguon = ast.unparse(self._main())
        assert "equity_dry_run(" in nguon and "'/api/v1/balance'" in nguon and "'/api/v1/profit'" in nguon

    def test_duong_trang_thai_moi_runmode_mot_thu_muc(self) -> None:
        assert duong_dan_theo_runmode("dry_run") == Path("runs/risk_supervisor/dry_run/state.json")
        assert duong_dan_theo_runmode("live") == Path("runs/risk_supervisor/live/state.json")


class TestBoKhoiDongVaCompose:
    def test_bot_dry_run_bat_control_api_chi_localhost(self) -> None:
        lenh = lenh_freqtrade(CauHinhDryRun(duong_dan=Path("runs/van_hanh/dry_run/cfg.json"), so_cap=1))
        assert [lenh[i + 1] for i, x in enumerate(lenh) if x == "--config"] == [
            str(Path("runs/van_hanh/dry_run/cfg.json")), str(CAU_HINH_API_SERVER)]
        api = json.loads((REPO_ROOT / CAU_HINH_API_SERVER).read_text(encoding="utf-8"))["api_server"]
        assert api["listen_ip_address"] == "127.0.0.1"

    def test_service_supervisor_dry_run(self) -> None:
        sv = yaml.safe_load((REPO_ROOT / "docker/docker-compose.yml").read_text(encoding="utf-8"))["services"]
        s = sv["risk-supervisor-dryrun"]
        assert s["profiles"] == ["van_hanh"] and s["network_mode"] == "service:dryrun"
        assert s["entrypoint"][s["entrypoint"].index("--runmode") + 1] == "dry_run"
        assert s["env_file"] == [{"path": "../.env.dryrun", "required": True}]
        assert s["restart"] == "unless-stopped"
        assert "/workspace/lockbox/data" in s["volumes"]
