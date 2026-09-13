"""TD-0080 — api_client/binance_public.py. Test đơn vị dùng mock (không
phụ thuộc mạng thật để chạy nhanh/ổn định) — bằng chứng THẬT về độ phủ
30 ngày của OI history đã xác nhận bằng tay (curl trực tiếp) và bằng
`entrypoints/backfill_data.py --probe-coverage` thật, ghi ở
`docs/research-log.md`, không lặp lại ở đây (đúng L-Z51: không coi mock
là "đạt" cho phát hiện thật).
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import date
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from tool_d.api_client.binance_public import (
    BASE_URL,
    ENV_BINANCE_API_KEY,
    ENV_BINANCE_API_SECRET,
    AggTradesNotFoundError,
    BinanceBreakerMoError,
    BinanceCredentialsMissingError,
    BinancePrivateApiError,
    BinancePublicApiError,
    _sign,
    _tran_goi_theo_phut,
    dat_lai_trang_thai_mang_cho_kiem,
    get_exchange_info,
    get_open_interest_hist,
    KhoLuuTruError,
    NenThangKhongCoError,
    doc_quote_volume_1d_thang,
    latency_samples_ms,
    liet_ke_kho_luu_tru,
    tai_dump_agg_trades,
    validate_credentials_for_live,
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
def _xml_s3(
    *,
    prefix: str,
    khoa: tuple[str, ...] = (),
    thu_muc: tuple[str, ...] = (),
    bi_cat: bool = False,
    next_marker: str | None = None,
) -> bytes:
    """Dựng phản hồi ListObjects v1 ĐÚNG hình dạng bucket thật trả về —
    kèm thẻ `<Prefix>` ở CẤP GỐC (echo lại prefix đã gửi). Thẻ gốc đó là
    cái bẫy: `iter("Prefix")` thẳng sẽ hút luôn nó và sinh một "thư mục"
    giả không tồn tại."""
    phan = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">',
        "<Name>data.binance.vision</Name>",
        f"<Prefix>{prefix}</Prefix>",
        "<Delimiter>/</Delimiter>",
        f"<IsTruncated>{'true' if bi_cat else 'false'}</IsTruncated>",
    ]
    if next_marker is not None:
        phan.append(f"<NextMarker>{next_marker}</NextMarker>")
    phan += [f"<Contents><Key>{k}</Key><Size>7</Size></Contents>" for k in khoa]
    phan += [f"<CommonPrefixes><Prefix>{t}</Prefix></CommonPrefixes>" for t in thu_muc]
    phan.append("</ListBucketResult>")
    return "".join(phan).encode("utf-8")


def _fake_conn_nhieu_trang(*bodies: bytes, status: int = 200) -> MagicMock:
    """Một `HTTPSConnection` giả trả LẦN LƯỢT từng body — cần thiết để ca
    phân trang là phân trang THẬT (nhiều lượt request), không phải một
    lượt được khẳng định là nhiều."""
    conn = MagicMock()
    responses = []
    for body in bodies:
        resp = MagicMock()
        resp.status = status
        resp.read.return_value = body
        responses.append(resp)
    conn.getresponse.side_effect = responses
    return conn


class TestLietKeKhoLuuTru:
    """TD-0230 — liệt kê kho tĩnh `data.binance.vision` (S3 ListObjects).

    🔴 Ba ca có RĂNG ở đây canh cùng một hình dạng lỗi: **trả một danh
    sách NGẮN HƠN thực tế mà không ai biết**. Ở phép đo TD-0230, ngắn hơn
    thực tế đọc thành *"pool thiếu ít mã hơn"* — tức im lặng đúng theo
    chiều PASS, chiều mà không cổng nào của dự án bắt được.
    """

    PREFIX = "data/futures/um/monthly/klines/"

    def test_mot_trang_doc_dung_khoa_va_thu_muc(self) -> None:
        body = _xml_s3(
            prefix=self.PREFIX,
            khoa=("data/x/a.zip",),
            thu_muc=(f"{self.PREFIX}BTCUSDT/", f"{self.PREFIX}ETHUSDT/"),
        )
        with patch("http.client.HTTPSConnection", return_value=_fake_conn_nhieu_trang(body)):
            kq = liet_ke_kho_luu_tru(prefix=self.PREFIX, delimiter="/")
        assert kq.khoa == ("data/x/a.zip",)
        assert kq.thu_muc == (f"{self.PREFIX}BTCUSDT/", f"{self.PREFIX}ETHUSDT/")
        assert kq.so_trang == 1

    def test_the_Prefix_cap_goc_KHONG_bi_tinh_la_thu_muc(self) -> None:
        """Nếu tính, mọi lượt liệt kê sẽ có thêm một "thư mục" giả =
        chính prefix đã gửi — và phép trừ tập của TD-0230 lệch đúng 1."""
        body = _xml_s3(prefix=self.PREFIX, thu_muc=(f"{self.PREFIX}BTCUSDT/",))
        with patch("http.client.HTTPSConnection", return_value=_fake_conn_nhieu_trang(body)):
            kq = liet_ke_kho_luu_tru(prefix=self.PREFIX, delimiter="/")
        assert kq.thu_muc == (f"{self.PREFIX}BTCUSDT/",)
        assert self.PREFIX not in kq.thu_muc

    def test_PHAN_TRANG_khong_dung_o_trang_dau(self) -> None:
        """RĂNG 1 — `DR-D1-01` §1 nêu đúng chỗ này: mỗi trang giới hạn
        1000 mục. Dừng ở trang đầu ⇒ thiếu mã, lệch chiều PASS."""
        t1 = _xml_s3(
            prefix=self.PREFIX,
            thu_muc=(f"{self.PREFIX}AAAUSDT/",),
            bi_cat=True,
            next_marker=f"{self.PREFIX}AAAUSDT/",
        )
        t2 = _xml_s3(prefix=self.PREFIX, thu_muc=(f"{self.PREFIX}ZZZUSDT/",))
        conn = _fake_conn_nhieu_trang(t1, t2)
        with patch("http.client.HTTPSConnection", return_value=conn):
            kq = liet_ke_kho_luu_tru(prefix=self.PREFIX, delimiter="/")
        assert kq.so_trang == 2
        assert kq.thu_muc == (f"{self.PREFIX}AAAUSDT/", f"{self.PREFIX}ZZZUSDT/")
        assert conn.request.call_count == 2
        # marker phải có mặt trong request thứ HAI, không phải request đầu
        assert "marker" not in conn.request.call_args_list[0][0][1]
        assert "marker" in conn.request.call_args_list[1][0][1]

    def test_thieu_NextMarker_thi_dung_khoa_CUOI_cua_trang(self) -> None:
        """ListObjects v1 chỉ trả `NextMarker` khi có `delimiter`. Không
        có thì marker của trang sau là khoá cuối trang này — không được
        giả định chỉ một dạng."""
        t1 = _xml_s3(prefix=self.PREFIX, khoa=("k/1.zip", "k/2.zip"), bi_cat=True)
        t2 = _xml_s3(prefix=self.PREFIX, khoa=("k/3.zip",))
        conn = _fake_conn_nhieu_trang(t1, t2)
        with patch("http.client.HTTPSConnection", return_value=conn):
            kq = liet_ke_kho_luu_tru(prefix=self.PREFIX)
        assert kq.khoa == ("k/1.zip", "k/2.zip", "k/3.zip")
        assert "marker=k%2F2.zip" in conn.request.call_args_list[1][0][1]

    def test_qua_TRAN_TRANG_thi_RAISE_chu_khong_tra_danh_sach_thieu(self) -> None:
        """RĂNG 2 — R5 vòng lặp có biên, nhưng cắt ở biên phải NỔ. Cắt im
        lặng là đúng thứ trả "kho chỉ có thế"."""
        bi_cat = _xml_s3(prefix=self.PREFIX, khoa=("k/1.zip",), bi_cat=True, next_marker="k/1.zip")
        conn = _fake_conn_nhieu_trang(bi_cat, bi_cat, bi_cat)
        with patch("http.client.HTTPSConnection", return_value=conn):
            with pytest.raises(KhoLuuTruError, match="còn bị cắt sau"):
                liet_ke_kho_luu_tru(prefix=self.PREFIX, tran_trang=2)

    def test_loi_mang_thi_RAISE_chu_khong_tra_RONG(self) -> None:
        """RĂNG 3 — N6. Rỗng ở đây đọc thành "không mã nào bị thiếu"."""
        conn = MagicMock()
        conn.request.side_effect = OSError("mô phỏng đứt mạng")
        with patch("http.client.HTTPSConnection", return_value=conn):
            with pytest.raises(KhoLuuTruError, match="thất bại"):
                liet_ke_kho_luu_tru(prefix=self.PREFIX)

    def test_http_loi_thi_RAISE(self) -> None:
        conn = _fake_conn_nhieu_trang(b"loi", status=503)
        with patch("http.client.HTTPSConnection", return_value=conn):
            with pytest.raises(KhoLuuTruError, match="HTTP 503"):
                liet_ke_kho_luu_tru(prefix=self.PREFIX)

    def test_xml_hong_thi_RAISE_chu_khong_tra_RONG(self) -> None:
        conn = _fake_conn_nhieu_trang(b"<khong phai xml hop le")
        with patch("http.client.HTTPSConnection", return_value=conn):
            with pytest.raises(KhoLuuTruError, match="không phải XML hợp lệ"):
                liet_ke_kho_luu_tru(prefix=self.PREFIX)

    def test_RONG_THAT_phan_biet_duoc_voi_LOI(self) -> None:
        """Prefix không tồn tại: HTTP 200, 0 mục. `so_trang >= 1` là bằng
        chứng đã có phản hồi thật — nên rỗng-thật đọc được, không lẫn với
        lỗi (lỗi đã raise từ trước)."""
        body = _xml_s3(prefix="data/khong-ton-tai/")
        with patch("http.client.HTTPSConnection", return_value=_fake_conn_nhieu_trang(body)):
            kq = liet_ke_kho_luu_tru(prefix="data/khong-ton-tai/", delimiter="/")
        assert kq.khoa == () and kq.thu_muc == ()
        assert kq.so_trang == 1

    def test_prefix_rong_bi_tu_choi_truoc_khi_goi_mang(self) -> None:
        with patch("http.client.HTTPSConnection") as mock_conn:
            with pytest.raises(KhoLuuTruError, match="prefix rỗng"):
                liet_ke_kho_luu_tru(prefix="")
        mock_conn.assert_not_called()

    def test_breaker_dang_mo_thi_khong_mo_ket_noi_moi(self) -> None:
        """Dùng CHUNG breaker với `_goi_json_cong_khai` — một hạ tầng
        Binance, đúng như `tai_dump_agg_trades` đã làm."""
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = _http_error(418)
            with pytest.raises(BinancePublicApiError):
                get_exchange_info()  # mở breaker DUNG_HAN qua đường fapi
        with patch("http.client.HTTPSConnection") as mock_conn:
            with pytest.raises(BinanceBreakerMoError):
                liet_ke_kho_luu_tru(prefix=self.PREFIX)
        mock_conn.assert_not_called()
def _zip_nen(rows: list[str], *, ten: str = "X-1d-2025-06.csv") -> bytes:
    """Dựng một file zip nến trong bộ nhớ, đúng hình dạng kho lưu trữ."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(ten, "\n".join(rows))
    return buf.getvalue()


