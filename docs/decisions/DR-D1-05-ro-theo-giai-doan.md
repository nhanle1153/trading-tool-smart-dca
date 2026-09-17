# DR-D1-05 — Rổ pool theo TỪNG GIAI ĐOẠN; `config/pool.yaml` không bị thay

> **Ngày chốt:** 17/09/2026 · **Người quyết:** chủ dự án (ba câu hỏi trực tiếp, phiên `-01`) · **0 trial**
> **Thi hành / mở lại:** `DR-D1-02` §6 (*"đưa rổ `T1` thành `config/pool.yaml` sản xuất — quyết định riêng,
> DR riêng"*). DR này **là** quyết định riêng đó, và kết luận là **không thay** theo cách hiểu đơn giản.
> **Đính chính:** con số *"430 mã"* của khối `explore:` ở `DR-D1-02` §2 và `DR-D1-03` §0 (§4 dưới đây).
> **Commit RIÊNG và TRƯỚC mọi dòng mã** của Khối 25, kiểm bằng `git merge-base --is-ancestor`.
> Đã báo phiên `-a2` mã `DR-D1-05` · `MT-60` · `TD-0298…TD-0303` · Khối 25 trước khi mở file (N12 mục 6).

---

## 0. Vì sao "thay `pool.yaml` bằng rổ `T1`" là sai hình

Khảo sát 17/09/2026 (0 trial, đọc mã + tài liệu):

1. **Không có mã nào đọc `config/pool.yaml` khi chạy.**
   - E1/E2/E3 chưa chọn cặp mã hay thư mục dữ liệu nào: E1 dừng ở `NotImplementedError`; E2 in kế hoạch
     fold rồi thoát.
   - `runs/pool_pairs.json` (102 mã) nằm ngoài git và không có bộ sinh.
   - Hôm nay `pool.yaml` chỉ giữ hai vai:
     - **rổ hôm nay**, đo 09/2026 bằng `exchangeInfo` sống;
     - **sổ 4 suất B0** (`b0_trial_ids` `D-0001…D-0004`, sha `4ae2c7dc`, `hypothesis_slot: POOL-0.3`).
2. **Mỗi tập dữ liệu cần rổ đúng tại mốc bắt đầu của nó** (H1-D, `spec:438`, `:4338`):
   - **CALIB `[T0,T1]`** → rổ tại `T0`. `DR-D5-01` §1:41 ghi *"mốc `T0`"*; `TD-0252` ghi *"rổ tại `T0`"*.
     Dùng rổ `T1` cho CALIB là chọn mã bằng thông tin **sau** khi giai đoạn đã bắt đầu, đúng thứ H1-D
     sinh ra để chặn.
   - **WFO `[T1,T2]`** → rổ `T1`. Đây là giai đoạn duy nhất `config/pool_t1.yaml` được dựng cho
     (`DR-D1-02` §0).
   - **LOCKBOX `[T2,T3]`** → rổ tại `T2`.
   - **Live** → rổ hôm nay.
3. **LOCKBOX đã niêm phong cho 102 mã `pool.yaml` cũ.** Chi tiết: `lockbox_seal_1.json`, 510 file,
   `DR-D0PRE-07` §6, *"commit, không sửa"*.
   - Lockbox chưa chạm lần nào.
   - Rổ `T1` có 52/107 mã không có dữ liệu lockbox; 7 mã đã huỷ niêm yết không thể có.
   - Dựng rổ `T2` còn bị `MT-59` chặn (`khoang_ton_tai` của TD-0230 đánh giá quá đời sống mã đã huỷ).

## 1. Quyết định (chủ dự án chốt 17/09/2026)

| Tập | Rổ | Thư mục dữ liệu | Trạng thái |
|---|---|---|---|
| CALIB `[T0,T1]` | `config/pool_t0.yaml` | `user_data/data/pool_t0/futures/` | **dựng mới** (Khối 25) |
| WFO `[T1,T2]` | `config/pool_t1.yaml` (107 mã, `a62540b`) | `user_data/data/pool_t1/futures/` | ✅ đã có (TD-0247) |
| LOCKBOX `[T2,T3]` | `config/pool_t2.yaml` | — | ⏸ **tới khi nối lại D8**, chặn bởi `MT-59` + `MT-60` |
| Live | `config/pool.yaml` | — | **không đổi**; vẫn là rổ hôm nay + sổ B0 |

- **Một hàm chọn rổ duy nhất cho mọi bộ chạy** (`src/tool_d/pool_giai_doan.py`): nhận tên tập, trả
  (file rổ, thư mục dữ liệu, mốc).
  - `LOCKBOX` ⇒ từ chối, nêu `MT-60`.
  - Tên tập lạ ⇒ từ chối.
  - File rổ chưa tồn tại ⇒ từ chối.
  - **Không bao giờ** rơi về `pool.yaml`.
  - Test khoá canh việc dùng rổ sai giai đoạn. E1/E2/E3 **chưa** gọi hàm này vì chúng chưa có bộ chạy
    thật; khi viết bộ chạy thì phải gọi nó, không tự đọc file rổ.
- **Mỗi rổ độc lập tại mốc của nó**, cùng luật `DR-D1-03` §1:
  - loại vĩnh viễn mọi mã có dữ liệu trong `user_data/data/explore/futures/`;
  - xét trượt tiêu chí **tại chính mốc đó**, không chuỗi `pairlist_over_time()` giữa các rổ.

## 2. Chi phí: 0 suất — và vì sao không được đọc thành "chọn lại pool miễn phí"

- **Tiêu chí không đổi một con số:** 15.000.000 USDT/ngày, 180 ngày niêm yết — đúng hai hằng 4 suất B0
  đã trả (`DR-D0PRE-05`).
- **Đo cùng tiêu chí tại mốc lịch sử là cách thi hành đúng H1-D**, không phải một lần thử:
  - spec `:438`: *"H1-D point-in-time viết riêng, không dùng VolumePairList mặc định"*;
  - rổ `T1` cũng đã làm với 0 suất (`DR-D1-02` §5).
- 🔴 **Vẫn cấm, không đổi:**
  - chọn lại pool sau khi thấy kết quả (`spec:350-352`, `:2855`);
  - chỉnh một tiêu chí pool, việc đó tốn 1 suất B3 (`spec:3252`);
  - dựng thêm rổ ở một mốc không phải `T0`/`T1`/`T2`/hôm nay rồi chọn rổ đẹp hơn.

  Mốc rổ do `DR-D0PRE-07` quy định, **không** là tham số.

## 3. Dữ liệu cho rổ `T0` (thi hành `DR-D1-03` §4–§5 ở mốc khác)

- **Loại file:** `1h`/`4h`/`1d` futures, `1h` mark, `1h` funding trên `[T0,T1]`, cắt `≤ T1 00:00 UTC`.
  Cắt tại mốc ngừng giao dịch nếu sớm hơn `T1` (§5 `DR-D1-03`: nến 1h cuối có `volume > 0`).
- **Không có 5m.** `timeframe-detail 5m` cho CALIB là việc của `TD-0252`, đang ⏸ cùng D5 (`DR-IQ-01`).
  Đây là **giới hạn đã biết**: rổ `T0` chưa đủ cho backtest CALIB có `--timeframe-detail 5m`.
- **`MT-59` không ảnh hưởng rổ `T0`:** mã chết sau `T0` vẫn sống tại `T0`. Mốc ngừng trong `[T0,T1]`
  đo lại từ nến, không đọc `khoang_ton_tai`.
- **Số dự kiến** (đếm 17/09/2026 từ artifact, 0 trial; con số thật do bộ sinh ghi):
  - `TD-0231` cho **164** mã đủ tiêu chí tại `T0`; trừ **21** mã có dữ liệu EXPLORE còn **143**.
  - Dữ liệu sẵn: 42 mã trong `binance/futures`, thêm 24 mã trong `pool_t1/futures`.
  - **77 mã chưa có dữ liệu**, nhiều mã đã huỷ niêm yết hoặc đổi tên (vd `MATICUSDT`, `FTMUSDT`,
    `RNDRUSDT`, `AGIXUSDT`, `OCEANUSDT`) ⇒ nhập từ kho, cùng đường §4.
- **Nguồn chép, theo thứ tự:** `binance/futures` rồi `pool_t1/futures`, chỉ 5 loại. Cắt `≤ T1` ở
  **thư mục đích**, không đụng thư mục nguồn.

## 4. Đính chính: khối `explore:` có 426 mã, không phải 430

- **Đếm lại 17/09/2026:** `trading` 102 · `explore` **426** · `b0_trial_ids` 4.
- **Nguồn con số 430:** phép đếm cũ cắt từ `explore:` tới hết file nên gộp 4 dòng `- D-000x`.
- **Không đổi kết luận nào:** giao với rổ `T1` vẫn là **54**, vì mã trial không phải tên mã.
- **Nơi đang mang con số sai:**
  - `DR-D1-02` §2 và `DR-D1-03` §0: gắn đính chính tại chỗ;
  - docstring `src/tool_d/pool_t1.py`: sửa (TD-0303);
  - ô `MT-54` của `back-end-note.md`: nối thêm (chờ "chuẩn hóa và lưu").

## 4b. ĐÍNH CHÍNH 18/09/2026 — `config/pool_t0.yaml` mang hai nhãn của mốc `T1`

`config/pool_t0.yaml` (`e538518`) ghi trong khối `dem`:

```
ung_vien_song_tai_t1: 285
du_tieu_chi_tai_t1: 164
```

**Đúng ra là `..._tai_t0`.** Hai CON SỐ không sai: 285 mã sống tại `T0`, 164 mã đủ tiêu chí tại `T0`
(khít `td0231["pool_dung_tai_t0"]`). Chỉ TÊN KHOÁ sai.

- **Nguyên nhân:** bộ sinh ghi cứng hậu tố `_t1` ở ba khoá đầu ra. Bản `5954e14` sửa **một** khoá
  (`thieu_hang_dung_ngay`), bỏ sót hai khoá của `dem`; phiên `-93` bắt được 18/09.
- **Đã sửa bộ sinh** (`4d3ab99`) + mở rộng test hồi quy: mọi khoá trong `dem` và `khong_do_duoc` phải
  mang đúng tên mốc, và không khoá nào được kết thúc bằng `_t1` khi sinh rổ `T0`.
- **Chủ dự án chốt 18/09/2026: ĐÍNH CHÍNH TẠI CHỖ, KHÔNG xoá file đã commit.** `pool_t0.yaml` giữ
  nguyên; mọi bộ đọc phải hiểu hai khoá đó theo mốc của chính file (`moc_t0`), không theo hậu tố.
  Sinh lại file sẽ phải xoá một rổ đã commit — đường mà `build_pool.py` mô tả là *"xoá thủ công + ghi
  DR mới"* — quá đắt cho một lỗi nhãn.
- 🔑 **Bài học, đã lặp HAI lần trong hai ngày:** tổng quát hoá một hàm theo tham số thì phải soát cả
  **tên khoá đầu ra**, không chỉ đường tính. Lần một: `thieu_hang_dung_ngay_t1` (17/09). Lần hai:
  `dem.*_tai_t1` (18/09) — cùng hàm, cùng lớp lỗi, khác khoá.

## 5. Ngoài phạm vi

- **Không đụng:** `config/pool.yaml`, `lockbox/`, `registry/trial_registry.jsonl`.
- **Không dựng rổ `T2`** (⏸ D8; `MT-59`, `MT-60`).
- **Không đo phễu / n / lệnh-năm** (Zone Absorption ⏸, `DR-IQ-01`).
- **Không tải 5m cho CALIB** (`TD-0252` ⏸).

## 6. Mâu thuẫn mới — `MT-60` (chờ "chuẩn hóa và lưu")

🟡 **Lockbox niêm phong dữ liệu cho 102 mã `pool.yaml`, nhưng rổ đúng cho LOCKBOX là rổ tại `T2`.**
- Không giải thì lần chạm lockbox duy nhất chấm cấu hình trên rổ đo 09/2026, **khác rổ** WFO đã dùng.
  Tệ hơn, rổ đó loại sẵn những mã suy giảm trước 09/2026: lệch sống sót theo chiều PASS, **đúng tại
  cổng cuối**.
- Niêm phong không sửa được; `L-Z13` cho tối đa 3 đoạn (`access_log.MAX_SEGMENTS`), nhưng chưa có đường
  mã ghi đoạn 2.
- **Phải giải trước lần chạm lockbox** (`TD-0274`/D8). Lockbox chưa chạm, nên hiện chưa mất gì.
