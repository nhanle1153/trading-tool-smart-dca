# DR-D0PRE-02 — Chốt `N_ĐĂNG_KÝ`

> TD-0032, việc thứ (3) trong thứ tự cứng của Khối 3 — chỉ được làm **sau** TD-0030 (verify
> zone_width) và TD-0031 (xác nhận DOF). 🔴 **L-Z29 đã PASS trước khi commit DR này**
> (spec dòng 4424: "L-Z29 PASS trước khi commit").

## 1. Input từ hai việc trước

- **TD-0030** (`DR-D0PRE-01`): `zone_width_min_atr` là **code chết**, đã xoá hẳn khỏi
  `tool_d_config.yaml`. Theo bảng đối chiếu spec (dòng 4423): chết → 114 tham số hiệu dụng
  cho công thức ngân sách, không phải 120.
- **TD-0031** (`config/dof_inventory.yaml` + `dof.py`): xác nhận độc lập bằng hai phép cộng
  trực tiếp — `DOF_gốc = 28` ✅, `|tier_b| = 12` ✅ — khớp đúng bảng DR-010 sau khi zone_width
  bị xoá.

## 2. Công thức ngân sách (DR-010, spec dòng 3226-3232)

```
N_ĐĂNG_KÝ = B0 + B1 + B2 + B3
B0. Pool §0.3(i)-(iv)          1 trial/tiêu chí, KHÔNG tune         =  4
B1. Calibration                 3 giá trị × 12 tham số × 2 hướng    = 72
B2. Ablation D0.9                9 cấu hình × 2 hướng                = 18
B3. Dự phòng                     sự cố dữ liệu / chạy lại do bug     = 20
                                                                    ─────
N_ĐĂNG_KÝ                                                            = 114
```

Xác nhận bằng máy (`dof.py`, `assert_dof_or_block()`, test `L-Z29`):
```
4 + 3×12×2 + 9×2 + 20 = 4 + 72 + 18 + 20 = 114
```

## 3. Quyết định

**`N_ĐĂNG_KÝ = 114`.**

Con số này đi thẳng vào công thức DSR ở §10.2 (rào Sharpe ≈ √(2·ln 114) ≈ 3.08, xác nhận bằng
`gates/dsr.py` ở TD-0033) — mọi kết quả GATE D0.9 (§10.1) từ đây trở đi tính DSR-adjusted
expectancy trên N=114, không phải một hằng số khác.

## 4. Ràng buộc đi kèm quyết định này (không được vi phạm sau khi commit)

- **Ngân sách B3 (20 trial dự phòng)** không phải "chỗ trống muốn dùng sao cũng được" — mọi lần
  tiêu một trial B3 phải ghi vào `trial_registry.jsonl` với `budget_line: "B3"` (DR-014), và
  `_budget_remaining_B3` trong `tool_d_config.yaml` giữ `null` vĩnh viễn (MT-03) — registry là
  nguồn sự thật duy nhất cho số dư B3, không phải con số này.
- **B3 giảm về 0 → KHÔNG được đổi** — phải mở giả thuyết mới ở NGÂN SÁCH A và chạy lại chu trình
  với lockbox MỚI (DR-012, spec dòng 2270-2274). Không tự ý nới B3.
- **N_ĐĂNG_KÝ chỉ tăng theo quy tắc `floor(số lệnh mới / 25)`** sau khi vào live (§12c.2/3),
  không tăng tay tuỳ tiện — canh bởi L-Z27.
- Nếu về sau phát hiện overlap pool đáng kể với Tool A (DR-007, §9), N có thể chuyển sang
  **union DSR** — đó là một quyết định RIÊNG, không tự động áp dụng ở đây.

## 5. Verify

```
docker compose run --rm tests -k lz29        → 8 passed (chạy TRƯỚC khi commit DR này)
docker compose run --rm --entrypoint python tests -m tool_d.config.dof --check
    → DOF_gốc=28 ✅, tier_b=12 ✅, N_ĐĂNG_KÝ=114
```

## 6. Lịch sử

| Ngày | Sự kiện |
|---|---|
| 06/09/2026 | Chốt `N_ĐĂNG_KÝ = 114`, sau khi L-Z29 PASS (TD-0032) |
