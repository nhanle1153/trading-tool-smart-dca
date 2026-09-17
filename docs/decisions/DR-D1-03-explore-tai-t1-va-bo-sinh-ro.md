# DR-D1-03 — Ranh giới EXPLORE của rổ `T1`: xét TẠI `T1`, loại mọi mã có dữ liệu EXPLORE đã dùng; và bộ sinh rổ có xuất xứ

> **Ngày chốt:** 17/09/2026 · **Người quyết:** chủ dự án (hai câu hỏi trực tiếp, phiên `-01`) · **0 trial**
> **Đính chính / mở lại:** `DR-D1-02` §2 (con số *"9 mã"* và cách đọc *"đã bị xếp EXPLORE"*).
> **Thuộc việc:** `TD-0247` (người giữ `-01` từ 17/09, `dfe4231`).
> **Commit RIÊNG và TRƯỚC mọi dòng mã** của phần còn lại `TD-0247`, kiểm bằng
> `git merge-base --is-ancestor <sha DR> <sha mã>`.
> Đã báo `-33`/`-30` mã `DR-D1-03` trước khi mở file (N12 mục 6); cả hai xác nhận không dùng.

---

## 0. Vì sao cần DR này — `DR-D1-02` §2 đếm sai, và cái sai đó đảo ngược mục đích `TD-0247`

`DR-D1-02` §2.1 ghi *"9 mã vừa đủ tiêu chí §0.3 tại `T1` vừa đang đứng trong khối `explore:` của
`config/pool.yaml`"*. Đo lại 17/09/2026 (0 trial, đọc `td0231-pool-point-in-time.json` +
`config/pool.yaml` + liệt kê thư mục):

| Tập | Số mã | Giao với rổ đúng tại `T1` (116 mã) |
|---|---|---|
| Khối `explore:` của `config/pool.yaml` | **430** | **54** |
| Mã có dữ liệu trong `user_data/data/explore/futures/` | 100 | **9** |
| 65 mã `TD-0291` đã tính PnL trên CALIB (phiên `-33`, `a634702`) | 65 | 9 (đúng 9 mã trên) |
| 23 mã chỉ đếm (`TD-0193/0205/0212/0228`) | 23 | 0 |

Khối `explore:` không phải *"tập dữ liệu EXPLORE đã dùng"*. `pool.py:38` (`PoolResult.explore`) và
spec §9c.4b (`tool-d-smart-dca.md:3818-3822`) định nghĩa nó là *"BTC + ETH + mọi coin TRƯỢT tiêu chí
pool §0.3"*, phân loại **bằng dữ liệu 09/2026**. Con số 9 của `DR-D1-02` thật ra là giao với
**thư mục dữ liệu** (chính DR đó viết *"cả 9 mã đều có dữ liệu OHLCV thật sẵn trong `explore/`"*),
nhưng quyết định lại được viết theo **khối `explore:`**. Hàm đã commit `loai_tru_explore_hien_tai()`
(`4fe5068`) cũng ghi docstring theo khối đó.

🔴 **Hệ quả nếu thi hành đúng chữ:** rổ `T1` còn **62 mã**. 45 mã bị loại thêm là những mã **đủ tiêu
chí giữa 2025 rồi suy giảm tới 09/2026**, nên bị xếp *"trượt tiêu chí"*. Loại chúng tái tạo đúng lệch
sống sót đi qua cửa tiêu chí lọc mà `TD-0231`/`MT-34` đo được và `TD-0247` sinh ra để sửa: rổ mới chỉ
thêm 7 mã so với `config/pool.yaml` (các mã đã huỷ niêm yết), WFO vẫn đo lệch theo chiều PASS.

> 🔄 **Đính chính 17/09/2026 (`DR-D1-05` §4):** bảng trên ghi khối `explore:` có **430** mã — đúng là
> **426** (phép đếm cũ gộp 4 dòng `b0_trial_ids`). Giao rổ `T1` vẫn là **54**; không kết luận nào đổi.

