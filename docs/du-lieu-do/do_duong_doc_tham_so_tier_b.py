"""TD-0195 — ĐO: mỗi tham số `tier_b` có ĐƯỜNG ĐỌC từ `tool_d_config.yaml`
vào đường chạy sản xuất không, hay đang bị một HẰNG SỐ CỨNG thay thế?

🔴 Câu hỏi này KHÁC câu hỏi của `L-Z15`/TD-0190. L-Z15 soi
`config/param_status.yaml` — *"tham số đã khai TUNED/FROZEN chưa"*. Nó
KHÔNG hỏi *"giá trị trong YAML có chảy tới nơi tính toán không"*. Một
tham số khai đầy đủ, có mặt trong kiểm kê DOF, tính vào N = 114 — mà
đường chạy vẫn đọc một hằng số cứng trong `.py` — thì mọi phép kiểm hiện
có đều XANH, vì hai con số đang BẰNG NHAU.

Đây là đo MÔ TẢ trên MÃ NGUỒN: không mở một nến dữ liệu nào, không đánh
giá cấu hình nào trên CALIB/WFO/LOCKBOX ⇒ không phải "chạm" theo DR-014
§2, **0 trial**. Chạy được ở bất kỳ đâu, không cần Freqtrade.

Cách đo, hai phần tách bạch để cãi lại được:

  PHẦN 1 (TỰ ĐỘNG, không khai gì trước) — với mỗi khoá `tier_b`, quét AST
  mọi `.py` trong `src/`, `user_data/strategies/`, `entrypoints/` tìm
  chuỗi literal `"tier_b.<khoá>"` ở vị trí GIÁ TRỊ THẬT (đối số lời gọi,
  phần tử dict/list) — KHÔNG tính docstring. Đó là cách duy nhất
  `loader.resolve()` nhận đường dẫn, nên "không có literal nào" ⇒ "không
  có đường đọc nào".

  PHẦN 2 (KHAI TAY rồi XÁC MINH) — bảng `NGHI_BAN_SAO` là kết quả đọc mã
  bằng mắt, ghi ra để máy kiểm lại chứ không phải để tin: script tự đối
  chiếu giá trị hằng số với giá trị YAML và tự tìm các hàm dùng hằng đó.
  Nếu ai sửa mã cho khớp mà quên bảng này, cột "giá trị hằng" sẽ lệch
  hoặc hằng số biến mất — đều thấy được.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
THU_MUC_DUONG_CHAY = ("src", "user_data/strategies", "entrypoints")

# PHẦN 2 — khai tay, script xác minh lại (xem docstring).
NGHI_BAN_SAO: dict[str, tuple[str, str]] = {
    "zss_threshold": ("src/tool_d/zone_strength.py", "NGUONG_ZSS"),
    "buf_sl_atr": ("src/tool_d/trade_plan.py", "BUF_SL_HE_SO"),
    "dg6a_atr_ratio": ("src/tool_d/dg6_early_invalidation.py", "NGUONG_ATR_RATIO_A"),
    "dg6d_retrace_frac": ("src/tool_d/dg6_early_invalidation.py", "NGUONG_HOI_GIA_D"),
    "funding_rate_pct": ("src/tool_d/dg6_early_invalidation.py", "NGUONG_FUNDING_D"),
}


def khoa_tier_b() -> dict[str, str]:
    """Đọc khối `tier_b` bằng regex — cố ý KHÔNG dùng `loader.py`.

    `loader.py` nằm trong chính thứ đang được kiểm; đo bằng nó thì hai vế
    cùng một nguồn và phép đo không thể báo đỏ (đúng lỗi `L-Z55` ở
    `folds`, 08/09).
    """
    txt = (ROOT / "config" / "tool_d_config.yaml").read_text(encoding="utf-8")
    m = re.search(r"^tier_b:.*?$(.*?)(?=^\S)", txt, re.S | re.M)
    if m is None:
        raise SystemExit("không tìm thấy khối tier_b trong tool_d_config.yaml")
    ra: dict[str, str] = {}
    for line in m.group(1).splitlines():
        k = re.match(r"^  ([a-zA-Z][a-zA-Z0-9_]*):\s*(.+?)\s*(?:#.*)?$", line)
        if k:
            ra[k.group(1)] = k.group(2).strip()
    return ra


def cac_file_duong_chay() -> list[pathlib.Path]:
    ra: list[pathlib.Path] = []
    for d in THU_MUC_DUONG_CHAY:
        ra.extend(sorted((ROOT / d).rglob("*.py")))
    return [f for f in ra if "__pycache__" not in f.parts]


def duong_doc(khoa: str, files: list[pathlib.Path]) -> list[str]:
    """Mọi literal `tier_b.<khoa>` ở vị trí GIÁ TRỊ (bỏ docstring)."""
    can = f"tier_b.{khoa}"
    ra: list[str] = []
    for f in files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        than_docstring = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                    than_docstring.add(id(node.body[0].value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value == can:
                if id(node) in than_docstring:
                    continue
                ra.append(f"{f.relative_to(ROOT).as_posix()}:{node.lineno}")
    return ra


def hang_so_module(path: pathlib.Path, ten: str) -> tuple[float | None, int | None]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name) and t.id == ten:
                try:
                    return float(ast.literal_eval(node.value)), node.lineno
                except Exception:
                    return None, node.lineno
    return None, None


def ham_dung_hang(path: pathlib.Path, ten: str) -> list[str]:
    """Tên các hàm nhắc tới hằng số `ten` trong thân — tức hàm ĐÓNG CỨNG
    giá trị thay vì nhận nó qua đối số."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    ra: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for con in ast.walk(node):
                if isinstance(con, ast.Name) and con.id == ten:
                    ra.append(node.name)
                    break
    return ra


