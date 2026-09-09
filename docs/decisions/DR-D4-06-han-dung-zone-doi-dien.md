# DR-D4-06 — Hạn dùng §1.3 KHÔNG áp cho zone đối diện, và H-4 tách làm hai số

> Quyết định của chủ dự án, 09/09/2026. Sinh từ **TD-0189** (chốt lời PHẦN 5).
> Bằng chứng: phép đo của phiên `-94` trên tập EXPLORE (100 mã 4H, 213.839 nến, **0 trial** —
> đường vòng hợp lệ theo MT-19 / `DR-D0PRE-05` §4) + phễu quét zone đỉnh của phiên `-2f`.
> Commit **RIÊNG và TRƯỚC** mọi dòng mã thi hành — tiền lệ DR-D4-02 / DR-D4-03 / DR-D4-05.

## 1. Vấn đề — hai câu spec loại trừ nhau trên dữ liệu thật

TD-0189 dựng tầng chốt lời §5.1. TP1 = *"zone đối diện gần nhất… **cùng thuật toán Phần 1**"*.
Chiến lược trước đó **chỉ quét zone đáy** — không một dòng nào cho `loai="dinh"` — nên phải dựng
vòng quét đối xứng (`_quet_zone_dinh`, TD-0189 chặng 2a, `5e70781`).

Bản đầu của vòng quét đó mang một lỗ hổng thật, phiên `-94` bắt: **hạn dùng 40 nến của §1.3 không
có hiệu lực với zone đỉnh.** Cả ba chỗ gọi `zone_hop_le()` trong repo đều truyền
`tuoi_nen=K_XAC_NHAN` — hằng **3** — trong khi `NGUONG_TUOI_ZONE_TOI_DA = 40`, nên vế `3 <= 40`
**không bao giờ trả `False`**.

🔑 **Cùng một dòng `zone_hop_le` ĐÚNG ở bên đáy và RỖNG ở bên đỉnh.** Zone đáy được tiêu thụ NGAY
tại nến xác nhận nên tuổi thật đúng bằng 3; zone đỉnh được tiêu thụ **bất kỳ lúc nào về sau**. Phép
đối xứng gãy ở *"khi nào zone được TIÊU THỤ"*, không ở *"zone được NHẬN thế nào"* — chép nguyên
vòng lặp là thừa hưởng luôn một giả định ngầm mà bản gốc không hề sai.

**Nhưng vá nó lại làm lộ ra thứ lớn hơn.** Đo trên EXPLORE:

| | |
|---|---|
| Zone đỉnh gần nhất **quá hạn 40 nến** | **73–75%** số ca (tầm 4% / 8% / 12%) |
| Tuổi zone đỉnh gần nhất (tầm 8%) | trung vị **169 nến 4H ≈ 28 ngày** · P90 1.078 · max 3.856 |

| Tầm tìm zone | Tỉ lệ nạng TRƯỚC vá | Tỉ lệ nạng SAU vá |
|---|---|---|
| ≤ 4% | 48,0% | **86,8%** |
| ≤ 8% | 31,4% | **81,9%** |
| ≤ 12% | 22,7% | **79,4%** |

Spec dòng 1684 chốt: *nạng > 40% ⇒ tiền đề SAI ⇒ phân loại **L2***. Ở 79–87% thì **L2 là kết luận
biết trước**, không còn là phép đo.

🔴 **Và đây là chỗ trớ trêu quyết định vấn đề:** nạng chính là `p_avg + 1,5 × R_eff` — **một bội số
R cố định**. §5.1 dòng 1653 mang đúng tiêu đề *"Vì sao KHÔNG dùng TP theo R-multiple"*. Chạy D4 với
bản chặt là tiêu **9 suất trial không hoàn lại** để đo một hệ thống chốt lời bằng đúng cái cơ chế
mà thiết kế viết ra để loại bỏ.

⇒ **§1.3** (zone chết sau 40 nến) và **§5.1** (zone đối diện là LUẬT, nạng là NGOẠI LỆ) **không thể
cùng đúng trên dữ liệu thật.** Đây là mâu thuẫn nội tại của spec, không phải lựa chọn cài đặt.
Ghi thành **MT-20** theo quy tắc 11.