## 1. Quyết định (chủ dự án chốt 17/09/2026)

### 1.1. Tập bị loại vĩnh viễn = mọi mã có dữ liệu EXPLORE đã dùng

Loại khỏi rổ `T1`, vĩnh viễn, không ngoại lệ, **mọi mã có dữ liệu trong
`user_data/data/explore/futures/` tại lúc sinh rổ**. Tên mã suy từ tên file theo quy ước Freqtrade
`BASE_USDT_USDT-<tf>-futures.feather` → `BASEUSDT`.

- **Giữ đúng ý 16/09 của chủ dự án:** thứ cần chặn là dữ liệu đã được nhìn để sinh giả thuyết rồi
  quay sang làm tập đo hiệu năng (§9c.4b ràng buộc (b): *"ngoại lệ sẽ biến EXPLORE thành tập
  train"*).
- **Rộng hơn *"9 cứng"*:** bao trùm cả 65 mã có PnL lẫn 88 mã từng đếm. Mã nào về sau được tải thêm
  vào EXPLORE **trước** lúc sinh rổ cũng tự động bị loại.
- **Vẫn là quy tắc theo MÃ, máy thi hành được** (tinh thần `DR-D1-02` §2.3). Không có danh sách chặn
  gõ tay theo tên: nguồn là thư mục dữ liệu. Danh sách đọc được lúc sinh **được chụp nguyên văn vào
  file rổ** (§2), nên về sau thư mục có thay đổi thì vẫn truy được rổ đã loại theo tập nào.
- **Fail-closed:** thư mục không tồn tại hoặc đọc ra 0 mã ⇒ **từ chối sinh rổ**. Một tập rỗng im lặng
  sẽ nhận lại chính những mã phải loại.

### 1.2. *"Trượt tiêu chí"* xét TẠI `T1`, không chuỗi từ `T0`, không theo phân loại 09/2026

Rổ `T1` = mã đủ tiêu chí §0.3 **tại chính ngày `T1`** (`pairlist_point_in_time()`, đúng cách
`TD-0231` dựng) trừ tập §1.1. **Không** chạy `pairlist_over_time()` từ `T0`.

- **Căn cứ đo được:** chuỗi `T0 → T1` loại vĩnh viễn thêm **22 mã** chỉ vì tại `T0` (09/04/2024) chúng
  còn quá mới (dưới 180 ngày) hoặc volume thấp. Nhóm này gồm `ENAUSDT`, `JUPUSDT`, `WIFUSDT`,
  `TAOUSDT`, `TIAUSDT`, `ONDOUSDT`, `TONUSDT`, `STRKUSDT`, `PYTHUSDT`, `ETHFIUSDT`… Rổ khi đó còn
  khoảng 85 mã.
- **Không mã nào trong 22 mã đó từng có dữ liệu EXPLORE.** "EXPLORE tại `T0`" chưa bao giờ tồn tại như
  một tập dữ liệu được nhìn. Loại chúng không chặn được rò rỉ nào, chỉ cắt mẫu và tạo một lệch mới
  (loại nhóm niêm yết cuối 2023 – đầu 2024).
- ⚠️ **Lệch chữ có ý thức:** spec §9c.4b định nghĩa EXPLORE theo **phân loại tiêu chí**, còn DR này
  thi hành ràng buộc (b) theo **dữ liệu đã dùng**. Đây là một cách đọc, không phải chữ tường minh ⇒
  ghi `MT-54` (chờ lệnh "chuẩn hóa và lưu"). `pairlist_over_time()` **không** bị sửa hay xoá; nó vẫn
  đúng cho việc dựng rổ nhiều mốc về sau, và DR này không dùng nó.

### 1.3. Lọc `TRADIFI_PERPETUAL` giữ nguyên (`DR-D1-02` §4 (iii))

Áp `loai_tru_tradifi_perpetual()` với `exchangeInfo` sống. Rổ `T1` (06/2025) dự kiến không có mã nào
bị lọc, nhưng bộ sinh vẫn áp và ghi số mã bị lọc (0 cũng ghi).

## 2. Bộ sinh rổ có xuất xứ (thi hành, không phải quyết định mới)

- **Không thêm entrypoint thứ 9** (`L-Z36`). Bộ sinh là cờ `--ro-t1` trên **E7** `build_pool.py`
  (đúng miền "chốt pool"), gọi `measurement_guard()` ở dòng đầu như mọi cờ E7. **0 trial**, không ghi
  sổ (dựng rổ không phải đánh giá cấu hình — `DR-014` §2).
- **Tính lại từ nguồn, không chép artifact:** volume đúng ngày `T1` + ngày onboard (đọc chính xác khi
  sát ngưỡng 180 ± 31 ngày) qua `doc_quote_volume_1d_thang()`, cùng adapter đã dùng ở `TD-0231`
  (R1 single egress). Khoảng tồn tại từng mã đọc từ `td0230-lech-song-sot-pool.json`; sha256 file đó
  ghi vào xuất xứ.
- **Đối chiếu độc lập với `TD-0231`:** tập *"đủ tiêu chí tại `T1`"* tính lại phải **trùng khít** danh
  sách `pool_dung_tai_t1` của `td0231-pool-point-in-time.json`. Lệch ⇒ in hiệu hai phía và **từ chối
  ghi**, vì hai đường chạy cùng logic mà ra hai rổ nghĩa là một trong hai đang sai.
- **Đầu ra:** `config/pool_t1.yaml`. **Không** đụng `config/pool.yaml` (`DR-D1-02` §6: đưa rổ `T1`
  thành rổ sản xuất là quyết định riêng). Từ chối ghi đè (khuôn E7). Chỉ ghi khi không có thay đổi
  chưa commit trong vùng ảnh hưởng phép đo (`src/ tests/ entrypoints/ config/ registry/schemas/`,
  cùng quy tắc cổng D3), để `git_sha` trong file trỏ đúng mã đã sinh ra nó.
- **Nội dung file:**
  - mốc `T1` và tiêu chí;
  - `trading` (rổ cuối);
  - danh sách **bị loại** tách theo lý do: `explore_da_dung`, `tradifi`;
  - danh sách **không đo được**: `thieu_ngay`, `404`. Tách riêng, không gộp vào "trượt" (N6);
  - danh sách mã EXPLORE chụp lúc sinh;
  - xuất xứ: `git_sha`, sha256 artifact nguồn, thời điểm sinh, kết quả đối chiếu `TD-0231`.
- **Tên hàm cũ:** `loai_tru_explore_hien_tai()` giữ nguyên chữ ký (lọc theo một tập), **sửa docstring**
  sang nghĩa §1.1. Tập truyền vào là mã có dữ liệu EXPLORE, không phải khối `explore:`.

## 3. Hệ quả

- **Rổ `T1` dự kiến ≈ 107 mã** (116 − 9; con số thật do bộ sinh ghi).
- **Mọi số quy đổi sang pool** (`325,6` · `n = 206` · `44,8` · sàn 150) phải đo lại trên rổ mới.
  Việc này đã có trong `TD-0247`/`TD-0184`.
- **Việc còn lại của `TD-0247` sau bộ sinh (chưa thuộc DR này):**
  - tải bù dữ liệu cho các mã thiếu vào `user_data/data/pool_t1/` qua E8;
  - đo lại phễu / `n` / lệnh-năm.

  Tập mã cần tải bù sẽ tính từ file rổ, không từ con số *"52"* cũ (con số đó đếm trên `K = 61`, trước
  khi biết cách loại EXPLORE đúng).
- **`MT-54`** (chờ lệnh "chuẩn hóa và lưu"): ràng buộc (b) §9c.4b thi hành theo **dữ liệu đã dùng**,
  xét tại `T1`, lệch chữ *"mọi coin trượt tiêu chí"*; kèm đính chính con số 9 của `DR-D1-02`.

---

## 4. PHỤ LỤC 17/09/2026 — dữ liệu `[T0,T2]` cho rổ `T1` (chủ dự án chốt, viết TRƯỚC code)

Bộ sinh chạy thật ra **107 mã** (`config/pool_t1.yaml`, `a62540b`), khít `TD-0231`. Đếm file
(0 trial, chỉ tên file) và hỏi `exchangeInfo` sống:

| Nhóm | Số mã | Cách có dữ liệu |
|---|---|---|
| Đã có đủ 6 loại file trong `user_data/data/binance/futures/` | 55 | **Sao chép nguyên byte** sang thư mục rổ, không tải lại |
| Thiếu, **đang giao dịch** | 45 | `freqtrade download-data` (quy trình TD-0093/TD-0200 + cắt ≤ `T2`) |
| Thiếu, **đã huỷ niêm yết** (6 `SETTLING`: DEGO, FLM, ICX, MKR, OM, TON; 1 vắng: AERGO) | 7 | **Nhập từ kho `data.binance.vision`** — Freqtrade không tải được mã không còn trên sàn |

**Chủ dự án chốt (hai câu hỏi trực tiếp):**

1. **7 mã đã huỷ niêm yết: viết đường nhập từ kho lưu trữ.** Bỏ chúng đi là tái tạo lệch sống sót
   theo chiều PASS, đúng thứ `TD-0247` sinh ra để sửa.
2. **`user_data/data/pool_t1/futures/` chứa đủ 107 mã.** Freqtrade chỉ đọc một thư mục dữ liệu mỗi
   lần backtest. 55 mã có sẵn thì sao chép.

**Thi hành, không phải quyết định mới:**

- **Phạm vi thời gian theo đúng quy ước file hiện có** (đo 17/09): `1h`/`4h`/`1d`-futures, `1h-mark`,
  `1h-funding_rate` từ `T0`; `5m`-futures từ `T1`. Mọi file cắt `date ≤ T2 00:00 UTC`. Mã niêm yết sau
  mốc thì bắt đầu từ lúc niêm yết; mã huỷ trước `T2` thì kết thúc lúc huỷ.
- **Khớp định dạng đã CHỨNG MINH bằng đối chiếu, không suy luận.** AAVE (đang giao dịch), tháng
  05/2024 và 09/2025, kho so với file Freqtrade thật:
  - nến `1h`/`4h`/`1d`/`5m` và `mark`: **0 ô lệch, 0 mốc chỉ-một-bên**;
  - `funding`: lần đầu lệch mốc vì `calc_time` của kho mang jitter **1–7 ms** (`1714665600002`), còn
    Freqtrade ghi tròn giờ. Sau khi làm tròn xuống giờ (từ chối nếu lệch ≥ 60 giây): **93/93 và 90/90
    hàng, 0 ô lệch**.
  - Script đối chiếu commit kèm artifact.
- 🔴 **Ngoại lệ có ý thức với docstring E8** *"E8 không tự tải — lớp gác không được phụ thuộc vào
  chính thứ nó giám sát"*. Đường nhập kho là một **cờ riêng** trên E8 (không thêm entrypoint thứ 9,
  `L-Z36`).
  - Ý của câu docstring vẫn giữ: `--snapshot-before`/`--verify-after` **không gọi** đường nhập, và
    đường nhập **không gọi** lớp gác.
  - Đường nhập **từ chối ghi đè** mọi file đã tồn tại. Thư mục rổ là thư mục mới, nên không có nến cũ
    nào để mất.
