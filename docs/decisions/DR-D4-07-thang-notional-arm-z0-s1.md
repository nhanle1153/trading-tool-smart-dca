# DR-D4-07 — Thang notional của arm `Z0-S1`: khai bằng CÔNG THỨC, tham chiếu `R_eff = 3,0%`

> Quyết định của chủ dự án, 09/09/2026. Sinh từ phép quét 9 arm của phiên `-f4` trên tập
> EXPLORE (0 trial). Commit **RIÊNG và TRƯỚC** mọi dòng mã thi hành — tiền lệ DR-D4-02/03/05/06.
> Bằng chứng: `docs/du-lieu-do/dg2-explore-quet-arm.json` (48 mã EXPLORE, [T0,T2], `E_D = 750`).

## 1. Vấn đề

`config/tool_d_config.yaml → tier_c.arm_ablation.notional_co_dinh_usdt` là `null`. Arm `Z0-S1`
định cỡ theo VỐN nên `arm_switches.py:210` **raise** khi thiếu con số này. Đo thật: `Z0-S1` sinh
ra **0 lệnh** trên 48 mã EXPLORE trong 22 tháng.

Nếu D4 đặt chỗ 9 suất trial mà `Z0-S1` không chạy được thì **một suất trong 114 mua thông tin
bằng không**. Spec KHÔNG chốt con số (300 USDT ở dòng 1285 nằm trong một lập luận minh hoạ),
nên `DR-D4-04 §5` đã ghi *"chờ chủ dự án, không tự điền"*.

## 2. `Z0-S1` là dụng cụ chẩn đoán, không phải đề xuất giao dịch

Hệ thống định cỡ theo **rủi ro cố định**: `N_full = ρ × E_D / R_eff`. Điều đó chỉ đúng nếu
`R_eff` đo đúng; nếu `R_eff` sai hệ thống thì phép chia **khuếch đại** cái sai vào mọi lệnh.

`Z0-S1` cắt đứt phụ thuộc đó — cỡ lệnh không nhìn `R_eff`. Cách đọc (TD-0183):

- `Z0-S1` ngang hoặc hơn `Z0` ⇒ việc chia cho `R_eff` không mang giá trị ⇒ nghi `R_eff` đo sai
  (phân loại **L2**), **KHÔNG** phải kết luận *"vốn cố định tốt hơn"*.
- `Z0` hơn rõ ⇒ `R_eff` mang thông tin thật.

⇒ Con số notional **không cần tối ưu** (nó là nhóm đối chứng), nhưng **bắt buộc khớp thang**.
Lệch thang thì phép so trộn hai nguyên nhân: *cách tính cỡ lệnh* và *quy mô vị thế*.

## 3. Phép đo — và nó BÁC đề xuất đầu tiên của chính phiên đề xuất

Phân bố `R_eff` của **83 lệnh `Z0`** (EXPLORE 48 mã, `[T0, T2]`, `E_D = 750`). Đây là thống kê
**đầu vào** (độ rộng zone); **không có PnL nào trong phép tính**.

| min | P10 | P25 | median | P75 | P90 | max | mean | **harmonic mean** |
|---|---|---|---|---|---|---|---|---|
| 1,303% | 2,073% | 2,434% | **3,028%** | 3,580% | 4,066% | 6,589% | 3,091% | **2,868%** |

🔴 **Dải giả định "0,9–3,0%" dùng khắp các bảng phân tích trước đây KHÔNG khớp thực tế đo được.**
Median nằm ở **đỉnh** dải; 90% số lệnh có zone rộng hơn 2%; **zone 0,9% không xuất hiện lần nào**
(min = 1,303%). Hệ quả: `N_full` thật của `Z0` là **98,08 USDT** (trung bình) / 92,87 (trung vị).

Đề xuất đầu của phiên `-f4` là `R_ref = 1,5%` với lý do *"giữa dải vận hành"* — **sai**, vì dải đó
là con số viết lúc thiết kế, không phải đo được. Ghi lại ở đây vì đó là **cùng hình dạng lỗi** mà
`CLAUDE.md` đã ghi hai lần trong ngày: *một dòng viết lúc thiết kế trông giống một sự thật đo được*.

## 4. Nguyên lý chọn thang, và vì sao là trung bình ĐIỀU HOÀ

Muốn `Z0-S1` triển khai **cùng lượng vốn trung bình** với `Z0`:

