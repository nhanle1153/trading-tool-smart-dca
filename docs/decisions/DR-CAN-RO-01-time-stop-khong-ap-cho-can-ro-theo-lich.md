# DR-CAN-RO-01 — Dải `TIME_STOP` của cổng thiết kế không áp cho chiến lược cân rổ theo lịch

> **Ngày chốt:** 24/09/2026 · **Người quyết:** chủ dự án (trả lời `MT-81`, hướng (c)) · phiên mã `12c579bc` thi hành.
> **Chi phí:** 0 trial. Không đổi `TIME_STOP_RATIO_BAND`, không đổi `N = 114`, không đổi rào DSR.
> Mã `DR-CAN-RO-01` + `TD-0397` đặt chỗ bằng commit `9ce15cd` (N12 mục 7c). Commit **RIÊNG và TRƯỚC** `TD-0398` (mã).

> 🔴 **PHIÊN IDEA/CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`).

---

## 1. Chỗ vênh (`MT-81`)

`TD-0375` (`src/tool_d/gates/exit_reason_thiet_ke.py`) chặn cứng suất đầu tiên của mọi slot `IQ-xxxx` khi tỉ lệ
`exit_reason == "TIME_STOP"` trên EXPLORE nằm ngoài `TIME_STOP_RATIO_BAND = (0.05, 0.25)`. Dải và phép kiểm sinh ra để
bắt một **cửa thoát theo thời gian (DG8) chết**: chiến lược vào lệnh chờ, có chốt lời/cắt lỗ theo giá, cộng thêm trần thời
gian giữ lệnh (`DR-PHAN-QUYET-01` §4.2).

`IQ-0003` là **rổ cân theo lịch**: vị thế đóng khi coin rời nhóm tại lần cân rổ hằng ngày, hoặc khi chạm stop thảm hoạ.
Không có chốt lời, không có trần thời gian giữ lệnh, nên **không có cửa DG8** nào để chết. Gắn nhãn thoát-khi-cân-rổ là
`TIME_STOP` thì tỉ lệ gần 100%, cổng chặn vì một lý do không tồn tại. Không gắn thì tỉ lệ 0%, cổng cũng chặn.

## 2. Quyết định

1. **Dải `TIME_STOP_RATIO_BAND` không áp cho chiến lược thuộc lớp `CAN_RO_THEO_LICH`.** Mọi slot khác giữ nguyên chặn
   cứng như `TD-0375`, từng chữ.
2. **Hiện vật EXPLORE vẫn bắt buộc** (`docs/du-lieu-do/<IQ-xxxx>-exit-reason-explore.json`, đã commit, khuôn `lenh_that`).
   Lớp `CAN_RO_THEO_LICH` được miễn **phép so dải**, không được miễn **phép đếm**: số đếm là thứ chứng minh lớp đã khai
   là thật.
3. **Nhãn thoát cân rổ là `CAN_RO`** — một nhãn **mới**, không mượn `TIME_STOP`. Mượn nhãn sẽ đổi nghĩa một đại lượng
   đang dùng khắp tầng đo (`chi_so_export.py`, bảng arm, `DR-ZA-01`).

## 3. Lối miễn phải hẹp — tiêu chí máy đọc được

Hiện vật được miễn dải **khi và chỉ khi** thoả **cả ba**:

1. **Khai lớp:** hiện vật có khoá `lop_chien_luoc: "CAN_RO_THEO_LICH"` và khoá `dr_thiet_ke` trỏ tới một file `.md` ngay
   trong `docs/decisions/`, **đã commit**, nhắc đích danh slot và `DR-CAN-RO-01`, và chứa khối máy đọc:

   ```
   <!-- DR-CAN-RO-01:LOP:BEGIN -->
   {"slot": "IQ-xxxx", "lop": "CAN_RO_THEO_LICH"}
   <!-- DR-CAN-RO-01:LOP:END -->
   ```

   `slot` trong khối phải trùng slot đang xin suất. Khối hỏng hay trỏ sai ⇒ từ chối, không quay về mặc định im lặng.
2. **Mọi lệnh thoát bằng lý do của lớp:** trong **mọi** arm của `lenh_that`, **mọi** khoá `exit_reason` thuộc tập
   `{"CAN_RO", "stop_loss", "stoploss_on_exchange", "force_exit"}`. `force_exit` là lệnh bị đóng khi backtest hết dữ
   liệu. Một nhãn nào khác (chốt lời, `custom_exit` khác, `roi`, `liquidation`, `TIME_STOP`…) ⇒ chiến lược **không phải**
   rổ cân theo lịch thuần ⇒ **không** được miễn, áp dải như cũ.
3. **Có cân rổ thật:** tổng `CAN_RO` trên mọi arm > 0. 0 lệnh `CAN_RO` ⇒ lớp đã khai không được chứng minh ⇒ từ chối
   (N6: không coi "không đo được" là đạt).

Vì sao đủ hẹp: một chiến lược kiểu ZA (có chốt lời, có DG8) sinh nhãn ngoài tập ở điều 2 nên không lọt được. Muốn lọt thì
phải bỏ hết cửa thoát theo giá, tức phải **thật sự** là rổ cân theo lịch. Lớp được khai trong một DR đã commit, không phải
trong mã.

## 4. Thi hành (`TD-0398`, cần "bắt đầu code")

- Sửa `kiem_exit_reason_thiet_ke()`: kiểm §3 trước phép so dải. Đạt §3 ⇒ bỏ qua phép so dải. Không khai lớp ⇒ hành vi
  `TD-0375` **không đổi một bit**.
- Hằng `EXIT_CAN_RO = "CAN_RO"` đặt cạnh `EXIT_TIME_STOP` (`chi_so_export.py`), không gõ chuỗi rải rác (MT-03).
- Test: (a) mọi ca cũ của `TD-0375` xanh không sửa khẳng định; (b) rổ khai đúng ⇒ qua; (c) mỗi điều §3 vi phạm riêng ⇒ đỏ;
  (d) phá thật: bỏ điều 2 ⇒ ca "chiến lược có chốt lời khai lớp rổ" phải đỏ.

## 5. Điểm yếu — khai thẳng

- Quyết định đến **sau** khi ứng viên cụ thể đã được chọn, và nó gỡ đúng cái cổng đang chặn ứng viên đó. Đối trọng: tiêu
  chí §3 viết theo **hình dạng lối thoát**, không theo tên ứng viên, và không nới gì cho chiến lược có cửa thoát theo giá.
- Rổ cân theo lịch mất một phép kiểm thiết kế. Phép kiểm tương đương cho lớp này (vd. vòng quay rổ quá cao làm phí nuốt
  lãi) **chưa có**; nếu cần, viết trong DR thiết kế D0 của ứng viên, trước suất đầu tiên.

## 6. Không thuộc DR này

- Không đổi dải, không đổi `DR-PHAN-QUYET-01`. Dòng đính chính trỏ về DR này nối cuối `DR-PHAN-QUYET-01` §4.2 cùng đợt
  "chuẩn hóa và lưu" ghi `MT-81` → ✅ đã thi hành.
- Không nói gì về cổng phán quyết D0.9: tiêu chí `time_stop_ratio` ở cổng đó (nếu áp cho ứng viên) là câu riêng, xử trong
  DR thiết kế D0.
