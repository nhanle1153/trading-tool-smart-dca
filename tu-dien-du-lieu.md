# Từ điển Dữ liệu (Data Dictionary)

> Nguồn tham chiếu DUY NHẤT về ý nghĩa mọi bảng/trường trong hệ thống — không phải tài liệu tham khảo tùy chọn.
> AI bắt buộc tra file này trước khi đọc/ghi bất kỳ trường nào, không suy đoán ý nghĩa từ tên trường hay code cũ.
> Cập nhật theo kiểu NỐI THÊM có version từng dòng — không ghi đè lịch sử.
> **Bất kỳ thay đổi migration nào (thêm/xóa/sửa bảng hoặc trường) đều bắt buộc cập nhật file này + ERD trong ARCHITECTURE.md ngay lập tức — dù thay đổi nhỏ đến đâu.**

---

## 0. File này do MÁY SINH — đừng sửa tay

🔴 **Sửa tay ở đây sẽ bị test khoá bắt đỏ** (`tests/lock/test_td0245_tu_dien_soi_schema_that.py`).
Toàn bộ nội dung sinh từ **schema THẬT** bằng:

```
docker compose -f docker/docker-compose.yml run --rm freqtrade \
    docs/du-lieu-do/do_td0245_schema_sqlite_freqtrade.py   # đo lại schema
docker compose -f docker/docker-compose.yml run --rm freqtrade \
    -m tool_d.tu_dien.ghi_tu_dien                          # sinh lại file này
```

Muốn sửa một dòng thì sửa **nguồn** của nó: kiểu dữ liệu/ràng buộc nằm ở chính database
(đo lại), cột *Ý nghĩa* nằm ở `src/tool_d/tu_dien/y_nghia_cot.py`.

### Xuất xứ của bản này

- **Nguồn schema:** `freqtrade.persistence.init_db` — models.py:48 — create_all(engine) rồi check_migrate(...); cùng đường mã bot gọi lúc khởi động
- **Đọc lại bằng:** PRAGMA table_info trên file sqlite, mode=ro
- **Freqtrade:** `freqtrade 2026.8`
- **Source commit:** `9f10e357a93c1dcf10c2a2b367659214d89c073e`
- **Image digest:** `sha256:7031bca43ed7668ebf421725dd5016acade6ef88b0771db3e08c96e6d19a42db`
- **Artifact:** `docs/du-lieu-do/td0245-schema-sqlite-freqtrade.json`
- **Quy mô:** **6 bảng / 109 cột**

⚠️ **Image đổi thì phải ĐO LẠI, không dùng số cũ.** Mọi `file:line` trong cột *Ý nghĩa*
là ảnh chụp mã nguồn Freqtrade tại thời điểm đọc, không phải hằng số.

### Ba trạng thái của cột *Ý nghĩa* — vì sao không điền cho đủ

- **đã tra** (49/109 cột): ý nghĩa đọc ra từ mã nguồn Freqtrade, có `file:line` kèm theo.
- **⏳ chưa tra cứu**: chưa ai đọc mã cho cột này.

Quy tắc 7 cấm *"suy đoán ý nghĩa từ tên trường"*. Điền nốt phần còn lại bằng suy đoán sẽ
tạo ra những dòng **trông y hệt** dòng đã tra — nguy hơn hẳn một ô ghi thẳng là chưa biết (N6).

🔴 **Cần một cột đang `⏳`?** Đọc mã nguồn Freqtrade trong ảnh Docker, thêm mục vào
`y_nghia_cot.py` kèm `file:line`, sinh lại. **Đừng đoán, và đừng đọc nó khi chưa tra** —
test khoá sẽ chặn đúng ở đó.

---

## 1. Phạm vi — đọc trước khi dùng

File này mô tả **database SQLite mà Freqtrade ghi lệnh** (`config/freqtrade/config.json` → `db_url`).

**KHÔNG thuộc phạm vi bản này** (mỗi mục là một việc riêng, chưa mở):

- **Hình dạng bên trong `trade_custom_data.cd_value`** — nơi Tool D cất dữ liệu riêng
  (`co_lenh`, `ke_hoach`, `tag`, `zone_dinh`, `chot_loi`). Chưa có schema nào mô tả.
- **Các sổ JSONL** (`trial_registry`, `idea_queue`, `param_change_proposals`, `decision_log`).
  Nguồn sự thật hình dạng của chúng là **JSON Schema trong `registry/schemas/`**, và
  `ARCHITECTURE.md:271-273` đã ràng buộc trước: nếu mô tả ở đây thì phải **sinh/kiểm tự động**,
  không chép tay — chép tay là dựng nguồn sự thật thứ hai, đúng bài học **MT-03**.