## 2. Quyết định

### 2.1 §1.3 KHÔNG áp cho zone đối diện (chốt)

`_zone_dinh_tren()` **không lọc theo tuổi**. Zone đỉnh hợp lệ theo §1.1/§1.2/§1.3 *trừ vế hạn dùng*.

🔴 **Nói thẳng cái giá:** vế `tuoi_nen ≤ 40` của §1.3 **không có hiệu lực** trên nhánh zone đối
diện. Đây là điều `-94` gọi đúng tên là PASS RỖNG ở bản trước bản vá. Phân biệt then chốt, và nó là
lý do quyết định này hợp lệ còn hiện trạng cũ thì không:

> **Một luật không áp dụng vì có người QUYẾT ĐỊNH thế thì không phải chốt rỗng.
> Chốt rỗng là luật trông như đang áp mà cấu trúc không cho nó đỏ.**

Trước DR này: luật *trông như* đang áp, không ai biết nó không thể đỏ. Sau DR này: luật **được khai
là không áp**, có lý do, có điều kiện xét lại, và có một con số đo riêng cho đúng phần bị bỏ.

### 2.2 H-4 tách làm HAI số (chốt)

| Số | Đếm ca | Nói lên điều gì |
|---|---|---|
| `h4_nang_khong_co_zone` | không zone đỉnh nào trong `4.0 × R_eff` | thị trường thiếu cấu trúc đối diện — **đúng tiền đề §5.1 đặt cược** |
| `h4_nang_zone_qua_han` | có zone trong tầm nhưng quá 40 nến | **chính sách của ta**, KHÔNG phải sự thật thị trường |

**Ngưỡng 40% ⇒ L2 của spec dòng 1684 áp cho số THỨ NHẤT.**

🔑 **Vì sao tách, và vì sao nó đúng bất kể bên nào thắng.** Đọc lại nguyên văn tiền đề H-4 canh:

> *"luôn tìm được zone đối diện trong **KHOẢNG CÁCH** hợp lý"* — dòng 1684

Tiền đề là về **khoảng cách**, không phải về **tuổi**. Gộp tuổi vào cùng con số là **đổi ý nghĩa
phép đo mà giữ nguyên ngưỡng viết cho ý nghĩa cũ** ⇒ phán quyết L2 sẽ nổ vì một lựa chọn cấu hình
của chính chúng ta, không phải vì thị trường. Đúng họ lỗi dự án sợ nhất — một phép kiểm trả lời câu
**khác** câu người đọc tưởng, ở đây theo chiều báo động giả.

### 2.3 Tuổi zone GHI VÀO Decision Log cho mọi lệnh dùng TP-theo-zone (chốt)

Không có số này thì quyết định 2.1 không thể xét lại được bằng gì ngoài cảm tính.

## 3. Vì sao chọn hướng này — bốn lập luận, xếp theo sức nặng

**(1) Đây là lựa chọn DUY NHẤT sinh ra bằng chứng để xét lại chính nó.** Bản chặt ⇒ ~80% lệnh dùng
nạng ⇒ **không bao giờ biết** zone cũ làm TP tốt hay tệ, vì chưa từng dùng. Bản lỏng + ghi tuổi ⇒
D4 tự trả lời *"TP trên zone 28 ngày tuổi có tệ hơn zone 3 ngày tuổi không?"*. Một bên **tạo** dữ
liệu, bên kia **huỷ** dữ liệu. Cùng nguyên tắc *"đo rẻ hơn đoán"*.

**(2) Bất đối xứng thiệt hại — hai zone làm hai việc khác nhau.** §1.3 đặt hạn dùng cho zone **VÀO
LỆNH**: ở đó luận điểm *"mức này sẽ hấp thụ lực bán"* cũ đi thì ta **cam kết vốn** vào một luận
điểm hỏng. Zone **ĐỐI DIỆN** ước lượng *"đà tăng hết chỗ ở đâu"*. Đặt sai mục tiêu chốt lời ⇒ thoát
chưa tối ưu; đặt sai zone vào lệnh ⇒ mất vị thế. Không cùng hạng rủi ro, không có lý do dùng chung
một hạn dùng.

