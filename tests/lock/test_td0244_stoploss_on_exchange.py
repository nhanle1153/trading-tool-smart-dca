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


def test_d2c_chua_la_na_hom_nay_dung_khi_arm_doi_thi_test_nay_do():
    """MT-43 (`back-end-note.md` mục 7) — D2c/`gap_ms` là N/A CÓ ĐIỀU
    KIỆN, không phải một sự thật vĩnh viễn: chỉ N/A khi arm sản xuất
    thuộc `arm_switches.ARM_DON_TRANCHE` (không bao giờ thêm tranche ⇒
    khối lượng SL không bao giờ đổi) VÀ TP1 không sinh sự kiện trên sàn
    thật (đã xác nhận bằng đọc mã nguồn: Binance Futures
    `stoploss_blocks_assets=False` khiến `cancel_stoploss_on_exchange(
    allow_nonblocking=True)` tự thoát sớm, không huỷ gì).

    Hôm nay (`tool_d_config.yaml:139` = `"Z3"`) arm CÓ DCA — vế đầu SAI —
    nên D2c hôm nay vẫn là điều kiện SỐNG, KHÔNG phải N/A. Test này CỐ Ý
    PASS trong tình trạng đó, và CỐ Ý ĐỎ đúng lúc `TD-0227` đổi arm sang
    một giá trị thuộc `ARM_DON_TRANCHE` (`"Z0"`) — buộc người thi hành
    `TD-0227` quay lại đọc `MT-43` và cập nhật `DR-D11-01` một cách
    TƯỜNG MINH, thay vì để "N/A" âm thầm trở thành sự thật mà không ai
    kiểm lại (đúng hình dạng PASS RỖNG mà `-3f`/`-80` cùng cảnh báo)."""
    from tool_d.arm_switches import ARM_DON_TRANCHE
    from tool_d.config.loader import load_tool_d_config, resolve

    cfg = load_tool_d_config()
    arm = resolve(cfg, "tier_c.arm_ablation.arm")
    assert arm not in ARM_DON_TRANCHE, (
        f"arm sản xuất đã đổi thành {arm!r}, thuộc ARM_DON_TRANCHE — D2c/"
        "gap_ms giờ THỰC SỰ N/A qua đường tranche (TP1 đã xác nhận riêng, "
        "không đổi theo arm). TRƯỚC khi coi ca đỏ này là bình thường: đọc "
        "lại MT-43 trong back-end-note.md và cập nhật ngưỡng D2c của "
        "DR-D11-01 một cách tường minh — đừng chỉ sửa test này cho xanh."
    )
