"""TD-0143 — cache resume WFO phải MANG VÂN TAY (§0d.3, bug Tool A số 4).

Đây đúng chỗ Tool A *"sửa code rồi chạy lại vẫn ra số y hệt"* — và chỉ phát
hiện được vì hai lần chạy trùng nhau **đến từng chữ số**. Cache không báo
lỗi khi nó sai; nó chỉ lặng lẽ trả lại quá khứ. Đó là nhiễm bậc hai: số ra
trông hợp lệ, chạy được, ghi vào sổ được — chỉ không phải số của lần chạy này.

Spec §0d.3: *"Cache tự viết (resume WFO) PHẢI ghi kèm `params_hash` +
`code_sha` + `data_hash`; đọc lại mà hash lệch → CẢNH BÁO TO và KHÔNG dùng."*

🔑 **Ba trạng thái, không phải hai.** Chỗ dễ sai nhất của module này là gộp
   "cache lệch vân tay" vào chung với "chưa có cache":

     HIT   — vân tay khớp        → dùng lại, tiết kiệm thật
     MISS  — chưa có mục cache   → bình thường, chạy mới, KHÔNG báo gì
     STALE — có mục nhưng LỆCH   → 🔴 CẢNH BÁO TO, chạy mới, KHÔNG dùng

   Nếu gộp STALE vào MISS thì kết quả vẫn ĐÚNG (vì đằng nào cũng chạy lại),
   nên không test nào đỏ và không ai nhận ra. Nhưng mất đúng thứ đáng giá:
   tín hiệu rằng có gì đó đã đổi mà mình không chủ ý đổi. Yêu cầu của việc
   này viết thẳng ra điều đó — *"không âm thầm dùng tiếp, cũng không âm thầm
   BỎ"*. Vì vậy STALE là một trạng thái riêng, mang theo câu giải thích
   lệch ở đâu, và `doc_cache()` không bao giờ trả payload cho nó.

🔑 **Một nguồn sự thật cho hình dạng mục cache.** `KHOA_BAT_BUOC` được DÙNG
   CHUNG bởi cả hàm ghi lẫn hàm đọc, và có test đối chiếu ĐẦU RA THẬT của
   `ghi_cache()` với đúng tập khoá đó. Lý do có ràng buộc này: phiên song
   song vừa mất một vòng vì thêm khoá vào sự kiện RESERVE mà quên
   `trial_event.schema.json` — 735 test xanh KHÔNG bắt được, vì test chỉ đối
   chiếu FIXTURE GÕ TAY chứ chưa lần nào đối chiếu đầu ra thật với schema.
   Ở đây không có file schema riêng để lệch, và test soi đầu ra thật.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from tool_d.config.loader import ToolDConfig
from tool_d.measurement.gitinfo import get_git_info

DEFAULT_CACHE_DIR = Path("runs/wfo_cache")

# Hình dạng một mục cache — nguồn sự thật DUY NHẤT, dùng chung cho ghi và đọc.
KHOA_BAT_BUOC = frozenset({"van_tay", "payload", "ghi_luc"})
KHOA_VAN_TAY = frozenset({"params_hash", "code_sha", "data_hash"})


class CacheError(RuntimeError):
    """Mục cache hỏng về cấu trúc — KHÔNG phải chuyện lệch vân tay.

    Lệch vân tay là chuyện BÌNH THƯỜNG (đổi code, đổi tham số, đổi dữ liệu)
    và được xử bằng trạng thái STALE. Còn file không đọc nổi / thiếu khoá là
    lỗi lập trình hoặc file bị hỏng — fail-closed, raise.
    """


class TrangThai(Enum):
    HIT = "HIT"
    MISS = "MISS"
    STALE = "STALE"


@dataclass(frozen=True)
class VanTay:
    """Ba thứ mà một kết quả backtest phụ thuộc vào — §0d.3 liệt kê đúng ba.

    Thiếu bất kỳ cái nào là mở lại đúng cửa đã hạ Tool A:
      • `params_hash` — đổi `tool_d_config.yaml` mà cache vẫn trả số cũ
      • `code_sha`    — sửa code chiến lược mà cache vẫn trả số cũ
      • `data_hash`   — backfill/vá dữ liệu mà cache vẫn trả số cũ
    """

    params_hash: str
    code_sha: str
    data_hash: str

    def lech_o_dau(self, khac: VanTay) -> list[str]:
        """Liệt kê tên các thành phần lệch — rỗng nghĩa là khớp.

        Trả DANH SÁCH chứ không trả bool: khi cảnh báo bật lên, câu hỏi đầu
        tiên của người đọc luôn là "lệch cái gì", và bắt họ tự so hai chuỗi
        hex 64 ký tự là cách chắc chắn khiến cảnh báo bị bỏ qua.
        """
        return [
            ten
            for ten in sorted(KHOA_VAN_TAY)
            if getattr(self, ten) != getattr(khac, ten)
        ]


@dataclass(frozen=True)
class KetQuaDoc:
    """Kết quả một lần đọc cache. `payload` chỉ khác None khi HIT."""

    trang_thai: TrangThai
    payload: dict[str, Any] | None = None
    canh_bao: str = ""

    @property
    def dung_duoc(self) -> bool:
        return self.trang_thai is TrangThai.HIT


def van_tay_hien_tai(
    *,
    cfg: ToolDConfig,
    data_hashes: dict[str, str],
    repo_dir: Path = Path("."),
) -> VanTay:
    """Vân tay của lần chạy ĐANG diễn ra.

    Dùng lại hạ tầng có sẵn, không tự băm lại: `cfg.sha256` (loader đã băm
    nguyên văn YAML), `get_git_info().sha`, và `data_hashes` do chỗ gọi đưa
    vào (thường từ `measurement.hashing.hash_many()` — cùng dict đã nằm
    trong khối provenance 0d.5, nên cache và provenance không thể kể hai
    câu chuyện khác nhau về cùng một lần chạy).

    `get_git_info()` cố ý KHÔNG bọc try/except: nó raise `GitInfoError` với
    ghi chú *"KHÔNG được bắt lỗi này rồi trả UNKNOWN"*. Một vân tay mang
    `code_sha = "UNKNOWN"` sẽ khớp với chính nó ở lần sau và biến cache
    thành đúng cái bẫy module này sinh ra để chặn.
    """
    return VanTay(
        params_hash=cfg.sha256,
        code_sha=get_git_info(repo_dir).sha,
        data_hash=_gop_data_hash(data_hashes),
    )


def _gop_data_hash(data_hashes: dict[str, str]) -> str:
    """Gộp nhiều hash file thành một chuỗi TẤT ĐỊNH (sắp theo tên).

    Không băm lại lần nữa: giữ nguyên văn để khi lệch còn đọc được file nào
    đổi. Dict rỗng cho ra chuỗi rỗng — hợp lệ và có nghĩa ("lần chạy này
    không đọc file dữ liệu nào"), khác hẳn với "không biết".
    """
    return ";".join(f"{ten}={data_hashes[ten]}" for ten in sorted(data_hashes))


def _duong_dan(cache_dir: Path, khoa: str) -> Path:
    if not khoa or "/" in khoa or "\\" in khoa or khoa in (".", ".."):
        raise CacheError(f"Khoá cache không hợp lệ: {khoa!r}")
    return cache_dir / f"{khoa}.json"


def ghi_cache(
    *,
    khoa: str,
    payload: dict[str, Any],
    van_tay: VanTay,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    ghi_luc: str,
) -> Path:
    """Ghi một mục cache KÈM vân tay. Trả đường dẫn file đã ghi.

    Vân tay là tham số BẮT BUỘC, không có mặc định: một mục cache không có
    vân tay chính là mục cache của Tool A, và nếu để nó mặc định được thì
    sớm muộn sẽ có chỗ gọi quên truyền.
    """
    muc = {
        "van_tay": asdict(van_tay),
        "payload": payload,
        "ghi_luc": ghi_luc,
    }
    assert set(muc) == set(KHOA_BAT_BUOC)  # nguồn sự thật dùng chung với hàm đọc

    duong_dan = _duong_dan(cache_dir, khoa)
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    duong_dan.write_text(
        json.dumps(muc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return duong_dan


def doc_cache(
    *,
    khoa: str,
    van_tay: VanTay,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> KetQuaDoc:
    """Đọc mục cache và ĐỐI CHIẾU vân tay. Không bao giờ trả payload khi lệch.

    Ba lối ra ứng với ba trạng thái (xem docstring module). STALE mang theo
    `canh_bao` đã dựng sẵn thành văn bản to — chỗ gọi chỉ việc in ra, không
    phải tự nghĩ cách diễn đạt, để cảnh báo không bị rút gọn dần qua từng
    chỗ gọi cho tới lúc chỉ còn một dòng log lặng lẽ.
    """
    duong_dan = _duong_dan(cache_dir, khoa)
    if not duong_dan.exists():
        return KetQuaDoc(TrangThai.MISS)

    try:
        muc = json.loads(duong_dan.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CacheError(f"Mục cache {duong_dan} không đọc được: {exc}") from exc

    thieu = KHOA_BAT_BUOC - set(muc)
    if thieu:
        raise CacheError(
            f"Mục cache {duong_dan} thiếu khoá {sorted(thieu)} — mục cache KHÔNG có "
            "vân tay là mục cache không kiểm được, TỪ CHỐI dùng (§0d.3)."
        )
    thieu_vt = KHOA_VAN_TAY - set(muc["van_tay"])
    if thieu_vt:
        raise CacheError(
            f"Vân tay trong {duong_dan} thiếu {sorted(thieu_vt)} — §0d.3 đòi đủ "
            "params_hash + code_sha + data_hash."
        )

    cu = VanTay(**{k: muc["van_tay"][k] for k in KHOA_VAN_TAY})
    lech = cu.lech_o_dau(van_tay)
    if lech:
        return KetQuaDoc(
            TrangThai.STALE,
            payload=None,  # tường minh: KHÔNG dùng
            canh_bao=_banner_lech(duong_dan=duong_dan, cu=cu, moi=van_tay, lech=lech),
        )
    return KetQuaDoc(TrangThai.HIT, payload=muc["payload"])


def _banner_lech(*, duong_dan: Path, cu: VanTay, moi: VanTay, lech: list[str]) -> str:
    """Cảnh báo TO — spec §0d.3 dùng đúng chữ đó, nên nó phải TO thật."""
    dong = [
        "=" * 72,
        "🔴 CACHE WFO LỆCH VÂN TAY — KHÔNG DÙNG, CHẠY LẠI TỪ ĐẦU (§0d.3)",
        "=" * 72,
        f"  mục cache: {duong_dan}",
        f"  lệch ở:    {', '.join(lech)}",
    ]
    for ten in lech:
        dong.append(f"    {ten}:")
        dong.append(f"      trong cache: {getattr(cu, ten)}")
        dong.append(f"      lần chạy này: {getattr(moi, ten)}")
    dong += [
        "",
        "  Đây KHÔNG phải lỗi — code/tham số/dữ liệu đã đổi là chuyện bình thường.",
        "  Nhưng nếu bạn KHÔNG chủ ý đổi thứ nào trong danh sách trên, hãy dừng lại",
        "  và tìm hiểu trước khi tin bất kỳ con số nào của lần chạy này.",
        "",
        "  Quy trình §0d.3: xoá cache trước khi đo lại sau khi đổi mặc định —",
        f"  `xoa_cache()` hoặc xoá tay {duong_dan.parent}/",
        "=" * 72,
    ]
    return "\n".join(dong)


def xoa_cache(*, cache_dir: Path = DEFAULT_CACHE_DIR, khoa: str | None = None) -> int:
    """Xoá một mục (`khoa`) hoặc toàn bộ cache. Trả số file đã xoá.

    Thực thi bước *"xoá cache trước khi đo lại sau khi đổi mặc định"* của
    §0d.3 — có hàm thì thao tác đó là một lệnh chạy được và ghi lại được,
    thay vì một câu dặn trong tài liệu mà người ta nhớ hoặc không.
    """
    if not cache_dir.exists():
        return 0
    if khoa is not None:
        duong_dan = _duong_dan(cache_dir, khoa)
        if duong_dan.exists():
            duong_dan.unlink()
            return 1
        return 0
    n = 0
    for f in sorted(cache_dir.glob("*.json")):
        f.unlink()
        n += 1
    return n
