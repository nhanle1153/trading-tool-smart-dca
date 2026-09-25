"""TD-0384 (`DR-D10-02` §5.3) — đặt chỗ MỘT dòng CTRL *đo vận hành* cho cả đợt D10, trước lần bật đầu tiên.

Người vận hành gọi qua E6 `--d10-dat-cho`; bot D10 KHÔNG bao giờ đụng sổ trial (lý do ở `DR-D10-02` §5.3: bot tiền thật
tự ghi vào file có trong git, nơi các phiên khác cùng ghi và commit). Bộ đo ba ngưỡng (`TD-0385`) ghi kết cục khi đợt
kết thúc. Cửa ghi `TrialLedger.reserve()` là máy kiểm (dạng thứ tư, `CTRL_VAN_HANH_ALLOWED`, tối đa một dòng D10 mở);
module này chỉ dựng đúng lời khai.

Khuôn giống `dr015.buoc1_lech_tranche.ghi_dong_ctrl`: khối xuất xứ đầy đủ (kể cả digest ảnh — chạy ngoài ảnh project thì
RAISE, N7), `config_hash` thật để cửa ghi tự tính vân tay lần chạy.
"""

from __future__ import annotations

from pathlib import Path

from tool_d.config.loader import DEFAULT_CONFIG_PATH, load_tool_d_config, resolve
from tool_d.ledger.registry import (
    CTRL_BUDGET_LINE,
    CTRL_VAN_HANH_ALLOWED,
    DATASET_D10,
    HYPOTHESIS_SLOT_D10,
    TrialLedger,
)
from tool_d.measurement.provenance import build_provenance, doc_runtime_image_digest
from tool_d.ops.live_d10 import RO_D10, doc_ro_d10, kiem_ro_da_commit

THAM_SO_D10 = "d10_ha_tang"


def dat_cho_dong_d10(
    *,
    ledger: TrialLedger,
    config_path: Path = DEFAULT_CONFIG_PATH,
    repo_dir: Path = Path("."),
) -> str:
    """Ghi `RESERVE budget_line=CTRL` dạng *đo vận hành* cho đợt D10. Trả `trial_id`.

    Rổ phải đã commit và nguyên vẹn (cùng chốt với lúc bật bot) — đặt chỗ cho một rổ chưa chốt là khai một đợt đo mà
    chính nó còn có thể đổi. `param_value` mang rổ + tham số CTRL, nên hai đợt khác rổ/khác tham số không trùng vân tay."""
    kiem_ro_da_commit(RO_D10, repo_dir=repo_dir)
    ro = doc_ro_d10(repo_dir / RO_D10)
    cfg = load_tool_d_config(repo_dir / config_path)
    tham_so = dict(resolve(cfg, "tier_c.ctrl_d10"))
    provenance = build_provenance(
        params_source="yaml",
        params_effective=tham_so,
        repo_dir=repo_dir,
        data_files={"d10_ro": repo_dir / RO_D10},
        cache_mode="none",
        guard_passed=True,
        runtime_image_digest=doc_runtime_image_digest(repo_dir),
    )
    return ledger.reserve(
        n_dang_ky=0,  # CTRL không kiểm ngân sách (MT-08)
        budget_line=CTRL_BUDGET_LINE,
        hypothesis_slot=HYPOTHESIS_SLOT_D10,
        direction="LONG",
        dataset=DATASET_D10,
        param_under_test=THAM_SO_D10,
        param_value={"ro": list(ro), "ctrl_d10": tham_so},
        params_frozen_hash=cfg.sha256,
        config_hash=cfg.sha256,
        code_commit=provenance.git_sha,
        provenance=provenance.to_dict(),
        contribution=1,
        ctrl_van_hanh_whitelist=sorted(CTRL_VAN_HANH_ALLOWED),
    )
