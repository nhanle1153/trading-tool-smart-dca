# DR-D35-01 — Môi trường đo Bước 2 của DR-015, và cách quy đổi sang đơn vị R

> **Ngày chốt:** 08/09/2026 · **Người quyết:** chủ dự án · **Việc:** TD-0160 (Khối 15, D3.5)
> 🔒 **File này commit RIÊNG và TRƯỚC mọi dòng code đo.** Cùng khuôn DR-D3-01/OQ-07: DR-015 §4
> tự cấm đặt ngưỡng sau khi thấy số (*"ngưỡng tuỳ tiện là chỗ uốn kết luận sau khi thấy số"*).
> Chọn môi trường đo cũng vậy — chọn sau khi thấy kết quả là uốn kết luận bằng cách khác.

---

## 1. Ba điều phải nói rõ trước, vì cách đóng khung cũ SAI

Lộ trình ghi *"D3.5 cần testnet, mà Freqtrade cố ý tắt testnet cho Binance"*. Cả hai vế đều
đúng về sự kiện, nhưng **ghép lại thành một kết luận sai**:

**(a) Bước 2 KHÔNG cần Freqtrade.** DR-015 §2 viết thẳng: *"thăm dò độc lập, mức lệnh — KHÔNG
cần chiến lược hoàn chỉnh, không cần bot chạy thật"*. Việc Freqtrade tắt testnet (xác minh ở
TD-0116: `binance.py:52 "supports_demo_trading": False`, cố ý) chỉ chặn **bot chạy trên
testnet**, không chặn ta tự đặt lệnh qua API.

**(b) Binance futures testnet CÓ THẬT và gọi được.** Kiểm 08/09/2026:
`GET https://testnet.binancefuture.com/fapi/v1/time` → HTTP 200. Không có rào kỹ thuật nào.

**(c) Bước 1 gần như đã đo xong từ TD-0115.** 91 lượt khớp tranche trên CALIB (spec đòi ≥30),
dữ liệu 5m thật, tách theo chỉ số tranche. Phần còn thiếu là **quy đổi sang đơn vị R** và tính
**Δ_R**, không phải đo lại.

⇒ Câu hỏi thật **không phải** "có testnet hay không", mà **"đo tỷ lệ không-khớp ở đâu thì con số
mang thông tin về thị trường ta sẽ giao dịch"**.

---

## 2. Vì sao LOẠI testnet — dù nó là chữ của spec

Mục tiêu duy nhất của Bước 2 (DR-015 §2): đo ca **"giá chạm vùng nhưng lệnh KHÔNG khớp"** — thứ
backtest gần như chắc chắn đang giả định là *luôn khớp*.

Đại lượng đó là hàm của **độ sâu sổ lệnh và dòng lệnh thật**: lệnh chờ post-only tại `p` có khớp
hay không phụ thuộc có ai bán xuyên qua `p` với đủ khối lượng, và vị trí của ta trong hàng đợi.
Binance futures testnet có **sổ lệnh riêng**, mỏng hơn nhiều, phần lớn thanh khoản đến từ bot thử
nghiệm. Tỷ lệ không-khớp đo ở đó là con số **về một thị trường khác**.

🔴 Đây chính là loại lỗi `N6` tồn tại để chặn: một con số **tự tin nhưng sai** nguy hiểm hơn hẳn
một ô trống. Và nó nguy hiểm gấp đôi ở đây, vì Δ_R chảy thẳng vào quy tắc phân xử Z0-vs-DCA
(DR-015 §4) — tức nó quyết định kiến trúc của cả hệ thống.

**Ghi nhận sai khác với spec:** spec §2 nói *"trên testnet"*. Ta đo ở nơi khác. Đây là **sai khác
có ý thức**, phải vào mục Mâu thuẫn của `back-end-note.md` (quy tắc 11), không được im lặng chọn.

---

## 3. QUYẾT ĐỊNH — Bước 2 đo bằng dữ liệu khớp lệnh THẬT của production

**Phương án chốt: suy tỷ lệ không-khớp từ `aggTrades` production, KHÔNG đặt lệnh nào.**

### 3.1 Nguyên tắc suy luận

Với một lệnh **mua chờ** đặt tại giá `p`, trong cửa sổ thời gian mà kế hoạch nói "giá chạm `p`":

| Quan sát trên dữ liệu khớp lệnh thật | Kết luận |
|---|---|
| Có giao dịch in ở giá **< `p`** | **CHẮC CHẮN KHỚP** — có người bán xuyên qua mức đó |
| Giá thấp nhất **đúng bằng `p`**, không có giao dịch nào dưới | **BẤT ĐỊNH** — phụ thuộc vị trí hàng đợi |
| Không có giao dịch nào ở `≤ p` | **CHẮC CHẮN KHÔNG KHỚP** |

(SHORT đảo dấu.)

### 3.2 Đầu ra là một KHOẢNG, không phải một số

```
p_nf_thap  = tỉ lệ "chắc chắn không khớp"
p_nf_cao   = tỉ lệ "chắc chắn không khớp" + tỉ lệ "bất định"
```

🔴 **Bắt buộc mang cả hai đầu vào §4, không được tự thu về một điểm.** Vùng bất định là chỗ ta
thật sự không biết; ép nó về một con số là bịa ra thông tin. Khi §4 chạy hiệu chỉnh hai chiều,
dùng `p_nf_cao` cho kịch bản bất lợi cho DCA (fail-closed, đúng tinh thần LD-31: *thước nghi ngờ
thì nghi về phía bất lợi cho cơ chế phức tạp hơn*).

