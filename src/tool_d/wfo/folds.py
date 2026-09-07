"""TD-0141 — sinh danh sách fold walk-forward từ `tier_c.wfo_folds`.

Sơ đồ đã niêm phong ở `docs/decisions/DR-D3-01-so-do-fold.md` (DR-D3-01,
chủ dự án chốt 07/09/2026): **neo gốc (anchored), 3 fold**, train khởi
tạo 12 tuần rồi dài dần, mỗi cửa sổ test 7 tuần, tất cả nằm trọn trong
`[T1, T2]`.

🔴 **Module này KHÔNG tự viết lại phép kiểm timerange.** Nó gọi
`assert_dataset_timerange()` (`ledger/timerange.py`, L-Z55) với
`boundary` lấy từ `dataset_boundaries_from_config()` — cùng một máy canh
đã có từ TD-0094. Viết một phép kiểm "gần giống" ở đây là tạo nguồn sự
thật thứ hai cho cùng một ràng buộc, đúng thứ TD-0094 đã tránh được một
lần (xem `docs/research-log.md` 07/09/2026: bản `enforce_timerange_ceiling()`
viết ra rồi xoá, không commit).

🔴 **Fail-closed toàn tuyến:** thiếu khoá cấu hình → raise; sơ đồ không
vừa cửa sổ → raise; cửa sổ test chồng lấn → raise. KHÔNG tự cắt bớt,
KHÔNG tự đoán mặc định, KHÔNG tự co số fold cho vừa — mọi hành vi "tự
sửa cho chạy được" đều biến một sai cấu hình thành một kết quả sai âm
thầm.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from tool_d.config.loader import ToolDConfig, resolve
from tool_d.ledger.timerange import (
    DatasetBoundary,
    assert_dataset_timerange,
    dataset_boundaries_from_config,
)

NGAY_MOI_TUAN = 7


class FoldConfigError(RuntimeError):
    """Cấu hình fold không dùng được — thiếu khoá, giá trị vô lý, hoặc sơ
    đồ không vừa cửa sổ WFO. Fail-closed: raise, không tự sửa."""


@dataclass(frozen=True)
class Fold:
    """Một fold walk-forward.

    `train_start` luôn bằng `T1` với sơ đồ neo gốc — giữ trường này tường
    minh thay vì ngầm hiểu, để khi nào đổi sang rolling (cần bằng chứng
    chế độ thị trường đổi hẳn, DR-D3-01 §6) thì chỗ đổi là ở đây chứ
    không phải rải rác trong code gọi.

    Ranh giới nửa mở `[start, end)`: `train_end == test_start` nghĩa là
    nến tại `train_end` thuộc TEST, không thuộc train. Quy ước này chọn
    một lần ở đây để không phải hỏi lại ở từng chỗ dùng — chồng lấn một
    nến giữa train và test là rò rỉ IS→OOS, loại lỗi không báo lỗi.
    """

    chi_so: int  # 1-based, khớp cách gọi "fold 1/2/3" trong DR và báo cáo
    train_start: date
    train_end: date
    test_start: date
    test_end: date

    @property
    def train_ngay(self) -> int:
        return (self.train_end - self.train_start).days

    @property
    def test_ngay(self) -> int:
        return (self.test_end - self.test_start).days


def _doc_cau_hinh(cfg: ToolDConfig) -> tuple[int, int, int]:
    """Đọc `so_fold` / `train_khoi_tao_tuan` / `test_tuan`. Thiếu khoá hay
    giá trị <= 0 → raise (N4 + fail-closed: không có mặc định ngầm)."""
    try:
        khoi = resolve(cfg, "tier_c.wfo_folds")
    except Exception as exc:  # khoá chưa tồn tại trong config
        raise FoldConfigError(
            "Thiếu `tier_c.wfo_folds` trong tool_d_config.yaml — sơ đồ fold "
            "phải đến từ cấu hình (N4), không có mặc định trong code."
        ) from exc

    gia_tri: list[int] = []
    for ten in ("so_fold", "train_khoi_tao_tuan", "test_tuan"):
        if ten not in khoi:
            raise FoldConfigError(f"Thiếu `tier_c.wfo_folds.{ten}`.")
        v = khoi[ten]
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            raise FoldConfigError(
                f"`tier_c.wfo_folds.{ten}` phải là số nguyên dương, nhận: {v!r}"
            )
        gia_tri.append(v)
    return gia_tri[0], gia_tri[1], gia_tri[2]


def san_lenh_moi_fold(cfg: ToolDConfig) -> int:
    """Ngưỡng dưới đã khai TRƯỚC ở DR-D3-01 §5.2. Fold có ít lệnh hơn số
    này thì mọi chỉ số của nó ghi `unreadable`, KHÔNG ghi số (N6).

    Tách thành hàm riêng để chỗ dùng (TD-0142/TD-0146) đọc từ đúng một
    nguồn — không ai được gõ lại con số 30 ở nơi khác.
    """
    khoi = resolve(cfg, "tier_c.wfo_folds")
    if "san_lenh_moi_fold" not in khoi:
        raise FoldConfigError("Thiếu `tier_c.wfo_folds.san_lenh_moi_fold`.")
    v = khoi["san_lenh_moi_fold"]
    if not isinstance(v, int) or isinstance(v, bool) or v < 1:
        raise FoldConfigError(
            f"`san_lenh_moi_fold` phải là số nguyên >= 1, nhận: {v!r}"
        )
    return v


def sinh_folds(cfg: ToolDConfig) -> tuple[Fold, ...]:
    """Sinh danh sách fold neo gốc cho cửa sổ WFO `[T1, T2]`.

    Bố cục (DR-D3-01 §5.1) — với `k` fold, train khởi tạo `A` tuần, test
    `B` tuần, mọi mốc tính từ `T1`::

        fold i (i = 1..k):
            train = [T1,  T1 + A + (i-1)·B)
            test  = [T1 + A + (i-1)·B,  T1 + A + i·B)

    Tức cửa sổ test nối đuôi nhau không hở không chồng, và train của fold
    sau nuốt trọn cả train lẫn test của fold trước — đó chính là "neo
    gốc": thông tin chỉ được đi từ quá khứ sang tương lai.

    RAISE nếu `A + k·B` vượt quá độ dài `[T1, T2]` — KHÔNG tự giảm `k`,
    KHÔNG tự cắt ngắn fold cuối. Sơ đồ fold là thứ đã niêm phong; nó
    không vừa dữ liệu thì phải sửa DR qua kênh chính thức
    (`param_change_proposals.jsonl`, L-Z26), không phải để code lặng lẽ
    co lại cho chạy được.
    """
    so_fold, train_tuan, test_tuan = _doc_cau_hinh(cfg)
    wfo = dataset_boundaries_from_config(cfg)["WFO"]

    can_ngay = (train_tuan + so_fold * test_tuan) * NGAY_MOI_TUAN
    co_ngay = (wfo.end - wfo.start).days
    if can_ngay > co_ngay:
        raise FoldConfigError(
            f"Sơ đồ fold cần {can_ngay} ngày (train {train_tuan} tuần + "
            f"{so_fold} × test {test_tuan} tuần) nhưng cửa sổ WFO "
            f"[{wfo.start}, {wfo.end}] chỉ có {co_ngay} ngày. "
            "TỪ CHỐI — không tự giảm số fold cũng không cắt ngắn fold cuối; "
            "sửa DR-D3-01 qua kênh đề xuất đổi tham số (L-Z26)."
        )

    folds: list[Fold] = []
    for i in range(so_fold):
        test_start = wfo.start + timedelta(days=(train_tuan + i * test_tuan) * NGAY_MOI_TUAN)
        test_end = test_start + timedelta(days=test_tuan * NGAY_MOI_TUAN)
        folds.append(
            Fold(
                chi_so=i + 1,
                train_start=wfo.start,  # neo gốc: mọi fold bắt đầu tại T1
                train_end=test_start,
                test_start=test_start,
                test_end=test_end,
            )
        )
    kiem_folds(tuple(folds), boundary=wfo)
    return tuple(folds)


def kiem_folds(folds: tuple[Fold, ...], *, boundary: DatasetBoundary) -> None:
    """Ba bất biến của một danh sách fold hợp lệ. Gọi ngay trong
    `sinh_folds()` — sinh xong tự kiểm, không chờ ai nhớ gọi.

    Tách hàm riêng (thay vì viết thẳng vào `sinh_folds`) để test khoá gọi
    được nó trên một danh sách fold DỰNG TAY bị hỏng cố ý; nếu chỉ kiểm
    qua `sinh_folds()` thì không dựng được ca hỏng nào, và bộ test sẽ
    xanh một cách vô nghĩa.
    """
    if not folds:
        raise FoldConfigError("Danh sách fold rỗng — không có gì để chạy.")

    for f in folds:
        # (1) Mọi mốc nằm TRỌN trong ranh giới WFO. Dùng lại đúng máy canh
        #     L-Z55, không viết phép so sánh riêng ở đây.
        assert_dataset_timerange(
            dataset="WFO",
            observed_start=f.train_start,
            observed_end=f.test_end,
            boundary=boundary,
        )
        # (2) Thứ tự thời gian trong một fold: train phải đi TRƯỚC test và
        #     không được rỗng. train_end == test_start là đúng thiết kế
        #     (ranh giới nửa mở), nhưng train_end > test_start là rò rỉ.
        if not (f.train_start < f.train_end <= f.test_start < f.test_end):
            raise FoldConfigError(
                f"Fold {f.chi_so} sai thứ tự thời gian: train "
                f"[{f.train_start}, {f.train_end}) test [{f.test_start}, {f.test_end})."
            )

    # (3) Cửa sổ TEST không chồng lấn nhau — hai fold cùng đo một đoạn thời
    #     gian thì chúng không còn là hai quan sát độc lập, và mọi phép
    #     thống kê "ổn định qua fold" mất nghĩa.
    theo_thoi_gian = sorted(folds, key=lambda f: f.test_start)
    for truoc, sau in zip(theo_thoi_gian, theo_thoi_gian[1:]):
        if sau.test_start < truoc.test_end:
            raise FoldConfigError(
                f"Cửa sổ test của fold {truoc.chi_so} [{truoc.test_start}, "
                f"{truoc.test_end}) chồng lấn fold {sau.chi_so} "
                f"[{sau.test_start}, {sau.test_end})."
            )
