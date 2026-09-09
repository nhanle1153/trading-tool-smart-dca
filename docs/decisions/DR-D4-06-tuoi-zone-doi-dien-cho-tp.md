# DR-D4-06 — Tuổi của zone đối diện dùng làm TP1: KHÔNG áp hạn dùng §1.3

> Quyết định của chủ dự án, 09/09/2026. Sinh từ TD-0189 chặng 2 (phiên `-2f`) + phép đo mô tả
> của phiên TD-0171. Commit **RIÊNG và TRƯỚC** mọi dòng mã thi hành — tiền lệ DR-D4-02 / 03 / 05.
> Bằng chứng: `docs/du-lieu-do/do_tuoi_zone_dinh_explore.py` (tập EXPLORE, 0 trial).

## 1. Vấn đề — một mâu thuẫn NỘI TẠI của spec, nay định lượng được

`_quet_zone_dinh` truyền `tuoi_nen=K_XAC_NHAN` (hằng **3**) vào `zone_hop_le`, mà ngưỡng là
`tuoi_nen <= 40`. `3 <= 40` **luôn đúng** ⇒ vế hạn dùng §1.3 **không bao giờ chặn được gì** trên
đường TP, trong khi zone đỉnh được tiêu thụ ở **bất kỳ lúc nào về sau**, không phải tại nến xác nhận.

🔑 **Hình dạng lỗi mới của dự án:** *cùng một dòng `zone_hop_le` ĐÚNG ở bên đáy và RỖNG ở bên đỉnh.*
Phép đối xứng gãy ở **"khi nào zone được TIÊU THỤ"**, không ở "zone được NHẬN thế nào" — bên đáy tiêu
thụ ngay tại nến xác nhận nên tuổi thật đúng bằng 3. Bản gốc **không hề sai**; lỗi sinh ra lúc chép
vòng lặp sang ngữ cảnh khác và thừa hưởng một giả định ngầm.

Nhưng khi định lượng thì lộ ra vấn đề lớn hơn nhiều một chốt rỗng. Đo trên **tập EXPLORE** (100 mã
4H, 213.839 nến, 0 trial — đường vòng hợp lệ theo MT-19 / `DR-D0PRE-05` §4):

| Tầm tìm zone (`4 × R_eff`) | Zone gần nhất **quá hạn 40 nến** | Nạng **nếu KHÔNG lọc** | Nạng **nếu LỌC** |
|---|---|---|---|
| ≤ 4% | 74,6% | 48,0% | **86,8%** |
| ≤ 8% | 73,6% | 31,4% | **81,9%** |
| ≤ 12% | 73,3% | 22,7% | **79,4%** |

Tuổi zone gần nhất (tầm 8%): **trung vị 169 nến 4H (~28 ngày)** · P90 1.078 · max 3.856.

🔴 **Hai câu trong spec không thể cùng đúng trên dữ liệu thật:**

- **§1.3** — zone chết sau 40 nến 4H (~6,7 ngày).
- **§5.1 + dòng 1684** — zone đối diện là **luật**, nạng là **ngoại lệ**; nạng > 40% ⇒ tiền đề
  *"luôn tìm được zone đối diện trong khoảng cách hợp lý"* **SAI** ⇒ phân loại **L2**.

Tiền đề của §5.1 **chỉ sống sót nếu dùng những zone mà §1.3 tuyên bố đã chết**. Ghi vào mục 7 của
`back-end-note.md` theo quy tắc 11 — **không tự chọn một bên rồi code tiếp**. Cả bản vá `5e70781`
lẫn bản trước nó đều là "tự chọn một bên", chỉ khác bên.

## 2. Quyết định — phương án B: KHÔNG áp hạn dùng, nhưng ĐO tuổi

Zone đỉnh dùng làm TP1 **không** bị lọc theo hạn dùng 40 nến của §1.3.

**Căn cứ, và nó không phải "B tiện hơn":** con số 40 nến được chọn cho **zone VÀO LỆNH** — nơi hệ
thống đang cược rằng *lực hấp thụ đang diễn ra ngay lúc này*. Zone dùng làm **mục tiêu chốt lời**
không mang khẳng định đó; nó chỉ là *nơi giá từng phản ứng*. Bê một ngưỡng ra khỏi ngữ cảnh nó được
chọn là động tác **cũng thiếu căn cứ** như bỏ qua nó — nhưng áp nó biến một **chẩn đoán** thành một
**kết luận biết trước**.