---

## 2. Sơ đồ quan hệ

```
trades ──1:N──> orders              (orders.ft_trade_id → trades.id)
       └─1:N──> trade_custom_data   (trade_custom_data.ft_trade_id → trades.id)

wallet_history   pairlocks   KeyValueStore    (độc lập, không khoá ngoại)
```

---

## Bảng: KeyValueStore

**7 cột** · đã tra ý nghĩa: **0/7**

| Trường | Kiểu dữ liệu | Ý nghĩa (định nghĩa rõ, không nhập nhằng) | Bắt buộc? | Giá trị hợp lệ | Ràng buộc/Khóa ngoại | Dùng bởi (module/function nào) | Version | Ngày cập nhật |
|---|---|---|---|---|---|---|---|---|
| `id` | INTEGER | ⏳ chưa tra cứu | ✅ (khoá chính) | — | PK | — | v1.0 | 14/09/2026 |
| `key` | VARCHAR(50) | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `value_type` | VARCHAR(20) | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `string_value` | VARCHAR(255) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `datetime_value` | DATETIME | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `float_value` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `int_value` | INTEGER | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |

## Bảng: orders

**26 cột** · đã tra ý nghĩa: **10/26**

| Trường | Kiểu dữ liệu | Ý nghĩa (định nghĩa rõ, không nhập nhằng) | Bắt buộc? | Giá trị hợp lệ | Ràng buộc/Khóa ngoại | Dùng bởi (module/function nào) | Version | Ngày cập nhật |
|---|---|---|---|---|---|---|---|---|
| `id` | INTEGER | Khoá chính của một lệnh đặt lên sàn — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:85`_ | ✅ (khoá chính) | — | PK | — | v1.0 | 14/09/2026 |
| `ft_trade_id` | INTEGER | Khoá ngoại trỏ `trades.id`. Một trade có NHIỀU order (mỗi tranche một order, cộng các lệnh SL và lệnh thoát) — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:86`_ | ✅ | — | FK → trades.id | — | v1.0 | 14/09/2026 |
| `ft_order_side` | VARCHAR(25) | Vai trò của order trong lệnh. 🔴 `stoploss` là giá trị RIÊNG, không phải `buy`/`sell` — đây là cách duy nhất lọc ra lịch sử SL — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:91-92`_ | ✅ | buy · sell · stoploss | — | `src/tool_d/reporting/freqtrade_db.py::_rut_gon` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._ghi_gap_ms` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._ghi_vao_lenh` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption.order_filled` | v1.0 | 14/09/2026 |
| `ft_pair` | VARCHAR(25) | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `ft_is_open` | BOOLEAN | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `ft_amount` | FLOAT | Khối lượng Freqtrade YÊU CẦU (khác `amount` do sàn báo về) — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:95`_ | ✅ | — | — | `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._ghi_gap_ms` | v1.0 | 14/09/2026 |
| `ft_price` | FLOAT | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `ft_cancel_reason` | VARCHAR(255) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `order_id` | VARCHAR(255) | Mã order do SÀN cấp. Tool D dùng làm khoá chống trùng của Decision Log (§8.3) — mỗi tranche một sự kiện — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:99`_ | ✅ | — | — | `src/tool_d/gap_ms.py::sinh_ban_ghi_doi_sl` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._ghi_gap_ms` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._ghi_vao_lenh` | v1.0 | 14/09/2026 |
| `status` | VARCHAR(255) | Trạng thái order theo CCXT. `canceled` là mốc suy ra khoảng trống không-SL (`gap_ms`) — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:100`_ | — | open · closed · canceled · expired · rejected | — | `src/tool_d/gap_ms.py` · `user_data/strategies/ZoneAbsorption.py` | v1.0 | 14/09/2026 |
| `symbol` | VARCHAR(25) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `order_type` | VARCHAR(50) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `side` | VARCHAR(25) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `price` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `average` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `amount` | FLOAT | Khối lượng order theo SÀN báo về. Khối lượng ĐÃ khớp là `filled` — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:106`_ | — | — | — | `src/tool_d/gap_ms.py` · `user_data/strategies/ZoneAbsorption.py` | v1.0 | 14/09/2026 |
| `filled` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `remaining` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `cost` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `stop_price` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `order_date` | DATETIME | Thời điểm order được TẠO. Mốc kết thúc khoảng trống không-SL — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:111`_ | — | — | — | `src/tool_d/gap_ms.py::sinh_ban_ghi_doi_sl` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._ghi_gap_ms` | v1.0 | 14/09/2026 |
| `order_filled_date` | DATETIME | Thời điểm order KHỚP; `NULL` nếu chưa khớp. Đây là mốc khớp thật, khác `order_date` — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:112`_ | — | — | — | `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._ghi_gap_ms` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._ghi_vao_lenh` | v1.0 | 14/09/2026 |
| `order_update_date` | DATETIME | Lần cuối trạng thái order đổi. Với order SL đã huỷ, đây là mốc BẮT ĐẦU khoảng trống không-SL — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:113`_ | — | — | — | `src/tool_d/gap_ms.py::sinh_ban_ghi_doi_sl` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._ghi_gap_ms` | v1.0 | 14/09/2026 |
| `funding_fee` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `ft_fee_base` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `ft_order_tag` | VARCHAR(255) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |

## Bảng: pairlocks

**7 cột** · đã tra ý nghĩa: **0/7**

| Trường | Kiểu dữ liệu | Ý nghĩa (định nghĩa rõ, không nhập nhằng) | Bắt buộc? | Giá trị hợp lệ | Ràng buộc/Khóa ngoại | Dùng bởi (module/function nào) | Version | Ngày cập nhật |
|---|---|---|---|---|---|---|---|---|
| `id` | INTEGER | ⏳ chưa tra cứu | ✅ (khoá chính) | — | PK | — | v1.0 | 14/09/2026 |
| `pair` | VARCHAR(25) | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `side` | VARCHAR(25) | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `reason` | VARCHAR(255) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `lock_time` | DATETIME | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `lock_end_time` | DATETIME | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `active` | BOOLEAN | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |

## Bảng: trade_custom_data

**7 cột** · đã tra ý nghĩa: **7/7**

| Trường | Kiểu dữ liệu | Ý nghĩa (định nghĩa rõ, không nhập nhằng) | Bắt buộc? | Giá trị hợp lệ | Ràng buộc/Khóa ngoại | Dùng bởi (module/function nào) | Version | Ngày cập nhật |
|---|---|---|---|---|---|---|---|---|
| `id` | INTEGER | Khoá chính — _nguồn: `/freqtrade/freqtrade/persistence/custom_data.py:36`_ | ✅ (khoá chính) | — | PK | — | v1.0 | 14/09/2026 |
| `ft_trade_id` | INTEGER | Khoá ngoại trỏ `trades.id`. Ràng buộc duy nhất `(ft_trade_id, cd_key)` ⇒ mỗi lệnh mỗi khoá đúng một bản ghi — _nguồn: `/freqtrade/freqtrade/persistence/custom_data.py:34 · 37`_ | — | — | FK → trades.id | — | v1.0 | 14/09/2026 |
| `cd_key` | VARCHAR(255) | Tên khoá do chiến lược đặt (Tool D dùng `co_lenh`, `ke_hoach`, `tag`, `zone_dinh`, `chot_loi`) — _nguồn: `/freqtrade/freqtrade/persistence/custom_data.py:41`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `cd_type` | VARCHAR(25) | Tên kiểu Python của giá trị, dùng để dựng lại khi đọc ra — _nguồn: `/freqtrade/freqtrade/persistence/custom_data.py:42`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `cd_value` | TEXT | Giá trị đã tuần tự hoá thành văn bản. 🔴 Hình dạng BÊN TRONG là của Tool D và CHƯA có schema nào mô tả — ngoài phạm vi TD-0245 — _nguồn: `/freqtrade/freqtrade/persistence/custom_data.py:43`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `created_at` | DATETIME | Lúc bản ghi được tạo — _nguồn: `/freqtrade/freqtrade/persistence/custom_data.py:44`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `updated_at` | DATETIME | Lúc sửa lần cuối; `NULL` nếu chưa sửa lần nào — _nguồn: `/freqtrade/freqtrade/persistence/custom_data.py:45`_ | — | — | — | — | v1.0 | 14/09/2026 |

## Bảng: trades

**51 cột** · đã tra ý nghĩa: **21/51**