def _hang(moc: int, quote_volume: str = "1000000.0") -> str:
    """Một hàng nến 12 cột; chỉ cột 0 (open_time) và 7 (quote_volume) có nghĩa."""
    o = [str(moc), "1", "2", "0.5", "1.5", "10", str(moc + 1), quote_volume, "5", "1", "1", "0"]
    return ",".join(o)


# 2025-06-12 00:00:00 UTC
MS_2025_06_12 = 1749686400000
US_2025_06_12 = MS_2025_06_12 * 1000


class TestDocQuoteVolume1dThang:
    """TD-0231 — dựng lại `quote_volume_24h` TẠI một mốc quá khứ, thứ mà
    `pool.pairlist_point_in_time()` đòi bên gọi cung cấp và chưa ai cung cấp.

    🔴 Ca có RĂNG quan trọng nhất ở đây là **chốt canh LẪN ĐƠN VỊ**: kho đã
    đổi mốc thời gian từ milli- sang micro-giây. Đọc lệch đơn vị đẩy mọi mốc
    về 1970, mà *"1970 thì trước mọi mốc T"* nghĩa là **"mã nào cũng đã tồn
    tại"** — lệch đúng chiều làm rổ trông đầy hơn thực tế, tức chiều PASS.
    """

    def test_doc_dung_quote_volume_milli_giay(self) -> None:
        body = _zip_nen([_hang(MS_2025_06_12, "12345678.9")])
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(body=body)):
            kq = doc_quote_volume_1d_thang(symbol="ABCUSDT", nam=2025, thang=6)
        assert kq == {date(2025, 6, 12): 12345678.9}

    def test_doc_dung_quote_volume_MICRO_giay(self) -> None:
        """File mới của kho ghi micro-giây — phải ra CÙNG một ngày."""
        body = _zip_nen([_hang(US_2025_06_12, "12345678.9")])
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(body=body)):
            kq = doc_quote_volume_1d_thang(symbol="ABCUSDT", nam=2025, thang=6)
        assert kq == {date(2025, 6, 12): 12345678.9}

    def test_moc_ROI_NGOAI_THANG_thi_RAISE(self) -> None:
        """RĂNG — chốt canh lẫn đơn vị. Hỏi tháng 7 mà file trả mốc tháng 6
        thì DỪNG, không trả một con số sai đơn vị."""
        body = _zip_nen([_hang(MS_2025_06_12)])
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(body=body)):
            with pytest.raises(KhoLuuTruError, match="LẪN ĐƠN VỊ"):
                doc_quote_volume_1d_thang(symbol="ABCUSDT", nam=2025, thang=7)

    def test_404_la_DU_KIEN_khong_phai_loi_va_khong_dung_breaker(self) -> None:
        """Tháng không có file = mã chưa lên sàn / đã rời sàn. Coi nó như
        `volume = 0` là gộp "không đo được" với "đo được và bằng 0" (N6)."""
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(status=404)):
            with pytest.raises(NenThangKhongCoError):
                doc_quote_volume_1d_thang(symbol="ABCUSDT", nam=2020, thang=1)
        # breaker còn sạch ⇒ lượt gọi sau vẫn đi được
        body = _zip_nen([_hang(MS_2025_06_12)])
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(body=body)):
            assert doc_quote_volume_1d_thang(symbol="ABCUSDT", nam=2025, thang=6)

    def test_http_loi_thi_RAISE(self) -> None:
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(status=503)):
            with pytest.raises(KhoLuuTruError, match="HTTP 503"):
                doc_quote_volume_1d_thang(symbol="ABCUSDT", nam=2025, thang=6)

    def test_zip_hong_thi_RAISE(self) -> None:
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(body=b"khong phai zip")):
            with pytest.raises(KhoLuuTruError, match="không giải nén được"):
                doc_quote_volume_1d_thang(symbol="ABCUSDT", nam=2025, thang=6)

    def test_hang_tieu_de_bi_bo_QUA_nhung_file_van_doc_duoc(self) -> None:
        """File mới của kho có hàng tiêu đề — bỏ qua đúng hàng đó, không bỏ file."""
        body = _zip_nen(["open_time,open,high,low,close,volume,close_time,quote_volume,count,a,b,c",
                         _hang(MS_2025_06_12, "777.0")])
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(body=body)):
            kq = doc_quote_volume_1d_thang(symbol="ABCUSDT", nam=2025, thang=6)
        assert kq == {date(2025, 6, 12): 777.0}

    def test_hang_thieu_cot_thi_RAISE(self) -> None:
        body = _zip_nen([f"{MS_2025_06_12},1,2,3"])
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(body=body)):
            with pytest.raises(KhoLuuTruError, match="thiếu cột"):
                doc_quote_volume_1d_thang(symbol="ABCUSDT", nam=2025, thang=6)

    def test_quote_volume_khong_doc_duoc_thi_RAISE_chu_khong_bo_qua(self) -> None:
        body = _zip_nen([_hang(MS_2025_06_12, "khong-phai-so")])
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(body=body)):
            with pytest.raises(KhoLuuTruError, match="quote_volume không đọc được"):
                doc_quote_volume_1d_thang(symbol="ABCUSDT", nam=2025, thang=6)

    def test_file_rong_thi_RAISE_chu_khong_tra_dict_RONG(self) -> None:
        """Dict rỗng ở đây đọc thành "tháng đó không có giao dịch nào" — khác
        hẳn "file không tồn tại" (404) và khác hẳn "đọc không ra"."""
        body = _zip_nen([""])
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(body=body)):
            with pytest.raises(KhoLuuTruError, match="0 hàng đọc được"):
                doc_quote_volume_1d_thang(symbol="ABCUSDT", nam=2025, thang=6)
