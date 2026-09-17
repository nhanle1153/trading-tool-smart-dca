# DR-IQ-01 — Tạm dừng tiêu suất Zone Absorption LONG + đường thoát (d) cho cửa chọn Idea Queue

> **Ngày chốt:** 17/09/2026 · **Người quyết:** chủ dự án (phân tích tổng thể sau cổng sống còn, phiên `-33`)
> **Căn cứ:** TD-0291 (`a634702`) ra **luật 4** của `DR-SONG-CON-01` §8 · **Giải:** `MT-57` · **0 trial**
> **Mở lại:** `DR-Q3-2026` §2 câu *"Không cái nào xảy ra → quý sau MẶC ĐỊNH lại là 0. Không phải quyết định lại"*
> — bằng điều kiện (d) dưới đây, thi hành qua file tiêu chí `DR-Q4-2026-tieu-chi-chon-y-tuong.md`.
> Commit RIÊNG và TRƯỚC mọi đơn CHỌN dùng nó. Mã `DR-IQ-01` · `MT-57` · `MT-58` · `TD-0295…0297` đã nhắn
> `-01`/`-30` trước khi ghi (N12 mục 6).

---

## 0. Kết quả dẫn tới DR này

`Z0-T1`, EXPLORE CALIB `[T0, T1)`, 65 mã, 162 lệnh (`td0291-song-con-explore.json`):

| Đại lượng | Giá trị |
|---|---|
| mean `R_trien_khai` sau phí | **−0,0015** |
| Khoảng tin cậy 95% | **[−0,177; +0,175]** |
| Mức cần để PASS `M` (N = 114) | **0,403** |
| Luật `DR-SONG-CON-01` §8 | **4 — KHÔNG TIÊU SUẤT lúc này, trình chủ dự án** |

Đọc đúng: **không có bằng chứng về lợi thế** — KHÔNG phải *có bằng chứng không có lợi thế* (khoảng tin cậy chứa 0
và chứa giá trị dương nhỏ). Một cấu hình chưa calibrate, dữ liệu 1H không có 5m, EXPLORE ≠ pool.

## 1. Quyết định 1 — tạm dừng tiêu suất, KHÔNG tuyên bố L3

| Hạng mục | Trạng thái | Lý do |
|---|---|---|
| TD-0184 bộ chạy ablation · cổng D4 (TD-0185/0186) | ⏸ **tạm dừng** | D4 gần như chắc chắn INCONCLUSIVE (§2.1) — 9 suất B2 mua một kết cục biết trước |
| D5 chạy B1 (TD-0258) · D9 (TD-0286…0288) | ⏸ **tạm dừng** | Phụ thuộc D4 |
| TD-0289 mã tiêu chí skewness (`DR-D9-02`) | ⏸ trả 🔓 | Chỉ có nghĩa khi đường ống chạy; `DR-D9-02` giữ hiệu lực |
| D6–D8 (Khối 20–22, `DR-D6D8-01`) | ⏸ **tạm dừng** (chủ dự án chốt trong kế hoạch phiên `-33`; phiên `-01` giữ khối sẽ trình xác nhận lại ở phiên mình trước khi ghi `TASKS.md`) · ✅ **ĐÃ XÁC NHẬN** ở phiên `-01`, 17/09/2026 (`c113567`, kèm TD-0261) | Riêng cho Tool D/Zone Absorption |
| TD-0247 rổ pool point-in-time | ▶ **làm tiếp phần rổ** | Không lệch sống sót, dùng lại cho MỌI chiến lược trên pool |
| TD-0247 phần *"đo lại phễu/n/lệnh-năm Z0-T1/Z0/Z0-T0/Z3 trên rổ mới"* | ⏸ **ĐỀ XUẤT tạm dừng — chờ chủ dự án xác nhận** (suy từ quyết định tạm dừng, không phải chốt tường minh; `-01` trình ở phiên mình) · ✅ **ĐÃ XÁC NHẬN** ở phiên `-01`, 17/09/2026 (`c113567`): bỏ khỏi TD-0247, chuyển sang TD-0184 khi nối lại | Đo riêng cho Zone Absorption — cùng lý do dòng đầu |
| Hạ tầng đo (sổ trial, lockbox, cổng, testnet/D10–D11, Risk Supervisor) | ▶ giữ nguyên | Không phụ thuộc chiến lược |
| TD-0292/0293 (CRLF, `git status` dưới tải) | ▶ làm | Hạ tầng dùng chung |

- **Không tuyên bố L3.** `DR-D4-13` §1.2 cấm dùng EXPLORE làm căn cứ phán quyết; và số liệu không nói "không có
  lợi thế". Không có phán quyết thì **không có** "dừng dự án" (§11b.1 L3).