| Trường | Kiểu dữ liệu | Ý nghĩa (định nghĩa rõ, không nhập nhằng) | Bắt buộc? | Giá trị hợp lệ | Ràng buộc/Khóa ngoại | Dùng bởi (module/function nào) | Version | Ngày cập nhật |
|---|---|---|---|---|---|---|---|---|
| `id` | INTEGER | Khoá chính của một lệnh (trade). Mọi tranche DCA của cùng một lệnh dùng CHUNG id này — nên đếm theo `id` là đếm LỆNH, không phải đếm lần vào — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1717`_ | ✅ (khoá chính) | — | PK | `user_data/strategies/ZoneAbsorption.py` | v1.0 | 14/09/2026 |
| `exchange` | VARCHAR(25) | Tên sàn thực hiện lệnh — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1731`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `pair` | VARCHAR(25) | Cặp giao dịch, dạng `BASE/QUOTE` (có hậu tố `:QUOTE` ở futures) — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1732`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `base_currency` | VARCHAR(25) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `stake_currency` | VARCHAR(25) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `is_open` | BOOLEAN | Lệnh còn mở hay đã đóng hẳn. Mẫu số của mọi tỉ lệ trên 'lệnh đã đóng' phải lọc `is_open = 0` — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1735`_ | ✅ | 0 hoặc 1 | — | `entrypoints/periodic_report.py::render_report` · `src/tool_d/reporting/freqtrade_db.py::_rut_gon` · `src/tool_d/reporting/report_model.py::_tinh_h3` · `src/tool_d/reporting/report_model.py::_tinh_winrate` · `user_data/strategies/ZoneAbsorption.py` | v1.0 | 14/09/2026 |
| `fee_open` | FLOAT | TỈ LỆ phí của lệnh vào (không phải số tiền). Số tiền là `fee_open_cost` — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1736`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `fee_open_cost` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `fee_open_currency` | VARCHAR(25) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `fee_close` | FLOAT | TỈ LỆ phí của lệnh ra. Số tiền là `fee_close_cost` — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1741`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `fee_close_cost` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `fee_close_currency` | VARCHAR(25) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `open_rate` | FLOAT | Giá vào TRUNG BÌNH hiện tại của lệnh. Với DCA, giá trị này ĐỔI sau mỗi tranche khớp (tính lại ở `recalc_trade_from_orders`) — không phải giá của tranche 1 — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1745`_ | ✅ | — | — | `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._cap_nhat_chot_loi` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption.custom_exit` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption.order_filled` · `user_data/strategies/ZoneAbsorptionMinimal.py::ZoneAbsorptionMinimal.custom_exit` | v1.0 | 14/09/2026 |
| `open_rate_requested` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `open_trade_value` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `close_rate` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `close_rate_requested` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `realized_profit` | FLOAT | Lãi/lỗ tuyệt đối ĐÃ THỰC HIỆN, CỘNG DỒN qua mọi lần thoát từng phần. Đây mới là 'đã thực hiện' — KHÔNG phải `close_profit_abs` — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1751 · 1320`_ | — | — | — | — | v1.0 | 14/09/2026 |
| `close_profit` | FLOAT | Lãi/lỗ theo TỈ LỆ. 🔴 DR-013 CẤM dùng tỉ lệ cho mọi chỉ số tổng hợp (mẫu số riêng từng lệnh; với DCA còn đổi giữa chừng) — dùng `pnl_abs` — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1752`_ | — | — | — | — | v1.0 | 14/09/2026 |
| `close_profit_abs` | FLOAT | 🔴 BẪY: khi trade CÒN MỞ sau một lần thoát từng phần, đây CHỈ là lãi của lần thoát CUỐI CÙNG, không phải tổng. Chỉ khi đóng hẳn nó mới là TỔNG. Đã bao gồm phí VÀ funding. Deprecated ở tầng RPC (bí danh `profit_abs`) — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1753 · 1318-1321 · 1342-1344 · 1160 · 747`_ | — | — | — | `src/tool_d/reporting/freqtrade_db.py::_rut_gon` · `src/tool_d/reporting/report_model.py::_tinh_winrate` | v1.0 | 14/09/2026 |
| `stake_amount` | FLOAT | Ký quỹ đã bỏ ra, TỔNG hiện tại của mọi tranche đã khớp (đã chia đòn bẩy). Với DCA giá trị này LỚN DẦN — không phải cỡ lệnh lúc mở — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1754`_ | ✅ | — | — | `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._deployed_ratio` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._phuc_hoi_ke_hoach_sau_restart` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._xet_tp1` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption.adjust_trade_position` · `user_data/strategies/ZoneAbsorptionMinimal.py::ZoneAbsorptionMinimal.adjust_trade_position` | v1.0 | 14/09/2026 |
| `max_stake_amount` | FLOAT | Ký quỹ lớn nhất lệnh từng chiếm, cộng dồn theo từng lần vào — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1755`_ | — | — | — | — | v1.0 | 14/09/2026 |
| `amount` | FLOAT | Khối lượng vị thế hiện tại theo đơn vị tài sản cơ sở (đã trừ phần đã thoát) — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1756`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `amount_requested` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `open_date` | DATETIME | Thời điểm mở lệnh (tranche 1). ⚠️ Lưu KHÔNG kèm múi giờ; Freqtrade coi là UTC và phơi bản có múi giờ qua thuộc tính `open_date_utc` — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1758`_ | ✅ | — | — | `src/tool_d/gates/cscv.py::tinh_pbo` · `src/tool_d/wfo/lenh.py::LenhWFO.__post_init__` · `src/tool_d/wfo/lenh.py::_trong_cua_so` · `src/tool_d/wfo/lenh.py::cat_lat_theo_fold` · `src/tool_d/wfo/lenh.py::cat_lat_theo_khoi` | v1.0 | 14/09/2026 |
| `close_date` | DATETIME | Thời điểm đóng hẳn lệnh; `NULL` khi lệnh còn mở. Cùng quy ước múi giờ với `open_date` — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1759`_ | — | — | — | `src/tool_d/wfo/lenh.py::LenhWFO.__post_init__` | v1.0 | 14/09/2026 |
| `stop_loss` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `stop_loss_pct` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `initial_stop_loss` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `initial_stop_loss_pct` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `is_stop_loss_trailing` | BOOLEAN | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `max_rate` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `min_rate` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `exit_reason` | VARCHAR(255) | Lý do thoát. Với Tool D đây là chuỗi do `custom_exit()` trả về (ví dụ `TIME_STOP`), hoặc tên cơ chế của Freqtrade — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1773`_ | — | — | — | `src/tool_d/reporting/freqtrade_db.py::_rut_gon` · `src/tool_d/reporting/report_model.py::_tinh_h3` | v1.0 | 14/09/2026 |
| `exit_order_status` | VARCHAR(100) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `strategy` | VARCHAR(100) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `enter_tag` | VARCHAR(255) | Nhãn vào lệnh do chiến lược gán. Tool D nhét kế hoạch tranche đã mã hoá vào đây và giải mã lại khi khởi động lại — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1776`_ | — | — | — | `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption._phuc_hoi_ke_hoach_sau_restart` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption.adjust_trade_position` · `user_data/strategies/ZoneAbsorptionMinimal.py::ZoneAbsorptionMinimal._doc_hoac_khoi_tao_ke_hoach` | v1.0 | 14/09/2026 |
| `timeframe` | INTEGER | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `trading_mode` | VARCHAR(7) | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `amount_precision` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `price_precision` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `precision_mode` | INTEGER | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `precision_mode_price` | INTEGER | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `contract_size` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `leverage` | FLOAT | Đòn bẩy của lệnh. `stake_amount × leverage = giá trị vị thế` — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1787`_ | — | — | — | `user_data/strategies/ZoneAbsorption.py` | v1.0 | 14/09/2026 |
| `is_short` | BOOLEAN | Hướng lệnh. 🔴 Quy ước DẤU của funding đảo theo cột này — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1788`_ | ✅ | 0 hoặc 1 | — | `src/tool_d/reporting/freqtrade_db.py::_rut_gon` · `src/tool_d/reporting/report_model.py::_tinh_winrate` · `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption.custom_stoploss` | v1.0 | 14/09/2026 |
| `liquidation_price` | FLOAT | ⏳ chưa tra cứu | — | — | — | — | v1.0 | 14/09/2026 |
| `interest_rate` | FLOAT | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `funding_fees` | FLOAT | Funding tích luỹ đã CHỐT. 🔴 DƯƠNG = lệnh ĐƯỢC NHẬN, ÂM = phải TRẢ. Đã được cộng/trừ vào `close_profit_abs` rồi — trừ lần nữa là tính hai lần — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1795 · 1128-1135`_ | — | — | — | `user_data/strategies/ZoneAbsorption.py::ZoneAbsorption.custom_exit` · `user_data/strategies/ZoneAbsorptionMinimal.py::ZoneAbsorptionMinimal.custom_exit` | v1.0 | 14/09/2026 |
| `funding_fee_running` | FLOAT | Funding đang chạy của phần vị thế CHƯA đóng — tách khỏi `funding_fees` để phần đã chốt không đổi khi giá funding kỳ sau thay đổi — _nguồn: `/freqtrade/freqtrade/persistence/trade_model.py:1796`_ | — | — | — | — | v1.0 | 14/09/2026 |
| `record_version` | INTEGER | ⏳ chưa tra cứu | ✅ | — | — | — | v1.0 | 14/09/2026 |

