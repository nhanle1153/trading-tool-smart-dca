# DR-D11-03 — Risk Supervisor: tiến trình riêng chạy được (TD-0241, phần còn lại sau L-Z44)

> Commit RIÊNG và TRƯỚC mọi dòng code, theo đúng khuôn `DR-D4-08`/`DR-D11-01`/`DR-D11-02`.
> Phần `L-Z44` (đối chiếu 5 hằng số + AST "không import code bot") đã xong ở `ac3f06f`/`7a90c99`
> (phiên `-3f`) — DR này KHÔNG đụng lại, chỉ giải phần còn lại mà `TASKS.md` ghi là "CHẶN BỞI
> QUYẾT ĐỊNH KIẾN TRÚC": **tiến trình riêng chạy được** + gọi Freqtrade API để dừng bot khi
> `LIQUIDATED`.

## 1. Ba quyết định — chủ dự án chốt qua `AskUserQuestion` (phiên `-a5`, 13-14/09/2026)

Đây là quyết định kiến trúc thuần tuý (`risk_supervisor.py:12-15` đã tự khai "CHƯA CHỐT — không tự
chọn"), theo đúng quy tắc gốc 2 — trình bày trade-off, không tự chọn:

1. **Phát hiện `LIQUIDATED`: REST polling qua `GET /fapi/v1/forceOrders?autoCloseType=LIQUIDATION`**,
   không phải WebSocket User Data Stream. Lý do đã trình: tái dùng đúng mô hình request/response +
   circuit breaker đã có (`_kiem_tra_breaker`/`ghi_nhan_ket_qua`), không thêm thư viện/mô hình kết
   nối bền mới. Đánh đổi chấp nhận: độ trễ phát hiện bằng đúng chu kỳ poll (mặc định 60s).
2. **Phạm vi "dừng toàn hệ thống": gọi LUÔN Freqtrade REST API để dừng bot thật** trong task này —
   không chỉ ghi cờ đỏ chờ nối sau. Mở rộng "Tiêu chí XONG" gốc của TD-0241 trong `TASKS.md`.
3. **Tiến trình chạy dạng module độc lập ngoài `entrypoints/`** — không phải entrypoint thứ 9
   (L-Z36 khoá cứng 8 file), không phải một service Docker dài hạn mới (project hôm nay không có
   service nào chạy nền, mọi service là `run --rm`). 🔄 **Điều chỉnh vị trí file so với plan gốc,
   theo bằng chứng mới phát hiện lúc bắt tay vào code:** phiên song song `-91` đang dựng
   `src/tool_d/ops/` (package mới, TD-0209 — `heartbeat.py`/`heartbeat_watchdog.py`/
   `telegram_client.py`) làm đúng khuôn "tiến trình vận hành, không phải entrypoint đo lường" mà DR
   này cũng cần — `heartbeat_watchdog.py` đã có sẵn mẫu chính xác (`chay_mot_vong()` thuần + trạng
   thái bất biến + `main()` khung CLI mỏng, `# pragma: no cover`). Đặt
   `src/tool_d/ops/risk_supervisor_daemon.py` (sibling file, KHÔNG sửa 3 file/`__init__.py` của
   `-91`) thay vì một thư mục `ops/` cấp gốc mới — tránh hai quy ước "ops" khác nhau cùng tồn tại
   trong một repo. Đã báo `-91`/`-ef` trước khi thêm file.

## 2. Bằng chứng đọc mã nguồn Freqtrade (image `docker-freqtrade:latest`, tag `2026.7`)

Đọc trực tiếp trong container (`docker run --rm --entrypoint sh docker-freqtrade:latest -c '...'`),
không đoán — cùng khuôn đã dùng ở TD-0028.

### 2.1. Endpoint đúng nghĩa "dừng TOÀN HỆ THỐNG"

`freqtrade/rpc/api_server/api_trading.py:327-334`:

```python
@router.post("/stop", response_model=StatusMsg, tags=["Bot-control"])
def stop(rpc: RPC = Depends(get_rpc)):
    return rpc._rpc_stop()

@router.post("/pause", ...)
@router.post("/stopentry", ...)
@router.post("/stopbuy", ...)
def pause(rpc: RPC = Depends(get_rpc)):
    return rpc._rpc_pause()
```

`/stop` dừng HẲN vòng lặp bot (`State.STOPPED`); `/stopentry`/`/stopbuy`/`/pause` chỉ CHẶN mở lệnh
mới, giữ nguyên vị thế đang mở. §6.6(2) nói "cờ đỏ dừng TOÀN HỆ THỐNG" — chọn `/stop`, không phải
`/stopentry`.

`freqtrade/rpc/rpc.py:978-983` (`_rpc_stop`) — **idempotent, không lỗi khi gọi lặp lại**:

```python
def _rpc_stop(self) -> dict[str, str]:
    if self._freqtrade.state != State.STOPPED:
        self._freqtrade.state = State.STOPPED
        return {"status": "stopping trader ..."}
    return {"status": "already stopped"}
```

R9 (idempotency) thoả sẵn ở phía Freqtrade — daemon gọi lặp lại không cần tự khử trùng lặp.

### 2.2. Xác thực

`freqtrade/rpc/api_server/webserver.py:222-230`:

```python
app.include_router(api_v1, prefix="/api/v1", dependencies=[Depends(http_basic_or_jwt_token)])
app.include_router(api_trading, prefix="/api/v1", tags=["Trading"],
                    dependencies=[Depends(http_basic_or_jwt_token), Depends(is_trading_mode)])
```

`http_basic_or_jwt_token` (`api_auth.py`) chấp nhận **HTTP Basic TRỰC TIẾP** (không bắt buộc bước
`/token/login` lấy JWT trước — JWT chỉ là lựa chọn thay thế). Chọn Basic: ít bước hơn, ít điểm lỗi
hơn cho một lời gọi khẩn cấp. `is_trading_mode` nghĩa là `/stop` chỉ tồn tại khi Freqtrade đang chạy
ở chế độ trading thật (không phải lúc backtest CLI) — đúng phạm vi "chỉ có ý nghĩa khi có bot sống",
khớp với "Ngoài phạm vi" đã ghi (mục 4 dưới).

### 2.3. Cấu hình `api_server` — KHÔNG đụng `config/freqtrade/config.json` dùng chung

`freqtrade/config_schema/config_schema.py` — `api_server` schema:

```json
"required": ["enabled", "listen_ip_address", "listen_port", "username", "password", "jwt_secret_key"]
```

Bốn trường `username`/`password`/`jwt_secret_key` **không có default hữu dụng** một khi khoá
`api_server` xuất hiện trong config — đúng lý do bản chú thích cũ trong `config.json:116` đã né hẳn
khoá này. `freqtrade/configuration/configuration.py:79-84` xác nhận **thứ tự nạp**:

```python
config: Config = load_from_files(self.args.get("config", []))
if self.args.get("command") not in NO_CONF_ALLOWED:
    env_data = environment_vars_to_dict()          # FREQTRADE__{section}__{key}
    config = deep_merge_dicts(env_data, config)      # ← merge TRƯỚC mọi _process_*/validate
```

⇒ `FREQTRADE__API_SERVER__*` nạp **trước** khi có bất kỳ bước validate schema nào chạy (các lệnh CLI
gọi `validate_config_consistency` sau khi `Configuration.get_config()` đã trả về config ĐÃ merge).

🔴 **Nhưng đây chính là lý do KHÔNG sửa `config/freqtrade/config.json` dùng chung**: một khi khoá
`api_server` xuất hiện trong BẤT KỲ file config nào được truyền vào Freqtrade, ba biến ENV
`FREQTRADE__API_SERVER__USERNAME/PASSWORD/JWT_SECRET_KEY` trở thành **bắt buộc cho MỌI lời gọi
Freqtrade dùng file đó** — kể cả các entrypoint E1-E3 chạy backtest thuần tuý mà 5-6 phiên song song
đang chạy hàng ngày. Thêm khoá vào file dùng chung sẽ làm **mọi backtest hiện tại** vỡ nếu ai chạy
mà thiếu ba biến ENV đó — một thay đổi "affecting shared systems" không cân xứng với lợi ích (Risk
Supervisor chỉ cần dùng nó từ D11).

**Quyết định:** tách khối `api_server` ra **file cấu hình phụ RIÊNG**,
`config/freqtrade/config.risk_supervisor.json` (mới, commit, KHÔNG chứa secret — chỉ
`enabled`/`listen_ip_address`/`listen_port`), chỉ được truyền vào Freqtrade qua tham số `-c` THỨ HAI
lúc D11 thật sự khởi động một tiến trình bot sống (`freqtrade trade -c config/freqtrade/config.json
-c config/freqtrade/config.risk_supervisor.json`). Không ai dùng flag `-c` thứ hai này hôm nay ⇒
0 ảnh hưởng tới backtest/D4 đang chạy. `listen_ip_address` PHẢI là `127.0.0.1`, không bao giờ
`0.0.0.0` — control API của bot không có lý do gì để nghe ngoài localhost.

### 2.4. `GET /fapi/v1/forceOrders?autoCloseType=LIQUIDATION` — xác nhận qua `ccxt` (bundled trong
chính image, `binance.py:13351`)

