"""🔴 L-Z45 (TD-0144) — `dedup_key` tất định + no-op khi trùng, append-only.

Spec dòng 2649: *"chạy hai lần liên tiếp cùng timerange ghi thêm ĐÚNG 0
dòng, **kể cả khi có tiến trình song song ghi cùng file**"*.

Vế "tiến trình song song" là vế khó và là lý do có `TestGhiSongSong` ở
cuối file: nó dựng **tiến trình THẬT** (`multiprocessing`), không phải
luồng, không phải mock. Một cửa ghi chỉ kiểm "khoá đã có chưa" rồi mới
ghi sẽ PASS mọi ca tuần tự ở trên mà vẫn sinh bản trùng khi hai tiến
trình chen nhau — tức xanh hết trừ đúng ca cần nó.
"""

from __future__ import annotations

import json
import multiprocessing as mp
from pathlib import Path

import pytest

from tool_d.ledger.decision_log import (
    TRUONG_KHOA,
    DecisionLogError,
    dedup_key,
    doc_khoa_da_co,
    ghi_neu_chua_co,
    ghi_nhieu,
)


def _lenh(order_id: str = "OID-1") -> dict:
    return {"loai": "VAO_RA_LENH", "exchange_order_id": order_id, "pnl_abs": 12.5}


def _plan(pair: str = "BTC/USDT:USDT", ts: str = "2025-07-01T00:00:00Z") -> dict:
    return {"loai": "PLAN", "pair": pair, "candle_ts": ts, "block": "block_zone_plan"}


class TestKhoaTheoTrancheKhongTheoTrade:
    def test_ba_tranche_cung_trade_cho_BA_khoa_khac_nhau(self) -> None:
        """🔴 Trọng tâm §8.3: mỗi TRANCHE là một sự kiện vào lệnh riêng.
        Khoá theo `trade_id` sẽ gộp ba tranche thành một — mất đúng thứ
        Tool D sinh ra để đo."""
        khoa = {
            dedup_key({"loai": "VAO_RA_LENH", "exchange_order_id": oid, "trade_id": 7})
            for oid in ("OID-t1", "OID-t2", "OID-t3")
        }
        assert len(khoa) == 3

    def test_khoa_khong_chua_trade_id(self) -> None:
        k = dedup_key({"loai": "VAO_RA_LENH", "exchange_order_id": "OID-t1", "trade_id": 7})
        assert k == "OID-t1" and "7" not in k

    def test_tat_dinh_goi_lai_ra_cung_khoa(self) -> None:
        assert dedup_key(_plan()) == dedup_key(_plan())

    def test_du_bon_loai_cua_spec(self) -> None:
        assert set(TRUONG_KHOA) == {"VAO_RA_LENH", "DOI_SL", "PLAN", "GATE_CHECK"}
        assert dedup_key({"loai": "DOI_SL", "sl_order_id_new": "SL-9"}) == "SL-9"
        assert (
            dedup_key({"loai": "GATE_CHECK", "trade_id": 7, "candle_ts": "T", "gate": "DG6"})
            == "7:T:DG6"
        )


class TestDungKhoaFailClosed:
    def test_loai_la_thi_raise(self) -> None:
        with pytest.raises(DecisionLogError, match="loai"):
            dedup_key({"loai": "KHONG_CO_LOAI_NAY", "x": 1})

    def test_thieu_loai_thi_raise(self) -> None:
        with pytest.raises(DecisionLogError):
            dedup_key({"exchange_order_id": "OID-1"})

    def test_thieu_truong_dung_khoa_thi_raise(self) -> None:
        with pytest.raises(DecisionLogError, match="candle_ts"):
            dedup_key({"loai": "PLAN", "pair": "BTC/USDT:USDT", "block": "b"})

    @pytest.mark.parametrize("rong", [None, "", "   "])
    def test_truong_dung_khoa_RONG_thi_raise(self, rong) -> None:
        """Không phải bắt bẻ hình thức: hai bản ghi khác hẳn nhau nhưng
        cùng có trường rỗng sẽ ra CÙNG một khoá và nuốt lẫn nhau — hỏng
        nặng hơn hẳn ghi trùng."""
        with pytest.raises(DecisionLogError, match="rỗng"):
            dedup_key({"loai": "PLAN", "pair": rong, "candle_ts": "T", "block": "b"})

    def test_hai_ban_ghi_khac_nhau_cung_truong_rong_se_trung_khoa(self) -> None:
        # Chứng minh mối nguy là có thật, không phải giả định: nếu bỏ chốt
        # ở trên thì hai bản ghi này ra cùng khoá "::".
        a = {"pair": "", "candle_ts": "", "block": ""}
        b = {"pair": None, "candle_ts": None, "block": None}
        assert ":".join(str(a[k] or "") for k in a) == ":".join(str(b[k] or "") for k in b)


