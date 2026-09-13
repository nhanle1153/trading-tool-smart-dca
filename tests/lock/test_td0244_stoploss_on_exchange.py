"""🔒 TD-0244 / `DR-D11-02` — SL phải sống trên sàn (MT-39), và lưới cuối
`-0,99` phải khớp GIỮA `config.json` và chiến lược.

Trước bản vá này, KHÔNG có phép kiểm nào ghim `order_types.stoploss_on_
exchange` — `L-Z24` chỉ ghim sáu cờ của §0c.4 (freqai/edge/trailing_stop/
position_adjustment_enable/use_exit_signal/protections), không đụng khối
SL. Một lần lật cờ về `false` (quay lại đúng vi phạm §6.6(1) mà `MT-39`
ghi nhận) sẽ đi qua **im lặng** — đúng hình dạng lỗi đã vá ở cổng D2
("xoá file test đi mà cổng vẫn đóng được").

Và trước bản vá này, `ZoneAbsorption.stoploss = -0.30` là một con số
**KHÔNG BAO GIỜ có hiệu lực** — Freqtrade ưu tiên Configuration → Strategy
→ default, `config.json` khai `-0.99` nên luôn ghi đè. Hai con số khác
nhau cho một lưới cuối dễ khiến người sau sửa nhầm chỗ (sửa chiến lược,
tưởng đã đổi SL cuối, nhưng config vẫn thắng).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config" / "freqtrade" / "config.json"
NGUON_CHIEN_LUOC = REPO_ROOT / "user_data/strategies/ZoneAbsorption.py"


def _load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _import_chien_luoc():
    if str(REPO_ROOT / "user_data/strategies") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "user_data/strategies"))
    spec = importlib.util.spec_from_file_location("ZoneAbsorption", NGUON_CHIEN_LUOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_stoploss_on_exchange_bat():
    """`DR-D11-02` §3.1 — SL phải sống trên sàn. Freqtrade tự huỷ+đặt lại
    `STOP_MARKET` (D2a) chỉ khi cờ này bật; tắt nó là quay lại đúng cơ chế
    §6.6(1) cấm (bot theo dõi giá rồi tự đóng — chết cùng tiến trình)."""
    cfg = _load_config()
    assert cfg["order_types"]["stoploss_on_exchange"] is True


def test_stoploss_config_la_luoi_cuoi_rat_rong():
    cfg = _load_config()
    assert cfg["stoploss"] == -0.99


def test_stoploss_chien_luoc_khop_config():
    """Freqtrade ưu tiên Configuration → Strategy → default — con số
    trong `config.json` LUÔN thắng. Nhưng để không còn hai con số khác
    nhau cho cùng một lưới cuối (bẫy đọc-nhầm), thuộc tính lớp phải khớp
    đúng giá trị hiệu dụng."""
    cfg = _load_config()
    m = _import_chien_luoc()
    assert m.ZoneAbsorption.stoploss == cfg["stoploss"] == -0.99


ARM_QUAN_SAT_13_09_2026 = "Z3"


def test_arm_san_xuat_doi_thi_phai_doc_lai_mt43():
    """MT-43 (`back-end-note.md` mục 7) — `d2c_na` (D2c/`gap_ms` là N/A)
    là một BẤT BIẾN HAI CHIỀU: hợp lệ KHI VÀ CHỈ KHI `tier_c.arm_
    ablation.arm ∈ arm_switches.ARM_DON_TRANCHE` (không bao giờ thêm
    tranche ⇒ khối lượng SL không bao giờ đổi; đã xác nhận riêng bằng
    đọc mã nguồn rằng TP1 cũng không cứu được — Binance Futures
    `stoploss_blocks_assets=False` khiến `cancel_stoploss_on_exchange(
    allow_nonblocking=True)` tự thoát sớm khi thoát một phần).

    🔴 CỐ Ý chốt CỨNG giá trị quan sát được HÔM NAY (`"Z3"`, KHÔNG thuộc
    `ARM_DON_TRANCHE` ⇒ D2c đang là điều kiện SỐNG) làm mốc so sánh,
    thay vì chỉ kiểm một chiều "còn thuộc tập không". Một tripwire một
    chiều (chỉ đỏ khi arm ĐI VÀO tập) sẽ xanh trở lại lặng lẽ đúng lúc
    arm ĐI RA khỏi tập lần thứ hai (ví dụ Idea Queue — `TD-0226` — đưa
    DCA quay lại production sau khi đã tạm dùng arm single-entry) — mà
    đó mới là chiều nguy hiểm: một cổng an toàn (§8.3/D2c) bị đánh dấu
    N/A rồi không ai xét lại. Chốt cứng giá trị cụ thể khiến MỌI thay
    đổi arm, bất kể hướng nào, đều đỏ — buộc người sửa tự tay xác nhận
    `d2c_na` đúng hay sai ở giá trị MỚI, không suy diễn theo một hướng
    rồi quên hướng ngược lại (rủi ro `-3f`/`-80` cùng cảnh báo)."""
    from tool_d.arm_switches import ARM_DON_TRANCHE
    from tool_d.config.loader import load_tool_d_config, resolve

    cfg = load_tool_d_config()
    arm = resolve(cfg, "tier_c.arm_ablation.arm")
    thuoc = "THUỘC" if arm in ARM_DON_TRANCHE else "KHÔNG thuộc"
    assert arm == ARM_QUAN_SAT_13_09_2026, (
        f"arm sản xuất đã đổi từ {ARM_QUAN_SAT_13_09_2026!r} sang {arm!r} "
        f"({thuoc} ARM_DON_TRANCHE). TRƯỚC khi sửa hằng số này cho xanh: "
        "đọc lại MT-43 trong back-end-note.md, tự xác nhận `d2c_na` ở giá "
        "trị MỚI này đúng hay sai, và cập nhật DR-D11-01 (ngưỡng D2c) một "
        "cách tường minh nếu trạng thái N/A đã đổi theo."
    )