```
N_fixed = E[N_full] = ρ × E_D × E[1/R_eff] = ρ × E_D / HM(R_eff)
```

Tham chiếu phải là **trung bình điều hoà**, không phải trung bình cộng, không phải "giữa dải" —
vì `N` tỉ lệ với `1/R_eff`, không tỉ lệ với `R_eff`.

Hệ quả bằng số (`ρ = 0,375%`, `E_D = 750`, ngân sách lỗ ngày 8%):

| `R_ref` | `N_fixed` | Rủi ro TB mỗi lệnh (Z0 = 0,375%·E_D) | Vị thế đồng thời tối đa |
|---|---|---|---|
| 1,50% (đề xuất đã bị bác) | 187,50 | **0,77% — gấp 2×** | ~10 |
| 2,868% (HM chính xác) | 98,08 | 0,404% (+8%) | ~20 |
| **3,00% (CHỐT)** | **93,75** | **0,386% (+3%)** | **~20** |
| 3,028% (median) | 92,87 | 0,383% | ~20 |

`R_ref = 1,5%` tạo **ba** confound cùng lúc: cỡ lệnh gấp đôi, rủi ro mỗi lệnh gấp đôi, và số vị
thế đồng thời **giảm một nửa** qua cổng kết nạp §6.8f. `Z0-S1` thua thì không ai phân biệt được
thua vì *cách tính* hay vì *bị bóp danh mục*.

## 5. QUYẾT ĐỊNH

**`notional_ref_r_eff = 0.03`**, đóng băng, khai bằng **công thức**:

```
notional_co_dinh = (rho_pct / 100) × E_D / notional_ref_r_eff
```

`notional_co_dinh_usdt` (con số cứng) **bị bỏ** — nó là đại lượng dẫn xuất.

**Vì sao 3,00 chứ không phải 2,868 (HM chính xác):** hai giá trị lệch **5%**, dưới sai số mẫu của
`n = 83` trên một tập không phải pool. Ghi `2,868` là **độ chính xác giả**. Thêm nữa, `3,0%` **đã
là mốc tham chiếu có sẵn** trong bảng sàn của `DR-D4-05` — dùng lại giữ cho cả repo nói một thứ tiếng.

**Vì sao CÔNG THỨC chứ không phải con số cứng** — bằng chứng có sẵn trong ngày: `E_D` vừa đổi
**500 → 750** (`DR-D4-05`). Nếu đã chốt `300` hồi `E_D = 500`:

| | `E_D = 500` | `E_D = 750` |
|---|---|---|
| Con số cứng 300 tương đương `R_ref` | 0,625% | 0,9375% |
| `Z0-S1` to gấp mấy lần cỡ TB của `Z0` | 2,4× | 1,6× |

Ý nghĩa của arm **tự đổi 50% mà không ai quyết gì**. Cùng họ với `E_D = 500` ghim cứng trong
docstring và `"2025-01-01"` ghim cứng trong test — hằng số đúng lúc viết, sai lặng lẽ về sau.

## 6. Vì sao lấy số từ dữ liệu ở đây KHÔNG vi phạm kỷ luật ngân sách

Ranh giới mà `N_ĐĂNG_KÝ` bảo vệ là: **không chọn cấu hình dựa trên KẾT QUẢ của nó**. Ở đây chỉ
dùng **phân bố đầu vào** (độ rộng zone) — không PnL, không expectancy, không so arm nào thắng.
Đây là *matched control* trong thiết kế thí nghiệm, cùng bản chất với cân bằng cỡ mẫu; nó **không**
mở rộng không gian tìm kiếm vì không có bước *"thử vài notional rồi chọn cái tốt nhất"*.

Tập EXPLORE được `DR-D0PRE-05 §4` cho phép **sinh giả thuyết, 0 trial** — và việc chọn thang cho
một nhóm đối chứng đúng là loại việc đó.

## 7. Kế toán DOF — `N` KHÔNG đổi

`notional_ref_r_eff` thuộc `tier_c.arm_ablation` (công tắc arm), **chưa từng** có mặt trong
`config/dof_inventory.yaml`. Theo tiền lệ `DR-D4-02` (ngưỡng 30% của DG5): **đóng băng một thứ
chưa từng được đếm thì không trừ gì**, `dof: 0` chứ không phải `-1`.

