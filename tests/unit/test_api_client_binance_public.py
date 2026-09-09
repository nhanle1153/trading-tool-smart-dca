"""TD-0080 — api_client/binance_public.py. Test đơn vị dùng mock (không
phụ thuộc mạng thật để chạy nhanh/ổn định) — bằng chứng THẬT về độ phủ
30 ngày của OI history đã xác nhận bằng tay (curl trực tiếp) và bằng
`entrypoints/backfill_data.py --probe-coverage` thật, ghi ở
`docs/research-log.md`, không lặp lại ở đây (đúng L-Z51: không coi mock
là "đạt" cho phát hiện thật).
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from tool_d.api_client.binance_public import (
    BASE_URL,
    AggTradesNotFoundError,
    BinanceBreakerMoError,
    BinancePrivateApiError,
    BinancePublicApiError,
    _sign,
    _tran_goi_theo_phut,
    dat_lai_trang_thai_mang_cho_kiem,
    get_exchange_info,
    get_open_interest_hist,
    latency_samples_ms,
    tai_dump_agg_trades,
)


def _http_error(ma_http: int) -> HTTPError:
    return HTTPError(url="https://fapi.binance.com/x", code=ma_http, msg="mô phỏng", hdrs=None, fp=None)


def _fake_response(payload: list[dict]) -> MagicMock:
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return cm


class TestGetOpenInterestHist:
    def test_goi_dung_url_va_tra_ve_du_lieu(self) -> None:
        payload = [{"symbol": "BTCUSDT", "timestamp": 1000}]
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response(payload)
            result = get_open_interest_hist(symbol="BTCUSDT", period="1d", limit=500)
        assert result == payload
        called_url = mock_urlopen.call_args[0][0]
        assert "symbol=BTCUSDT" in called_url
        assert "period=1d" in called_url
        assert "limit=500" in called_url

    def test_limit_ngoai_khoang_thi_raise_khong_tu_sua(self) -> None:
        with pytest.raises(ValueError):
            get_open_interest_hist(symbol="BTCUSDT", limit=501)
        with pytest.raises(ValueError):
            get_open_interest_hist(symbol="BTCUSDT", limit=0)

    def test_loi_mang_thi_raise_binance_public_api_error(self) -> None:
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("mô phỏng timeout")
            with pytest.raises(BinancePublicApiError):
                get_open_interest_hist(symbol="BTCUSDT")

    def test_json_hong_thi_raise_khong_tra_du_lieu_rac(self) -> None:
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = b"khong phai json"
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen", return_value=cm):
            with pytest.raises(BinancePublicApiError):
                get_open_interest_hist(symbol="BTCUSDT")


class TestProbeCoverageEntrypoint:
    """Kiểm logic tính toán của probe_oi_coverage() bằng dữ liệu giả lập
    — KHÔNG thay thế bằng chứng thật (đã ghi research-log riêng)."""

    def test_tinh_dung_khoang_ngay_tu_du_lieu_gia_lap(self) -> None:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "entrypoints"))
        from backfill_data import probe_oi_coverage

        fake_data = [
            {"symbol": "BTCUSDT", "timestamp": 1754524800000},  # 2025-08-07 UTC (ví dụ)
            {"symbol": "BTCUSDT", "timestamp": 1757116800000},  # 30 ngày sau
        ]
        with patch(
            "backfill_data.get_open_interest_hist", return_value=fake_data
        ):
            text = probe_oi_coverage("BTCUSDT")
        assert "2 bản ghi" in text
        assert "30 ngày" in text

    def test_du_lieu_rong_thi_bao_khong_do_duoc(self) -> None:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "entrypoints"))
        from backfill_data import probe_oi_coverage

        with patch("backfill_data.get_open_interest_hist", return_value=[]):
            text = probe_oi_coverage("BTCUSDT")
        assert "không đo được" in text


class TestSign:
    """`_sign()` phải là HMAC-SHA256 chuẩn Binance — chữ ký sai/dấu sai
    làm sàn từ chối lặng lẽ (cùng dạng lỗi LD-14 đã gặp ở DG7)."""

    def test_vector_co_dinh_dung_hmac_sha256(self) -> None:
        # Vector tự tính bằng hashlib độc lập, không copy từ tài liệu
        # Binance — chỉ xác nhận _sign() dùng đúng thuật toán/encoding.
        import hashlib
        import hmac as hmac_module
        import urllib.parse

        params = {"symbol": "BTCUSDT", "timestamp": "123456"}
        expected = hmac_module.new(
            b"mysecret", urllib.parse.urlencode(params).encode("utf-8"), hashlib.sha256
        ).hexdigest()
        assert _sign(params, "mysecret") == expected

    def test_doi_secret_thi_doi_chu_ky(self) -> None:
        params = {"symbol": "BTCUSDT", "timestamp": "123456"}
        assert _sign(params, "secret_a") != _sign(params, "secret_b")


def _fake_conn(status: int = 200, body: bytes = b"{}") -> MagicMock:
    conn = MagicMock()
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = body
    conn.getresponse.return_value = resp
    return conn


class TestLatencySamplesMs:
    """TD-0116 (H15) — testnet đã bị LOẠI bằng bằng chứng mã nguồn
    (Freqtrade `supports_demo_trading: False` cho Binance, cố ý), nên
    phép đo chạy trên production."""

    def test_khong_con_testnet_trong_module(self) -> None:
        import tool_d.api_client.binance_public as mod

        assert not hasattr(mod, "TESTNET_BASE_URL")
        assert "testnet" not in BASE_URL

    def test_lay_dung_so_mau_yeu_cau(self) -> None:
        with patch("http.client.HTTPSConnection", return_value=_fake_conn()):
            samples = latency_samples_ms(n=5, signed=False, reuse_connection=True)
        assert len(samples) == 5
        assert all(s >= 0.0 for s in samples)

    def test_reuse_connection_chi_mo_MOT_ket_noi(self) -> None:
        with patch("http.client.HTTPSConnection", return_value=_fake_conn()) as mock_conn:
            latency_samples_ms(n=10, signed=False, reuse_connection=True)
        assert mock_conn.call_count == 1  # ẤM: dùng lại, không bắt tay TLS lại

    def test_khong_reuse_thi_moi_mau_mot_ket_noi_moi(self) -> None:
        with patch("http.client.HTTPSConnection", return_value=_fake_conn()) as mock_conn:
            latency_samples_ms(n=10, signed=False, reuse_connection=False)
        assert mock_conn.call_count == 10  # LẠNH: mỗi mẫu cõng một bắt tay TLS

    def test_signed_gui_dung_header_va_khong_lo_secret(self) -> None:
        conn = _fake_conn()
        with patch("http.client.HTTPSConnection", return_value=conn):
            latency_samples_ms(
                n=1,
                signed=True,
                reuse_connection=True,
                path="/fapi/v1/order/test",
                method="POST",
                api_key="fake_key",
                api_secret="fake_secret_value",
                extra_params={"symbol": "BTCUSDT"},
            )
        method, path = conn.request.call_args[0][0], conn.request.call_args[0][1]
        headers = conn.request.call_args[1]["headers"]
        assert method == "POST" and path.startswith("/fapi/v1/order/test?")
        assert "signature=" in path and "timestamp=" in path
        assert headers["X-MBX-APIKEY"] == "fake_key"
        # Secret KHÔNG BAO GIỜ đi ra khỏi máy — chỉ chữ ký (hash một chiều).
        assert "fake_secret_value" not in path

    def test_moi_mau_ky_lai_timestamp_moi(self) -> None:
        # Ký một lần rồi dùng lại cho cả loạt sẽ bị Binance từ chối khi
        # timestamp cũ quá recvWindow -- mỗi mẫu phải có chữ ký riêng.
        conn = _fake_conn()
        with patch("http.client.HTTPSConnection", return_value=conn):
            latency_samples_ms(
                n=3, signed=True, reuse_connection=True,
                path="/api/v3/account", api_key="k", api_secret="s",
            )
        paths = [call[0][1] for call in conn.request.call_args_list]
        assert len(paths) == 3
        assert all("signature=" in p for p in paths)

    def test_khong_signed_dung_endpoint_public_lam_doi_chung(self) -> None:
        conn = _fake_conn()
        with patch("http.client.HTTPSConnection", return_value=conn):
            latency_samples_ms(n=1, signed=False, reuse_connection=True)
        method, path = conn.request.call_args[0][0], conn.request.call_args[0][1]
        assert method == "GET" and path == "/fapi/v1/time"
        assert conn.request.call_args[1]["headers"] == {}  # không gửi khoá cho endpoint public

    def test_signed_thieu_khoa_thi_raise_som_khong_goi_mang(self) -> None:
        with patch("http.client.HTTPSConnection") as mock_conn:
            with pytest.raises(ValueError):
                latency_samples_ms(n=1, signed=True, reuse_connection=True, api_key="", api_secret="")
        mock_conn.assert_not_called()

    def test_http_khong_200_thi_raise_khong_ghi_mau_rac(self) -> None:
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(status=401, body=b"bad key")):
            with pytest.raises(BinancePrivateApiError, match="401"):
                latency_samples_ms(n=3, signed=False, reuse_connection=True)

    def test_loi_mang_thi_raise_binance_private_api_error(self) -> None:
        conn = _fake_conn()
        conn.request.side_effect = OSError("mô phỏng đứt mạng")
        with patch("http.client.HTTPSConnection", return_value=conn):
            with pytest.raises(BinancePrivateApiError):
                latency_samples_ms(n=1, signed=False, reuse_connection=True)

    def test_n_khong_hop_le_thi_raise(self) -> None:
        with pytest.raises(ValueError):
            latency_samples_ms(n=0, signed=False, reuse_connection=True)

    def test_n_vuot_tran_thi_raise_khong_goi_mang(self) -> None:
        with patch("http.client.HTTPSConnection") as mock_conn:
            with pytest.raises(ValueError, match="MAX_MAU_LATENCY|<="):
                latency_samples_ms(n=201, signed=False, reuse_connection=True)
        mock_conn.assert_not_called()

    def test_vuot_han_chot_tong_thi_dung_khong_tra_ket_qua_mot_phan(self) -> None:
        # Chuỗi monotonic(): [han_chot=0+50] [check vòng 1: 0<=50 qua]
        # [t0 vòng 1] [elapsed vòng 1] [check vòng 2: vượt 50 -> raise].
        # Mẫu đầu vẫn lấy được, nhưng hàm phải RAISE — không trả về 1 mẫu
        # như thể đó là câu trả lời đủ (N6, cấm kết quả một phần âm thầm).
        with patch(
            "http.client.HTTPSConnection", return_value=_fake_conn()
        ), patch(
            "time.monotonic", side_effect=[0.0, 0.0, 1.0, 2.0, 1_000_000.0]
        ):
            with pytest.raises(BinancePrivateApiError, match="vượt timeout tổng"):
                latency_samples_ms(n=5, signed=False, reuse_connection=True, timeout=10.0)


class TestGuardMangTD0197:
    """R2 (rate limit theo `tier_c.api_calls_per_min`) + R3 (circuit
    breaker) nối vào `_goi_json_cong_khai` — điểm nghẽn chung của 5 hàm
    GET/JSON. `tests/conftest.py` reset trạng thái TRƯỚC MỖI test."""

    def test_tran_doc_tu_config_khong_hardcode(self) -> None:
        # config/tool_d_config.yaml thật ghi 30 (§6.6(3), LD-23) — đo
        # trực tiếp, không giả lập, đúng tinh thần "đo rẻ hơn đoán".
        assert _tran_goi_theo_phut() == 30.0

    def test_lan_goi_dau_khong_cho(self) -> None:
        with patch("time.sleep") as mock_sleep, patch(
            "tool_d.api_client.binance_public.urllib.request.urlopen"
        ) as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"ok": True})
            get_exchange_info()
        mock_sleep.assert_not_called()

    def test_lan_goi_thu_hai_giu_dung_khoang_cach_toi_thieu(self) -> None:
        with (
            patch("tool_d.api_client.binance_public._tran_goi_theo_phut", return_value=30.0),
            patch("time.monotonic", side_effect=[0.0, 0.5, 0.5]),
            patch("time.sleep") as mock_sleep,
            patch("tool_d.api_client.binance_public.urllib.request.urlopen") as mock_urlopen,
        ):
            mock_urlopen.return_value = _fake_response({"ok": True})
            get_exchange_info()
            get_exchange_info()
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == pytest.approx(1.5, abs=1e-6)  # 60/30 - 0.5

    def test_breaker_mo_sau_du_nguong_loi_429_lien_tiep(self) -> None:
        with patch("time.sleep"), patch(
            "tool_d.api_client.binance_public.urllib.request.urlopen"
        ) as mock_urlopen:
            mock_urlopen.side_effect = _http_error(429)
            for _ in range(5):  # NGUONG_BREAKER_MAC_DINH = 5, không có env override trong test
                with pytest.raises(BinancePublicApiError):
                    get_exchange_info()
            mock_urlopen.reset_mock(side_effect=True)
            with pytest.raises(BinanceBreakerMoError):
                get_exchange_info()
        # Breaker chặn TRƯỚC khi gọi mạng — gọi tiếp trong lúc bị cấm chỉ
        # kéo dài án phạt (bài học Tool A).
        mock_urlopen.assert_not_called()

    def test_thanh_cong_reset_bo_dem_loi(self) -> None:
        with patch("time.sleep"), patch(
            "tool_d.api_client.binance_public.urllib.request.urlopen"
        ) as mock_urlopen:
            mock_urlopen.side_effect = _http_error(429)
            for _ in range(4):  # dưới ngưỡng 5
                with pytest.raises(BinancePublicApiError):
                    get_exchange_info()
            mock_urlopen.side_effect = None
            mock_urlopen.return_value = _fake_response({"ok": True})
            get_exchange_info()  # thành công — phải reset bộ đếm về 0
            mock_urlopen.side_effect = _http_error(429)
            for _ in range(4):  # lại dưới ngưỡng — nếu bộ đếm KHÔNG reset thì vòng này mở breaker
                with pytest.raises(BinancePublicApiError):
                    get_exchange_info()
            mock_urlopen.side_effect = None
            mock_urlopen.return_value = _fake_response({"ok": True})
            get_exchange_info()  # nếu breaker lỡ mở thì dòng này raise BinanceBreakerMoError

    def test_418_chan_vinh_vien_khong_tu_go(self) -> None:
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = _http_error(418)
            with pytest.raises(BinancePublicApiError):
                get_exchange_info()
        with pytest.raises(BinanceBreakerMoError):
            get_exchange_info()

    def test_loi_khong_co_http_status_khong_dung_breaker(self) -> None:
        # URLError/TimeoutError không có mã HTTP — không phân loại được
        # (đúng chữ `phan_loai_ma_loi()`), nên KHÔNG cộng vào bộ đếm breaker.
        with patch("time.sleep"), patch(
            "tool_d.api_client.binance_public.urllib.request.urlopen"
        ) as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("mô phỏng timeout")
            for _ in range(10):  # nhiều hơn ngưỡng 5, nhưng không có http_status
                with pytest.raises(BinancePublicApiError):
                    get_exchange_info()
            mock_urlopen.side_effect = None
            mock_urlopen.return_value = _fake_response({"ok": True})
            get_exchange_info()  # breaker KHÔNG mở — nếu mở sẽ raise ở đây

    def test_dat_lai_trang_thai_cho_kiem_xoa_sach_breaker(self) -> None:
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = _http_error(418)
            with pytest.raises(BinancePublicApiError):
                get_exchange_info()
        dat_lai_trang_thai_mang_cho_kiem()
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"ok": True})
            get_exchange_info()  # không raise — breaker đã sạch


class TestTaiDumpAggTradesBreaker:
    """`tai_dump_agg_trades()` (host phụ `data.binance.vision`) dùng
    CHUNG breaker với `_goi_json_cong_khai`, nhưng KHÔNG nhận giãn nhịp
    `tier_c.api_calls_per_min` (trần đó chỉ công bố cho `fapi.binance.com`,
    không có trần tương đương công bố cho host phụ này)."""

    def test_cache_hit_khong_dung_toi_breaker(self, tmp_path) -> None:
        dich = tmp_path / "BTCUSDT-aggTrades-2024-06-01.zip"
        dich.write_bytes(b"noi dung gia")
        with patch("http.client.HTTPSConnection") as mock_conn:
            ket_qua = tai_dump_agg_trades(
                symbol="BTCUSDT", ngay=date(2024, 6, 1), thu_muc_cache=tmp_path
            )
        assert ket_qua == dich
        mock_conn.assert_not_called()

    def test_breaker_dang_mo_thi_khong_mo_ket_noi_moi(self, tmp_path) -> None:
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = _http_error(418)
            with pytest.raises(BinancePublicApiError):
                get_exchange_info()  # mở breaker DUNG_HAN qua đường fapi
        with patch("http.client.HTTPSConnection") as mock_conn:
            with pytest.raises(BinanceBreakerMoError):
                tai_dump_agg_trades(symbol="BTCUSDT", ngay=date(2024, 6, 1), thu_muc_cache=tmp_path)
        mock_conn.assert_not_called()

    def test_404_khong_dung_breaker(self, tmp_path) -> None:
        conn_404 = _fake_conn(status=404, body=b"not found")
        with patch("http.client.HTTPSConnection", return_value=conn_404):
            with pytest.raises(AggTradesNotFoundError):
                tai_dump_agg_trades(symbol="BTCUSDT", ngay=date(2024, 6, 1), thu_muc_cache=tmp_path)
        # 404 là DỮ KIỆN (không có dump), không phải lỗi mạng — breaker còn sạch:
        conn_200 = _fake_conn(status=200, body=b"noi dung that")
        with patch("http.client.HTTPSConnection", return_value=conn_200):
            ket_qua = tai_dump_agg_trades(
                symbol="ETHUSDT", ngay=date(2024, 6, 2), thu_muc_cache=tmp_path
            )
        assert ket_qua.exists()
