"""TD-0439 — lệnh ghi nạp/rút cho người vận hành, vào sổ đỉnh của Risk Supervisor (chủ đỉnh DUY NHẤT).

Hồi quy đầu-cuối: ghi bằng lệnh ⇒ Supervisor đọc cùng sổ ⇒ rút vốn không thành sụt vốn (`dd_tu_account`).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tool_d.equity_peak import NAP_RUT, DinhEquityError, doc_so_su_kien
from tool_d.ops.ghi_nap_rut import EXIT_GHI_NAP_RUT_TU_CHOI, NHAC_QUY_UOC, ghi, main
from tool_d.ops.risk_supervisor_daemon import dd_tu_account, duong_dan_dinh_supervisor

T0 = datetime(2026, 9, 27, 0, 0, 0, tzinfo=timezone.utc)


def _state(tmp_path: Path, runmode: str = "live") -> Path:
    return tmp_path / runmode / "state.json"


class TestGhi:
    def test_ghi_dung_so_cua_supervisor(self, tmp_path) -> None:
        so = ghi("live", so_tien=-100.0, ghi_chu="rút về ví chính", now=T0, state_path=_state(tmp_path))
        assert so == tmp_path / "live" / "equity_peak_events.jsonl"
        (_, sk), = doc_so_su_kien(so)
        assert (sk.loai, sk.so_tien, sk.stake_currency, sk.ghi_chu) == (NAP_RUT, -100.0, "USDT", "rút về ví chính")

    @pytest.mark.parametrize("so_tien", [0.0, float("nan"), float("inf")])
    def test_so_tien_rac_thi_tu_choi_khong_ghi(self, tmp_path, so_tien) -> None:
        with pytest.raises(DinhEquityError):
            ghi("live", so_tien=so_tien, ghi_chu="x", now=T0, state_path=_state(tmp_path))
        assert not (tmp_path / "live").exists()

    def test_ghi_chu_rong_thi_tu_choi(self, tmp_path) -> None:
        with pytest.raises(DinhEquityError):
            ghi("live", so_tien=5.0, ghi_chu="  ", now=T0, state_path=_state(tmp_path))

    def test_runmode_la_thi_tu_choi(self, tmp_path) -> None:
        with pytest.raises(DinhEquityError):
            ghi("backtest", so_tien=5.0, ghi_chu="x", now=T0, state_path=_state(tmp_path))

    def test_dau_cuoi_rut_co_ghi_so_thi_supervisor_khong_doc_thanh_sut(self, tmp_path) -> None:
        dinh = duong_dan_dinh_supervisor(_state(tmp_path))
        dd_tu_account({"totalMarginBalance": "1100"}, duong_dan_dinh=dinh)
        ghi("live", so_tien=-100.0, ghi_chu="rút", now=T0, state_path=_state(tmp_path))
        assert dd_tu_account({"totalMarginBalance": "1000"}, duong_dan_dinh=dinh) == pytest.approx(0.0)


class TestMain:
    def test_thanh_cong_in_quy_uoc(self, tmp_path, capsys) -> None:
        rc = main(["--runmode", "dry_run", "--so-tien", "250", "--ghi-chu", "nạp thử", "--state-path",
                   str(_state(tmp_path, "dry_run"))])
        err = capsys.readouterr().err
        assert rc == 0 and NHAC_QUY_UOC in err and "NẠP" in err

    def test_tu_choi_tra_ma_rieng(self, tmp_path, capsys) -> None:
        rc = main(["--runmode", "live", "--so-tien", "0", "--ghi-chu", "x", "--state-path", str(_state(tmp_path))])
        assert rc == EXIT_GHI_NAP_RUT_TU_CHOI and "TỪ CHỐI" in capsys.readouterr().err

    def test_thieu_ghi_chu_thi_argparse_tu_choi(self) -> None:
        with pytest.raises(SystemExit):
            main(["--runmode", "live", "--so-tien", "5"])

    def test_dong_ghi_la_json_mot_dong_LF(self, tmp_path) -> None:
        so = ghi("live", so_tien=10.0, ghi_chu="x", now=T0, state_path=_state(tmp_path))
        b = so.read_bytes()
        assert b.endswith(b"\n") and b"\r\n" not in b and json.loads(b.decode("utf-8"))["loai"] == NAP_RUT
