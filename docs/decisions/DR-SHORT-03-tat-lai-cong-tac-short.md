# DR-SHORT-03 — Tắt lại công tắc Short chung (`tier_a.enable_short: false`)

> **Ngày chốt:** 25/09/2026 · **Người quyết:** chủ dự án (*"Ngưng hệ thống, thiết kế lại"*, *"Dừng hết, kể cả D10"*) · phiên
> mã `12c579bc` thi hành. **Chi phí:** 0 trial. Mã `DR-SHORT-03` + `TD-0415` đặt chỗ bằng commit `82fa025`. Commit
> **RIÊNG và TRƯỚC** khi lật khoá.

> 🔴 **PHIÊN IDEA/CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`).

## 1. Quyết định

- `tier_a.enable_short` về **`false`**. Lý do duy nhất để bật (`DR-SHORT-02`) là chân Short của rổ `IQ-0003`; ứng viên đó đã
  dừng ở WFO (`DR-KET-CUC-IQ0003-01`), nên không còn ứng viên nào cần chân Short.
- Trạng thái Short trở về như `DR-SHORT-01`: đường Short **đã dựng**, khâu **đo** ⏸. Điều kiện mở lại của `DR-HUONG-01` §3 và
  `DR-D4-01` §2b đứng nguyên từng chữ.
- `DR-SHORT-02` §5 đã cho phép lật về vì lỗi API mà không cần DR mới. Lần tắt này vì lý do **khác** (ngưng hệ thống), nên
  ghi thành DR.

## 2. Lần bật vừa qua — số liệu, không suy diễn

- Có hiệu lực ở dry-run từ ~04:31 UTC ngày 25/09/2026, trước commit `5fc1cbb` (`MT-86`), tới lúc dừng bot (§3).
- Sổ dry-run (`user_data/tradesv3_dryrun.sqlite`, đọc 25/09/2026): **0 lệnh Short**, 0 lệnh đang mở, 3 lệnh Long đã đóng.
- Không thấy lỗi giới hạn API nào trong log dry-run (điều kiện đảo ngược của `DR-SHORT-02` §5 không kích hoạt).

## 3. Kèm theo — ngưng hệ thống (`TD-0415`)

- Dừng `dryrun` + `dryrun-watchdog` (profile `van_hanh`). Chạy lại: `docker compose -f docker/docker-compose.yml --profile
  van_hanh up -d`.
- D10 cho `IQ-0003` không chạy (`DR-KET-CUC-IQ0003-01` §3).

## 4. Thi hành

- `config/tool_d_config.yaml`: `enable_short: false`, chú thích trỏ DR này.
- `tests/lock/test_td0321_duong_short_backtest_that.py`: ghim về `False`, nêu DR này. Các fixture/ca đã sửa ở `TD-0402` căn lại
  sao cho khẳng định hành vi không đổi.
- `L-Z56` không đổi. Với Short tắt, E3 hết bị chặn vì thiếu Δ_R(SHORT).
