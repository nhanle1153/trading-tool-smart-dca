"""🔴 TD-0165 — `L-Z56` CRITICAL: bộ chạy ablation TỪ CHỐI khởi động khi
chưa có kết quả Δ_R của cổng D3.5 **đã commit**.

Spec `L-Z56` nguyên văn: *"Chạy bất kỳ arm ablation nào khi chưa có kết
quả Δ_R của cổng D3.5 (cả ba bước, cả hai hướng) đã commit → bộ chạy TỪ
CHỐI (DR-015 §1)."*

════ Vì sao chốt này tồn tại, và vì sao nó phải là MÁY ════

DR-015 §1 nói thẳng trạng thái mà v7 để lại là *"tệ nhất có thể"*: đo
thước SAU ablation rồi "đọc lại" kết luận. Tức kết luận Z0-vs-DCA hình
thành TRƯỚC, thước được kiểm SAU. Cổng D3.5 sinh ra để đảo thứ tự đó.

Nhưng thứ tự chỉ là kỷ luật con người cho tới khi có một máy từ chối
chạy. Module này là cái máy đó.

════ "ĐÃ COMMIT" — hai chữ mang toàn bộ sức nặng ════

Chốt này KHÔNG chỉ hỏi "file có tồn tại không". Nó đòi file **được git
theo dõi VÀ khớp đúng bản trong HEAD**. Lý do: một con số nằm trên đĩa
mà chưa commit thì vẫn sửa được sau khi nhìn thấy kết quả ablation, và
sửa xong không để lại dấu vết nào. Đúng thứ §1 tồn tại để chặn.

Đây cũng là bài học rút từ cổng D3 (08/09/2026): cổng ghi `git_sha`
nhưng không kiểm cây sạch, nên bằng chứng có thể trỏ tới một commit
không chứa thứ vừa được kiểm.

════ Và một chốt nữa mà chữ của spec không đòi ════

Ngoài "đã commit", module này **tính lại Δ_R từ dữ liệu thô đã commit và
đối chiếu** với con số trong artifact. Vì sao cần: một artifact commit từ
tháng trước vẫn "đã commit" hoàn hảo trong khi code tính Δ_R đã đổi —
lúc đó ablation chạy với một con số không còn là thứ code hiện tại sinh
ra. Lệch → TỪ CHỐI, buộc người ta commit lại artifact **một cách có ý
thức** chứ không để nó trôi.

════ "Cả hai hướng" — diễn giải, và vì sao không đọc theo chữ ════

Đọc theo chữ thì phải có Δ_R cho CẢ Long lẫn Short. Nhưng
`ZoneAbsorptionMinimal` hiện LONG-only (TD-0114) nên Δ_R(Short) là
`unreadable` — đọc theo chữ thì cổng KHÔNG BAO GIỜ mở được, và một chốt
không bao giờ thoả được sẽ bị gỡ bỏ (bài học cổng D3, 08/09/2026).

Diễn giải đã chọn: **đòi Δ_R cho mọi hướng mà ablation THỰC SỰ sẽ chạy**,
lấy từ `tier_a.enable_long` / `tier_a.enable_short` — cấu hình, không
phải lời khai của người chạy. Bật Short mà chưa có Δ_R(Short) → TỪ CHỐI.
Đây là diễn giải, không phải chữ của spec; ghi ra để cãi lại được.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from tool_d.config.loader import ToolDConfig, load_tool_d_config, resolve

# Exit code riêng — 86..97 đã có chủ (xem các entrypoint).
EXIT_CHUA_CO_DELTA_R = 98

DEFAULT_DU_LIEU_THO_PATH = Path("docs/du-lieu-do/dr015-luot-khop-tranche.json")
FILE_KET_QUA_D35: tuple[tuple[str, str], ...] = (
    ("Bước 1 (Δ_R theo hướng)", "docs/du-lieu-do/dr015-buoc1-delta-r.json"),
    ("Bước 2 (tỷ lệ không khớp)", "docs/du-lieu-do/dr015-buoc2-ty-le-khong-khop.json"),
    ("Bước 3 (đối chứng Z0)", "docs/du-lieu-do/dr015-buoc3-doi-chung-z0.json"),
)
# Δ_R tính lại được phép lệch bao nhiêu so với artifact. Chỉ để nuốt sai
# số làm tròn khi JSON đi qua text — KHÔNG phải biên cho "gần đúng".
DUNG_SAI_DELTA_R = 1e-12


class CongD35ChuaDongError(RuntimeError):
    """`L-Z56` — chưa đủ điều kiện chạy ablation. Fail-closed."""


def _da_commit(path: Path, repo_dir: Path) -> str | None:
    """`None` nếu file ĐÃ COMMIT và khớp HEAD; ngược lại trả lý do.

    Hai phép kiểm tách bạch, vì hai hỏng hóc khác nhau:
      • `git ls-files` rỗng  → file chưa từng được theo dõi;
      • `git diff HEAD` khác rỗng → có theo dõi nhưng bản trên đĩa đã bị
        sửa so với bản đã commit (tức con số đang chạy KHÁC con số niêm
        phong — chính xác là ca chốt này sinh ra để bắt).
    """
    if not (repo_dir / path).exists():
        return f"KHÔNG TỒN TẠI: {path}"
    theo_doi = subprocess.run(
        ["git", "--no-optional-locks", "ls-files", "--error-unmatch", str(path)],
        cwd=repo_dir, capture_output=True, text=True,
    )
    if theo_doi.returncode != 0:
        return f"CHƯA COMMIT (git không theo dõi): {path}"
    lech = subprocess.run(
        ["git", "--no-optional-locks", "diff", "--name-only", "HEAD", "--", str(path)],
        cwd=repo_dir, capture_output=True, text=True,
    )
    if lech.stdout.strip():
        return (
            f"ĐÃ SỬA SAU KHI COMMIT: {path} — con số đang chạy KHÁC con số niêm phong"
        )
    return None


def _huong_can_co(cfg: ToolDConfig) -> list[str]:
    """Các hướng ablation THỰC SỰ sẽ chạy, đọc từ cấu hình (N4) chứ không
    nhận lời khai của người chạy."""
    huong = []
    if resolve(cfg, "tier_a.enable_long"):
        huong.append("LONG")
    if resolve(cfg, "tier_a.enable_short"):
        huong.append("SHORT")
    if not huong:
        raise CongD35ChuaDongError(
            "Cấu hình tắt CẢ hai hướng — không có arm ablation nào để chạy."
        )
    return huong


def kiem_cong_d35(
    *,
    repo_dir: Path = Path("."),
    cfg: ToolDConfig | None = None,
    du_lieu_tho_path: Path = DEFAULT_DU_LIEU_THO_PATH,
    tinh_lai: bool = True,
) -> dict[str, Any]:
    """Raise `CongD35ChuaDongError` nếu chưa đủ điều kiện chạy ablation.

    Trả về khối Δ_R đã niêm phong khi đạt — để bên gọi dùng đúng con số
    ĐÃ COMMIT, không tự tính lại một bản khác.

    `tinh_lai=False` chỉ dành cho test dựng artifact giả; đường chạy thật
    luôn tính lại (xem docstring module).
    """
    cfg = cfg or load_tool_d_config()

    ly_do = [r for _, p in FILE_KET_QUA_D35 if (r := _da_commit(Path(p), repo_dir))]
    if ly_do:
        raise CongD35ChuaDongError(
            "🛑 L-Z56 — TỪ CHỐI chạy ablation: kết quả cổng D3.5 chưa commit đầy đủ.\n"
            + "\n".join(f"  {r}" for r in ly_do)
            + "\nDR-015 §1: đo thước SAU ablation là trạng thái tệ nhất có thể."
        )

    buoc1 = json.loads((repo_dir / FILE_KET_QUA_D35[0][1]).read_text(encoding="utf-8"))
    delta = buoc1.get("delta_r", {})

    thieu = [
        h for h in _huong_can_co(cfg)
        if delta.get(h, {}).get("trang_thai") != "ok"
    ]
    if thieu:
        raise CongD35ChuaDongError(
            f"🛑 L-Z56 — TỪ CHỐI chạy ablation: thiếu Δ_R cho hướng {thieu}. "
            "Cấu hình bật hướng đó nhưng cổng D3.5 chưa đo được — bật Short thì phải "
            "có Δ_R(Short), không dùng Δ_R(Long) thay thế."
        )

    if tinh_lai:
        from tool_d.dr015.buoc1_lech_tranche import tinh_buoc1

        tho = json.loads((repo_dir / du_lieu_tho_path).read_text(encoding="utf-8"))
        moi = tinh_buoc1(tho)
        for h, v in delta.items():
            if v.get("trang_thai") != "ok" or h not in moi or not moi[h].delta_r.is_ok():
                continue
            if abs(moi[h].delta_r.value - v["gia_tri"]) > DUNG_SAI_DELTA_R:
                raise CongD35ChuaDongError(
                    f"🛑 L-Z56 — TỪ CHỐI chạy ablation: Δ_R({h}) niêm phong = "
                    f"{v['gia_tri']} nhưng tính lại từ dữ liệu thô đã commit ra "
                    f"{moi[h].delta_r.value}. Artifact đã TRÔI khỏi code — commit lại "
                    "một cách CÓ Ý THỨC trước khi chạy, đừng để nó tự khớp."
                )

    return delta