- **Suất đo giữ nguyên:** `N = 114`, rào 3,0777, sổ trial 13 dòng, 0 suất tiêu thêm.
- **Nối lại đường ống — BẤT ĐỐI XỨNG, viết ngay bây giờ (phản biện #3 của `-30`):**
  - Chỉ khi có **dữ liệu MỚI chưa từng dùng** (sau `T3 = 2026-09-06`) đủ để một phép đo đổi kết luận, **kèm DR viết
    TRƯỚC khi đo**, và DR đó khai rằng Zone Absorption LONG là *giả thuyết đã có kết quả EXPLORE ≈ 0*.
  - 🔴 **KHÔNG phải điều kiện nối lại:** ý tưởng chọn qua (d) ra FAIL/INCONCLUSIVE; "đã hết ý tưởng khác"; thời
    gian trôi qua. Cấm tường minh con đường *"ý tưởng mới thất bại ⇒ quay lại calibrate ZA"* — đó là lối vòng
    §11b.1 chặn (*"không có đường nào từ L3 về L1"*) được mở bằng cửa sau.
  - 🔴 **Không có cả hai cùng lúc:** trong khi một ý tưởng (d) đang chạy chu trình, Zone Absorption LONG giữ tạm
    dừng — không song song vừa thay vừa giữ ứng viên cũ "để dành".

## 2. `MT-57` — ngõ cụt quản trị

### 2.1 Đường ống không bác bỏ được chiến lược

`DR-D4-12` §2: `Z0-T1` ở D4 ra FAIL chỉ khi `std_R ≤ 0,466`. TD-0291 đo `std_R = 1,14` ⇒ **D4 gần như chỉ có thể
ra PASS hoặc INCONCLUSIVE**; PASS cần `mean ≥ ~0,40 R`, EXPLORE đo ≈ 0 ⇒ INCONCLUSIVE gần như chắc chắn. Đi tiếp
D5 (≤ 16) và D9 (≤ 16) theo `DR-D4-12` §2.3 (INCONCLUSIVE vẫn mở D5) ⇒ tới ~41 suất, và phán quyết cứng đầu tiên
chỉ tới ở D9.5 LOCKBOX (DR-011: INCONCLUSIVE tối đa 2 gia hạn rồi FAIL mặc định) — nhiều tháng.

### 2.2 Cửa chọn ý tưởng khoá vĩnh viễn

`DR-Q3-2026` §2 mở cửa chọn chỉ khi: (a) `mult_edge = 0.5` trên 50 lệnh **live** · (b) phán quyết **L2/L3**
chính thức · (c) **B3 cạn**. Ngày 17/09: chưa có lệnh live (a không thể), §2.1 ⇒ không có phán quyết (b không
tới), B3 0/20 (c không). *"Quý sau MẶC ĐỊNH lại là 0."*

⇒ **Ứng viên duy nhất không cho thấy lợi thế, nhưng hệ thống không có đường nào để khai tử nó hay thay nó.** Một
bộ quy tắc không có lối ra cho đúng tình huống §9c.7.2 sinh ra để xử lý (*"có sẵn quy trình khai tử + thay thế
[…] thay vì phải nghĩ vội lúc đang thua"*) — đó là khoảng hở, không phải kỷ luật.

## 3. Quyết định 2 — điều kiện (d)

```
(d)  Cổng sống còn (DR-SONG-CON-01 hoặc DR kế nhiệm viết TRƯỚC khi đo) ra luật 2 (DỪNG) hoặc luật 4
     (KHÔNG TIÊU SUẤT), VÀ chủ dự án xác nhận tạm dừng bằng một DR
     ⇒ mở cửa chọn ĐÚNG 1 suất Ngân sách A, từ quý kế tiếp sau DR xác nhận.
```

- **Hiệu lực từ 01/10/2026** (quý 4) — `DR-Q3-2026` là append-only, *"sửa giữa quý chỉ có hiệu lực từ quý sau"*,
  và máy TD-0120 coi `SELECTED` trong quý khai `HAN_NGACH_CHON: 0` là sổ bẩn. Thi hành bằng
  `DR-Q4-2026-tieu-chi-chon-y-tuong.md` với `HAN_NGACH_CHON: 1`.
- **Một lần cho một lần tạm dừng.** Dùng xong suất đó, quý sau trở về luật `(a)(b)(c)` cộng (d) chỉ khi có một
  cổng sống còn MỚI ra luật 2/4 cho ứng viên mới.
- **Tiêu chí xếp hạng KHÔNG đổi:** nội dung `TC-Q3-2026-01…04` chép nguyên sang `TC-Q4-2026-01…04` (máy TD-0120 đòi
  mã đúng quý). Thứ tự từ điển, không trọng số.
- **Ý tưởng được chọn vẫn phải:** qua cửa CHỌN (`tin_hieu` · `quy_tac` · `nguong_bac_bo` · `so_bien_the`, MT-12);
  có **lockbox MỚI** trên dữ liệu chưa từng dùng (DR-011, §9c.7.5); đi đủ chu trình từ D0; `hypothesis_slot = IQ-xxxx`.

### 3.1 Danh sách loại trừ cơ chế — viết TRƯỚC, không dựa vào so chữ

➡️ **Nguồn duy nhất: `DR-IQ-01A-danh-sach-loai-tru-co-che.md`** (Z-1…Z-5, gồm IQ-0001 thuộc Z-2; luật *"nghi ngờ ⇒ coi
như thuộc"*; không có máy canh). Suất (d) **KHÔNG** được dùng cho ý tưởng thuộc bất kỳ mục nào trong đó.

🔴 **Đính chính 17/09/2026 (cùng ngày, trước khi có đơn CHỌN nào):** bản commit `0db8587` đặt nguyên bảng Z-1…Z-5 ở
đây. Phiên `-30` chỉ ra: phiên CHỌN sạch (§3.2) phải mở file này để đọc bảng — tức phải **tự bỏ qua** §0/§2 có số
kết quả; ranh giới dựa vào thói quen đọc, không có máy giữ. Bảng được **chuyển nguyên văn** sang phụ lục không có số
(không chép sang hai nơi — một nguồn). Nội dung quyết định không đổi; bản cũ còn trong lịch sử git.

### 3.2 Tách KÍCH HOẠT khỏi CHỌN — DR-009 (phản biện #4 của `-30`)

- **KÍCH HOẠT** (cửa có mở không) được dẫn kết quả TD-0291 — việc của DR này, đã xong.
- **CHỌN** (ý tưởng nào) phải do một **phiên sạch** làm: `session_type = "IDEA"`, **chưa đọc** artifact TD-0291,
  §0 và §2 của DR này, hay bất kỳ kết quả backtest/WFO/ablation nào của Tool D (spec `:3108-3116`).
  `selection_reason` **không được** tham chiếu kết quả định lượng Tool D (§9c.7.4). Phiên `-33` và `-30` (đã thấy số)
  **không** sinh ý tưởng, **không** chọn.
- Phiên chọn chỉ cần đọc: `DR-Q4-2026-tieu-chi-chon-y-tuong.md`, `DR-IQ-01A-danh-sach-loai-tru-co-che.md` (cả hai không
  chứa số kết quả), và sổ `idea_queue.jsonl`. **Phiên chọn KHÔNG mở file `DR-IQ-01` này.**
- Hệ quả: giả thuyết *"sửa cấu trúc chốt lời/cắt lỗ"* dự kiến ở TD-0296 **bị huỷ** — nó sinh ra từ kết quả Tool D
  (`TOOL_D_RESULTS` ⇒ loại thẳng, spec `:3062`) và thuộc Z-4.

## 4. Điểm yếu — khai thẳng

**Điều kiện (d) được viết SAU khi đã thấy kết quả TD-0291.** Đúng hình thứ `DR-Q3-2026` §2 cảnh báo (*"lúc đang
thua là lúc bạn muốn thay nhất và tệ nhất trong việc quyết định thay"*). Ba điều giảm nhẹ, không xoá được điểm yếu:

1. **Chính cổng sống còn được viết trước** (`DR-SONG-CON-01` `dd76a61`, §8 `ed25bbd`) — (d) chỉ nối một kết quả đã
   định nghĩa trước vào cửa chọn, không tạo ra ngưỡng mới.
2. **Tiêu chí xếp hạng không đổi một chữ** — không có núm nào vặn theo các đơn đang nằm trong hàng chờ.
3. **Chỉ 1 suất, không tích luỹ, cần lockbox mới** — giá của một lựa chọn sai bị chặn ở một chu trình.

Phương án bị loại: *"chỉ nộp, chờ"* (cửa có thể không bao giờ mở ⇒ dự án đứng yên) · *"tuyên bố L3"* (trái
`DR-D4-13` và trái số liệu).

## 5. Ràng buộc thực tế phải biết trước

- **Lockbox cho ứng viên mới chưa tồn tại:** dữ liệu sạch sau `T3 = 2026-09-06` tích luỹ ~1 quý mỗi quý (spec câu
  hỏi mở #10). Chọn ý tưởng từ 01/10 thì chu trình D0 của nó chạy được, nhưng cổng lockbox của nó sớm nhất vài quý sau.
- **Idea Queue hôm nay có 1 đơn** (IQ-0001, thuộc Z-2 ⇒ bị loại khỏi suất (d)). ⇒ **Nếu không có phiên IDEA sạch
  nộp ý tưởng mới trước/trong quý 4, suất (d) không có ứng viên** và hết hạn cuối quý (không dồn).

## 6. Thi hành

| Mã | Việc |
|---|---|
| TD-0295 | DR này + `DR-Q4-2026-tieu-chi-chon-y-tuong.md` |
| TD-0296 | ❌ **Huỷ** — giả thuyết sinh từ kết quả Tool D (DR-009 `TOOL_D_RESULTS`) và thuộc Z-4 (§3.2). Ý tưởng mới do phiên IDEA sạch nộp — chủ dự án sắp xếp |
| TD-0297 | `MT-55` · `MT-57` · `MT-58` qua "chuẩn hóa và lưu" |
| (nhãn) | Ghi ⏸ + mốc DR này trên các dòng tạm dừng trong `TASKS.md` |
