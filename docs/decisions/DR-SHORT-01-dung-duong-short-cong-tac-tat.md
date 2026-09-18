# DR-SHORT-01 — Dựng đường SHORT cho `ZoneAbsorption`, công tắc TẮT

> **Ngày chốt:** 18/09/2026 · **Người quyết:** chủ dự án (trả lời hai câu hỏi phạm vi + duyệt kế hoạch, phiên mã `aab049b6`)
> **Chi phí:** **0 trial** · Không đo trên CALIB/WFO/LOCKBOX/EXPLORE · Không chạm lockbox · Không gỡ ⏸ nào của khâu đo.
> Mã `DR-SHORT-01` + `TD-0318`…`TD-0322` đặt chỗ bằng commit `d4e722f` (N12 mục 7c) trước khi file này tồn tại.

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`), cùng lý do `DR-HUONG-01` §0:
> soạn bởi một phiên đã thấy số đo của Tool D.

---

## 1. Yêu cầu và chỗ nó va

Chủ dự án yêu cầu *"triển khai Short đồng thời"*. Hiện trạng: `ZoneAbsorption.py` `can_short = False`,
`tool_d_config.yaml` `tier_a.enable_short: false`; chiều Short chỉ có một lần **đếm tín hiệu** trên EXPLORE,
0 lệnh, 0 PnL.

Yêu cầu này va với ba quyết định đã chốt (quy tắc 11 — ghi, không tự chọn bên):

| Quyết định | Chữ đang có |
|---|---|
| `DR-HUONG-01` §2, §3 (18/09) | Phương án D (ZA SHORT) ⏸ *"không làm lúc này"*; điều kiện mở lại viết TRƯỚC; *"Long thất bại nên thử Short"* **KHÔNG** phải điều kiện |
| `DR-D4-01` §2b (08/09) | Bật Short cần đủ ba: DG7 có ngưỡng riêng đã calibrate · Δ_R(SHORT) `ok` đã commit · còn ≥ 9 suất |
| `DR-D6D8-01` §1.1 (17/09) | Long-only tới live; Short là chu trình riêng D3.5-Short → … → lockbox MỚI |

## 2. Quyết định

Chủ dự án chọn giữa ba mức (*chỉ dựng code* · *dựng + đo ngay* · *giữ nguyên*):

1. ✅ **Chỉ DỰNG code, công tắc TẮT.** Phương án D của `DR-HUONG-01` §2 tách làm hai:
   - **D-dựng** — ✅ được làm: viết đường Short trong chiến lược + module thuần, kiểm bằng **dữ liệu tổng hợp**
     (fixture) — không phải dữ liệu thị trường, nên không phải "chạm" theo `DR-014` §2 / N2.
   - **D-đo** — ⏸ **giữ nguyên**: mọi điều kiện mở lại của `DR-HUONG-01` §3 và `DR-D4-01` §2b đứng nguyên
     **từng chữ**. DR này **không** thay, không nới, không diễn giải lại chúng.
2. ✅ **Đích vận hành: MỘT bot, CẢ HAI chiều.** Cùng `ZoneAbsorption.py`, cùng `E_D`: Long vào ở zone đáy,
   Short vào ở zone đỉnh. Hai chiều bật/tắt độc lập bằng `tier_a.enable_long` / `tier_a.enable_short` (N4).

## 3. Vì sao D-dựng không phá kỷ luật thống kê — và khai thẳng điểm yếu

**Khai thẳng:** DR này được quyết **SAU** khi đã thấy kết quả ZA LONG (`DR-IQ-01`: không có bằng chứng lợi thế).
Đó đúng là hình dạng mà `DR-HUONG-01` §3 viết trước để chặn.

**Vì sao vẫn an toàn:** thứ bị chặn là **chọn phép đo sau khi thấy kết quả** — mỗi phép đo là một lần thử, và
chọn phép đo tiếp theo theo kết quả phép đo trước là cách "vườn lối rẽ" thổi phồng tỉ lệ dương tính giả. Viết
code **không phải phép đo**: không sinh con số hiệu năng nào, không tiêu suất nào, không làm ai biết thêm gì về
lợi thế của Short. Mọi thứ có thể bị dẫn dắt bởi kết quả Long đều nằm ở D-đo, và D-đo vẫn khoá.

**Rủi ro còn lại, không giả vờ là không có:** code Short có sẵn làm việc *"bật thử Short"* rẻ đi, tức cám dỗ
tăng. Đối trọng là máy, không phải lời hứa: `L-Z56` (không sửa) từ chối ablation khi `enable_short: true` mà
thiếu Δ_R(SHORT) `ok`; `TD-0321` thêm một test ghim `enable_short: false` mà dòng assert nêu đích danh DR này.
Đổi giá trị đó ⇒ phải sửa một dòng có nhắc tới quyết định, không phải một hằng số vô danh.

**Được gì:** khi điều kiện D-đo đạt, Short đo được ngay thay vì chờ 3–5 phiên viết code. Và việc soát đường
Short đã bắt được một lỗi thật (§5).

## 4. Hệ quả của "một bot, hai chiều" — khai trước

- **Futures one-way:** Freqtrade chỉ hỗ trợ một vị thế mỗi cặp. Cặp đang mở Long thì tín hiệu Short trên cặp
  đó bị bỏ, và ngược lại. Không có hedge trên cùng cặp.
- **Chung trần rủi ro và `E_D`:** định cỡ (`sizing.py`), số lệnh tối đa cùng lúc, thang drawdown áp chung cho cả
  hai chiều — không có ngân sách vốn riêng cho Short.
- **Bất đối xứng của spec §3.3d vẫn là việc của D-đo:** funding (DG7 ngưỡng riêng), biến động nền (DG6-A
  calibrate riêng), short squeeze (DG6-D). D-dựng chỉ **nối** DG6-D và dùng DG7 hiện có (trung lập hướng qua
  `trade.funding_fees` có dấu); **không** calibrate ngưỡng nào cho Short.

## 5. Phạm vi (Khối 28 của `TASKS.md`)

| Việc | Nội dung |
|---|---|
| `TD-0318` | DR này |
| `TD-0319` | Module thuần nhận `huong` (mặc định `"long"`): `trade_plan.py`, `arm_switches.py`, `take_profit.py`. `KeHoachTranche` **không** thêm trường; hướng đọc từ `trade.is_short` |
| `TD-0320` | (a) 🐛 `entry_confirmation.py:379` — với `loai="dinh"` vòng quét cụm tìm giá **thấp** nhất thay vì **cao** nhất ⇒ mốc so phân kỳ (nhánh b) sai cho zone đỉnh. Lỗi code ≠ spec, `DR-012` Hạng 1, 0 trial. Đường Long chỉ gọi `loai="day"` (`ZoneAbsorption.py:510`) ⇒ không ảnh hưởng Long; **có** ảnh hưởng phễu `do_short_pheu_tin_hieu_explore.json` — ghi chú, **không chạy lại** (chạy lại = D-đo). (b) DG6-D đọc `tier_b.funding_rate_pct` qua `resolve()` và **chia 100** (YAML ghi phần trăm, hằng cũ ghi tỉ lệ — bẫy ×100) |
| `TD-0321` | Đường Short trong `ZoneAbsorption.py`: quét zone một lõi tham số `loai`; §3.3b gương (kể cả chặn đóng-xuyên-SL `TD-0294`); `enter_short` lọc `DOWN`; hai chiều gated bởi `tier_a.enable_*` + chốt kép ở `confirm_trade_entry`; `can_short = True`; tag thêm khoá hướng **chỉ** cho Short; đảo mọi so sánh callback theo `trade.is_short`; DG1–DG6 nhận hướng thật |
| `TD-0322` | *(tuỳ)* bộ đo DR-015 sẵn hướng Short, **không chạy**; artifact niêm phong D3.5 không đổi byte |

## 6. KHÔNG làm (thuộc D-đo, ⏸)

- Đo Δ_R(SHORT) · calibrate DG7 / DG6-A cho Short · chạy ablation Short · lockbox Short (`TD-0276`) · chạy lại
  phễu tín hiệu Short · đổi `enable_short` thành `true`.
- **Không sửa** `tests/lock/test_lz56_*`, `src/tool_d/dr015/cong_d35.py`, `ZoneAbsorptionMinimal.py` (fixture
  `L-Z49`).
- **Không** đổi thứ tự ưu tiên của `DR-HUONG-01`: suất (d) vẫn là hướng chính; Khối 28 là việc hạ tầng song song.

## 7. Điều kiện dừng / đảo ngược (viết TRƯỚC)

- Đường Long lệch **một lệnh** (mã, giờ mở, số tranche, giờ đóng, lý do đóng) trên bất kỳ fixture hiện có nào
  ⇒ **dừng**, không merge, tìm nguyên nhân. Một test cũ phải sửa khẳng định mới xanh ⇒ cũng dừng, báo chủ dự án.
- Cần sửa `L-Z56` hay artifact niêm phong để đi tiếp ⇒ đó là D-đo lọt vào D-dựng ⇒ **dừng**.
- Code mới cần đọc một cột DB Freqtrade chưa có nghĩa duyệt trong `y_nghia_cot.py` ⇒ dừng (N13 mục 3, quy tắc 7).
  (`trades.is_short` đã có nghĩa — kiểm 18/09/2026.)

## 8. Việc giấy tờ còn treo

Ghi một mục `MT` vào `back-end-note.md` §7 trỏ về DR này (va chạm với `DR-HUONG-01` §3, giải bằng tách
D-dựng/D-đo) — chờ lệnh *"chuẩn hóa và lưu"* theo N9, không ghi ở đây. Nối một dòng đính chính trỏ về DR này
vào `DR-HUONG-01` §2 dòng D — cùng đợt đó.