class TestLZ45ChayHaiLanThemDung0Dong:
    def test_chay_lai_cung_loat_them_DUNG_0_dong(self, tmp_path: Path) -> None:
        """🔴 Đúng câu chữ spec dòng 2649."""
        so = tmp_path / "decision_log.jsonl"
        loat = [_lenh("OID-1"), _lenh("OID-2"), _plan()]

        assert ghi_nhieu(so, loat) == 3
        dong_sau_lan_1 = so.read_text(encoding="utf-8").count("\n")

        assert ghi_nhieu(so, loat) == 0  # lần hai: ĐÚNG 0
        assert so.read_text(encoding="utf-8").count("\n") == dong_sau_lan_1

    def test_ghi_trung_la_no_op_khong_doc_sua_ghi_de(self, tmp_path: Path) -> None:
        so = tmp_path / "s.jsonl"
        ghi_neu_chua_co(so, {**_lenh("OID-1"), "pnl_abs": 10.0})
        truoc = so.read_text(encoding="utf-8")

        # Cùng khoá nhưng nội dung KHÁC — phải no-op, KHÔNG đè bản cũ.
        assert ghi_neu_chua_co(so, {**_lenh("OID-1"), "pnl_abs": 999.0}) is False
        assert so.read_text(encoding="utf-8") == truoc
        assert "999" not in truoc

    def test_chay_lai_loat_dai_hon_chi_them_phan_moi(self, tmp_path: Path) -> None:
        so = tmp_path / "s.jsonl"
        ghi_nhieu(so, [_lenh("OID-1"), _lenh("OID-2")])
        assert ghi_nhieu(so, [_lenh("OID-1"), _lenh("OID-2"), _lenh("OID-3")]) == 1

    def test_file_chua_ton_tai_thi_tap_khoa_rong(self, tmp_path: Path) -> None:
        assert doc_khoa_da_co(tmp_path / "chua_co.jsonl") == set()

    def test_dong_hong_thi_RAISE_khong_bo_qua(self, tmp_path: Path) -> None:
        """Bỏ qua dòng hỏng = coi khoá trong đó như chưa tồn tại = tạo
        đúng bản trùng mà L-Z45 sinh ra để chặn."""
        so = tmp_path / "s.jsonl"
        so.write_text('{"loai": "VAO_RA_LENH"\nkhong phai json\n', encoding="utf-8")
        with pytest.raises(DecisionLogError, match="JSON"):
            doc_khoa_da_co(so)


class TestAppendOnlyVaCorrects:
    def test_ban_ghi_cu_khong_bao_gio_bi_sua(self, tmp_path: Path) -> None:
        so = tmp_path / "s.jsonl"
        ghi_neu_chua_co(so, _lenh("OID-1"))
        dong_dau = so.read_text(encoding="utf-8").splitlines()[0]

        ghi_neu_chua_co(so, _lenh("OID-2"))
        ghi_neu_chua_co(so, {**_lenh("OID-3"), "corrects": "OID-1"})

        # Dòng đầu vẫn nguyên văn sau khi có bản sửa trỏ về nó.
        assert so.read_text(encoding="utf-8").splitlines()[0] == dong_dau

    def test_ban_sua_la_dong_MOI_mang_corrects(self, tmp_path: Path) -> None:
        so = tmp_path / "s.jsonl"
        ghi_neu_chua_co(so, _lenh("OID-1"))
        ghi_neu_chua_co(so, {**_lenh("OID-2"), "corrects": "OID-1"})
        dong = [json.loads(d) for d in so.read_text(encoding="utf-8").splitlines()]
        assert len(dong) == 2
        assert dong[1]["corrects"] == "OID-1" and "corrects" not in dong[0]

    def test_corrects_tro_vao_khoa_KHONG_ton_tai_thi_raise(self, tmp_path: Path) -> None:
        so = tmp_path / "s.jsonl"
        ghi_neu_chua_co(so, _lenh("OID-1"))
        truoc = so.read_text(encoding="utf-8")
        with pytest.raises(DecisionLogError, match="corrects"):
            ghi_neu_chua_co(so, {**_lenh("OID-9"), "corrects": "KHONG-CO-KHOA-NAY"})
        assert so.read_text(encoding="utf-8") == truoc  # sổ không dài thêm

    def test_moi_dong_mang_san_dedup_key(self, tmp_path: Path) -> None:
        so = tmp_path / "s.jsonl"
        ghi_neu_chua_co(so, _plan())
        assert json.loads(so.read_text(encoding="utf-8"))["dedup_key"] == dedup_key(_plan())


def _ghi_tu_tien_trinh_con(duong_dan: str, order_id: str, so_lan: int, rao=None) -> None:
    """Chạy trong TIẾN TRÌNH RIÊNG — mỗi tiến trình có bộ nhớ riêng, nên
    không có tập khoá nào dùng chung; chỉ `flock` trên file mới chặn được
    ghi trùng. `rao` (Barrier) để mọi tiến trình cùng lao vào một lúc."""
    from tool_d.ledger.decision_log import ghi_neu_chua_co as ghi

    if rao is not None:
        rao.wait(timeout=30)
    for _ in range(so_lan):
        ghi(Path(duong_dan), {"loai": "VAO_RA_LENH", "exchange_order_id": order_id})