**Trớ trêu quyết định:** nạng là `p_avg + 1.5 × R_eff`, tức **một bội số R cố định** — đúng thứ §5.1
dòng 1653 viết ra để **bác bỏ** (*"R-multiple cố định giả định biên độ kỳ vọng như nhau ở mọi
lệnh"*). Áp §1.3 ⇒ 80% lệnh dùng đúng cái TP mà thiết kế đã loại ⇒ D4 tiêu 9 suất trial để đo một
hệ thống khác hệ thống spec mô tả (đúng hình dạng MT-16 / MT-17).

**Giá của phương án A, tính bằng tài nguyên thật:** nạng 80–87% ⇒ H-4 vượt 40% gần như chắc chắn ⇒
**L2**, mà `§11b.1` + DR-012 định giá L2 = **1 suất Ngân sách A + một lockbox MỚI**. Ngân sách A là
5 suất/quý **dùng chung Tool A + D** (MT-11); lockbox hiện tại **chưa chạm lần nào** và chỉ được
chạm **đúng một lần** (D9.5). L2 cũng nằm trong ba điều kiện buộc mở lại hạn ngạch mà `DR-Q3-2026`
đã cố ý đặt **bằng 0** cho quý này.

🔴 **B KHÔNG mua một điểm đậu.** Ở dải 4% nạng vẫn **48%**, vẫn vượt 40% — B **có thể vẫn** dẫn tới
L2. Cái B mua là: nếu L2 xảy ra thì đó là **kết luận rút từ dữ liệu**, không phải hệ quả của một
ngưỡng ta tự áp sai ngữ cảnh.

### Phương án bị loại, có lý do

- **A — áp hạn dùng 40 nến:** xem giá ở trên. Nếu chọn A thì hệ quả đúng đắn là **DỪNG D4 và thiết
  kế lại tầng TP**, không phải chạy D4 rồi mới "phát hiện" điều đã biết trước.
- **C — hạn dùng RIÊNG cho TP (ví dụ 200 nến):** **+1 bậc tự do ⇒ N 114 → 120, rào DSR +0,54%,
  tiêu 6 trial**, và con số phải bịa vì chưa có dữ liệu nào đỡ. Bị loại vì **đắt và sớm**, không
  phải vì sai — nếu ràng buộc 1 dưới đây cho thấy tuổi có ảnh hưởng thật thì C là đường quay lại.

## 3. Năm ràng buộc — B chỉ hợp lệ khi có ĐỦ

1. **Ghi `tp_zone_age_bars` vào Decision Log mỗi lệnh.** Biến *"zone cũ có tệ hơn không"* từ tranh
   luận thành số đo được **sau** D4, **0 trial** (đọc lại dữ liệu D4 đã có).
2. **Tách H-4 làm HAI số:** nạng vì *không có zone nào* / nạng vì *zone quá hạn*. Ngưỡng 40% khi đó
   được đánh giá trên **đúng mẫu số** mà spec viết về nó.
3. **DR này commit TRƯỚC mọi dòng mã thi hành** (đang làm).
4. **MT ghi mâu thuẫn §1.3 ↔ §5.1** vào mục 7 `back-end-note.md`, phân loại 🔴, **không chốt bên
   nào đúng** — quy tắc 11.
5. **Đóng băng zone TP đã chọn tại lúc VÀO LỆNH** (ghi `custom_data`), chỉ tính lại TP1 khi `p_avg`
   đổi, tức khi tranche 2/3 khớp. **Ràng buộc này áp dụng DÙ chọn A hay B** — nó sửa một lỗi khác:
   lọc tuổi chạy ở thời điểm xét TP thì cửa sổ **trượt**, zone hết hạn **giữa lúc lệnh đang mở**, và
   TP1 nhảy từ zone sang nạng **do đồng hồ chứ không do giá**. TP1 theo zone nằm trong `(0 … 3,2 R]`
   còn nạng là **đúng 1,5 R**, nên cú nhảy đi **cả hai chiều**: xuống thì có thể kích hoạt thoát lệnh
   gần như tức thì, lên thì mục tiêu chạy xa ra sau khi lệnh đã được định cỡ theo kỳ vọng khác.
   Đóng băng đúng kỷ luật đã có ở ba chỗ khác: `sl_immutable: true`, `KeHoachTranche` (L-Z49),
   `N_full` chốt một lần ở tranche 1.

## 4. Điều kiện mở lại — viết TRƯỚC (khuôn OQ-07)

1. 🔑 **Phép kiểm chính, 0 trial:** sau D4, tách kết quả theo `tp_zone_age_bars`. **Nếu lệnh dùng
   zone > 40 nến có hiệu quả tệ hơn rõ rệt lệnh dùng zone mới** ⇒ §1.3 đúng cả cho TP ⇒ **quyết định
   này SAI**, quay về A và chấp nhận L2. Đây là cách tự bác bỏ đã cài sẵn, không phải lời hứa.
2. H-4 (vế *"không có zone nào"*, sau khi tách theo ràng buộc 2) **vẫn > 40%** ⇒ tiền đề §5.1 hỏng
   **độc lập với chuyện tuổi** ⇒ L2 theo đúng spec, và lần này là kết luận rút từ dữ liệu.
3. Pool đổi sang nhóm mã có phân bố giá/biến động khác hẳn ⇒ phân bố tuổi zone phải **đo lại**.

## 5. Cái quyết định này KHÔNG giải quyết

- ❌ **Không** trả lời *zone cũ có tệ hơn zone mới không* — nó **dựng phép đo** cho câu đó.
- ❌ **Không** xoá nguy cơ L2 (xem mục 2).
- ❌ Bằng chứng đo trên **EXPLORE, không phải pool** (MT-19 chặn đường pool), và đếm theo **nến,
  không theo lệnh**. Cỡ hiệu ứng lớn (73% so với ngưỡng 40%, không sát biên) nên tin được **chiều**
  và **bậc độ lớn**, không tin con số lẻ. Sai số nghiêng **về phía** kết luận này: điều kiện vào lệnh
  đòi trend UP, mà trend UP thì giá phá đỉnh cũ ⇒ đỉnh còn nằm trên giá càng dễ là đỉnh CŨ ⇒ tính
  theo lệnh thì tỉ lệ quá hạn **xấu hơn**, không tốt hơn.
- ❌ **Không** đụng tới rủi ro mỗi lệnh. Cả A lẫn B đều không đổi cắt lỗ; đây thuần tuý là câu hỏi
  *chốt lời ở đâu*.
- ❌ **Không** phủ hướng SHORT (D4 đợt này chỉ LONG — DR-D4-01).