**(3) Không tiêu 9 suất trial để đo nhầm hệ thống** — xem §1. 9 suất là thứ **không hoàn lại được**
trong ngân sách `N = 114`.

**(4) Biến một chốt rỗng thành một quyết định** — xem §2.1.

## 4. Cái giá phải trả, và giới hạn của phép đo

- 🔴 Vế hạn dùng §1.3 **không áp** trên nhánh zone đối diện. Phải đọc kèm mọi kết quả D4 có TP tham
  gia; ghi vào `d4_han_che` khi đóng cổng (TD-0186).
- TP1 có thể nhắm một mức **~28 ngày tuổi** (trung vị). P90 là 1.078 nến ≈ **180 ngày** — con số này
  đủ lớn để tự nó là một lý do xét lại, xem §5.
- ⚠️ **Giới hạn phép đo, không được đọc quá tay:** đo trên **EXPLORE, KHÔNG phải pool**, và đếm
  theo **NẾN, không theo LỆNH**. Tin được **chiều** và **bậc độ lớn** (73% so với ngưỡng 40% —
  không sát biên), **không** tin con số lẻ. Lập luận của `-94` về chiều sai số: điều kiện vào lệnh
  đòi trend UP, mà trend UP thì giá phá đỉnh cũ ⇒ đỉnh còn nằm TRÊN giá càng dễ là đỉnh CŨ ⇒ tính
  theo lệnh thì con số **xấu hơn**, không tốt hơn.
- Cửa sổ tuổi trượt theo thời gian nên ở bản CHẶT một zone có thể **hết hạn giữa lúc lệnh đang
  mở**, làm mục tiêu TP1 nhảy từ zone sang nạng giữa chừng. Quyết định 2.1 khử luôn hành vi đó —
  một lợi ích phụ, không phải lý do chính.

## 5. Ba điều kiện XÉT LẠI, viết TRƯỚC (khuôn OQ-07)

Chỉ cần **một** trong ba:

1. **`h4_nang_khong_co_zone` > 40%** trên kết quả D4 thật — lúc đó tiền đề §5.1 sai *đúng theo
   nghĩa spec viết*, và phân loại L2 là phán quyết thật, không phải tự tạo.
2. **D4 cho thấy TP-theo-zone-cũ tệ hơn nạng** — so expectancy giữa hai nhóm chia theo tuổi zone
   (số ghi ở §2.3). Nếu zone cũ không hơn được một bội số R cố định thì §1.3 đúng và DR này sai.
3. **Ai đó đo lại theo LỆNH trên POOL** (không phải theo nến trên EXPLORE) và ra bậc độ lớn khác.

Không điều kiện nào xảy ra ⇒ quyết định này **giữ nguyên**, không bàn lại.

## 6. Nếu về sau muốn có trần tuổi cho zone đối diện

Phải là một tham số **ĐẶT TÊN RIÊNG, khai tường minh** — **KHÔNG** tái dùng con số 40 của §1.3, vì
hai thứ đo hai chuyện khác nhau (xem §3.2). Đó sẽ là **một khoá mới trong kiểm kê DOF**, tức một
quyết định riêng của chủ dự án về `N` và rào DSR, không phải một dòng sửa cấu hình.

## 7. Thứ DR này KHÔNG nói

- ❌ Không nói zone cũ **tốt** làm mục tiêu TP. Nó nói ta **chưa biết**, và chọn con đường đo được.
- ❌ Không nói §1.3 sai. §1.3 đúng cho việc nó được viết ra — zone vào lệnh.
- ❌ Không gỡ ngưỡng 40%. Ngưỡng giữ nguyên, chỉ áp lên đúng mẫu số spec viết về nó.
- ❌ Không đụng zone đáy. `_tinh_zone_4h` và `ZoneAbsorptionMinimal` không đổi một dòng.