def main() -> int:
    files = cac_file_duong_chay()
    tier_b = khoa_tier_b()
    ket: dict[str, dict] = {}
    for khoa, gia_tri_yaml in tier_b.items():
        if khoa.startswith("_"):
            continue  # `_budget_remaining_B3` là derived (MT-03), không phải tham số
        doc = duong_doc(khoa, files)
        muc: dict = {"gia_tri_yaml": gia_tri_yaml, "duong_doc": doc, "co_duong_doc": bool(doc)}
        if khoa in NGHI_BAN_SAO:
            rel, ten = NGHI_BAN_SAO[khoa]
            p = ROOT / rel
            val, dong = hang_so_module(p, ten)
            try:
                khop = val is not None and abs(val - float(gia_tri_yaml)) < 1e-12
            except ValueError:
                khop = None
            muc["ban_sao_hardcode"] = {
                "vi_tri": f"{rel}:{dong}" if dong else f"{rel}:KHONG_TIM_THAY {ten}",
                "ten_hang": ten,
                "gia_tri_hang": val,
                "khop_yaml": khop,
                "ham_dong_cung": ham_dung_hang(p, ten),
            }
        ket[khoa] = muc

    thieu = [k for k, v in ket.items() if not v["co_duong_doc"]]
    ra = {
        "cau_hoi": "mỗi tham số tier_b có đường đọc từ tool_d_config.yaml vào đường chạy sản xuất không",
        "pham_vi_quet": list(THU_MUC_DUONG_CHAY),
        "so_tham_so_tier_b": len(ket),
        "so_khong_co_duong_doc": len(thieu),
        "khong_co_duong_doc": thieu,
        "chi_tiet": ket,
        "gioi_han": (
            "Đo TĨNH trên mã nguồn. 'Có đường đọc' nghĩa là có literal "
            "'tier_b.<khoá>' ở vị trí giá trị — KHÔNG chứng minh giá trị đọc "
            "được thật sự chảy tới phép tính cuối (một biến đọc rồi bỏ đó vẫn "
            "tính là có). Chiều NGƯỢC LẠI thì chắc chắn: không có literal nào "
            "⇒ resolve() không thể được gọi cho khoá đó ⇒ không có đường đọc."
        ),
    }
    out = ROOT / "docs" / "du-lieu-do" / "td0195-duong-doc-tham-so-tier-b.json"
    out.write_text(json.dumps(ra, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"tier_b: {len(ket)} tham so — {len(thieu)} KHONG co duong doc: {', '.join(thieu)}")
    for k in thieu:
        bs = ket[k].get("ban_sao_hardcode")
        if bs:
            print(f"  {k:24} <- {bs['vi_tri']} {bs['ten_hang']}={bs['gia_tri_hang']} "
                  f"(khop YAML: {bs['khop_yaml']}) dung o: {', '.join(bs['ham_dong_cung']) or '—'}")
        else:
            print(f"  {k:24} <- khong tim thay ban sao hardcode nao da khai")
    print(f"da ghi {out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