### 3.3 Điều phương án này KHÔNG thấy được — ghi rõ, không giấu

1. **Post-only bị sàn từ chối** (lệnh sẽ khớp ngay lúc đặt → sàn huỷ). Không quan sát được từ
   dữ liệu giao dịch.
2. **Khớp một phần.** DR-015 §2 đòi trạng thái thứ ba này với trọng số = tỷ lệ đã khớp. Suy từ
   `aggTrades` chỉ cho biết *có* khối lượng xuyên qua mức, không cho biết ta đứng đâu trong hàng
   đợi. → Xử bằng cách gộp vào vùng **bất định**, tức tính về phía `p_nf_cao`.
3. **Vị trí hàng đợi.** Cùng lý do trên.

Ba lỗ này đều được vùng bất định `[p_nf_thap, p_nf_cao]` **bao phủ về phía an toàn**, không cái
nào làm kết luận lạc quan hơn thực tế.

### 3.4 Vì sao không chọn "production, vốn nhỏ thật" ngay bây giờ

Nó **đúng hơn về nguyên tắc** (sổ lệnh thật, hàng đợi thật, thấy được cả khớp một phần) và vẫn
để ngỏ. Không chọn bây giờ vì: nó là tiền thật, và nó **leo thang hai rủi ro TD-0116 đã ghi và
chủ dự án đã chấp nhận có ý thức nhưng CHƯA siết** — IP chưa whitelist (nhà mạng động) và
Universal Transfer đang bật. Mở đường đặt lệnh thật trước khi siết hai thứ đó là đổi thứ tự sai.

**Điều kiện mở lại:** xem §5.

---

## 4. Bước 1 — quy đổi sang đơn vị R (không đo lại)

Dùng lại đúng 91 lượt khớp tranche của TD-0115 (CALIB, dữ liệu 5m thật). Ba việc:

1. **Quy lệch sang đơn vị R**: `lệch_R = (fill_price − p_i) / planned_risk_usdt` theo đúng
   `planned_risk_usdt` đã **ĐÓNG BĂNG tại tranche 1** (DR-013 §2) — không lấy giá vào trung bình,
   không lấy `initial_stop_loss_abs` (L-Z46 cấm).
2. **Lệch-mỗi-lệnh** `= Σ |lệch_R|` của các tranche **≥ 2** (DR-015 §3 — tranche 1 không tính,
   vì Z0 cũng có nó).
3. **Δ_R = P90** của phân phối đó nếu `n ≥ 30`; `= max quan sát được` nếu `n < 30` (fail-closed).
   Tính **riêng Long/Short**.

**Short = `unreadable`, không phải 0.** `ZoneAbsorptionMinimal` hiện LONG-only (TD-0114), nên
không có dữ liệu Short. Ghi `unreadable` theo `N6`; §4 chạy chiều bất lợi cho Short bằng Δ_R của
Long cho tới khi có số thật.

**Kế toán:** dòng `CTRL`, **0 trial** (đo THƯỚC, không đánh giá cấu hình) — nhất quán DR-014 §2,
kèm assert timerange (`L-Z55`). Chạy trên **CALIB**, không phải WFO: DR-015 §2 nói rõ chạy trên
WFO trước ablation là *nhìn trước cấu trúc chạm zone của tập đánh giá*.

---

## 5. Điều kiện mở lại quyết định này

Viết trước, để việc đổi ý phải có căn cứ chứ không phải vì con số không đẹp:

1. **Vùng bất định quá rộng để phân xử** — cụ thể: `p_nf_cao − p_nf_thap` lớn tới mức §4 đổi
   người thắng giữa hai đầu khoảng. Khi đó khoảng này **không đủ tư cách phân xử**, và phương án
   "production vốn nhỏ" trở thành đáng chi. Điều kiện đi kèm bắt buộc: **siết xong hai rủi ro
   TD-0116 trước** (IP whitelist BẬT, Universal Transfer TẮT).
2. **Có bằng chứng testnet phản ánh được hàng đợi thật** — hiện không có; nếu Binance công bố
   testnet dùng chung sổ lệnh/dòng lệnh với production thì lập luận §2 mất hiệu lực.
3. **DR-015 §5.2 kích hoạt** (người thắng đổi giữa hai chiều VÀ lợi thế thô của DCA ≥ 20%) — lúc
   đó dự án đã chấp nhận chi cho phương án đắt, và đo thật là bước rẻ hơn tự xây bộ mô phỏng.

---

## 6. Liên kết

- Nguồn: `tool-d-smart-dca.md` DR-015 (dòng 3566–3660), §10.2 Nhánh 2, §3.5.
- Bước 1 dựa trên: TD-0115 (`docs/research-log.md` 07/09/2026), DR-013 (đơn vị R).
- Test khoá phải có trước khi cổng D3.5 đóng: `L-Z56` (ablation từ chối chạy khi chưa có Δ_R),
  `L-Z58` (hiệu chỉnh hai chiều). `L-Z57` thuộc GATE §10.2, không thuộc cổng này.
- Sai khác với spec (§2 ghi "testnet") → mục Mâu thuẫn của `back-end-note.md`, chờ lệnh
  **"chuẩn hóa và lưu"** (N9).
