# research-log.md — Nhật ký nghiên cứu Tool D

> **Append-only.** Không sửa, không xoá mục cũ. Ghi theo ngày, mục mới xuống dưới.
> Bắt buộc ghi mỗi lần: chẩn đoán "bot sai hay tầng đo sai" (§0d.7), quyết định chọn mốc dữ liệu
> (DR-011), và mỗi rủi ro tồn dư được chấp nhận có ý thức.

---

## 06/09/2026 — Khởi tạo repo, Giai đoạn 1–2

- Khởi tạo git repo, cây thư mục, 4 file quy trình.
- Chốt 7 quyết định nền tảng (xem `back-end-note.md` §0.2 và bảng đầu `TASKS.md`).
- Ghi nhận 7 mâu thuẫn, 5 trong đó đã chốt cách giải ngay (`back-end-note.md` mục 7).

### Rủi ro tồn dư được chấp nhận có ý thức

**RR-01 — L-Z25 không chứng minh được tuyệt đối rằng chưa từng chạy hyperopt.**
Spec (dòng 510) đòi grep cả "lịch sử lệnh". Kiểm được: `git grep` trên worktree,
`git log -S hyperopt --all` (bắt cả file đã xoá rồi), và `runs/cmd_audit.log` do wrapper tự ghi.
KHÔNG kiểm được: người dùng gõ thẳng `docker run ... freqtrade hyperopt` ngoài wrapper.
Chấp nhận vì cùng loại với thừa nhận của chính spec ở dòng 3317–3320 (cơ chế lockbox không cứng)
và 3507–3510. Biện pháp bù duy nhất là kỷ luật cá nhân — đã ghi thành điều cấm N3 trong `CLAUDE.md`.

**RR-02 — Lockbox chỉ tồn tại trên một ổ đĩa.** Dữ liệu lockbox không commit lên git (kích thước),
và spec dòng 4002 nói rõ không có lockbox thứ hai. Mất ổ = mất khả năng xác nhận cuối cùng của
cả dự án. Đã mở TD-0085 (backup ngoài git + **test khôi phục thật**) và OQ-08. Cho tới khi TD-0085
xong, đây là điểm hỏng đơn lẻ nghiêm trọng nhất của toàn bộ hạ tầng.

## 06/09/2026 — TD-0031, phát hiện lỗi số học trong comment gốc của spec §6.9.5

Xác nhận lại bảng DOF của DR-010 từng dòng (yêu cầu TD-0031). Hai phép cộng trực tiếp đều khớp
số cuối cùng của spec:
- Σ(v5 của 26 dòng bảng) + Σ(2 mục "bỏ sót" DG7, w_tranche) = 26 + 2 = **28** = DOF_gốc ✅
- Σ(cột dof_v6 của 26+2 dòng) = **12** = |tier_b| ✅

Nhưng **chuỗi trừ trung gian** trong comment gốc (chép nguyên văn từ spec §6.9.5 vào
`tool_d_config.yaml` ở TD-0013, trước khi TD-0031 sửa lại):
```
28 - 6 (đóng băng) - 4 (pool→B0) - 2 (xoá §2.4,§3.3c)
   - 1 (mult_dd→Cấp C) - 1 (L_BASE→mult_regime đóng băng)
   - 1 (zone_width, có điều kiện) = 12
```
Tính literal: `28−6−4−2−1−1−1 = 13`, không phải 12. **Nguyên nhân:** khoản "−1
(L_BASE→mult_regime đóng băng)" bị đếm **hai lần** — `mult_regime` (dof=−1) đã nằm sẵn trong
tổng "−6 (đóng băng)" của `tier_frozen` (5 khoá đóng góp: w_zss −2, mult_regime −1,
tp2_trail_atr −1, dg6b_bars_1h −1, trend_age_days −1 = −6), không phải một khoản trừ độc lập.

**Mức độ:** không phải mâu thuẫn 🔴 chặn tiến độ — không đổi bất kỳ số quyết định nào
(`tier_b=12`, `DOF_gốc=28`, `N_ĐĂNG_KÝ=114` đều được xác nhận độc lập bằng phép cộng trực tiếp,
không đi qua chuỗi trừ có lỗi). Xử lý: `config/dof_inventory.yaml` (TD-0031) dùng cách kiểm
KHÔNG đi qua chuỗi trừ này — cộng trực tiếp cột `v5`/`v5_dung_ra` và cột `dof_v6` của từng dòng.
`src/tool_d/config/dof.py` (`dof_report()`/`assert_dof_or_block()`) tự động hoá phép kiểm này,
canh bởi L-Z29 vế (b).

**Bài học:** đây đúng loại lỗi mà chính DR-010 sinh ra để chặn (v5 cũng từng có phép trừ không
ra số đúng, dòng 3168-3180 của spec) — cho thấy kiểm bằng tay dễ sai ngay cả khi người viết đã
cẩn thận, và củng cố lý do L-Z29 phải là kiểm TỰ ĐỘNG, không phải đối chiếu bằng mắt.

## 06/09/2026 (buổi tối) — 3 lần đánh dấu sai TASKS.md do 2 phiên chung 1 thư mục

Trong một phiên làm Khối 5, phát hiện **3 lần riêng biệt** một dòng `TASKS.md` bị đánh dấu ✅ dù
chưa có code/test thật tương ứng trên đĩa:

1. TD-0051 (`ledger/registry.py`) — do `sed` của chính phiên này chạy đúng lúc phiên kia cũng đang
   sửa `TASKS.md`, `git add` gộp cả hai thay đổi vào một commit.
2. TD-0052→0056 (5 dòng liền, Khối 5) — cùng cơ chế, quy mô lớn hơn (5 dòng một lúc).
3. TD-0057 (nối E6 vào E1/E2/E3) — `git add TASKS.md` chụp luôn một thay đổi ✅ mà phiên kia vừa
   ghi song song, trong khi `grep run_audit entrypoints/*.py` xác nhận E1/E2/E3 chưa hề gọi hàm đó.

**Nguyên nhân gốc:** `TASKS.md` là bảng sửa-tại-chỗ (mỗi lần đổi trạng thái = ghi đè dòng cũ), và
`git add <file>` chụp toàn bộ nội dung trên đĩa tại thời điểm gọi — không có cách nào để `git add`
phân biệt "dòng tôi vừa sửa" với "dòng phiên kia đang gõ dở cùng lúc" khi cả hai cùng sửa một file.

**Quyết định của chủ dự án** (hỏi trực tiếp, không tự chọn): KHÔNG đổi định dạng `TASKS.md` sang sổ
nhật ký append-only (dù đúng pattern MT-01 đã dùng cho `trial_registry.jsonl`), KHÔNG chuyển sang
git worktree riêng cho mỗi phiên — giữ nguyên cách làm việc hiện tại (2 phiên chung 1 thư mục), chỉ
**siết kỷ luật git**. Đã ghi thành quy tắc bắt buộc ở `CLAUDE.md` mục N12: luôn `git diff` đối chiếu
trước khi commit đụng `TASKS.md`, không bao giờ tin một dòng ✅ mà không xác minh bằng chứng trên
đĩa trước khi dùng nó làm điều kiện phụ thuộc cho việc tiếp theo.

**Rủi ro tồn dư đã chấp nhận có ý thức:** kỷ luật git là biện pháp con người, không phải cơ chế kỹ
thuật — vẫn có thể tái diễn nếu một phiên quên đối chiếu diff. Không có lớp chặn tự động nào khác
được dựng thêm theo quyết định này.