class TestMaPhiASCIITrongDuongDan:
    """🔴 Đã NỔ THẬT trong lượt chạy TD-0231 (629 mã, chết ở mã thứ ~600):
    `UnicodeEncodeError: 'ascii' codec can't encode characters`.

    `http.client._encode_request` gọi `request.encode("ascii")`, nên một ký tự
    ngoài ASCII trong đường dẫn làm nó raise **trước khi** gửi đi. Mà sàn có
    mã tên phi ASCII, và **một trong số đó nằm trong chính pool 102 mã giao
    dịch**: `币安人生USDT`.

    ⇒ `tai_dump_agg_trades()` (DR-015 Bước 2, từ TD-0162) mang **CÙNG** lỗi và
    chưa nổ chỉ vì chưa lần nào chạm đúng mã đó. Hai ca dưới canh **cả hai**
    hàm — vá một chỗ rồi để chỗ kia là chọn để nó nổ lần sau.
    """

    MA_PHI_ASCII = "币安人生USDT"

    def test_doc_quote_volume_khong_no_voi_ma_phi_ascii(self) -> None:
        body = _zip_nen([_hang(MS_2025_06_12, "42.0")])
        conn = _fake_conn(body=body)
        with patch("http.client.HTTPSConnection", return_value=conn):
            kq = doc_quote_volume_1d_thang(
                symbol=self.MA_PHI_ASCII, nam=2025, thang=6
            )
        assert kq == {date(2025, 6, 12): 42.0}
        duong_dan = conn.request.call_args[0][1]
        # Đường dẫn phải THUẦN ASCII — nếu không, http.client raise trước khi gửi
        duong_dan.encode("ascii")
        assert "%" in duong_dan

    def test_tai_dump_agg_trades_khong_no_voi_ma_phi_ascii(self, tmp_path) -> None:
        conn = _fake_conn(body=b"noi dung gia")
        with patch("http.client.HTTPSConnection", return_value=conn):
            kq = tai_dump_agg_trades(
                symbol=self.MA_PHI_ASCII,
                ngay=date(2025, 6, 12),
                thu_muc_cache=tmp_path,
            )
        assert kq.exists()
        duong_dan = conn.request.call_args[0][1]
        duong_dan.encode("ascii")
        assert "%" in duong_dan