def _giu_khoa_roi_nha(duong_dan: str, da_giu, giu_giay: float) -> None:
    """Tiến trình con GIỮ `flock` độc quyền trên file sổ trong `giu_giay`
    giây, rồi nhả."""
    import fcntl as _fcntl
    import time as _time

    with open(duong_dan, "a+", encoding="utf-8") as f:
        _fcntl.flock(f.fileno(), _fcntl.LOCK_EX)
        da_giu.set()
        _time.sleep(giu_giay)
        _fcntl.flock(f.fileno(), _fcntl.LOCK_UN)


class TestGhiSongSong:
    """🔴 Vế *"kể cả khi có tiến trình song song ghi cùng file"* (spec dòng
    2649-2650).

    🔴 **Bản đầu của lớp này KHÔNG kiểm được thứ nó tự nhận, và tôi phát
    hiện bằng cách gỡ hẳn `flock` khỏi module: 22/22 vẫn XANH.** Lý do:
    4 tiến trình ghi cùng một khoá nhưng thời điểm khởi động lệch nhau
    hàng chục mili giây, trong khi cửa sổ tranh chấp (đọc tập khoá → nối
    thêm) chỉ vài micro giây — nên tiến trình sau luôn thấy khoá đã có,
    kể cả khi không có khoá nào. Nó xanh vì may, không vì đúng: đúng họ
    lỗi PASS RỖNG.

    Sửa bằng hai ca bổ sung cho nhau:
      • `test_cua_ghi_THUC_SU_cho_khoa` — **tất định**: chứng minh cửa ghi
        có thực sự chờ `flock` hay không, bằng đồng hồ. Gỡ khoá đi là ca
        này đỏ ngay, không phụ thuộc may rủi lịch biểu.
      • ca chạy đua có `Barrier` — xác suất, giữ lại vì nó kiểm đúng hành
        vi ở mức hệ thống chứ không chỉ mức cơ chế.
    """

    def test_cua_ghi_THUC_SU_cho_khoa(self, tmp_path: Path) -> None:
        """Tiến trình ngoài giữ `flock` 1 giây; `ghi_neu_chua_co()` phải
        BỊ CHẶN suốt thời gian đó. Không có khoá thì nó xong tức thì."""
        import threading
        import time

        so = tmp_path / "cho_khoa.jsonl"
        so.touch()
        da_giu = mp.Event()
        GIU_GIAY = 1.0

        con = mp.Process(target=_giu_khoa_roi_nha, args=(str(so), da_giu, GIU_GIAY))
        con.start()
        try:
            assert da_giu.wait(timeout=30), "tiến trình con không giữ được khoá"

            xong_luc: list[float] = []

            def _ghi() -> None:
                ghi_neu_chua_co(so, _lenh("OID-CHO"))
                xong_luc.append(time.monotonic())

            bat_dau = time.monotonic()
            luong = threading.Thread(target=_ghi)
            luong.start()
            luong.join(timeout=30)
            assert xong_luc, "lượt ghi không hoàn tất"

            da_cho = xong_luc[0] - bat_dau
            assert da_cho >= GIU_GIAY * 0.5, (
                f"Cửa ghi hoàn tất sau {da_cho:.3f}s trong khi khoá bị giữ "
                f"{GIU_GIAY}s — nghĩa là nó KHÔNG chờ flock."
            )
        finally:
            con.join(timeout=30)

    def test_bon_tien_trinh_cung_lao_vao_MOT_khoa_chi_ra_MOT_dong(self, tmp_path: Path) -> None:
        so = tmp_path / "song_song.jsonl"
        rao = mp.Barrier(4)  # ép bốn tiến trình cùng lao vào một lúc
        tien_trinh = [
            mp.Process(target=_ghi_tu_tien_trinh_con, args=(str(so), "OID-DUNG-MOT", 25, rao))
            for _ in range(4)
        ]
        for p in tien_trinh:
            p.start()
        for p in tien_trinh:
            p.join(timeout=60)

        assert all(p.exitcode == 0 for p in tien_trinh), [p.exitcode for p in tien_trinh]
        dong = [d for d in so.read_text(encoding="utf-8").splitlines() if d.strip()]
        assert len(dong) == 1, f"100 lượt ghi cùng một khoá phải ra ĐÚNG 1 dòng, ra {len(dong)}"

    def test_bon_tien_trinh_ghi_bon_khoa_khac_nhau_ra_du_bon_dong(self, tmp_path: Path) -> None:
        """Đối chứng: nếu ca trên xanh chỉ vì cửa ghi chặn nhầm mọi thứ
        thì ca này sẽ đỏ."""
        so = tmp_path / "bon_khoa.jsonl"
        rao = mp.Barrier(4)
        tien_trinh = [
            mp.Process(target=_ghi_tu_tien_trinh_con, args=(str(so), f"OID-{i}", 10, rao))
            for i in range(4)
        ]
        for p in tien_trinh:
            p.start()
        for p in tien_trinh:
            p.join(timeout=60)

        assert all(p.exitcode == 0 for p in tien_trinh)
        dong = [d for d in so.read_text(encoding="utf-8").splitlines() if d.strip()]
        assert len(dong) == 4