## Bảng: wallet_history

**11 cột** · đã tra ý nghĩa: **11/11**

| Trường | Kiểu dữ liệu | Ý nghĩa (định nghĩa rõ, không nhập nhằng) | Bắt buộc? | Giá trị hợp lệ | Ràng buộc/Khóa ngoại | Dùng bởi (module/function nào) | Version | Ngày cập nhật |
|---|---|---|---|---|---|---|---|---|
| `id` | INTEGER | Khoá chính — _nguồn: `/freqtrade/freqtrade/persistence/wallet_history.py:18`_ | ✅ (khoá chính) | — | PK | — | v1.0 | 14/09/2026 |
| `timestamp` | DATETIME | Mốc bản ghi. 🔴 Độ phân giải NGÀY — ràng buộc duy nhất `(timestamp, currency)` khoá ĐÚNG MỘT bản ghi mỗi đồng mỗi ngày, nên đỉnh equity TRONG NGÀY không suy được từ bảng này — _nguồn: `/freqtrade/freqtrade/persistence/wallet_history.py:19 · 40-43`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `currency` | VARCHAR(25) | Đồng của dòng ví này — _nguồn: `/freqtrade/freqtrade/persistence/wallet_history.py:20`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `rate` | FLOAT | Giá 1 đơn vị `currency` quy theo `quote_currency` — _nguồn: `/freqtrade/freqtrade/persistence/wallet_history.py:21-23`_ | — | — | — | — | v1.0 | 14/09/2026 |
| `quote_currency` | VARCHAR(25) | Đồng định giá cho `rate` và các cột `total_*` — _nguồn: `/freqtrade/freqtrade/persistence/wallet_history.py:24-25`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `balance` | FLOAT | Số dư theo đơn vị `currency` (chưa quy đổi) — _nguồn: `/freqtrade/freqtrade/persistence/wallet_history.py:27-28`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `total_quote` | FLOAT | Tổng giá trị ví quy theo `quote_currency` — đại lượng 'equity' chuẩn tắc. Với futures tính bằng `collateral` + PnL — _nguồn: `/freqtrade/freqtrade/persistence/wallet_history.py:30-32`_ | — | — | — | — | v1.0 | 14/09/2026 |
| `total_position_value` | FLOAT | Tổng giá trị vị thế, ĐÃ nhân đòn bẩy — _nguồn: `/freqtrade/freqtrade/persistence/wallet_history.py:33-34`_ | — | — | — | — | v1.0 | 14/09/2026 |
| `collateral` | FLOAT | Ký quỹ đang giữ — _nguồn: `/freqtrade/freqtrade/persistence/wallet_history.py:35`_ | — | — | — | — | v1.0 | 14/09/2026 |
| `leverage` | FLOAT | Đòn bẩy tại thời điểm chụp — _nguồn: `/freqtrade/freqtrade/persistence/wallet_history.py:36`_ | ✅ | — | — | — | v1.0 | 14/09/2026 |
| `bot_managed` | BOOLEAN | Phần ví do bot này quản lý hay không — lọc cột này để không tính nhầm tiền của người/bot khác trên cùng tài khoản — _nguồn: `/freqtrade/freqtrade/persistence/wallet_history.py:38`_ | ✅ | 0 hoặc 1 | — | — | v1.0 | 14/09/2026 |

---

## Lịch sử thay đổi Từ điển Dữ liệu

| Bảng.Trường | Loại thay đổi (➕ Thêm mới / ❌ Xóa / ♻️ Sửa đổi) | Nội dung cũ | Nội dung mới | Lý do | Ngày |
|---|---|---|---|---|---|
| (toàn bộ) | ➕ Thêm mới | — | Khởi tạo từ schema THẬT: 6 bảng / 109 cột | TD-0245 — Quy tắc 7 đang chặn TD-0238 và TD-0240; từ điển chưa bao giờ tồn tại ở gốc repo | 14/09/2026 |

---

_Bằng chứng ý nghĩa đọc từ: Freqtrade 2026.8, source commit 9f10e357a93c1dcf10c2a2b367659214d89c073e, image sha256:7031bca43ed7668ebf421725dd5016acade6ef88b0771db3e08c96e6d19a42db_