- **Tháng thiếu giữa khoảng tồn tại** (404 ở một tháng nằm giữa `thang_dau` và `thang_cuoi` theo
  `TD-0230`) ⇒ **từ chối**, không lấp, không bỏ qua (N6).
- **Kiểm đủ rổ bằng máy** trước khi coi `TD-0247` xong. Cờ E8 kiểm từng mã trong
  `config/pool_t1.yaml`: đủ 6 file, không rỗng, không có nến sau `T2`, bắt đầu đúng mốc, kết thúc đúng
  mốc (hoặc đúng tháng huỷ niêm yết).

---

## 5. PHỤ LỤC 17/09/2026 (2) — nến "chết" sau khi sàn ngừng giao dịch (chủ dự án chốt, viết TRƯỚC code)

**Sự việc đo được (0 trial, nến 1h của kho + API funding lịch sử):** lần nhập kho đầu tiên dừng đúng
theo chốt §4 ở `FLMUSDT`: kho không có funding tháng 12/2025, dù `TD-0230` ghi mã tồn tại tới 2026-08.
Đo tiếp thì thấy không phải kho thiếu file:

| Mã | Nến cuối có volume > 0 | Sau đó | Funding |
|---|---|---|---|
| `MKRUSDT` | **2025-09-08 08:00** | 543 nến 1h tháng 9 + mọi tháng sau: `high = low`, `volume = 0`, đứng ở **1650,1** | kho và API cùng dừng **08/09/2025** |
| `FLMUSDT` | **2025-11-21 08:00** | nến phẳng `volume = 0`, đứng ở **0,0082** (đầu tháng 11: 0,0248, tức **−67%** trước khi huỷ) | kho dừng sau 11/2025, API trả 0 bản ghi |
| `ICX` · `OM` · `TON` · `AERGO` | tới hết 01/2026, `volume > 0` | — | đủ |

