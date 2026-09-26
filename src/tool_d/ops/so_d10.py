"""TD-0384 (`DR-D10-02` §5.3) — đặt chỗ MỘT dòng CTRL *đo vận hành* cho cả đợt D10, trước lần bật đầu tiên.

Người vận hành gọi qua E6 `--d10-dat-cho`; bot D10 KHÔNG bao giờ đụng sổ trial (lý do ở `DR-D10-02` §5.3: bot tiền thật
tự ghi vào file có trong git, nơi các phiên khác cùng ghi và commit). Bộ đo ba ngưỡng (`TD-0385`) ghi kết cục khi đợt
kết thúc. Cửa ghi `TrialLedger.reserve()` là máy kiểm (dạng thứ tư, `CTRL_VAN_HANH_ALLOWED`, tối đa một dòng D10 mở);
module này chỉ dựng đúng lời khai.

Khuôn giống `dr015.buoc1_lech_tranche.ghi_dong_ctrl`: khối xuất xứ đầy đủ (kể cả digest ảnh — chạy ngoài ảnh project thì
RAISE, N7), `config_hash` thật để cửa ghi tự tính vân tay lần chạy.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from tool_d.config.loader import DEFAULT_CONFIG_PATH, load_tool_d_config, resolve
from tool_d.ledger.con_dau import ConDauError, duong_con_dau, duong_khai_so
from tool_d.ledger.registry import (
    CTRL_BUDGET_LINE,
    CTRL_VAN_HANH_ALLOWED,
    DATASET_D10,
    HYPOTHESIS_SLOT_D10,
    TrialLedger,
)
from tool_d.measurement.provenance import build_provenance, doc_runtime_image_digest
from tool_d.ops.live_d10 import RO_D10, TEN_CHIEN_LUOC, doc_ro_d10, kiem_ro_da_commit

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
        param_value={"ro": list(ro), "chien_luoc": TEN_CHIEN_LUOC, "ctrl_d10": tham_so},  # §6: RoFundingD10
        params_frozen_hash=cfg.sha256,
        config_hash=cfg.sha256,
        code_commit=provenance.git_sha,
        provenance=provenance.to_dict(),
        contribution=1,
        ctrl_van_hanh_whitelist=sorted(CTRL_VAN_HANH_ALLOWED),
    )


THU_MUC_HIEN_VAT = Path("docs/du-lieu-do")


def dong_d10_dang_mo(ledger: TrialLedger) -> str:
    """`trial_id` của dòng D10 đang mở — đúng MỘT (cửa ghi đã chặn dòng thứ hai). Không có ⇒ RAISE: đo mà không có
    dòng đặt chỗ trước là đo không khai (DR-D10-02 §5.3)."""
    mo = sorted(
        p.trial_id
        for p in ledger.projections().values()
        if p.budget_line == CTRL_BUDGET_LINE
        and p.hypothesis_slot == HYPOTHESIS_SLOT_D10
        and not p.outcome_written
        and not p.refunded
    )
    if len(mo) != 1:
        raise ValueError(f"cần đúng một dòng D10 đang mở, thấy {mo} — đặt chỗ bằng E6 --d10-dat-cho trước khi bật D10")
    return mo[0]


def ghi_ket_cuc_d10_dca(
    *,
    ledger: TrialLedger,
    db_url: str,
    decision_log: Path,
    repo_dir: Path = Path("."),
) -> tuple[str, Path, dict]:
    """TD-0385 — đo ba ngưỡng (`ops/do_d10_dca.py`), rồi ghi con dấu `runs/<trial>/metrics.seal` → SEAL → ghi hiện vật
    `docs/du-lieu-do/d10-ket-qua-<trial>.json` → CONSUME dòng D10 đang mở.

    TỪ CHỐI (sổ không đổi) khi đợt chưa kết thúc: còn lệnh vào đang mở, hoặc DB chưa có lệnh nào — CONSUME chỉ ghi
    được một lần, ghi giữa đợt là khoá kết cục trên nửa mẫu. Trả `(trial_id, đường hiện vật, dict kết quả)`."""
    from tool_d.ops.do_d10_dca import (
        DoD10DcaError,
        do_d10_dca,
        ket_cuc_so_trial,
    )

    trial_id = dong_d10_dang_mo(ledger)
    kq = do_d10_dca(db_url=db_url, decision_log=decision_log)
    if kq.post_only.dang_mo:
        raise DoD10DcaError(f"đợt D10 chưa kết thúc: {len(kq.post_only.dang_mo)} lệnh vào còn mở — chưa ghi kết cục")
    if kq.post_only.so_lenh_vao_ket_thuc == 0:
        raise DoD10DcaError("DB live chưa có lệnh vào nào kết thúc — chưa có gì để ghi kết cục (pending)")

    duong = THU_MUC_HIEN_VAT / f"d10-ket-qua-{trial_id}.json"
    cfg = load_tool_d_config(repo_dir / DEFAULT_CONFIG_PATH)
    provenance = build_provenance(
        params_source="yaml",
        params_effective={"ctrl_d10": dict(resolve(cfg, "tier_c.ctrl_d10"))},
        repo_dir=repo_dir,
        data_files={
            "db_live": Path(db_url.removeprefix("sqlite:///")),
            **({"decision_log_live": decision_log} if decision_log.exists() else {}),
        },
        cache_mode="none",
        guard_passed=True,
        runtime_image_digest=doc_runtime_image_digest(repo_dir),
    )
    hien_vat = {"trial_id": trial_id, "db_url": db_url, **kq.ra_dict(), "provenance": provenance.to_dict()}
    van_ban = json.dumps(hien_vat, ensure_ascii=False, indent=2) + "\n"

    # Khuôn `ledger/con_dau.py` (TD-0357): hiện vật con dấu ghi TRƯỚC `seal()`, một lần, nguyên tử — sổ không được khai
    # một đường chưa tồn tại (schema đòi `runs/<trial>/metrics.seal`). Rồi mới SEAL, rồi mới ghi bản đọc được ở docs/.
    con_dau = duong_con_dau(repo_dir / "runs", trial_id)
    if con_dau.exists():
        raise ConDauError(f"{con_dau} đã tồn tại — con dấu là hiện vật MỘT LẦN, không ghi đè")
    con_dau.parent.mkdir(parents=True, exist_ok=True)
    tam = con_dau.with_name(con_dau.name + ".dang-ghi")
    tam.write_text(van_ban, encoding="utf-8", newline="\n")
    os.replace(tam, con_dau)
    ledger.seal(trial_id, seal_path=duong_khai_so(trial_id))  # DR-014 §3
    (repo_dir / duong).write_text(van_ban, encoding="utf-8", newline="\n")
    ledger.consume(
        trial_id,
        outcome=ket_cuc_so_trial(kq),
        verdict=kq.verdict,
        rejection_reason="; ".join(kq.ly_do) if kq.verdict == "REJECTED" else None,
    )
    return trial_id, duong, hien_vat
