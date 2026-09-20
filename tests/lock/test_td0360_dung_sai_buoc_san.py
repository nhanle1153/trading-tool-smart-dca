"""🔒 TD-0360 (`DR-D4-20` §8) — dung sai tỉ trọng tranche theo BƯỚC HỢP ĐỒNG + cổng D4 đếm suất `B2` THEO LÔ.

Hai chốt của cổng D4 phải đổi sau khi lô `DR-D4-20` chạy thật, và cả hai đổi vì **số đo**, không vì tiện:

1. **Dung sai `DR-D4-04` §7 (ii).** `TD-0359` (EXPLORE, 0 trial) đo: 5/16 lệnh đủ ba tranche vượt 1%, lệch lớn
   nhất 5,91%; cơ chế là bước hợp đồng của sàn nuốt phần chênh ở cỡ lệnh 12–30 USDT (`MTL`/`ETH`: ba tranche
   CÙNG một số lượng hợp đồng). Chốt mới: `max(1%, một bước tại giá đó)`.
   🔴 Phần lệch THẬT của cỡ lệnh vẫn phải bị bắt — ca `test_lech_that_van_bi_bat` giữ đúng điều đó.
2. **Kế toán cổng.** Sổ mang `D-0015` (suất chết của lô `DR-D4-19`, hệ thống CHƯA vá) nên phép đếm gộp mọi `B2`
   CONSUMED báo lệch 5 ≠ 4 **mãi mãi**. Cổng nay đếm suất của ĐÚNG lô đang chấm, suy từ chính bản ghi arm.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tool_d.ablation.chi_so_export import DUNG_SAI_TI_TRONG, ti_trong_tranche

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))
import trial_ledger_audit as e6  # noqa: E402


def _lenh(pair: str, amounts: list[float], gia: list[float]) -> dict:
    return {
        "pair": pair,
        "orders": [
            {"ft_is_entry": True, "order_filled_timestamp": 1000 + i, "amount": a, "safe_price": g}
            for i, (a, g) in enumerate(zip(amounts, gia))
        ],
    }


class TestDungSaiTheoBuocSan:
    #: Ca THẬT rút từ `td0359-ti-trong-tranche-explore.json`: `MTL`, ba tranche cùng 11 hợp đồng (bước 1),
    #: giá giảm dần ⇒ `cost_3/cost_1 = 0,9757` (lệch 2,43% > 1%) hoàn toàn do làm tròn.
    MTL = _lenh("MTL/USDT:USDT", [11.0, 11.0, 11.0], [1.148, 1.1376, 1.12])

    def test_lech_do_lam_tron_KHONG_bi_coi_la_sai(self) -> None:
        assert ti_trong_tranche([self.MTL], buoc_amount=lambda p: 1.0).value is True

    def test_khong_biet_buoc_thi_giu_nguyen_1_phan_tram(self) -> None:
        """Fail-closed theo hướng CHẶT: không có thông tin bước ⇒ dung sai gốc."""
        assert ti_trong_tranche([self.MTL]).value is False
        assert ti_trong_tranche([self.MTL], buoc_amount=lambda p: None).value is False

    def test_lech_that_van_bi_bat(self) -> None:
        """Cỡ lệnh tranche 3 nhỏ đi 20% — lớn hơn NHIỀU so với một bước ⇒ vẫn phải báo sai."""
        sai = _lenh("MTL/USDT:USDT", [11.0, 11.0, 8.8], [1.148, 1.1376, 1.12])
        assert ti_trong_tranche([sai], buoc_amount=lambda p: 1.0).value is False

    def test_buoc_min_thi_dung_sai_ve_1_phan_tram(self) -> None:
        """Bước rất mịn (ETH 0,001 ở giá lớn vẫn có thể thô; ở đây lấy bước bé) ⇒ không nới gì thêm."""
        sai = _lenh("X/USDT:USDT", [100.0, 100.0, 97.0], [10.0, 10.0, 10.0])
        assert ti_trong_tranche([sai], buoc_amount=lambda p: 1e-9).value is False

    def test_khong_co_lenh_du_ba_tranche_van_la_unreadable(self) -> None:
        mot = _lenh("X/USDT:USDT", [1.0], [10.0])
        assert ti_trong_tranche([mot], buoc_amount=lambda p: 1.0).status.value == "unreadable"

    def test_dung_sai_goc_khong_bi_noi_lang(self) -> None:
        assert DUNG_SAI_TI_TRONG == 0.01


class TestCongDemTheoLo:
    @staticmethod
    def _so(tmp_path: Path, dong: list[tuple[str, str, str]]) -> Path:
        """Sổ tối thiểu: mỗi phần tử `(trial_id, slot, trạng thái cuối)`."""
        import json

        duong = tmp_path / "trial_registry.jsonl"
        ban_ghi = []
        for tid, slot, trang_thai in dong:
            ban_ghi.append(
                {
                    "event": "RESERVE", "trial_id": tid, "budget_line": "B2", "hypothesis_slot": slot,
                    "direction": "LONG", "dataset": "WFO", "param_under_test": "tier_c.arm_ablation.arm",
                    "param_value": "Z0", "params_frozen_hash": "a" * 64, "config_hash": "b" * 64,
                    "code_commit": "c" * 40, "reserved_at": "2026-09-20T00:00:00.000000Z",
                    "n_dang_ky": 114, "contribution": 1,
                    "provenance": {
                        "params_source": "yaml", "params_effective": {}, "git_sha": "c" * 40,
                        "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none",
                        "guard_passed": True,
                    },
                }
            )
            if trang_thai == "CONSUMED":
                ban_ghi.append(
                    {"event": "SEAL", "trial_id": tid, "sealed_at": "2026-09-20T00:00:01.000000Z",
                     "seal_path": f"runs/{tid}/metrics.seal"}
                )
                ban_ghi.append(
                    {"event": "CONSUME", "trial_id": tid, "consumed_at": "2026-09-20T00:00:02.000000Z",
                     "outcome": {"expectancy": None, "sharpe": None, "n_trades": 1,
                                 "max_single_loss_ratio": None},
                     "verdict": "INCONCLUSIVE", "rejection_reason": None}
                )
        duong.write_text("\n".join(json.dumps(b, ensure_ascii=False) for b in ban_ghi) + "\n", encoding="utf-8")
        return duong

    def test_dem_dung_lo_dang_cham_bo_qua_lo_cu(self, tmp_path) -> None:
        """Đúng ca thật: `D-0015` thuộc lô cũ và KHÔNG có bản ghi arm ⇒ không được tính vào lô này."""
        so = self._so(
            tmp_path,
            [("D-0015", "DR-D4-19", "CONSUMED")] + [(f"D-00{19 + i}", "DR-D4-20", "CONSUMED") for i in range(4)],
        )
        ban_ghi = [{"trial_id": f"D-00{19 + i}"} for i in range(4)]
        slot = e6._slot_cua_lo(ban_ghi, so)
        assert slot == "DR-D4-20"
        assert e6._dem_b2_da_tieu(so, slot=slot) == 4
        assert e6._dem_b2_da_tieu(so) == 5  # gộp mọi lô — con số cũ, giữ được để so

    def test_nhieu_lo_lan_lon_thi_khong_suy_duoc_slot(self, tmp_path) -> None:
        """Bản ghi arm trỏ hai lô khác nhau ⇒ `None` ⇒ quay về đếm gộp ⇒ phép so vẫn LỆCH ⇒ cổng từ chối."""
        so = self._so(tmp_path, [("D-0015", "DR-D4-19", "CONSUMED"), ("D-0019", "DR-D4-20", "CONSUMED")])
        assert e6._slot_cua_lo([{"trial_id": "D-0015"}, {"trial_id": "D-0019"}], so) is None

    def test_ban_ghi_tro_trial_khong_co_trong_so(self, tmp_path) -> None:
        so = self._so(tmp_path, [("D-0019", "DR-D4-20", "CONSUMED")])
        assert e6._slot_cua_lo([{"trial_id": "D-9999"}], so) is None
