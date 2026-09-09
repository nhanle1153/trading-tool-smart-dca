"""TD-0195 — LỚP CANH: mọi tham số `tier_b` phải có ĐƯỜNG ĐỌC từ
`config/tool_d_config.yaml` vào mã chạy; cấm bản sao cứng trong `.py`.

🔴 Vì sao lớp canh này cần tồn tại, dù suite đã có `L-Z15` và kiểm kê DOF:
`L-Z15` (TD-0190) soi `config/param_status.yaml` — *"tham số đã khai
TUNED/FROZEN chưa"*. `dof_inventory.yaml` đếm bậc tự do. **Không cái nào
hỏi câu này: giá trị trong YAML có thật sự chảy tới phép tính không.**

Trước bản vá, 7 trong 12 khoá `tier_b` không có một literal
`"tier_b.<khoá>"` nào trong toàn bộ mã chạy, và ba trong số đó
(`zss_threshold`, `buf_sl_atr`, `dg6a_atr_ratio`) NẰM TRÊN đường chạy sản
xuất `ZoneAbsorption.py` dưới dạng hằng số cứng trùng giá trị. Hậu quả
KHÔNG phải một con số sai — nó là: đổi YAML không có tác dụng gì, mọi
phép kiểm vẫn XANH (hai số bằng nhau), và một trial B3 tiêu thật để đo
một thay đổi KHÔNG XẢY RA. Cùng họ MT-15 (bẫy PASS RỖNG đốt ngân sách),
khác chỗ MT-15 làm hai arm trùng nhau còn cái này làm hai *cấu hình*
trùng nhau.

🔑 Phép kiểm chạy trên AST, không phải grep: một chuỗi trong docstring
hay comment trông y hệt một đối số thật, mà chỉ cái sau mới là đường đọc.
Bằng chứng của phiên `-94` cho `L-Z25` (chuỗi cấm nằm trong dòng chú
thích giải thích chính lệnh cấm) là ca đã xảy ra thật của nhầm lẫn đó.

⚠️ Phạm vi phép kiểm, ghi ra để không ai đọc quá tay: nó chứng minh
chiều PHỦ ĐỊNH — *không có literal nào ⇒ `resolve()` không thể được gọi
cho khoá đó*. Chiều khẳng định thì yếu hơn: một khoá được đọc rồi bỏ đó
vẫn tính là "có đường đọc". Muốn chặt hơn phải theo vết luồng dữ liệu,
việc đó lớp canh này KHÔNG làm.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[2]
THU_MUC_MA_CHAY = ("src", "user_data/strategies", "entrypoints")

# Khoá `tier_b` được phép KHÔNG có đường đọc, kèm lý do và điều kiện gỡ.
# 🔴 Đây là danh sách MIỄN TRỪ CÓ HẠN, không phải danh sách "không cần
# làm": mỗi dòng là một tầng CHƯA ĐƯỢC NỐI, nên vá bây giờ là vá một
# đường không ai đi. Khi tầng tương ứng được nối, XOÁ dòng ở đây — nếu
# quên, phép kiểm `test_mien_tru_het_han` bên dưới sẽ báo đỏ.
MIEN_TRU: dict[str, str] = {
    "v_min": (
        "§3.3b điều kiện (c) — `entry_confirmation.tim_xac_nhan_entry()` chưa "
        "được gọi trên đường chạy (MT-21). Gỡ miễn trừ khi TD-0193 nối xong."
    ),
    "wick_close_upper_frac": (
        "§3.3b điều kiện (a) — cùng lý do với `v_min`. Hiện là số ma `0.5` "
        "trong `entry_confirmation._la_nen_rejection`, chưa có tên hằng số."
    ),
    "funding_rate_pct": (
        "DG6-D — `dieu_kien_d()` chưa có người gọi (`ZoneAbsorption` truyền "
        "`d=False` cứng). 🔴 Gỡ miễn trừ PHẢI kèm chốt ĐƠN VỊ: YAML ghi "
        "-0.05 (phần trăm), hằng số cũ là -0.0005 (tỉ lệ) — sai 100 lần nếu "
        "nối mà quên ÷100 (lớp lỗi L-Z48c)."
    ),
    "dg6d_retrace_frac": "DG6-D — cùng lý do với `funding_rate_pct`.",
}


def _khoa_tier_b() -> dict[str, str]:
    """Đọc khối `tier_b` bằng regex — cố ý KHÔNG qua `loader.py`.

    `loader.py` nằm trong chính thứ đang được kiểm; đọc bằng nó thì hai vế
    cùng một nguồn và phép kiểm không thể báo đỏ khi nguồn đó sai (đúng
    lỗi `L-Z55` ở `folds`, 08/09/2026).
    """
    txt = (GOC / "config" / "tool_d_config.yaml").read_text(encoding="utf-8")
    m = re.search(r"^tier_b:.*?$(.*?)(?=^\S)", txt, re.S | re.M)
    assert m is not None, "không tìm thấy khối tier_b trong tool_d_config.yaml"
    ra: dict[str, str] = {}
    for dong in m.group(1).splitlines():
        k = re.match(r"^  ([a-zA-Z][a-zA-Z0-9_]*):\s*(.+?)\s*(?:#.*)?$", dong)
        if k and not k.group(1).startswith("_"):
            ra[k.group(1)] = k.group(2).strip()
    return ra


def _file_ma_chay() -> list[Path]:
    ra: list[Path] = []
    for d in THU_MUC_MA_CHAY:
        ra.extend(sorted((GOC / d).rglob("*.py")))
    return [f for f in ra if "__pycache__" not in f.parts]


def _literal_duong_dan(khoa: str) -> list[str]:
    """Mọi literal `tier_b.<khoa>` ở vị trí GIÁ TRỊ (bỏ docstring)."""
    can = f"tier_b.{khoa}"
    ra: list[str] = []
    for f in _file_ma_chay():
        try:
            cay = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover — mã hỏng thì test khác báo
            continue
        docstring = {
            id(n.body[0].value)
            for n in ast.walk(cay)
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and n.body
            and isinstance(n.body[0], ast.Expr)
            and isinstance(n.body[0].value, ast.Constant)
        }
        for n in ast.walk(cay):
            if isinstance(n, ast.Constant) and n.value == can and id(n) not in docstring:
                ra.append(f"{f.relative_to(GOC).as_posix()}:{n.lineno}")
    return ra


TIER_B = _khoa_tier_b()


class TestMoiThamSoTierBCoDuongDoc:
    @pytest.mark.parametrize("khoa", sorted(k for k in TIER_B if k not in MIEN_TRU))
    def test_co_it_nhat_mot_duong_doc(self, khoa: str) -> None:
        vi_tri = _literal_duong_dan(khoa)
        assert vi_tri, (
            f"`tier_b.{khoa}` = {TIER_B[khoa]} KHÔNG có đường đọc nào trong "
            f"{', '.join(THU_MUC_MA_CHAY)} — không một literal "
            f'"tier_b.{khoa}" nào ở vị trí giá trị, nên `resolve()` không thể '
            "được gọi cho nó. Giá trị đang dùng đến từ đâu đó KHÁC YAML (N4 "
            "cấm hardcode). Hậu quả không phải một con số sai mà là: đổi YAML "
            "không có tác dụng gì, và một trial B3 sẽ tiêu thật để đo một "
            "thay đổi không xảy ra. Sửa: cho hàm thuần nhận ngưỡng qua đối số "
            "BẮT BUỘC, tầng chiến lược đọc `resolve(cfg, \"tier_b."
            f'{khoa}")` rồi truyền xuống. Nếu tầng dùng nó chưa được nối, '
            "thêm một dòng vào MIEN_TRU kèm lý do và điều kiện gỡ."
        )

    def test_mien_tru_het_han(self) -> None:
        """Khoá đã có đường đọc mà vẫn nằm trong MIEN_TRU ⇒ ĐỎ.

        Một danh sách miễn trừ không tự dọn sẽ lặng lẽ phình ra cho tới lúc
        nó che mất chính thứ nó được lập ra để theo dõi.
        """
        thua = {k: _literal_duong_dan(k) for k in MIEN_TRU if _literal_duong_dan(k)}
        assert not thua, (
            "các khoá này đã có đường đọc, phải XOÁ khỏi MIEN_TRU: "
            + "; ".join(f"{k} ({', '.join(v)})" for k, v in thua.items())
        )

    def test_mien_tru_chi_chua_khoa_co_that(self) -> None:
        la = sorted(set(MIEN_TRU) - set(TIER_B))
        assert not la, (
            f"MIEN_TRU nhắc tới khoá không có trong `tier_b`: {la} — "
            "khoá đã đổi tên hoặc rời tầng, dòng miễn trừ nay canh một thứ "
            "không tồn tại."
        )


class TestCamBanSaoCungGiaTri:
    """Ba hằng số đã bị xoá, không được lặng lẽ quay lại.

    Chúng không sai về giá trị — chúng sai vì là NGUỒN SỰ THẬT THỨ HAI cho
    một khoá `tier_b`. Ca đúng nhất để canh không phải "giá trị bằng bao
    nhiêu" mà "cái tên đó có tồn tại lại không".
    """

    @pytest.mark.parametrize(
        "tep,ten_hang,khoa",
        [
            ("src/tool_d/zone_strength.py", "NGUONG_ZSS", "zss_threshold"),
            ("src/tool_d/trade_plan.py", "BUF_SL_HE_SO", "buf_sl_atr"),
            ("src/tool_d/dg6_early_invalidation.py", "NGUONG_ATR_RATIO_A", "dg6a_atr_ratio"),
        ],
    )
    def test_hang_so_khong_quay_lai(self, tep: str, ten_hang: str, khoa: str) -> None:
        cay = ast.parse((GOC / tep).read_text(encoding="utf-8"))
        gan = [
            n.lineno
            for n in cay.body
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == ten_hang for t in n.targets)
        ]
        assert not gan, (
            f"{tep}:{gan} — `{ten_hang}` đã quay lại. Nó là bản sao cứng của "
            f"`tier_b.{khoa}`; hai nguồn sự thật cho một con số, và vì hai giá "
            "trị thường bằng nhau nên KHÔNG phép kiểm nào khác báo đỏ. Ngưỡng "
            "phải đi qua đối số, giá trị đọc từ YAML (TD-0195)."
        )


class TestNguongZssLaDoiSoBatBuoc:
    """`zone_hop_le` không được có mặc định cho `nguong_zss`.

    Một mặc định ở đây là chỗ để một đường gọi quên khai mà vẫn lặng lẽ
    chạy — đúng lý do `bat_dieu_kien_c` của `entry_confirmation` cũng
    không có mặc định (nếu có, hai arm lại nhập làm một).
    """

    def test_khong_co_mac_dinh(self) -> None:
        from tool_d import zone_strength

        cay = ast.parse(Path(zone_strength.__file__).read_text(encoding="utf-8"))
        ham = next(
            n for n in ast.walk(cay)
            if isinstance(n, ast.FunctionDef) and n.name == "zone_hop_le"
        )
        ten = [a.arg for a in ham.args.kwonlyargs]
        assert "nguong_zss" in ten, "`zone_hop_le` phải nhận `nguong_zss` keyword-only"
        mac_dinh = ham.args.kw_defaults[ten.index("nguong_zss")]
        assert mac_dinh is None, (
            "`nguong_zss` có giá trị mặc định — bỏ mặc định đi. Mặc định biến "
            "một tham số bắt buộc thành một tuỳ chọn im lặng: đường gọi nào "
            "quên truyền sẽ chạy bằng con số của ai đó viết một lần trong quá "
            "khứ, và không có gì báo."
        )
