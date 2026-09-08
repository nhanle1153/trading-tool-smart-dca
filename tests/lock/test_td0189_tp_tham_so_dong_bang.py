"""🔒 TD-0189 — bốn con số của §5.1 không được trôi, và hai con số nạng
không được leo vào `tier_b`.

Chủ dự án chốt 08/09/2026 **phương án (a)**: giữ nguyên chỗ ngồi của
`tp_fallback_dist_r` / `tp_fallback_target_r` trong khối `diag_thresholds`
— khối đó là bản chép NGUYÊN VĂN spec dòng 2369-2372 — và **đóng cửa
nguy hiểm bằng một lớp canh** thay vì bằng cách dọn chỗ ngồi.

🔑 **Vì sao cửa đó mới là chỗ nguy, không phải chỗ ngồi.** Dời hai khoá
sang `tier_b` KHÔNG làm đỏ bất cứ thứ gì hiện có, mà lại đổi ba con số
đắt nhất của dự án: `|tier_b|` 12 → 14, **N 114 → 126**, rào DSR
3,0777 → **3,1101**, và tiêu **12 trial** trong 110 suất còn lại — để
tune một thứ mà chính spec (dòng 1678-1682) gọi là **NẠNG DỰ PHÒNG**:
*"nếu phải tune nó để hệ thống có lãi, nghĩa là TP CHÍNH đang hỏng —
đó là L2, xử bằng ablation arm mới, KHÔNG bằng cách tune ngưỡng của
nạng"*. Đúng hình dạng bẫy dự án đã gặp nhiều lần: một dòng sửa trông
vô hại làm rào tự hạ xuống.

📌 Kèm một đính chính ghi tại chỗ. Khi rà, tôi báo rằng spec liệt kê BA
bậc tự do chưa đếm (§3.1 `w`, §4c DG7, §5.1 TP_fallback) nhưng chỉ
thăng hai vào `DOF_gốc = 28`, và *"không dòng nào ghi vì sao khác
nhau"*. Vế sau SAI: spec dòng 1674-1682 ghi rõ — đóng băng cả hai số,
**0 trial**. Cộng với luật TD-0169 (*đóng băng thứ CHƯA TỪNG được đếm
thì trừ đi là trừ khống*), `dof: 0` là kế toán ĐÚNG. Thứ còn lệch chỉ
là `ly_do` trong `dof_inventory.yaml:159` — nó ghi *"bổ sung v7/v8"*,
đúng cho `time_stop_band` nhưng sai cho hai khoá nạng vốn là số §5.1
có từ trước. Một cái NHÃN sai trong sổ kế toán của chính chúng ta,
không phải một lỗ hổng trong phép đo.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

from tool_d.config.loader import load_tool_d_config, resolve, tunable_param_names
from tool_d.take_profit import DUONG_DAN_THAM_SO, doc_tham_so_tp

REPO_ROOT = Path(__file__).resolve().parents[2]
NGUON_TP = REPO_ROOT / "src/tool_d/take_profit.py"

# Hai khoá NẠNG — đóng băng, 0 trial (spec dòng 1674).
KHOA_NANG = ("tp_fallback_dist_r", "tp_fallback_target_r")


@pytest.fixture(scope="module")
def cfg():
    return load_tool_d_config()


@pytest.fixture(scope="module")
def cay() -> ast.Module:
    return ast.parse(NGUON_TP.read_text(encoding="utf-8"))


class TestBonConSoDungNhuSpec:
    def test_doc_duoc_tu_cau_hinh_that(self, cfg) -> None:
        ts = doc_tham_so_tp(cfg)
        assert ts.tp1_haircut_pct == 20.0
        assert ts.tp2_trail_atr == 1.5
        assert ts.tp_fallback_dist_r == 4.0
        assert ts.tp_fallback_target_r == 1.5

    def test_con_so_khop_CHU_trong_spec(self) -> None:
        """Ghim vào chính câu spec, không vào trí nhớ. Cấu hình trôi khỏi
        spec (hoặc ngược lại) là ĐỎ, không phải im lặng."""
        spec = (REPO_ROOT / "tool-d-smart-dca.md").read_text(encoding="utf-8")
        assert "> 4 × R_eff" in spec
        assert "`TP_fallback = p_avg + **1.5 × R_eff**`" in spec
        assert "ĐÓNG BĂNG CẢ HAI SỐ (4.0 và 1.5), 0 trial" in spec

    def test_moi_tham_so_deu_co_duong_dan_khai_bao(self) -> None:
        assert set(DUONG_DAN_THAM_SO) == {
            "tp1_haircut_pct",
            "tp2_trail_atr",
            "tp_fallback_dist_r",
            "tp_fallback_target_r",
        }

    def test_thieu_khoa_thi_RAISE_chu_khong_lay_mac_dinh(self, cfg, tmp_path) -> None:
        """Một mức chốt lời tính bằng số mặc định nào đó là số không ai
        duyệt — cùng chốt với `nguong_giam_toi_da` của DG5 (TD-0169) và
        `notional_co_dinh_usdt` của Z0-S1 (TD-0183)."""
        thieu = tmp_path / "cfg.yaml"
        thieu.write_text(
            "tier_a: {}\ntier_b:\n  _budget_remaining_B3: null\n"
            "tier_frozen: {}\ntier_c: {}\n",
            encoding="utf-8",
        )
        with pytest.raises(KeyError):
            doc_tham_so_tp(load_tool_d_config(thieu))


class TestPhamViKhongDuocNoi:
    """🔴 Lớp canh trung tâm của phương án (a)."""

    def test_hai_khoa_nang_KHONG_duoc_nam_trong_tier_b(self, cfg) -> None:
        tunable = tunable_param_names(cfg)
        vi_pham = [k for k in KHOA_NANG if k in tunable]
        assert not vi_pham, (
            f"{vi_pham} đã leo vào `tier_b`. Đây KHÔNG phải một dòng sửa cấu "
            "hình: |tier_b| 12 → 14, N 114 → 126, rào DSR 3,0777 → 3,1101, "
            "+12 trial. Spec dòng 1674 đóng băng cả hai số với 0 trial và "
            "gọi chúng là NẠNG DỰ PHÒNG — phải tune chúng nghĩa là TP CHÍNH "
            "hỏng (L2), không phải nạng cần chỉnh. Muốn đổi thì cần một DR."
        )

    def test_tier_b_van_dung_12_khoa(self, cfg) -> None:
        """Bất biến đắt nhất, ghim lại ngay tại chỗ dễ phá nhất."""
        assert len(tunable_param_names(cfg)) == 12

    def test_hai_khoa_nang_van_o_trong_khoi_dong_bang(self, cfg) -> None:
        khoi = resolve(cfg, "tier_frozen.diag_thresholds")
        assert khoi["dof"] == 0
        for k in KHOA_NANG:
            assert k in khoi["value"]

    def test_tp1_haircut_pct_co_TRANG_THAI(self) -> None:
        """Con số này từng CHẶN chính TD-0189 vì "im lặng" theo L-Z15
        (TD-0190 gỡ). Ghim để nó không im lặng trở lại."""
        ps = yaml.safe_load(
            (REPO_ROOT / "config/param_status.yaml").read_text(encoding="utf-8")
        )["params"]
        muc = ps["tp1_haircut_pct"]
        assert muc["status"] == "FROZEN"
        assert muc["chua_calibrate"] is True
        assert muc["frozen_rationale"].strip()


class TestKhongCoHangSoLau:
    """Hỏi *có DÙNG không*, không phải *có NHẮC TỚI không* — bằng AST,
    theo bài học `L-Z25` / TD-0181 / TD-0183."""

    def test_khong_hardcode_bon_con_so(self, cay: ast.Module) -> None:
        cam = {4.0, 1.5, 20.0}
        thay = [
            n.value
            for n in ast.walk(cay)
            if isinstance(n, ast.Constant)
            and isinstance(n.value, (int, float))
            and not isinstance(n.value, bool)
            and float(n.value) in cam
        ]
        assert not thay, (
            f"hằng số {thay} nằm thẳng trong `take_profit.py` — mọi tham số "
            "phải đọc từ `tool_d_config.yaml` (N4). Một bản sao thứ hai của "
            "cùng một con số chính là cơ chế đã gây lệch số của v5."
        )

    def test_chi_doc_cau_hinh_qua_resolve(self, cay: ast.Module) -> None:
        """`resolve()` là cách DUY NHẤT được phép đọc tham số (loader.py:117)."""
        goi = {
            n.func.id
            for n in ast.walk(cay)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        assert "resolve" in goi
        truy_cap_thang = [
            n
            for n in ast.walk(cay)
            if isinstance(n, ast.Attribute) and n.attr.startswith("tier_")
        ]
        assert not truy_cap_thang, (
            "đọc thẳng `cfg.tier_*` — đường vòng qua mặt `resolve()`, tức qua "
            "mặt cả L-Z39 (cấm env) lẫn MT-03"
        )
