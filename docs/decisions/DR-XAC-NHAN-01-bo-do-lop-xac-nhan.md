# DR-XAC-NHAN-01 — Bộ đo lớp xác nhận sau lockbox (`DR-LOCKBOX-04` §2 dòng 3, §3)

> **Trạng thái:** ✅ **ĐÃ CHỐT 24/09/2026** — chủ dự án trả lời ba câu mở ở §3 (khối quyết định cuối file). Bản nháp đầu:
> `d2f738c`. Chưa có dòng mã nào theo DR này.
> **Ngày soạn:** 24/09/2026 · phiên mã `143375ad` · `TD-0388`. Mã đặt chỗ bằng commit `dc11974` (N12 mục 7c).
> **Chi phí:** **0 trial**. Không chạm dữ liệu.

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`) — nó mô tả lockbox và lớp xác nhận của ứng viên.

---

## 0. Đã chốt ở nơi khác — DR này không đổi

| Điều | Nguồn |
|---|---|
| Vốn vượt trần D12 (`E_D` 750 · `rho_pct` 0,375 · `L_exchange` 3) ⇒ `load_tool_d_config()` từ chối, trừ khi hiện vật xác nhận đạt | `TD-0382` (`365f4a8`), `src/tool_d/config/tran_von.py` |
| Chỉ số `mean_r` (trung bình `r_trien_khai`), ngưỡng **≥ 0,10 R**, **n ≥ 30** | `DR-LOCKBOX-04` ô ký (`fe1da36`) |
| Dữ liệu **từ ngày CHỌN** của ứng viên, backtest đúng cấu hình đã chạm lockbox, đo **đúng một lần** | `DR-LOCKBOX-04` ô ký; máy thi hành `TD-0387` |
| Hiện vật `docs/du-lieu-do/xac-nhan-sau-t3.json`, khoá `dr`, `hypothesis_slot`, `tu_ngay`, `n_lenh`, `chi_so`, `gia_tri` (+ `config_sha256` từ `TD-0387`) | `tran_von.py`; `TD-0387` |

## 1. Vấn đề — chưa có đường nào sinh ra hiện vật

- E1 chỉ nhận `--tap CALIB|WFO` (`entrypoints/run_backtest.py:86`); biên tập đọc từ `tier_c.data_split` và dừng ở `T3`
  (`src/tool_d/ledger/timerange.py:82-88`); `ro_cho_tap()` không có mục cho đoạn sau `T3` (`src/tool_d/pool_giai_doan.py:59`).
- E5 đọc DB dry-run nhưng không tính được R (`reporting/freqtrade_db.py` không đọc `enter_tag`/giá lệnh); và lựa chọn đã chốt
  là **backtest**, không phải lệnh live.
- Không được thêm entrypoint thứ 9 (`L-Z36`); script rời trong `docs/du-lieu-do/` thì không đi qua `measurement_guard()`
  — sai với một con số nuôi cổng tiền (`measurement/entrypoint_registry.py:3-6`).

## 2. Thiết kế đề xuất

1. **Tập mới `XAC_NHAN`** — biên nửa mở `[ngày CHỌN còn hiệu lực của slot, ngày đo)` (khuôn `DR-D9-01`). Ngày CHỌN đọc từ
   `registry/idea_queue.jsonl` (bỏ lần `VOIDED`), không nhập tay. Biên này **động** nên không nằm trong
   `tier_c.data_split`; thêm một hàm biên riêng cạnh `dataset_boundaries_from_config()` và nối vào `L-Z55`
   (`assert_dataset_timerange`) như ba tập cũ.
2. **Đường chạy:** E1 `run_backtest.py --tap XAC_NHAN --hypothesis-slot IQ-xxxx --with-params-file <params đã chạm lockbox>
   --chay`. Giữ nguyên năm cổng hiện có của E1 (guard, H17, `L-Z55`, cache…). Sau backtest, chuỗi dùng lại có sẵn:
   xuất backtest → `bo_chay/trich_lenh.lenh_tu_freqtrade` → `wfo/lenh.LenhWFO.r_trien_khai` →
   `ablation/ban_ghi.thong_ke_arm()["mean_r"]`. E1 ghi hiện vật, người commit **một lần**.
3. **Thư mục dữ liệu riêng** `user_data/data/xac_nhan/` (khuôn EXPLORE: tách ở tầng thư mục), tải bằng E8, cắt và kiểm nằm
   trọn biên.
4. **Cấu hình:** hiện vật mang `config_sha256`; `TD-0387` so với cấu hình ghi trong `lockbox_access.log` lúc chạm.

## 3. 🔴 Câu mở — chờ chủ dự án, KHÔNG tự chọn

**Q1. Kế toán sổ trial cho lần đo này.** Theo `DR-014` §2, đánh giá một cấu hình trên dữ liệu là "chạm". Ba phương án:

| | Phương án | Được | Mất |
|---|---|---|---|
| (a) | Ghi một dòng **B3** (tiêu 1 suất dự phòng) | Không cần luật mới | Tốn suất dự phòng cho một phép đo không chọn gì giữa các cấu hình; B3 có thể đã cạn lúc đó |
| (b) | Dòng sổ hạng **mới `XAC`**, **ngoài N**, trần cứng **1 dòng mỗi slot** do máy kiểm | Đúng bản chất: không chọn giữa cấu hình nên không làm tăng đa phép thử | Thêm một hạng sổ ⇒ đổi schema, cần luật + test như `CTRL` (MT-08) |
| (c) | Tính vào suất của slot `IQ-xxxx` như một lượt WFO cuối | Không thêm hạng | Lẫn nghĩa với WFO; slot có thể đã hết suất |

**Khuyến nghị: (b)** — N đo *số cấu hình đã thử để chọn*, lần đo này không chọn gì; trần 1 dòng/slot + hiện vật một commit
(`TD-0387`) giữ nó không thành cửa sau để thử nhiều lần.

**Q2. Khi nào đo.** Không biết trước bao giờ đủ 30 lệnh. Khuyến nghị: **đếm số lệnh được lặp lại** (chỉ đếm, không đọc R, cùng
khuôn *"đếm, chỉ đếm"* của TD-0251); **tính `mean_r` đúng một lần**, ở lần đếm đầu tiên thấy n ≥ 30, trên đúng các lệnh tới
ngày đó. Cấm: tính `mean_r` ở n < 30 "để xem", hoặc chờ thêm sau khi đã thấy số.

**Q3. Rổ mã.** Khuyến nghị: rổ **tại ngày CHỌN** (nguyên tắc point-in-time của `DR-D1-05`), sinh bằng E7 và commit TRƯỚC khi
tải dữ liệu. Phương án khác: dùng lại rổ lockbox (`pool_t2.yaml`) — đơn giản hơn nhưng lệch sống sót theo thời gian.

## 4. Điểm yếu — khai thẳng

- Backtest không đo khớp lệnh thật; lớp xác nhận vì thế kiểm **tín hiệu** trên thị trường mới, không kiểm **thực thi**. Thực
  thi do D10/D11/D12 kiểm.
- Ứng viên tần suất thấp có thể mất nhiều tháng mới đủ 30 lệnh; trong lúc đó vốn đứng ở trần D12 — đúng hướng sai đã chấp nhận
  ở `DR-LOCKBOX-04`.
- Máy vẫn không chứng minh được hiện vật do chính bộ đo sinh ra (điểm mù của `TD-0382`); `config_sha256` + một commit thu hẹp,
  không đóng hẳn.

## 5. Thi hành (sau khi chốt)

| Mã | Việc |
|---|---|
| TD-0387 | Siết chốt: `tu_ngay` ≥ ngày CHỌN, hiện vật một commit, `config_sha256` khớp lần chạm lockbox |
| TD-0389 | Bộ đo: tập `XAC_NHAN`, biên + `L-Z55`, rổ, E1 `--tap XAC_NHAN`, ghi hiện vật; kế toán theo Q1 |

---

## 6. ✅ QUYẾT ĐỊNH — 24/09/2026, chủ dự án chọn qua công cụ hỏi-chọn (phiên mã `143375ad`)

Cả ba câu, chủ dự án chọn đúng phương án được gắn *"(Recommended)"* do phiên này soạn — khai theo khuôn `DR-LOCKBOX-01` §1.

| Câu | Chốt |
|---|---|
| Q1 kế toán | **Hạng sổ mới `XAC`, ngoài `N`.** Trần cứng **1 dòng `XAC` mỗi `hypothesis_slot`**, máy kiểm tại cửa ghi sổ (`registry.reserve()`), không nhận lời khai. Không đổi `N = 114`, không đổi rào DSR. Cần: schema sổ + luật + test cùng khuôn `CTRL` (MT-08, TD-0130) |
| Q2 thời điểm | **Đếm số lệnh được lặp lại, không đọc R; tính `mean_r` đúng một lần** ở lần đếm đầu tiên thấy n ≥ 30, trên đúng các lệnh tới ngày đó. Cấm tính sớm "để xem" và cấm chờ thêm sau khi đã thấy số. Phép đếm và phép tính phải là **hai chế độ tách biệt** của E1 (chế độ đếm không được sinh ra bất kỳ con số hiệu năng nào) |
| Q3 rổ | **Rổ tại ngày CHỌN** (point-in-time, `DR-D1-05`), sinh bằng E7, commit TRƯỚC khi tải dữ liệu `XAC_NHAN` |

**Điều kiện dừng khi code (`TD-0389`):** một test cũ phải sửa khẳng định mới xanh ⇒ dừng, báo; hạng `XAC` làm đổi `n_used()` ⇒ dừng
(nó phải đứng ngoài `N`); chế độ đếm lộ ra bất kỳ trường nào ngoài số lệnh và khoảng ngày ⇒ dừng.
