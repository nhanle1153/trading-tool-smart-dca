# DR-D1-02 — Dựng lại rổ pool point-in-time có xuất xứ (H1-D, TD-0247)

> TD-0247, đường A-đầy-đủ của `MT-34` (chốt 13/09/2026, xác nhận lại 16/09/2026 — `MT-45`).
> Commit **RIÊNG và TRƯỚC** mọi dòng mã của TD-0247; thứ tự kiểm bằng
> `git merge-base --is-ancestor <commit DR này> <commit mã đầu tiên>`, không bằng mắt
> (khuôn `DR-D3-01`/`TD-0243`).
>
> **Đánh số:** dùng `DR-D1-02` (nối lineage `DR-D1-01`, cùng chủ đề H1-D/nguồn dữ liệu lịch sử),
> KHÔNG dùng `DR-D4-13` — dãy số đó phiên song song `-22` đang giữ cho `MT-24`/`MT-25` (đã nhắn
> xác nhận qua N12 mục 6, không trùng).

## 0. Vấn đề

`config/pool.yaml` (102 mã "trading") chốt bằng tiêu chí đo tại **09/2026** rồi dùng cho toàn bộ
`[T1,T2]` (WFO + Ablation D4). `TD-0231` đo pool ĐÚNG tại `T1` (bằng `pairlist_point_in_time()`,
`src/tool_d/pool.py:91`) = **116 mã**; chung với `pool.yaml` chỉ **55**. `K = 61` (52,6%) mã đủ
tiêu chí tại `T1` nhưng vắng khỏi `pool.yaml` — gấp hơn năm lần ngưỡng ≲10% viết trước khi đo
(`td0231-pool-point-in-time.json`, commit `ab290eb`) ⇒ theo cách đọc đã viết trước, đây là kết cục
**"K lớn"**, WFO đang đo sai rổ theo chiều PASS. `TD-0230`/`DR-D1-01` §3 đã cấm chấp nhận
survivorship bias — không có đường thứ hai ngoài dựng lại rổ có xuất xứ.

## 1. Ba điều kiện đã biết (thi hành, không phải quyết định)

**(a) `build_pool.py` (nay `entrypoints/build_pool.py:210-216`) từ chối ghi đè `config/pool.yaml`**
khi file đã tồn tại, tự khai đường hợp lệ duy nhất là *"xoá thủ công + ghi DR mới"* (exit
`EXIT_POOL_ALREADY_COMMITTED`). DR này thoả điều kiện đó cho phần **đo lại** (không đổi
`pool.yaml`); nếu sau này quyết đưa rổ mới vào sản xuất thay `pool.yaml` hiện tại, đó là một quyết
định RIÊNG, cần DR riêng — **không nằm trong phạm vi DR này**.

**(b) Phạm vi "số cũ mất hiệu lực" (spec dòng 4338) là các số QUY ĐỔI SANG POOL**, không phải mọi
con số: `325,6` (lệnh/năm quy đổi, `DR-D4-10` §2.1), `n = 206`, `44,8`, phép so sàn 150 của Nhánh 1.
Phép đếm **EXPLORE thô** (0 trial, không quy đổi pool) vẫn đúng nguyên — không cần đo lại các
artifact `td0212`/`td0228`/`dg2-explore-quet-arm`.

**(c) Rổ backtest 102 mã hôm nay KHÔNG CÓ XUẤT XỨ MÁY**: `runs/pool_pairs.json` (danh sách
`download-data` đã dùng) không được git theo dõi, và không có bộ sinh nào trong repo tái lập được
nó. Rổ mới của DR này **phải** sinh bằng mã có xuất xứ (script + tham số + commit), nếu không lặp
lại đúng lỗi đang sửa.

## 2. Quyết định 1 — ranh giới §9c.4b cho 9 mã đã bị xếp EXPLORE

### 2.1. Sự việc đo được (16/09/2026, đối chiếu `td0231-pool-point-in-time.json` với
`config/pool.yaml`, 0 trial)

Trong `K = 61` mã, **9 mã** vừa (i) đủ tiêu chí §0.3 tại `T1` (thuộc `K`, tức thuộc "pool đúng" 116
mã) **vừa** (ii) đang đứng trong khối `explore:` của `config/pool.yaml` (dòng 108 trở đi) — một
phân loại §9c.4b THẬT do `compute_pool()` sinh ra bằng dữ liệu hiện tại (09/2026), không phải tình
cờ nằm trong thư mục lưu trữ:

```
ARKMUSDT · BRETTUSDT · CETUSUSDT · MEUSDT · PNUTUSDT · RENDERUSDT · SEIUSDT · THETAUSDT · XTZUSDT
```

Cả 9 mã đều có dữ liệu OHLCV thật sẵn trong `user_data/data/explore/futures/` (khớp qua base
symbol, ví dụ `ARKM_USDT_USDT-1h-futures.feather`).

### 2.2. Vì sao chữ spec không giải được tình huống này một mình