- `dof_goc` = **28** — không đổi
- `|tier_b|` = **12** — không đổi
- **`N_ĐĂNG_KÝ` = 114** — không đổi
- Rào DSR §10.2 = **3,0777** — không đổi
- Chi phí: **0 trial**

Bắt buộc thêm **một dòng** vào `dof_inventory.yaml` mục *không đếm vào dof gốc* — một hằng số
không được khai chính là lỗi mà `DR-D4-02` sinh ra để chặn.

## 8. Đổi về sau — câu trả lời viết TRƯỚC, không tranh luận lúc đang nhìn kết quả

| Đổi lúc nào | Chi phí | Đường hợp lệ |
|---|---|---|
| Trước khi `TD-0184` đặt chỗ | 0 trial | DR ngắn |
| Sau đặt chỗ, trước khi chạy | 0 trial, phải huỷ + đặt lại chỗ | DR + ghi sổ (`N` đã cam kết) |
| **Sau khi có kết quả** | 🔴 **tiêu trial** | Là **cấu hình mới**, không phải "sửa tham số"; bắt buộc qua sổ đề xuất `param_change_proposals.jsonl` / `L-Z26` |

Mốc thứ ba đắt chính là lý do phải đóng băng **ngay từ đầu và khai ra**, thay vì để một khoá
`null` không ai đếm — vì một khoá như thế mời đúng câu *"tại chọn hơi to, thử số khác xem"*, và
mỗi lần thử là một phép thử thật mà không suất trial nào bị trừ.

## 9. Điều kiện mở lại — viết TRƯỚC, khuôn OQ-07

`3,0%` đo trên EXPLORE, **không phải pool**. Mở lại DR này nếu:

1. Đo hợp lệ được phân bố `R_eff` trên pool 102 mã (vướng **MT-19** — cần quyết đường ghi sổ), **VÀ**
2. `3,0%` rơi **ngoài dải P25–P75** của phân bố pool đó.

Dùng phân vị của chính phân bố làm điều kiện, **không bịa một ngưỡng phần trăm** — cùng kỷ luật
§4 đã dùng ở `DR-015` Bước 4 (*"ngưỡng tuỳ tiện là chỗ uốn kết luận sau khi thấy số"*).

❌ **KHÔNG** phải điều kiện mở lại: `Z0-S1` cho kết quả kém. Đó chính là đổi cấu hình sau khi
nhìn kết quả.

## 10. Hạn chế phải ghi vào `d4_han_che`

- Thang notional của `Z0-S1` khớp với phân bố `R_eff` của **EXPLORE**, không phải của pool. Nếu
  pool có zone hẹp hơn hệ thống thì `Z0-S1` sẽ **nhỏ tương đối** so với `Z0` và phép so lệch
  theo chiều bất lợi cho `Z0-S1`.
- `Z0-S1` vào một lệnh notional 93,75 ⇒ ký quỹ **31,25** ở 3x ⇒ lề **4,2%** trên sàn live 30,00
  của BCH/ETC/LINK/LTC. Cùng lề mỏng mà `DR-D4-05 §2.2` đã ghi cho `Z0` — **không phải rủi ro
  mới**, nhưng có mặt ở cả hai vế của phép so.

## 11. Việc thi hành

1. `config/tool_d_config.yaml` — bỏ `notional_co_dinh_usdt`, thêm `notional_ref_r_eff: 0.03`.
2. `config/dof_inventory.yaml` — một dòng ở mục *không đếm vào dof gốc*, `dof: 0`.
3. `src/tool_d/arm_switches.py` — nhận giá trị dẫn xuất; giữ nguyên fail-closed (thiếu ⇒ raise;
   truyền cho arm rủi-ro-cố-định ⇒ raise).
4. `user_data/strategies/ZoneAbsorption.py` — tính `ρ × E_D / ref` thay vì đọc thẳng con số.
5. **Test khoá có răng:** notional **PHẢI đổi khi `E_D` đổi** (đó là toàn bộ lý do chọn công
   thức — một test chỉ kiểm giá trị hiện tại sẽ không bắt được việc quay lại con số cứng), và
   **KHÔNG được đổi khi `R_eff` đổi** (test hiện có của TD-0183, giữ nguyên).
6. **Chốt chống PASS RỖNG:** chạy lại `Z0-S1` trên EXPLORE và đòi **≥ 1 lệnh**. Trước bản vá nó
   ra 0 lệnh; một bản vá không kiểm điều này thì không có gì chứng minh nó đã sửa được thứ gì.