class TestValidateCredentialsForLive:
    """TD-0242 — fail-closed khi thiếu `BINANCE_API_KEY`/`BINANCE_API_SECRET`.

    Dùng `env=` (một `dict` truyền tay) thay vì `monkeypatch.setenv`/`delenv`
    trên `os.environ` thật — cô lập hoàn toàn khỏi biến môi trường thật của
    máy chạy test (Docker/host có thể vô tình có sẵn `.env.binance` đã
    `source`), đúng tinh thần L-Z51 (không để trạng thái ẩn ngoài tầm kiểm).
    """

    DU: dict[str, str] = {
        ENV_BINANCE_API_KEY: "khoa-gia-de-test",
        ENV_BINANCE_API_SECRET: "bi-mat-gia-de-test",
    }

    def test_du_ca_hai_bien_thi_tra_ve_dung_gia_tri_khong_raise(self) -> None:
        api_key, api_secret = validate_credentials_for_live(env=self.DU)
        assert (api_key, api_secret) == (self.DU[ENV_BINANCE_API_KEY], self.DU[ENV_BINANCE_API_SECRET])

    def test_thieu_api_key_raise_fail_closed(self) -> None:
        env = {ENV_BINANCE_API_SECRET: self.DU[ENV_BINANCE_API_SECRET]}
        with pytest.raises(BinanceCredentialsMissingError, match=ENV_BINANCE_API_KEY):
            validate_credentials_for_live(env=env)

    def test_thieu_api_secret_raise_fail_closed(self) -> None:
        env = {ENV_BINANCE_API_KEY: self.DU[ENV_BINANCE_API_KEY]}
        with pytest.raises(BinanceCredentialsMissingError, match=ENV_BINANCE_API_SECRET):
            validate_credentials_for_live(env=env)

    def test_thieu_ca_hai_raise_va_thong_bao_neu_ca_hai_ten_bien(self) -> None:
        with pytest.raises(BinanceCredentialsMissingError) as exc_info:
            validate_credentials_for_live(env={})
        assert ENV_BINANCE_API_KEY in str(exc_info.value)
        assert ENV_BINANCE_API_SECRET in str(exc_info.value)

    def test_chuoi_rong_tinh_nhu_thieu_khong_phai_hop_le(self) -> None:
        """Tiêu chí XONG đòi 'thiếu' — rỗng là một cách thiếu phổ biến nhất
        (`.env.binance` tồn tại, biến có khai nhưng chưa điền giá trị)."""
        env = {ENV_BINANCE_API_KEY: "", ENV_BINANCE_API_SECRET: ""}
        with pytest.raises(BinanceCredentialsMissingError):
            validate_credentials_for_live(env=env)

    def test_thong_bao_khong_phai_loi_mang(self) -> None:
        """Tiêu chí XONG: 'không phải một lỗi mạng trông giống sự cố sàn' —
        thông báo phải tự khai rõ đây là lỗi cấu hình cục bộ."""
        with pytest.raises(BinanceCredentialsMissingError, match="CẤU HÌNH cục bộ"):
            validate_credentials_for_live(env={})
        with pytest.raises(BinanceCredentialsMissingError, match="KHÔNG phải sự cố mạng"):
            validate_credentials_for_live(env={})

    def test_mac_dinh_doc_tu_os_environ_khi_khong_truyen_env(self, monkeypatch) -> None:
        """Kiểm-có-răng của TD-0242: XOÁ biến môi trường thật ⇒ đúng
        hàm này (và chỉ hàm này trong lớp test) đỏ — không đọc `env=` giả,
        mà đọc thẳng `os.environ` như một entrypoint thật sẽ làm."""
        monkeypatch.delenv(ENV_BINANCE_API_KEY, raising=False)
        monkeypatch.delenv(ENV_BINANCE_API_SECRET, raising=False)
        with pytest.raises(BinanceCredentialsMissingError):
            validate_credentials_for_live()

        monkeypatch.setenv(ENV_BINANCE_API_KEY, "khoa-that-gia-lap")
        monkeypatch.setenv(ENV_BINANCE_API_SECRET, "bi-mat-that-gia-lap")
        api_key, api_secret = validate_credentials_for_live()
        assert (api_key, api_secret) == ("khoa-that-gia-lap", "bi-mat-that-gia-lap")