```python
if type != 'spot':
    request['autoCloseType'] = 'LIQUIDATION'
...
response = self.fapiPrivateGetForceOrders(self.extend(request, params))
```

Response (linear futures, comment `ccxt/binance.py:13405-13424`, xác nhận bằng mã nguồn thật thay
vì trang docs render-JS không đọc được qua WebFetch):

```
[{"orderId": ..., "symbol": ..., "status": "FILLED", "clientOrderId": "autoclose-...",
  "price": ..., "avgPrice": ..., "origQty": ..., "executedQty": ..., "cumQuote": ...,
  "side": ..., "positionSide": ..., "time": <ms>, "updateTime": <ms>, ...}]
```

`autoCloseType` là tham số REQUEST lọc phía server (không phải trường trong response) — endpoint chỉ
trả các lệnh KHỚP bộ lọc khi được truyền, nên **bất kỳ phần tử nào trong mảng trả về ⇒ đã có ít nhất
một lệnh bị thanh lý**. `time` (ms) là mốc tạo lệnh, dùng làm cơ sở lọc "mới hơn từ_thời_điểm".

## 3. Ngoài phạm vi (không đổi so với plan đã duyệt)

- Topology mạng thật daemon ↔ Freqtrade sống (Docker network / `127.0.0.1`) — quyết ở D11 setup.
- Kênh cảnh báo Telegram (TD-0209, 0 dòng code) — chưa nối.
- Cơ chế khởi chạy tiến trình bền vững (systemd/Task Scheduler/service dài hạn) — quyết ở D11 setup.

