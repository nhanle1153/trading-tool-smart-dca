"""TD-0143 (§0d.3, bug Tool A số 4) — cache resume WFO phải MANG VÂN TAY.

Đây là chỗ Tool A *"sửa code rồi chạy lại vẫn ra số y hệt"*, và chỉ phát
hiện được vì hai lần chạy trùng nhau đến từng chữ số. Cache sai không báo
lỗi — nó lặng lẽ trả lại quá khứ.

🔴 Bất biến quan trọng nhất của bộ test này: **STALE không được gộp vào
MISS**. Gộp lại thì kết quả cuối vẫn ĐÚNG (đằng nào cũng chạy lại), nên
không test nào đỏ — nhưng mất đúng thứ đáng giá: tín hiệu rằng có gì đó
đã đổi mà mình không chủ ý đổi. Vì vậy có test riêng đòi hai trạng thái
đó phân biệt được, và đòi cảnh báo phải TO thật.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from tool_d.config.loader import DEFAULT_CONFIG_PATH, load_tool_d_config
from tool_d.measurement.gitinfo import get_git_info
from tool_d.wfo.cache import (
    KHOA_BAT_BUOC,
    KHOA_VAN_TAY,
    CacheError,
    TrangThai,
    VanTay,
    doc_cache,
    ghi_cache,
    van_tay_hien_tai,
    xoa_cache,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

VT = VanTay(params_hash="p" * 64, code_sha="c" * 40, data_hash="BTC=abc;ETH=def")
PAYLOAD = {"fold": 1, "pnl_abs": 12.5, "n_trades": 41}


def _ghi(thu_muc: Path, *, van_tay: VanTay = VT, khoa: str = "fold1") -> Path:
    return ghi_cache(
        khoa=khoa,
        payload=PAYLOAD,
        van_tay=van_tay,
        cache_dir=thu_muc,
        ghi_luc="2026-09-07T22:00:00Z",
    )


@pytest.fixture
def thu_muc(tmp_path: Path) -> Path:
    return tmp_path / "wfo_cache"


class TestBaTrangThaiPhanBietDuoc:
    """Ba lối ra, không phải hai — xem docstring module."""

    def test_khop_van_tay_thi_HIT_va_tra_payload(self, thu_muc: Path) -> None:
        _ghi(thu_muc)
        kq = doc_cache(khoa="fold1", van_tay=VT, cache_dir=thu_muc)
        assert kq.trang_thai is TrangThai.HIT
        assert kq.payload == PAYLOAD
        assert kq.dung_duoc is True
        assert kq.canh_bao == "", "HIT không được kèm cảnh báo — sẽ làm nhiễu cảnh báo thật"

    def test_chua_co_muc_thi_MISS_va_IM_LANG(self, thu_muc: Path) -> None:
        """Chưa có cache là chuyện bình thường, KHÔNG được cảnh báo —
        cảnh báo cho ca bình thường sẽ dạy người đọc bỏ qua cảnh báo."""
        kq = doc_cache(khoa="chua_co", van_tay=VT, cache_dir=thu_muc)
        assert kq.trang_thai is TrangThai.MISS
        assert kq.payload is None
        assert kq.canh_bao == ""

    @pytest.mark.parametrize("thanh_phan", sorted(KHOA_VAN_TAY))
    def test_lech_bat_ky_thanh_phan_nao_deu_STALE(self, thu_muc: Path, thanh_phan: str) -> None:
        """Ba thành phần §0d.3 liệt kê, thiếu canh cái nào là mở lại đúng
        một cửa đã hạ Tool A: đổi tham số / sửa code / vá dữ liệu."""
        _ghi(thu_muc)
        moi = replace(VT, **{thanh_phan: "KHAC" * 10})
        kq = doc_cache(khoa="fold1", van_tay=moi, cache_dir=thu_muc)
        assert kq.trang_thai is TrangThai.STALE, f"lệch {thanh_phan} mà vẫn cho dùng"
        assert kq.payload is None, "STALE tuyệt đối KHÔNG được trả payload"
        assert kq.dung_duoc is False
        assert thanh_phan in kq.canh_bao

    def test_STALE_KHAC_MISS(self, thu_muc: Path) -> None:
        """🔴 Bất biến chính. Gộp hai cái này lại thì kết quả vẫn đúng nên
        không ai nhận ra — nhưng mất tín hiệu 'có gì đó đổi ngoài ý muốn'."""
        _ghi(thu_muc)
        stale = doc_cache(khoa="fold1", van_tay=replace(VT, code_sha="z" * 40), cache_dir=thu_muc)
        miss = doc_cache(khoa="khong_co", van_tay=VT, cache_dir=thu_muc)
        assert stale.trang_thai is not miss.trang_thai
        assert stale.canh_bao != "" and miss.canh_bao == ""


class TestCanhBaoPhaiTOThat:
    """§0d.3 dùng đúng chữ 'CẢNH BÁO TO' — nên nó phải to thật."""

    def test_canh_bao_neu_duoc_lech_o_dau_va_ca_hai_gia_tri(self, thu_muc: Path) -> None:
        _ghi(thu_muc)
        moi = replace(VT, code_sha="z" * 40)
        cb = doc_cache(khoa="fold1", van_tay=moi, cache_dir=thu_muc).canh_bao
        assert "code_sha" in cb
        assert "c" * 40 in cb, "phải in giá trị TRONG CACHE"
        assert "z" * 40 in cb, "phải in giá trị LẦN CHẠY NÀY"
        assert "0d.3" in cb
        assert cb.count("\n") >= 8, "cảnh báo một dòng thì không phải cảnh báo TO"

    def test_canh_bao_noi_ro_day_khong_phai_loi(self, thu_muc: Path) -> None:
        """Đổi code/tham số/dữ liệu là bình thường. Cảnh báo phải nói rõ
        điều đó, nếu không nó sẽ bị coi là báo động giả và bị tắt."""
        _ghi(thu_muc)
        cb = doc_cache(khoa="fold1", van_tay=replace(VT, code_sha="z" * 40), cache_dir=thu_muc).canh_bao
        assert "KHÔNG phải lỗi" in cb
        assert "KHÔNG chủ ý" in cb

    def test_lech_nhieu_thanh_phan_thi_liet_ke_du(self, thu_muc: Path) -> None:
        _ghi(thu_muc)
        moi = replace(VT, code_sha="z" * 40, data_hash="doi-roi")
        cb = doc_cache(khoa="fold1", van_tay=moi, cache_dir=thu_muc).canh_bao
        assert "code_sha" in cb and "data_hash" in cb
        assert "params_hash" not in cb.split("lệch ở:")[1].split("\n")[0]


class TestHinhDangMucCacheKhongLechDuoc:
    """Bài học từ phiên song song (TD-0130): thêm khoá vào bản ghi mà quên
    schema — 735 test xanh VẪN không bắt được, vì test chỉ đối chiếu FIXTURE
    GÕ TAY chứ chưa lần nào đối chiếu ĐẦU RA THẬT. Ở đây soi đầu ra thật."""

    def test_dau_ra_that_cua_ghi_cache_khop_dung_KHOA_BAT_BUOC(self, thu_muc: Path) -> None:
        duong_dan = _ghi(thu_muc)
        tren_dia = json.loads(duong_dan.read_text(encoding="utf-8"))
        assert set(tren_dia) == set(KHOA_BAT_BUOC), (
            "đầu ra thật lệch tập khoá mà hàm đọc dựa vào — đúng loại drift "
            "mà bộ test fixture-gõ-tay không bắt được"
        )
        assert set(tren_dia["van_tay"]) == set(KHOA_VAN_TAY)

    def test_ghi_roi_doc_lai_khop_tron_ven(self, thu_muc: Path) -> None:
        _ghi(thu_muc)
        assert doc_cache(khoa="fold1", van_tay=VT, cache_dir=thu_muc).payload == PAYLOAD

    def test_van_tay_bat_buoc_khong_co_mac_dinh(self) -> None:
        """Một mục cache không vân tay CHÍNH LÀ mục cache của Tool A. Nếu
        tham số này có mặc định thì sớm muộn có chỗ gọi quên truyền."""
        with pytest.raises(TypeError):
            ghi_cache(khoa="x", payload={}, ghi_luc="x")  # type: ignore[call-arg]


class TestMucHongThiFailClosed:
    """Lệch vân tay = bình thường (STALE). File hỏng = lỗi (raise).
    Hai thứ khác nhau, không được gộp."""

    def test_json_hong_thi_raise(self, thu_muc: Path) -> None:
        thu_muc.mkdir(parents=True)
        (thu_muc / "fold1.json").write_text("{khong phai json", encoding="utf-8")
        with pytest.raises(CacheError):
            doc_cache(khoa="fold1", van_tay=VT, cache_dir=thu_muc)

    @pytest.mark.parametrize("bo_khoa", sorted(KHOA_BAT_BUOC))
    def test_thieu_khoa_bat_buoc_thi_raise(self, thu_muc: Path, bo_khoa: str) -> None:
        duong_dan = _ghi(thu_muc)
        muc = json.loads(duong_dan.read_text(encoding="utf-8"))
        del muc[bo_khoa]
        duong_dan.write_text(json.dumps(muc), encoding="utf-8")
        with pytest.raises(CacheError):
            doc_cache(khoa="fold1", van_tay=VT, cache_dir=thu_muc)

    @pytest.mark.parametrize("bo", sorted(KHOA_VAN_TAY))
    def test_van_tay_thieu_thanh_phan_thi_raise_KHONG_phai_STALE(
        self, thu_muc: Path, bo: str
    ) -> None:
        """Vân tay thiếu thành phần thì KHÔNG kết luận được là khớp hay lệch
        — fail-closed, raise. Coi nó là STALE sẽ che mất một file cache hỏng."""
        duong_dan = _ghi(thu_muc)
        muc = json.loads(duong_dan.read_text(encoding="utf-8"))
        del muc["van_tay"][bo]
        duong_dan.write_text(json.dumps(muc), encoding="utf-8")
        with pytest.raises(CacheError):
            doc_cache(khoa="fold1", van_tay=VT, cache_dir=thu_muc)

    @pytest.mark.parametrize("khoa_xau", ["", "..", "a/b", "a\\b", "."])
    def test_khoa_cache_ban_thi_raise(self, thu_muc: Path, khoa_xau: str) -> None:
        with pytest.raises(CacheError):
            doc_cache(khoa=khoa_xau, van_tay=VT, cache_dir=thu_muc)


class TestXoaCache:
    """§0d.3: 'xoá cache trước khi đo lại sau khi đổi mặc định' — có hàm thì
    bước đó chạy được và ghi lại được, thay vì một câu dặn trong tài liệu."""

    def test_xoa_mot_muc(self, thu_muc: Path) -> None:
        _ghi(thu_muc, khoa="fold1")
        _ghi(thu_muc, khoa="fold2")
        assert xoa_cache(cache_dir=thu_muc, khoa="fold1") == 1
        assert doc_cache(khoa="fold1", van_tay=VT, cache_dir=thu_muc).trang_thai is TrangThai.MISS
        assert doc_cache(khoa="fold2", van_tay=VT, cache_dir=thu_muc).trang_thai is TrangThai.HIT

    def test_xoa_toan_bo(self, thu_muc: Path) -> None:
        for k in ("fold1", "fold2", "fold3"):
            _ghi(thu_muc, khoa=k)
        assert xoa_cache(cache_dir=thu_muc) == 3
        assert xoa_cache(cache_dir=thu_muc) == 0

    def test_thu_muc_chua_ton_tai_thi_tra_0_khong_raise(self, tmp_path: Path) -> None:
        assert xoa_cache(cache_dir=tmp_path / "chua_co") == 0


class TestVanTayHienTaiNoiVaoThuThAT:
    """Hàm này là chỗ cache gặp config + git THẬT. Test ba lớp trên toàn
    bằng vân tay dựng tay — nếu chỗ nối này sai thì mọi test kia vẫn xanh
    trong khi cache thật hỏng hoàn toàn."""

    def test_params_hash_lay_dung_tu_config_khong_bam_lai(self) -> None:
        """`loader` đã băm nguyên văn YAML. Băm lại ở đây là nguồn sự thật
        thứ hai cho cùng một con số."""
        cfg = load_tool_d_config(REPO_ROOT / DEFAULT_CONFIG_PATH)
        vt = van_tay_hien_tai(cfg=cfg, data_hashes={}, repo_dir=REPO_ROOT)
        assert vt.params_hash == cfg.sha256

    def test_code_sha_lay_dung_tu_git(self) -> None:
        cfg = load_tool_d_config(REPO_ROOT / DEFAULT_CONFIG_PATH)
        vt = van_tay_hien_tai(cfg=cfg, data_hashes={}, repo_dir=REPO_ROOT)
        assert vt.code_sha == get_git_info(REPO_ROOT).sha
        assert vt.code_sha != "UNKNOWN", "giá trị lính canh lọt vào vân tay (N6)"

    def test_data_hash_tat_dinh_khong_phu_thuoc_thu_tu_dict(self) -> None:
        """Hai dict cùng nội dung khác thứ tự phải cho CÙNG vân tay — nếu
        không, cache sẽ STALE giả mỗi lần chạy và thành vô dụng."""
        cfg = load_tool_d_config(REPO_ROOT / DEFAULT_CONFIG_PATH)
        a = van_tay_hien_tai(cfg=cfg, data_hashes={"BTC": "1", "ETH": "2"}, repo_dir=REPO_ROOT)
        b = van_tay_hien_tai(cfg=cfg, data_hashes={"ETH": "2", "BTC": "1"}, repo_dir=REPO_ROOT)
        assert a.data_hash == b.data_hash

    def test_doi_mot_file_du_lieu_thi_van_tay_DOI(self) -> None:
        cfg = load_tool_d_config(REPO_ROOT / DEFAULT_CONFIG_PATH)
        a = van_tay_hien_tai(cfg=cfg, data_hashes={"BTC": "1"}, repo_dir=REPO_ROOT)
        b = van_tay_hien_tai(cfg=cfg, data_hashes={"BTC": "2"}, repo_dir=REPO_ROOT)
        assert a.data_hash != b.data_hash

    def test_khong_doc_file_nao_thi_data_hash_rong_KHAC_voi_khong_biet(self) -> None:
        """Chuỗi rỗng có nghĩa 'lần chạy này không đọc file dữ liệu nào' —
        một trạng thái hợp lệ, khác hẳn 'không biết' (N6 cấm lính canh)."""
        cfg = load_tool_d_config(REPO_ROOT / DEFAULT_CONFIG_PATH)
        assert van_tay_hien_tai(cfg=cfg, data_hashes={}, repo_dir=REPO_ROOT).data_hash == ""

    def test_vong_doi_that_ghi_roi_doc_lai_bang_van_tay_that(self, thu_muc: Path) -> None:
        cfg = load_tool_d_config(REPO_ROOT / DEFAULT_CONFIG_PATH)
        vt = van_tay_hien_tai(cfg=cfg, data_hashes={"BTC": "abc"}, repo_dir=REPO_ROOT)
        ghi_cache(khoa="that", payload=PAYLOAD, van_tay=vt, cache_dir=thu_muc, ghi_luc="x")
        assert doc_cache(khoa="that", van_tay=vt, cache_dir=thu_muc).trang_thai is TrangThai.HIT
