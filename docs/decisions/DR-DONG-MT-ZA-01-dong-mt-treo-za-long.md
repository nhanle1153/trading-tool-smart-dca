# DR-DONG-MT-ZA-01 — Đóng bảy dòng MT còn treo của Zone Absorption LONG, mỗi dòng có nơi nhận

> **Ngày chốt:** 25/09/2026 · **Người quyết:** chủ dự án (duyệt kế hoạch phiên mã `2d853646`) · **Chi phí:** 0 trial,
> không sửa mã, không chạm dữ liệu. Mã `DR-DONG-MT-ZA-01` + `TD-0424` đặt chỗ bằng commit `ef3be7d`.

> 🔴 **PHIÊN IDEA/CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`) — file nhắc kết cục của ZA LONG. Phần dành cho phiên đó được nối
> vào `DR-VONG-DOI-01` (§4 dưới), không chứa số hay kết cục.

## 1. Vì sao

`DR-TRIEN-KHAI-01` §3 điều 4: vào D12 cần **0 mục `MT` 🟡/🔴 còn mở**, đếm trên toàn `back-end-note.md` mục 7. Bảy dòng
`MT-30`, `MT-31`, `MT-34`, `MT-44`, `MT-55`, `MT-58`, `MT-64` sinh ra khi đường ống ZA LONG còn chạy và ghi *"chờ chủ dự
án"*. `DR-ZA-01` đã bác bỏ ZA LONG ở cấu hình đã đo (`retest_forbidden`) ⇒ không dòng nào còn chặn việc gì.

Đóng cả bảy bằng lý do *"không còn áp dụng"* là **sai ở năm dòng**:
- `trade_plan.py`, `sizing.py`, `ZoneAbsorption.py` vẫn là mã của **ZA SHORT** (`huong="short"`, `DR-SHORT-01`; đo ⏸ theo
  `DR-SHORT-03`) và của mọi arm DCA sau này ⇒ `MT-30`/`MT-55`/`MT-58` vẫn nằm trong mã đang sống.
- `MT-31`, `MT-34` là lỗi **phương pháp** — áp cho mọi ứng viên.
- `MT-44` ghi một sự thật của chính project: phần *"Smart"* (DG1–DG5) **chưa bao giờ được đo** trên arm ứng viên. Đóng mà
  không chuyển đi thì câu hỏi gốc biến mất khỏi sổ.

## 2. Quyết định

**Không nới luật đếm của điều kiện 4.** Việc thu hẹp điều kiện thành *"chỉ đếm MT của ứng viên sắp lên tiền"* bị bác, vì nó
mở ra một chỗ để tự phán xét dòng nào được đếm. Thay vào đó, đóng từng dòng và chỉ rõ **nơi nhận** của rủi ro còn sống:

| MT | Cách đóng | Nơi nhận | Đọc lúc nào |
|---|---|---|---|
| `MT-64` | **Đóng hẳn.** Lập luận *"D4 gần như không thể FAIL"* (`DR-IQ-01` §2.1) là căn cứ của quyết định TẠM DỪNG; kết cục thật của `DR-ZA-01` đã thay nó. Hai cách đọc (a)/(b) không còn quyết định gì | — | — |
| `MT-31` | **Đóng + bài học chung.** Một arm ablation phải chứng minh chỉ đổi đúng một biến, bằng tập lệnh giao với mốc so; arm làm đổi cỡ lệnh hoặc cổng kết nạp thì phải khai phạm vi *"hẹp, không ngoại suy"* | `DR-VONG-DOI-01` §7 điều 1 | DR thiết kế D0 của mọi ứng viên có nhiều arm |
| `MT-34` | **Đóng + bài học chung.** Phần thi hành đã có: rổ đúng thời điểm `config/pool_t0/t1/t2.yaml` (`TD-0247`, `DR-D1-03`). Luật chung: CALIB/WFO/lockbox dùng rổ đúng thời điểm, **không** dùng `config/pool.yaml` (rổ hôm nay, chỉ cho D10–D12) | `DR-VONG-DOI-01` §7 điều 2 | DR thiết kế D0; kiểm lại một lần khi một ứng viên (kể cả `IQ-0003` nếu nối lại) tiêu suất CALIB |
| `MT-44` | **Đóng + chuyển câu hỏi.** *"DG1–DG5 có giá trị không"* **chưa được trả lời**; đo được nó đòi một arm có tranche 2/3 và ràng buộc tần suất ghi ở `MT-44` | Điều kiện vào của `IQ-0001` (§3 dưới) | Khi `IQ-0001` được CHỌN |
| `MT-30` | **Đóng ở ZA LONG, chuyển thành điều kiện mở lại.** Lọc `> p_avg` bằng `p_avg` cũ ở `_zone_dinh_tren`; tách *"đóng băng danh sách"* (`DR-D4-06` §3, giữ) khỏi *"lọc sai thời điểm"* | §3 dưới | Trước suất đầu tiên của ZA SHORT hoặc của bất kỳ arm DCA nào dùng mã này |
| `MT-55` | **Như trên.** Arm vào lệnh một lần định cỡ theo `p_avg`/`N_full` của ba tranche. Nửa (i) đã đóng ở `TD-0294`; nửa (ii) còn | §3 dưới | Như trên |
| `MT-58` | **Như trên.** Không gì giữ thứ tự `p3 < p2 < p1` trong `trade_plan.tinh_ke_hoach`; chưa đo tần suất. Vẫn giữ lời cấm cũ: không lặng lẽ thêm `max`/đổi `p2` | §3 dưới | Như trên |

## 3. Điều kiện mở lại — nhận từ `MT-30`, `MT-44`, `MT-55`, `MT-58`

Áp cho: (a) suất đầu tiên của **ZA SHORT** (bổ sung vào điều kiện của `DR-HUONG-01` §3 và `DR-D4-01` §2b, không thay);
(b) suất đầu tiên của **`IQ-0001`** hoặc bất kỳ ứng viên nào có tranche 2/3 dùng `trade_plan.py`/`sizing.py`.

1. `MT-58`: chủ dự án chốt thứ tự tranche hợp lệ khi `close(C)` dưới điểm giữa zone (và chiều gương cho Short), bằng DR,
   **trước** khi viết mã; đo tần suất ca vi phạm trên EXPLORE (0 suất).
2. `MT-55` nửa (ii): chốt cách định cỡ cho arm không khớp đủ ba tranche, hoặc khai rõ đơn vị `R_trien_khai` là đơn vị phán
   quyết (như `DR-D4-12` §1).
3. `MT-30`: chốt có bỏ phép lọc `> p_avg` ở `_zone_dinh_tren` hay không; ghi trước rằng mọi số đo cũ dùng tập ứng viên TP1
   cũ không so sánh được với số mới.
4. `MT-44` (chỉ cho (b)): tờ chọn `IQ-0001` phải khai arm có tranche 2/3, và phép tính độ mạnh (`DR-VONG-DOI-01` §3) phải
   tính trên **số lệnh có khớp tranche 2/3**, không phải tổng số lệnh.

`registry/idea_queue.jsonl` **không** được sửa để ghi các điều kiện này (sổ chỉ nối thêm). Phiên thi hành CHỌN `IQ-0001`
đọc DR này trước khi ghi dòng `SELECTED`.

## 4. Thi hành

- `back-end-note.md` mục 7: nối cuối ô trạng thái của bảy dòng bằng *"✅ ĐÓNG 25/09/2026 — `DR-DONG-MT-ZA-01`, <cách
  đóng>"*. Chữ cũ giữ nguyên (cần lệnh *"chuẩn hóa và lưu"*, N9).
- `DR-VONG-DOI-01`: nối §7 (hai điều kiểm thủ tục, **không số, không kết cục**, để phiên IDEA/CHỌN vẫn được đọc file đó).
- `DR-SHORT-03`: nối một dòng trỏ §3 của DR này.

## 5. Không thuộc DR này

Không sửa mã. Không lật `DR-ZA-01`. Không đụng các MT khác còn mở (`MT-72`…`MT-89` và nhóm cũ). Dry-run ZA LONG (`TD-0423`)
vẫn chạy như cũ; nó là dry-run vận hành, không phải phép đo (`DR-TRIEN-KHAI-01` §4).