⇒ Sau khi sàn ngừng giao dịch, kho vẫn sinh nến ở **giá thanh toán**, khối lượng 0, không funding, kéo
dài nhiều tháng. `khoang_ton_tai` của `TD-0230` suy từ **sự tồn tại của file nến**, nên **đánh giá quá
đời sống** của những mã này. Rổ `T1` không bị ảnh hưởng vì cả hai còn giao dịch tại `T1`; con số đó
chỉ sai khi dùng cho các mốc muộn hơn.

**Chủ dự án chốt: cắt dữ liệu tại nến cuối có giao dịch.**

- **Mốc ngừng giao dịch** của một mã = mốc mở của **nến 1h futures cuối cùng có `volume > 0`**, nếu
  mốc đó sớm hơn `T2 − 1 giờ`. Máy **đo**, không gõ tay ngày.
- Cả 6 loại file của mã đó giữ `date ≤ mốc ngừng`, **không tải** các tháng sau tháng ngừng. Vì vậy
  funding 404 sau khi ngừng không còn là lỗi, còn 404 **trước** mốc ngừng vẫn là lỗi (§4).
- **Lý do:** giữ nến chết cho phép backtest mở lệnh vào một thị trường đã đóng (lệnh ma). Còn vị thế
  đang mở lúc ngừng được chốt ở giá nến cuối, trùng với giá thanh toán của sàn. Loại hẳn MKR/FLM thì
  mất đúng hai mã chết trong WFO (FLM −67%), tức lệch sống sót theo chiều đẹp.
- **Mốc ngừng ghi thành artifact có bằng chứng** (`docs/du-lieu-do/td0247-moc-ngung-giao-dich.json`:
  mốc, giá đóng nến cuối, số nến phẳng phía sau). Bộ kiểm đủ rổ đọc artifact đó. Mã kết thúc trước `T2`
  mà **không có** trong artifact thì bộ kiểm báo lỗi.
- **Bộ kiểm còn soi đuôi nến chết ở MỌI mã** (kể cả mã tải bằng Freqtrade): ≥ 24 nến 1h liền nhau ở
  cuối file có `volume = 0` mà mã không có trong artifact ⇒ báo lỗi. Không tin rằng *"mã đang TRADING
  thì không có nến chết"*.