## 4. Cập nhật "Tiêu chí XONG" của TD-0241 (`TASKS.md`)

Giữ nguyên chữ cũ (rule 5), thêm dòng: tiến trình `ops/risk_supervisor_daemon.py` chạy được (kiểm
bằng test có `--max-iterations` hữu hạn + smoke test thủ công fail-closed khi thiếu credential),
`grep` import xác nhận không trỏ vào chiến lược (đã có máy kiểm AST trong `test_lz44_...py`, mở rộng
sang các file mới — xem mục 5), và khi `LIQUIDATED`/breaker `dung_han` xảy ra, daemon gọi
`POST /api/v1/stop` (module `freqtrade_control.py`) trước khi tự thoát.

## 5. Mở rộng lock test hiện có (theo đề xuất của phiên `-3f`, KHÔNG viết lock test thứ hai)

`tests/lock/test_lz44_khai_lai_hang_so_supervisor.py`: đổi `FILE_SUPERVISOR` (một đường dẫn) thành
tuple đường dẫn, thêm `src/tool_d/api_client/freqtrade_control.py` và
`src/tool_d/ops/risk_supervisor_daemon.py`; hai ca AST hiện có (`test_khong_import_code_bot`,
`test_chi_dung_thu_vien_chuan`) lặp trên tuple. Mở rộng `cho_phep` cho các module HTTP CHUẨN
(`urllib.request`, `urllib.parse`, `urllib.error`, `http.client`, `json`, `argparse`, `sys`,
`logging`, `time`) — KHÔNG thêm `requests`/`httpx` (giữ đúng khuôn `binance_public.py`, không thêm
phụ thuộc mới, R1 single egress không cần thư viện thứ hai).