Spec dòng 3831-3833 (§9c.4b, ràng buộc (b)): *"Coin nào đã ở EXPLORE thì KHÔNG BAO GIỜ được đưa
vào pool giao dịch sau này — kể cả khi nó bắt đầu thoả tiêu chí §0.3. Không có ngoại lệ; ngoại lệ
sẽ biến EXPLORE thành tập train."* Câu này viết cho **chiều thời gian xuôi**: một mã từng bị xếp
EXPLORE, rồi SAU ĐÓ (muộn hơn) thoả tiêu chí trở lại — cấm cho nó "lên hạng". Cơ chế thi hành
tương ứng đã có sẵn ở `pairlist_over_time()` (`pool.py:120-157`, tập `permanently_excluded` cộng
dồn theo thời gian).

Trường hợp 9 mã này **ngược chiều**: chúng bị xếp EXPLORE ở mốc **muộn hơn** (09/2026, khi
`pool.yaml` được chốt), còn giai đoạn ta muốn đưa chúng vào lại (`T1`, giữa 2025) là **sớm hơn**
mốc xếp loại đó. Chữ spec không có điều khoản cho hướng này — đây chính là khoảng hở `TD-0247` yêu
cầu quyết trong DR, không tự quyết.

### 2.3. Quyết định (chốt qua `AskUserQuestion` với chủ dự án, phiên này)

**Loại vĩnh viễn — giữ nguyên cả 9 mã trong EXPLORE, KHÔNG đưa vào rổ pool `T1` mới, dưới bất kỳ
hình thức nào (kể cả gắn nhãn "chỉ dùng lại dữ liệu, không tính là lên hạng").**

**Lý do:**
- Nhất quán với văn bản chữ "không có ngoại lệ" — thà xử lý bảo thủ hơn phạm vi chữ viết còn hơn
  đọc hẹp một khoảng hở rồi tự suy diễn ngoại lệ có lợi cho chính việc đang làm.
- Cùng khuôn lý luận đã dùng ở `MT-22` (chọn phương án A vì "hướng sai của A an toàn hơn hướng sai
  của B"): hướng sai của việc LOẠI (rổ `T1` thiếu thêm 9 mã, tổng thiệt hại tối đa +9/116 ≈ 7,8
  điểm phần trăm so với pool đúng lý thuyết) an toàn hơn hướng sai của việc NHẬN (nếu dữ liệu 9 mã
  này từng — hoặc sau này — được dùng để sinh một ý tưởng qua kênh EXPLORE, đưa chính mã đó vào tập
  đo hiệu năng sẽ biến EXPLORE thành tập train một cách không kiểm chứng được, đúng thứ ràng buộc
  (b) tồn tại để chặn).
- Ranh giới này phải là **quy tắc theo MÃ**, không theo "đã từng được phân tích hay chưa" — dự án
  nhất quán từ chối các lớp canh dựa trên "kỷ luật con người"/lời khai không kiểm chứng được (N6,
  L-Z15, `MT-11`); một quy tắc bright-line theo phân loại máy tính được là quy tắc duy nhất
  `L-Z55`/`pairlist_over_time()` có thể thi hành bằng máy.

**Hệ quả kiểm được:**
- Rổ `T1` mới sẽ có tối đa `116 − 9 = 107` mã (chưa trừ các mã không tải được dữ liệu — mục 4).
- `pairlist_over_time()` chạy trên các mốc `[T0, T1, T2]` phải tự động xếp cả 9 mã này vào
  `explore` ở **mọi** mốc từ lúc chúng lần đầu bị xếp EXPLORE trở đi (cơ chế `permanently_excluded`
  đã có, không cần sửa `pool.py`) — kiểm-có-răng: xoá một trong 9 mã khỏi `permanently_excluded`
  giả lập ⇒ nó phải xuất hiện lại ở `trading` của mốc sau, và test phải bắt được sai lệch đó.
