# DR-HUONG-01 — Hướng chiến lược sau `DR-IQ-01`: suất (d) là hướng chính

> **Ngày chốt:** 18/09/2026 · **Người quyết:** chủ dự án (duyệt bản đánh giá tổng thể + phương án, phiên `-a2`)
> **Chi phí:** **0 trial** · Không gỡ ⏸ nào, không chạm dữ liệu, không chạm lockbox.
> Tên `DR-HUONG-01` đã nhắn `-2b`, `-9c`, `-2c` trước khi mở (N12 mục 6); `-2b` và `-9c` xác nhận không trùng; `-2c` chưa trả lời lúc commit (không có file `DR-HUONG*` nào trên đĩa).

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`: bịt mắt). File này do một
> phiên đã thấy số đo của Tool D soạn. Nó cố ý chỉ nói **dùng suất (d)**, không nói **tìm loại ý tưởng gì**.
> Danh sách file phiên sạch được đọc là danh sách CHO PHÉP trong `docs/mau-don-y-tuong.yaml` (`TD-0304`);
> file này không nằm trong đó, và không file nào trong danh sách đó được trích dẫn tới đây.

---

## 1. Tình trạng tại ngày chốt (chỉ trỏ nguồn, không chép lại)

| Mặt | Tình trạng | Nguồn |
|---|---|---|
| Hạ tầng đo | 5 cổng đóng (D0-PRE…D3.5); 4/114 suất đã tiêu (B0); lockbox chưa chạm; lõi bộ chạy + E1 có | `runtime_state.json`, `trial_registry.jsonl`, `DR-BC-01` |
| Zone Absorption LONG | Không có bằng chứng lợi thế; đang ⏸ | `DR-SONG-CON-01`, `td0291-song-con-explore.json`, `DR-IQ-01` §1 |
| Đi tiếp D4 | Gần như chắc chắn INCONCLUSIVE | `DR-IQ-01` §2.1, `DR-D4-12` §2 |
| Phần DCA | Ứng viên chỉ khớp tranche 1; đo DCA cần nhiều năm | `DR-D4-10`, `IQ-0001` |
| Suất (d) | Mở từ 01/10/2026, hạn ngạch 1; **chưa có ứng viên** | `DR-IQ-01` §3, `DR-Q4-2026` |

## 2. Quyết định

| # | Phương án | Chốt |
|---|---|---|
| **C** | Ý tưởng MỚI qua suất (d) | ✅ **HƯỚNG CHÍNH** |
| **A** | Chờ dữ liệu mới rồi đo lại ZA LONG | ▶ **giữ ở chế độ nền** — không tốn gì, điều kiện nối lại giữ nguyên chữ `DR-IQ-01` §1 |
| **B** | Gỡ ⏸, chạy D4 → D9 cho ZA LONG | ❌ **không làm** — ~36 suất để mua một kết cục gần như biết trước |
| **D** | ZA SHORT | ⏸ **không làm lúc này** — xem §3 |
| **E** | Tuyên bố L3, dừng dự án | ❌ **không làm** — số liệu nói *"không có bằng chứng lợi thế"*, không nói *"có bằng chứng không có lợi thế"*; spec cấm dùng EXPLORE làm phán quyết |
| F | Nới bộ lọc / chỉnh tham số ZA | ❌ **cấm**, không phải lựa chọn (`DR-IQ-01A` Z-5; spec §11b *"không có đường nào từ L3 về L1"*) |

**Vì sao C:** là đường spec thiết kế sẵn cho đúng tình huống *"ứng viên đầu tiên không cho thấy lợi thế"*
(§9c.7: *"chết có kiểm soát, có sẵn quy trình thay thế"*); dùng lại toàn bộ hạ tầng; không tiêu ngân sách
trial của ZA.

**Việc cho suất (d) đã có sẵn — trỏ, không mô tả lại:** mẫu đơn + danh sách file phiên sạch được đọc
(`TD-0304`, `d418443`); thông báo cửa nộp không in cứng quý/hạn ngạch (`TD-0315`, `dd3ff7c`); danh sách loại
trừ cơ chế (`DR-IQ-01A`). **Phiên IDEA sạch chưa được mở** — đó là việc của chủ dự án, không phải của phiên đã
đọc số.

## 3. Vì sao KHÔNG làm D (ZA SHORT) lúc này, và khi nào mở lại

D hấp dẫn vì hai lý do, và **cả hai đều đáng nghi**:
1. Nhiều tín hiệu hơn chiều Long ở cùng tầng lọc (`do_short_pheu_tin_hieu_explore.json`) — nhưng đó là số
   **tín hiệu**, chưa có một lệnh hay một đồng PnL nào.
2. 🔴 **Bẫy chế độ thị trường.** Kết quả của một chiều giao dịch trên CALIB có thể phản ánh **xu hướng của
   chính giai đoạn đó** chứ không phản ánh lợi thế (số đo hướng 1D tại nến xác nhận: `td0193-lenh-nam-explore.json`).
   Một chiến lược thắng vì ăn theo xu hướng sẽ thua khi xu hướng đổi.

Thêm: `DR-IQ-01` §1 chốt *"không có cả hai cùng lúc"* — không vừa thay ứng viên vừa giữ ứng viên cũ để dành.
D dùng chung cơ chế với chiều Long vừa cho ≈ 0.

**Điều kiện mở lại D** (viết TRƯỚC, bất đối xứng như `DR-IQ-01`):
- Ý tưởng qua suất (d) đã có **kết cục tại cổng của nó** (PASS / FAIL / INCONCLUSIVE), **và**
- một DR viết **TRƯỚC khi đo** Short, trong đó khai rõ cách tách lợi thế khỏi xu hướng của giai đoạn đo.
- 🔴 **KHÔNG phải điều kiện:** *"Long thất bại nên thử Short"*; *"Short nhiều tín hiệu hơn"*; thời gian trôi qua.
- Điều kiện kỹ thuật của `DR-D4-01` (DG7 riêng, Δ_R(SHORT), ≥ 9 suất) vẫn đứng nguyên, không thay bằng DR này.

## 4. Việc vẫn làm tiếp — HẠ TẦNG ĐO, không phải việc riêng của ZA

Đọc đúng `DR-IQ-01` §1 (dòng *"Hạ tầng đo … không phụ thuộc chiến lược"* ▶ giữ nguyên). Những việc dưới đây
**không** bị ⏸ bởi DR này, vì mọi chiến lược — kể cả ý tưởng chọn qua suất (d) — đều cần:
- `TD-0252` dữ liệu 5m cho CALIB trên rổ `T0` (✅ `f7a788e`).
- `TD-0314` nối hàm đo độ phủ khung chi tiết vào lõi bộ chạy.
- Khối 26 (rổ `T2`, vá `verify_seal`) theo đúng phạm vi `DR-LOCKBOX-01` §4.
- Nợ trước go-live (`TD-0277`), Risk Supervisor, đường D10–D12.

## 5. Lockbox của ứng viên suất (d) — ĐÃ có lập trường; câu còn mở thật nằm ở chỗ khác

> 🔴 **ĐÍNH CHÍNH 18/09/2026 — bản commit đầu của mục này SAI ở hai chỗ, phiên `-2b` bắt, đã kiểm trên đĩa.**
> Chữ cũ giữ nguyên trong khối trích dưới đây làm lịch sử.
>
> 1. Tiền đề *"`DR-LOCKBOX-01` đã dành seal 1 cho lần chạm của ZA"* **sai**: DR đó không nhắc Zone Absorption lần
>    nào (grep chuỗi cố định: "Zone" 0, "ZA " 0, "LONG" 0; `TD-0274` chỉ ghi *"không thuộc DR này"*). Nó quy định
>    **rổ** nào và **cách niêm phong lại**, không gán lockbox cho chiến lược nào.
> 2. Câu *"ứng viên mới có được dùng seal 1 không"* **không còn mở**: `DR-IQ-01:86` đòi ứng viên chọn qua (d) có
>    *"lockbox MỚI trên dữ liệu chưa từng dùng"*; `DR-IQ-01:125-126` ghi *"Lockbox cho ứng viên mới chưa tồn tại:
>    dữ liệu sạch sau `T3 = 2026-09-06` … cổng lockbox của nó sớm nhất vài quý sau"*; spec §9c.7.5 (`:4134`):
>    *"Không dùng queue để né lockbox"*. Coi nó là câu mở là đặt `DR-HUONG-01` đứng khác `DR-IQ-01` ở cùng một
>    điểm. Lỗi đọc: viết từ bản phân tích của chính phiên này mà không mở `DR-IQ-01` §5.
>
> <details><summary>Chữ cũ (sai)</summary>
>
> ## 5. 🔴 Câu hỏi MỞ — KHÔNG chốt trong DR này
>
> **Một lockbox, hai bên muốn dùng.** Spec §9c.7.5: mỗi ứng viên được chọn cần *"một lockbox trên dữ liệu
> CHƯA TỪNG DÙNG"*. Lockbox hiện có (`lockbox_seal_1.json`, `[T2,T3]` = 29/01 → 06/09/2026) **chưa bị chạm lần
> nào** — nhưng `DR-LOCKBOX-01` đã dành nó cho lần chạm của ZA (`TD-0274`, qua seal cấp lại trên rổ `T2`). Một
> lockbox đã chạm thì hết.
>
> - Nếu ý tưởng mới **được** dùng seal 1 ⇒ nó chạy được đủ chu trình ngay, nhưng **ZA LONG mất lockbox của mình**:
>   phương án A khi đó phải chờ cả dữ liệu mới cho CALIB/WFO **lẫn** một lockbox mới.
> - Nếu **không** ⇒ ý tưởng mới cũng phải chờ dữ liệu sau `T3 = 06/09/2026`, như A.
>
> Đây là diễn giải luật về dữ liệu, cùng hạng với *"băm ≠ chạm"* (`DR-BC-01` §3). **Chủ dự án quyết**, và phải
> quyết **TRƯỚC khi có ứng viên nào được CHỌN qua suất (d)** — từ lúc biết ý tưởng là gì, câu trả lời có thể bị
> dẫn dắt bởi việc ý tưởng đó trông hứa hẹn hay không. *(Đính chính cùng ngày: bản commit đầu ghi "trước khi ý
> tưởng tới D8" — sai mốc, vì rủi ro dẫn dắt bắt đầu ngay lúc CHỌN, không phải lúc chạm lockbox.)* Đề xuất ghi thành một `OQ` trong `back-end-note.md` ở lần *"chuẩn hóa và lưu"* kế tiếp.
>
> </details>

**Lập trường giữ nguyên chữ `DR-IQ-01`:** ứng viên chọn qua suất (d) cần lockbox trên dữ liệu **sau `T3`**. Hệ
quả phải nói rõ: chu trình D0→D9 của ứng viên chạy được ngay từ khi chọn (dữ liệu `[T0,T2]` chưa từng dùng
cho *ý tưởng đó*), nhưng **cổng lockbox của nó sớm nhất vài quý sau**. Hướng C không có đường tắt tới tiền thật.

**Câu còn mở thật — nêu, KHÔNG chốt** (phiên `-2b` chỉ ra): **dữ liệu sau `T3` có hai bên cần**:
- điều kiện nối lại ZA LONG (`DR-IQ-01:43`: *"dữ liệu MỚI chưa từng dùng (sau `T3`)"*), và
- lockbox của ứng viên suất (d) (`DR-IQ-01:125`).

Dữ liệu đã dùng cho bên này thì hết với bên kia. `DR-IQ-01:47-49` cấm hai bên chạy **cùng lúc**, nhưng không nói
đoạn dữ liệu sau `T3` **thuộc về ai**. Theo quy tắc 11 đây là một chỗ hở giữa hai điều đã chốt ⇒ đề xuất ghi
thành một mục `MT` trong `back-end-note.md` ở lần *"chuẩn hóa và lưu"* kế tiếp. **Chủ dự án quyết**, và nên
quyết **trước khi có ứng viên nào được CHỌN qua suất (d)** — từ lúc biết ý tưởng là gì, câu trả lời có thể bị
dẫn dắt bởi việc ý tưởng đó trông hứa hẹn hay không.

> ✅ **QUYẾT ĐỊNH 18/09/2026 — chủ dự án chốt, đóng câu hỏi mở ở trên.**
>
> **Mặc định:** dữ liệu mới sau `T3` tính cho điều kiện nối lại ZA LONG (`DR-IQ-01:43`).
>
> **Nhường:** ngay khi một ý tưởng được **CHỌN** qua suất (d) — mốc là lúc `selected_at` được ghi vào
> `idea_queue.jsonl`, KHÔNG phải lúc nộp đơn hay lúc lọt vòng lọc sơ bộ — dữ liệu mới **từ thời điểm đó
> trở đi** chuyển sang tính cho lockbox của ý tưởng đó, cho tới khi ý tưởng có kết cục tại cổng của nó
> (PASS/FAIL/INCONCLUSIVE) hoặc bị rút. Sau đó, dữ liệu mới **trả lại** mặc định cho ZA LONG.
>
> **Vì sao phương án này, bằng hậu quả kinh doanh chứ không chỉ kỹ thuật:** không có khoảng trống chết.
> Ngay lúc chốt, Idea Queue chỉ có `IQ-0001` (đã bị loại khỏi suất (d), thuộc Z-2) — tức suất (d) hiện
> KHÔNG có ứng viên. Nếu mặc định dữ liệu mới thuộc về suất (d), toàn bộ thời gian không ai nộp ý tưởng
> sẽ là thời gian chết cho cả hai bên. Mặc định về ZA LONG thì đồng hồ tái kích hoạt vẫn chạy trong lúc
> chờ, và chỉ nhường khi có một ý tưởng THẬT được chọn — lúc đó ý tưởng mới không phải cạnh tranh với
> một chiến lược đang đứng yên không làm gì.
>
> **Hệ quả phải khai rõ, không để ngầm:** trong khoảng thời gian ý tưởng (d) đang "giữ" dữ liệu, đồng hồ
> tái kích hoạt ZA LONG (`DR-IQ-01` §1) **không cộng dồn thêm** — đúng khuôn *"không có cả hai cùng lúc"*
> (`DR-IQ-01:47-49`) — dù về mặt kỹ thuật ZA LONG không "chạm" gì trong lúc đó. Nếu ý tưởng (d) kéo dài
> nhiều quý (`DR-IQ-01:125-126`: *"cổng lockbox của nó sớm nhất vài quý sau"*), ZA LONG có thể phải chờ
> tương ứng nhiều quý mới có dữ liệu mới tiếp theo tính cho nó — đây là giá đã biết trước, không phải
> hệ quả bất ngờ phát sinh sau này.
>
> **Việc còn treo, không thuộc DR này:** ghi mục `MT-62` vào `back-end-note.md` tham chiếu quyết định này
> — chờ lệnh *"chuẩn hóa và lưu"* theo N9, không tự ghi ở đây.

## 6. Điểm yếu, khai thẳng

- DR này do một phiên **đã thấy số** soạn — đó là lý do §0 cấm phiên IDEA/CHỌN đọc nó, và lý do nó không nêu
  hướng ý tưởng nào.
- Phương án được đánh giá bằng số đo trên **EXPLORE**, không phải pool, không phải phán quyết. Chọn C là chọn
  **quy trình**, không phải kết luận rằng ZA không có lợi thế.
- Con số *"~1,5 năm dữ liệu mới để thu hẹp khoảng tin cậy xuống ±0,1 R"* dùng để so phương án A là **tính tay**
  (n ≈ (1,96 × 1,14 / 0,1)² ≈ 500 lệnh, ở ~335 lệnh/năm quy đổi pool), không phải phép đo.
- Suất (d) hết hạn **31/12/2026** nếu không có ứng viên. Hướng C thất bại theo cách đó thì quay về A; **không**
  quay về B, D, hay F.