- Không sửa `pool.py`; không thêm danh sách chặn cứng theo tên 9 mã (đó sẽ là một "nguồn sự thật
  thứ hai" ngoài `config/pool.yaml`, đúng lỗi `MT-03`) — nguồn xếp loại EXPLORE vẫn là
  `config/pool.yaml` hiện tại, đọc lại đúng cách mỗi lần cần.

## 3. Quyết định 2 — thư mục lưu dữ liệu rổ `T1` mới

Dữ liệu 52 mã còn thiếu (mục 4) **không được** đổ vào `user_data/data/binance/` (sẽ làm lệch nghĩa
pool 102 hiện tại đang neo ở đó) **cũng không** vào `user_data/data/explore/` (§9c.4b: EXPLORE
không sang pool — đổ chung thư mục sẽ xoá đúng ranh giới tầng-thư-mục dự án dùng để KHÔNG phải dựa
vào kỷ luật con người).

**Chọn:** thư mục thứ ba `user_data/data/pool_t1/` (cùng cấu trúc con `futures/` như hai thư mục
kia), trỏ tới qua `--datadir` của Freqtrade — đúng cơ chế đã dùng để tách `explore/` khỏi
`binance/`. Đây là chi tiết triển khai không ảnh hưởng hành vi hệ thống (tên thư mục), không phải
quyết định cần trình bày trade-off; nêu ở đây để không ai phải dựng lại lý do khi tới lúc code.
Nếu chủ dự án muốn tên khác, đổi tự do trước khi có dòng mã nào tham chiếu tới nó.

## 4. Ba bẫy đã biết — cách xử (thi hành, không phải quyết định mới)

**(i) `download-data --timerange` không tôn trọng mốc kết thúc** (bug đo ở `TD-0093`, 10/10 file
lấn quá `T2`). Bắt buộc đi đúng quy trình đã có: `entrypoints/backfill_data.py` (E8)
`--snapshot-before` → `download-data` → `--verify-after`, và `assert_dataset_timerange()`
(`src/tool_d/ledger/timerange.py:40`, canh bởi `tests/lock/test_lz55_ctrl_explore_timerange_self_check.py`)
phải xanh cho **mọi** mã mới trong `[T1,T2]`. Không viết lại cơ chế cắt/kiểm timerange.

**(ii) Ranh giới §9c.4b cho 9 mã** — giải ở mục 2.

**(iii) Lọc TÊN ở "phía kho" sẽ hút mã `TRADIFI_PERPETUAL`** (cổ phiếu token hoá — `AAPLUSDT`,
`ANTHROPICUSDT`…) vào pool crypto. Xác nhận cơ chế: `entrypoints/build_pool.py` (qua
`build_symbol_stats()`, `pool.py:41-54`) lọc đúng bằng `contractType == "PERPETUAL"` khi đọc
**trực tiếp từ `exchangeInfo` sống** — filter này ĐÚNG và không cần sửa. Lỗ hổng nằm ở khâu liệt kê
ứng viên từ **kho lưu trữ tĩnh** (`data.binance.vision`, cùng cơ chế `DR-D1-01` dùng — liệt kê thư
mục theo TÊN, không có trường `contractType`): `DR-D1-01` §1 tự khai đúng lỗi này (đếm nhầm 219,
trong đó có `AAPLUSDT` v.v., xem `docs/du-lieu-do/td0230-lech-song-sot-pool.json:571`, trường
`doi_chung_dr_d1_01._doc`). **Cách xử:** mọi danh sách ứng viên rút ra từ kho lưu trữ theo tên
PHẢI được đối chiếu lại với `exchangeInfo`/`SymbolStat.contractType` (hoặc một ảnh chụp lịch sử
tương đương) trước khi coi là ứng viên hợp lệ — tái dùng đúng phép đối chiếu `874 → 658` đã làm ở
`DR-D1-01`, không phát minh bộ lọc mới. Kiểm-có-răng: đưa một mã `TRADIFI_PERPETUAL` giả vào danh
sách kho ⇒ phải bị loại trước khi vào bước tải dữ liệu.

⚠️ **Mã sàn phi ASCII** (`币安人生USDT` nằm trong pool 102 hiện tại): mọi đường tải/URL trong việc
này phải chịu được (bài học 13/09 — `http.client` raise trước khi gửi nếu path chứa ký tự ngoài
Latin-1).

## 5. Phạm vi và bằng chứng

**0 trial cho toàn bộ DR + việc thi hành nó** — dựng rổ và tải dữ liệu không phải đánh giá cấu hình
(`DR-014` §2). Không đổi `config/pool.yaml` một byte trong phạm vi DR này. Tiêu chí XONG (theo
`TASKS.md` TD-0247, không lặp lại ở đây): rổ đúng tại `T1` sinh bằng mã có xuất xứ + commit; dữ
liệu `[T1,T2]` đủ cho rổ đó trong `user_data/data/pool_t1/`, đã kiểm timerange; đo lại phễu + `n` +
lệnh/năm của `Z0-T1`/`Z0`/`Z0-T0`/`Z3` trên rổ mới (kiểu EXPLORE, 0 trial), ghi file MỚI trong
`docs/du-lieu-do/`, không đụng artifact cũ; bằng chứng chạy trong Docker (N7).

## 6. Việc CHƯA nằm trong phạm vi DR này

- Đưa rổ `T1` mới thành `config/pool.yaml` sản xuất (đổi tiêu chí/rổ chính thức) — quyết định
  riêng, cần DR riêng, sau khi đã đo xong và nhìn thấy số.
- Đo lại các số quy đổi sang pool (`325,6`/`n=206`/`44,8`/so sàn 150) trên rổ mới — thuộc `TD-0184`
  sau khi `TD-0247` ✅ (đã ghi ở `TASKS.md` dòng `TD-0184`, hệ quả phạm vi).
- Bất kỳ dòng mã sản xuất nào — DR này phải commit xong (kiểm bằng `git merge-base
  --is-ancestor`) trước khi `TD-0247` có dòng mã đầu tiên.
