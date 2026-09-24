"""TrialLedger — đọc/ghi `trial_registry.jsonl`. DR-014 (sổ hai trạng thái).

Sổ NHẬT KÝ SỰ KIỆN (MT-01, back-end-note.md mục 7): mỗi dòng một sự kiện
(RESERVE/SEAL/CONSUME/REFUND/CONTAMINATE), append-only TUYỆT ĐỐI — không
bao giờ sửa hay xoá một dòng đã ghi. Trạng thái hiện tại của một trial là
BẢN CHIẾU tính lại bằng cách đọc hết sổ, không phải trường ghi tại chỗ.

Đường DUY NHẤT tới CALIB/WFO/LOCKBOX phải đi qua `reserve()` trước khi
chạm dữ liệu (L-Z52) — không có đặt chỗ hợp lệ, bộ chạy TỪ CHỐI khởi
động, KHÔNG được chạm dữ liệu trước.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import lru_cache
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import jsonschema

from tool_d.calibration.ung_vien import (
    BUDGET_LINE_B1,
    DEFAULT_DR_D5_01_PATH,
    KHOA_CONG_VAO_D9,
    UngVienError,
    doc_bang_ung_vien,
    kiem_dat_cho_b1,
)
from tool_d.gates.d0_pre import DEFAULT_RUNTIME_STATE_PATH
from tool_d.ledger.budget import REFUND_CAP_PER_HYPOTHESIS, HypothesisKey
from tool_d.ledger import budget as _budget

DEFAULT_REGISTRY_PATH = Path("registry/trial_registry.jsonl")


def _doc_d4_complete(runtime_state_path: Path) -> bool:
    """`d4_complete` theo `DR-D4-11` (cổng đóng bằng hiện vật, ghi bởi một lần
    chạy thật). Thiếu file / JSON hỏng / thiếu khoá / khác `true` ⇒ False —
    cùng khuôn fail-closed `gates/d0_pre.is_d0_pre_complete()`."""
    try:
        data = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and data.get("d4_complete") is True


def _doc_khoa_cong_vao_d9(runtime_state_path: Path) -> dict[str, bool]:
    """Các khoá cổng vào D9 (`DR-D9-01` §6.1.1). Cùng khuôn fail-closed `_doc_d4_complete`:
    thiếu file / JSON hỏng / thiếu khoá / khác `true` ⇒ False cho khoá đó."""
    try:
        data = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    return {k: data.get(k) is True for k in KHOA_CONG_VAO_D9}

CTRL_BUDGET_LINE = "CTRL"
#: `B0` = tiêu chí pool (§0.3), quyết định hạ tầng — không phải đánh giá cấu hình của một ứng viên (TD-0375).
BUDGET_LINE_B0 = "B0"

CTRL_OUTPUT_ALLOWED = frozenset({"price_delta", "tranche_index", "direction"})
"""Đầu ra cho phép của CTRL dạng *đo thước* — spec dòng 3605-3607 liệt kê
ĐÚNG ba thứ: {chênh lệch giá, chỉ số tranche, hướng}, "TUYỆT ĐỐI không PnL,
không win/loss, không metric theo arm. Bộ chạy cưỡng chế danh sách này,
không phải người."

🔴 Đây là danh sách CHO PHÉP, không phải danh sách CẤM. Một danh sách cấm
chỉ chặn được những tên đã nghĩ ra trước; khoá nào chưa nghĩ tới sẽ lọt.
Fail-closed đòi chiều ngược lại: không nằm trong ba khoá này thì từ chối.
"""


CTRL_MO_TA_ALLOWED = frozenset(
    {"so_lenh", "lenh_moi_nam", "so_lenh_theo_thang", "so_ma_co_lenh", "phan_bo_so_tranche"}
)
"""Đầu ra cho phép của CTRL dạng thứ BA *đo mô tả* — `MT-19` đường (c), liệt kê ĐÍCH DANH ở `DR-D4-16` §3,
mỗi tên kèm một câu vì-sao-không-phải-chỉ-số-hiệu-năng. Toàn là SỐ ĐẾM sự kiện vào lệnh/khớp lệnh.

🔴 Cố ý KHÔNG có `exit_reason` (tỉ lệ TP/SL rò thắng/thua), thời gian giữ lệnh, hay bất cứ thứ gì mang
`profit`/`pnl`/`R_realized`/`R_trien_khai`. Thêm tên = DR mới. Tách hẳn khỏi `CTRL_OUTPUT_ALLOWED` (D3.5 Bước 1): hai phạm vi, hai danh
sách — gộp là nới danh sách của D3.5 một cách lặng lẽ (`MT-19`: *"KHÔNG nới danh sách của D3.5"*).
"""


class TrialState(Enum):
    RESERVED = "RESERVED"
    CONSUMED = "CONSUMED"
    REFUNDED = "REFUNDED"


class LedgerError(RuntimeError):
    """Lỗi chung của sổ trial."""


class UnknownTrialError(LedgerError):
    """Thao tác trên một trial_id chưa từng RESERVE."""


class BudgetExhaustedError(LedgerError):
    """Khả dụng < contribution — TỪ CHỐI khởi động, KHÔNG chạm dữ liệu (L-Z52)."""


class B1Error(LedgerError):
    """TD-0253 — một lần đặt chỗ B1 không thuộc `DR-D5-01` (sai giá trị thử, vượt
    trần, cổng D4 chưa đóng…). Từ chối TẠI CỬA, trước khi ghi dòng nào: suất B1
    đã vào sổ là đã chạm CALIB, sổ append-only không lùi được."""


class ThietKeChuaKiemError(LedgerError):
    """TD-0375 — suất ĐẦU TIÊN của ứng viên `IQ-xxxx` khi `DR-PHAN-QUYET-01` §4.2 bước 3 chưa thoả (thiếu số đếm
    `exit_reason` EXPLORE đã commit, hoặc `TIME_STOP` ngoài dải mà không có DR khai trước). Từ chối TẠI CỬA, trước
    khi ghi dòng nào — cùng lý do `B1Error`."""


class CtrlClaimError(LedgerError):
    """Dòng CTRL không khai được dạng hợp lệ → TỪ CHỐI ghi (MT-08).

    CTRL đứng NGOÀI ngân sách N, nên nếu ai cũng khai được CTRL thì đó là
    đường thoát khỏi kế toán phép thử. Cửa này bắt máy kiểm lời khai, cùng
    triết lý DR-014 §3 ("máy tự ghi, người không có đường nhập liệu").
    """


class SchemaViolationError(LedgerError):
    """Sự kiện sắp ghi KHÔNG hợp lệ theo `trial_event.schema.json` —
    TỪ CHỐI ghi (TD-0150).

    Sổ này append-only tuyệt đối (MT-01): một dòng sai đã ghi là sai vĩnh
    viễn. Nên phép kiểm phải đứng TRƯỚC `_append()`; báo lỗi sau khi ghi
    chỉ cho ta biết mình vừa làm hỏng sổ, không sửa được gì.
    """


class SealedTrialError(LedgerError):
    """Cố hoàn trả một trial ĐÃ có con dấu — không có quyền phủ quyết
    của người vận hành (L-Z53, spec dòng 3499-3500)."""


class AlreadyFinalizedError(LedgerError):
    """Trial đã CONSUMED/REFUNDED — không ghi outcome hay hoàn trả lại
    lần hai (outcome chỉ được ghi ĐÚNG MỘT LẦN, spec dòng 3762)."""


@dataclass
class TrialProjection:
    """Bản chiếu trạng thái của MỘT trial — tính lại từ sổ sự kiện,
    KHÔNG phải trường lưu sẵn trên đĩa.

    `state` là THUỘC TÍNH TÍNH, không phải cờ set thủ công — đúng DR-014
    §1: "CÓ con dấu ⇒ CONSUMED" là một quy tắc ĐỊNH NGHĨA, không phụ
    thuộc việc sự kiện CONSUME (mang outcome thật) đã được ghi hay chưa.
    Một tiến trình bị giết NGAY SAU khi seal nhưng TRƯỚC khi kịp ghi
    outcome vẫn phải tính là CONSUMED (L-Z53) — nếu `state` chỉ đổi khi
    thấy sự kiện CONSUME, kịch bản đó sẽ bị đếm sai thành RESERVED mãi
    mãi, làm N_ĐÃ_DÙNG hụt so với thực tế đã "nhìn thấy" kết quả.
    """

    trial_id: str
    contribution: int
    budget_line: str
    hypothesis_slot: str
    param_under_test: str
    param_value: Any
    dataset: str  # TD-0284 — B1 mang hai tập (CALIB của D5, WFO của D9), phân biệt bằng trường này
    sealed: bool = False
    outcome_written: bool = False
    outcome: dict[str, Any] | None = field(default=None)
    refunded: bool = False

    @property
    def state(self) -> TrialState:
        if self.refunded:
            return TrialState.REFUNDED
        if self.sealed or self.outcome_written:
            return TrialState.CONSUMED
        return TrialState.RESERVED


TRIAL_EVENT_SCHEMA_PATH = Path("registry/schemas/trial_event.schema.json")


@lru_cache(maxsize=1)
def _doc_schema() -> dict[str, Any]:
    """Đọc schema MỘT LẦN rồi nhớ lại — `_append()` gọi mỗi lần ghi.

    Không bọc try/except trả về "bỏ qua kiểm": schema đọc không được thì
    `_kiem_schema()` phải TỪ CHỐI ghi. Bỏ qua bước kiểm đúng lúc nó hỏng
    là mất lớp canh ở chính thời điểm cần nó nhất.
    """
    return json.loads(TRIAL_EVENT_SCHEMA_PATH.read_text(encoding="utf-8"))


def _kiem_schema(event: Mapping[str, Any]) -> None:
    """Đối chiếu MỘT sự kiện với `trial_event.schema.json` — TD-0150.

    Vì sao cần: schema là nguồn sự thật đã chốt cho hình dạng sổ
    (ARCHITECTURE mục 7), nhưng trước TD-0150 cửa ghi KHÔNG biết ràng buộc
    của nó — `seal()` nhận mọi `seal_path`, `consume()` nhận mọi `verdict`.
    Hai trường khác nhau, cùng một hiện tượng. Cùng họ với lỗ TD-0149 vừa
    vá nhưng ngược chiều: lỗ kia là *schema không biết khoá mới*, lỗ này
    là *cửa ghi không biết ràng buộc của schema*.
    """
    try:
        schema = _doc_schema()
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaViolationError(
            f"Không đọc được {TRIAL_EVENT_SCHEMA_PATH} để đối chiếu sự kiện sắp ghi: "
            f"{exc}. TỪ CHỐI ghi — sổ append-only không có đường lùi, và bỏ qua "
            "bước kiểm đúng lúc nó hỏng là mất lớp canh khi cần nhất."
        ) from exc
    try:
        jsonschema.validate(dict(event), schema)
    except jsonschema.ValidationError as exc:
        raise SchemaViolationError(
            f"Sự kiện {event.get('event')!r} của {event.get('trial_id')!r} KHÔNG hợp lệ "
            f"theo {TRIAL_EVENT_SCHEMA_PATH.name}: {exc.message}. TỪ CHỐI ghi — một dòng "
            "sai trong sổ append-only là sai vĩnh viễn."
        ) from exc


def _dem_vao_n(proj: TrialProjection) -> bool:
    """Dòng này có tiêu ngân sách phép thử không?

    CTRL = điểm kiểm soát: chạy lại để KIỂM TRA tái lập, hoặc đo THƯỚC —
    không đánh giá một cấu hình nào, nên không phải một phép thử. Spec nói
    điều này ở 5 chỗ (§0d.4 dòng 594; DR-014 §2 dòng 3490 "ngoài sổ này";
    dòng 3608 "dòng CTRL, 0 trial"; dòng 3715; changelog v8 dòng 71).

    🔴 Vì sao đáng sửa (MT-08): điểm kiểm soát chạy sau MỖI lần một tham số
    đổi trạng thái; Tầng B có 12 tham số, trần B3 = 20 → cận trên ~20-25
    trial trên tổng 114 bốc hơi vì kế toán sai. Nguy hơn con số là ĐỘNG CƠ
    CHẠY NGƯỢC: càng kỷ luật (càng chạy nhiều điểm kiểm soát) càng bị phạt
    ngân sách, dẫn tới bỏ điểm kiểm soát.
    """
    return proj.budget_line != CTRL_BUDGET_LINE


def _utcnow_iso() -> str:
    """UTC, ISO-8601, kết thúc bằng Z — bắt buộc (G.12: cấm giờ local,
    L-Z10 đòi registered_at < executed_at, chỉ đúng khi cùng múi giờ).

    🔴 Độ phân giải MICRO GIÂY, không phải giây: L-Z10 đòi `<` CHẶT.
    Với độ phân giải giây, hai sự kiện cách nhau vài mili-giây (đúng
    hình dạng reserve()->seal()->consume() chạy trong cùng một tiến
    trình, không phải một lần backtest thật kéo dài) có thể rơi vào
    CÙNG một giây, làm `registered_at == executed_at` và L-Z10 báo VI
    PHẠM một cách giả — phát hiện khi viết test cho TD-0056.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class TrialLedger:
    def __init__(
        self,
        path: Path = DEFAULT_REGISTRY_PATH,
        *,
        dr_d5_path: Path = DEFAULT_DR_D5_01_PATH,
        runtime_state_path: Path = DEFAULT_RUNTIME_STATE_PATH,
        repo_dir: Path = Path("."),
    ) -> None:
        """`dr_d5_path` / `runtime_state_path` chỉ dùng cho cửa B1 (TD-0253), tiêm
        được cùng khuôn `path` của sổ — mặc định là đường THẬT. Không có tham số
        nào TẮT cửa B1: tắt được là một đường vòng, không phải một cấu hình.

        `repo_dir` (TD-0375) là gốc repo để cửa thiết kế tìm hiện vật `exit_reason` và kiểm nó đã commit — cũng
        không tắt được cửa: đổi gốc thì hiện vật vẫn phải có và đã commit ở gốc mới."""
        self._path = path
        self._dr_d5_path = dr_d5_path
        self._runtime_state_path = runtime_state_path
        self._repo_dir = repo_dir
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.touch()

    # ── đọc sổ / bản chiếu ──────────────────────────────────────────
    def _read_events(self) -> list[dict[str, Any]]:
        text = self._path.read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def _append(self, event: Mapping[str, Any]) -> None:
        """ĐIỂM NGHẼN DUY NHẤT của mọi lần ghi vào sổ — và vì thế là chỗ
        đặt phép đối chiếu schema (TD-0150).

        Vá ở đây chứ không vá trong từng `seal()`/`consume()`/…: khoảng hở
        lộ ra ở HAI trường khác nhau (`seal_path`, `verdict`) nên nó là
        tính chất của cửa ghi, không phải hai chỗ sót lẻ. Đặt phép kiểm ở
        điểm nghẽn thì cửa ghi nào viết SAU NÀY cũng tự động được kiểm;
        vá từng hàm là mời lỗi thứ ba xuất hiện ở hàm thứ bảy.
        Test `TestDiemNghenDuyNhat` canh cho điểm nghẽn này thật sự duy
        nhất (không hàm nào tự `write` vòng qua đây).
        """
        _kiem_schema(event)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def projections(self) -> dict[str, TrialProjection]:
        """Tính lại trạng thái MỌI trial từ đầu sổ."""
        result: dict[str, TrialProjection] = {}
        for e in self._read_events():
            tid = e["trial_id"]
            kind = e["event"]
            if kind == "RESERVE":
                result[tid] = TrialProjection(
                    trial_id=tid,
                    contribution=e["contribution"],
                    # Cố ý KHÔNG dùng .get() với mặc định: một dòng RESERVE
                    # thiếu `budget_line` phải NỔ, không được lặng lẽ hoá
                    # thành "không phải CTRL" rồi bị cộng vào N.
                    budget_line=e["budget_line"],
                    hypothesis_slot=e["hypothesis_slot"],
                    param_under_test=e["param_under_test"],
                    param_value=e["param_value"],
                    # Không .get(): RESERVE thiếu `dataset` phải NỔ (schema đòi trường này),
                    # không lặng lẽ thành một tập nào đó rồi lọt qua cửa B1/WFO.
                    dataset=e["dataset"],
                )
            elif kind == "SEAL":
                result[tid].sealed = True
            elif kind == "CONSUME":
                result[tid].outcome = e["outcome"]
                result[tid].outcome_written = True
            elif kind == "REFUND":
                result[tid].refunded = True
            elif kind == "CONTAMINATE":
                pass  # dấu vết audit — không đổi state
        return result

    def get(self, trial_id: str) -> TrialProjection:
        proj = self.projections().get(trial_id)
        if proj is None:
            raise UnknownTrialError(f"chưa từng reserve: {trial_id}")
        return proj

    # ── kế toán ───────────────────────────────────────────────────
    def n_used(self) -> int:
        """N_ĐÃ_DÙNG = Σ contribution của dòng state==CONSUMED (L-Z11),
        **KHÔNG kể dòng CTRL** — xem `_dem_vao_n()`."""
        return sum(
            p.contribution
            for p in self.projections().values()
            if p.state is TrialState.CONSUMED and _dem_vao_n(p)
        )

    def n_reserved(self) -> int:
        return sum(
            p.contribution
            for p in self.projections().values()
            if p.state is TrialState.RESERVED and _dem_vao_n(p)
        )

    def available(self, *, n_dang_ky: int, so_lenh_da_dong: int = 0) -> int:
        """Khả dụng hiện tại.

        🔴 L-Z27: KHÔNG có tham số nào nhận thẳng một con số ngân sách.
        Người gọi chỉ đưa được SỐ LỆNH ĐÃ ĐÓNG — thứ đo được từ thực tế —
        rồi công thức §12c.2 tự quyết B3 sinh thêm bao nhiêu. "Tăng B3
        bằng tay" (spec dòng 4956) vì thế không biểu diễn được, chứ không
        phải bị một phép kiểm chặn lại sau khi đã xảy ra.
        """
        return _budget.available(
            n_dang_ky=n_dang_ky,
            n_tai_sinh=_budget.b3_tai_sinh(so_lenh_da_dong),
            n_used=self.n_used(),
            n_reserved=self.n_reserved(),
        )

    def refund_count(self, key: HypothesisKey) -> int:
        events = self._read_events()
        reserve_by_trial = {e["trial_id"]: e for e in events if e["event"] == "RESERVE"}
        count = 0
        for e in events:
            if e["event"] != "REFUND":
                continue
            r = reserve_by_trial.get(e["trial_id"])
            if r is not None and key.matches(
                hypothesis_slot=r["hypothesis_slot"],
                param_under_test=r["param_under_test"],
                param_value=r["param_value"],
            ):
                count += 1
        return count

    # ── ghi sự kiện ───────────────────────────────────────────────
    def _next_trial_id(self) -> str:
        n_reserves_ever = sum(1 for e in self._read_events() if e["event"] == "RESERVE")
        return f"D-{n_reserves_ever + 1:04d}"

    def _kiem_khai_ctrl(
        self,
        *,
        reproduces_trial_id: str | None,
        ctrl_output_whitelist: Sequence[str] | None,
        ctrl_mo_ta_whitelist: Sequence[str] | None = None,
        params_frozen_hash: str,
        config_hash: str,
    ) -> None:
        """Máy kiểm lời khai CTRL — raise `CtrlClaimError` nếu không thoả.

        CTRL đứng ngoài ngân sách, nên "khai CTRL" là một đặc quyền. Nếu
        nhận lời khai suông thì bất kỳ trial nào cũng trốn được kế toán chỉ
        bằng cách đổi một chuỗi. Phải thuộc ĐÚNG MỘT trong BA dạng, và máy
        tự đối chiếu được cả ba: *tái lập* (§0d.4), *đo thước* (D3.5 Bước 1),
        *đo mô tả* (`MT-19` đường (c), `DR-D4-16`).

        🔴 `MT-19`: ba phép kiểm cũ là NHỊ PHÂN — thêm dạng thứ ba mà không
        đổi chúng thì khai chồng với `ctrl_output_whitelist` sẽ QUA và danh
        sách mô tả bị bỏ qua IM LẶNG. Nên đếm số dạng đã khai, không so cặp.

        🔴 L-Z55 một mình KHÔNG đủ ở đây: một điểm kiểm soát HỢP LỆ *có*
        chạm CALIB nên nó không vi phạm timerange. Chỗ phân biệt phải là
        ĐẦU RA, không phải dữ liệu được chạm.
        """
        khai = {
            "tái lập (reproduces_trial_id)": reproduces_trial_id is not None,
            "đo thước (ctrl_output_whitelist)": ctrl_output_whitelist is not None,
            "đo mô tả (ctrl_mo_ta_whitelist)": ctrl_mo_ta_whitelist is not None,
        }
        da_khai = [ten for ten, co in khai.items() if co]

        if len(da_khai) > 1:
            raise CtrlClaimError(
                f"dòng CTRL khai CHỒNG {len(da_khai)} dạng {da_khai} — chọn đúng một. "
                "Khai chồng là chừa đường lách sang dạng dễ kiểm hơn (MT-19)"
            )
        if not da_khai:
            raise CtrlClaimError(
                "dòng CTRL phải khai một trong BA dạng: *tái lập* (reproduces_trial_id, §0d.4), "
                "*đo thước* (ctrl_output_whitelist, D3.5 Bước 1) hoặc *đo mô tả* "
                "(ctrl_mo_ta_whitelist, MT-19 / DR-D4-16) — TỪ CHỐI ghi"
            )

        if reproduces_trial_id is not None:
            self._kiem_ctrl_tai_lap(
                reproduces_trial_id=str(reproduces_trial_id),
                params_frozen_hash=params_frozen_hash,
                config_hash=config_hash,
            )
        elif ctrl_output_whitelist is not None:
            self._kiem_ctrl_do_thuoc(list(ctrl_output_whitelist))
        else:
            self._kiem_ctrl_mo_ta(list(ctrl_mo_ta_whitelist or []))

    def _kiem_ctrl_tai_lap(
        self, *, reproduces_trial_id: str, params_frozen_hash: str, config_hash: str
    ) -> None:
        """Dạng *tái lập* (§0d.4): chạy lại ĐÚNG một trial đã có, để xem có
        ra cùng số không. "Đúng" ở đây máy kiểm được: cùng tham số, cùng
        cấu hình. Đổi một trong hai thì đó là phép thử mới, không phải tái
        lập — và phải tiêu ngân sách như mọi phép thử."""
        goc = None
        for e in self._read_events():
            if e["event"] == "RESERVE" and e["trial_id"] == reproduces_trial_id:
                goc = e
                break
        if goc is None:
            raise CtrlClaimError(
                f"CTRL khai tái lập {reproduces_trial_id} nhưng sổ không có trial đó"
            )
        lech = [
            ten
            for ten, moi, cu in (
                ("params_frozen_hash", params_frozen_hash, goc["params_frozen_hash"]),
                ("config_hash", config_hash, goc["config_hash"]),
            )
            if moi != cu
        ]
        if lech:
            raise CtrlClaimError(
                f"CTRL khai tái lập {reproduces_trial_id} nhưng {', '.join(lech)} lệch "
                "bản ghi gốc — đổi cấu hình thì không còn là tái lập, đó là phép thử mới"
            )

    def _kiem_ctrl_do_thuoc(self, whitelist: list[str]) -> None:
        """Dạng *đo thước* (D3.5 Bước 1): đo cơ học khớp lệnh, không đánh
        giá cấu hình. Spec cưỡng chế bằng ĐẦU RA — xem `CTRL_OUTPUT_ALLOWED`."""
        if not whitelist:
            raise CtrlClaimError(
                "CTRL khai đo thước nhưng danh sách đầu ra RỖNG — khai suông, không đo gì"
            )
        ngoai = sorted(set(whitelist) - CTRL_OUTPUT_ALLOWED)
        if ngoai:
            raise CtrlClaimError(
                f"CTRL đo thước có đầu ra ngoài danh sách cho phép: {ngoai}. "
                f"Chỉ cho phép {sorted(CTRL_OUTPUT_ALLOWED)} (spec dòng 3605-3607)"
            )

    def _kiem_ctrl_mo_ta(self, whitelist: list[str]) -> None:
        """Dạng *đo mô tả* (`MT-19` đường (c), `DR-D4-16`): chỉ SỐ ĐẾM, cưỡng chế bằng ĐẦU RA —
        xem `CTRL_MO_TA_ALLOWED`."""
        if not whitelist:
            raise CtrlClaimError(
                "CTRL khai đo mô tả nhưng danh sách đầu ra RỖNG — khai suông, không đo gì"
            )
        ngoai = sorted(set(whitelist) - CTRL_MO_TA_ALLOWED)
        if ngoai:
            raise CtrlClaimError(
                f"CTRL đo mô tả có đầu ra ngoài danh sách cho phép: {ngoai}. "
                f"Chỉ cho phép {sorted(CTRL_MO_TA_ALLOWED)} (DR-D4-16 §3) — thêm tên = DR mới"
            )

    def _kiem_cua_b1(
        self, *, dataset: str, direction: str, param_under_test: str, param_value: Any
    ) -> None:
        """TD-0253 — cửa B1. Mọi lỗi (DR đọc không được, băm lệch, runtime_state
        hỏng, suất không hợp lệ) đều thành `B1Error`: fail-closed.

        TD-0373: khoá `D5_DO_TAM_DUNG` đứng ĐẦU cửa — trước cả khi đọc DR hay sổ. Đọc thuộc tính mô-đun lúc
        gọi (không `from … import` giá trị) để lật khoá là sửa ĐÚNG một dòng ở `khoa_do.py`."""
        from tool_d.ablation import khoa_do

        if khoa_do.D5_DO_TAM_DUNG:
            raise B1Error(f"TỪ CHỐI đặt chỗ B1 — {khoa_do.LY_DO_KHOA_D5}")
        try:
            bang = doc_bang_ung_vien(self._dr_d5_path)
            kiem_dat_cho_b1(
                self.projections().values(),
                bang=bang,
                d4_complete=_doc_d4_complete(self._runtime_state_path),
                khoa_cong_vao_d9=_doc_khoa_cong_vao_d9(self._runtime_state_path),
                dataset=dataset,
                direction=direction,
                param_under_test=param_under_test,
                param_value=param_value,
            )
        except UngVienError as e:
            raise B1Error(f"TỪ CHỐI đặt chỗ B1 — {e}") from e

    def _kiem_cua_thiet_ke(self, *, budget_line: str, hypothesis_slot: str) -> None:
        """TD-0375 — `DR-PHAN-QUYET-01` §4.2 bước 3, CHẶN CỨNG (chủ dự án chốt 24/09/2026).

        Chỉ áp cho suất ĐẦU TIÊN của một slot ứng viên `IQ-xxxx`, dòng không phải `B0` (hạ tầng pool, không đánh giá
        cấu hình) — CTRL không tới được đây. Slot đã có dòng nào trên sổ ⇒ đã qua cửa này lúc đó, không kiểm lại.
        ZA LONG (slot `A-xx`) không bị áp. Import trễ để không kéo `chi_so_export` vào lúc nạp sổ."""
        from tool_d.gates import exit_reason_thiet_ke as tk

        if budget_line == BUDGET_LINE_B0 or not tk.la_slot_ung_vien(hypothesis_slot):
            return
        if any(p.hypothesis_slot == hypothesis_slot for p in self.projections().values()):
            return
        try:
            tk.kiem_exit_reason_thiet_ke(hypothesis_slot, repo_dir=self._repo_dir)
        except tk.ExitReasonThietKeError as e:
            raise ThietKeChuaKiemError(f"TỪ CHỐI suất đầu tiên — {e}") from e

    def reserve(
        self,
        *,
        n_dang_ky: int,
        so_lenh_da_dong: int = 0,
        tool_id: str = "D",
        budget_line: str,
        hypothesis_slot: str,
        direction: str,
        dataset: str,
        param_under_test: str,
        param_value: Any,
        params_frozen_hash: str,
        config_hash: str,
        code_commit: str,
        provenance: Mapping[str, Any],
        contribution: int,
        reproduces_trial_id: str | None = None,
        ctrl_output_whitelist: Sequence[str] | None = None,
        ctrl_mo_ta_whitelist: Sequence[str] | None = None,
    ) -> str:
        """Đặt chỗ. Raise `BudgetExhaustedError` nếu Khả dụng < contribution
        — TRƯỚC KHI CHẠM BẤT KỲ DỮ LIỆU NÀO (L-Z52, spec dòng 3471-3472).

        Dòng `budget_line="CTRL"` đi đường riêng (MT-08): không kiểm ngân
        sách (điểm kiểm soát phải chạy được đúng lúc N đã cạn — chính lúc
        sắp go-live là lúc cần kiểm tra tái lập nhất), nhưng ĐỔI LẠI phải
        qua `_kiem_khai_ctrl()`. Ba tham số cuối chỉ dùng cho CTRL.
        """
        if contribution < 1:
            raise LedgerError("contribution phải >= 1 — không có mức 0 (fail-closed)")
        if budget_line == CTRL_BUDGET_LINE:
            self._kiem_khai_ctrl(
                reproduces_trial_id=reproduces_trial_id,
                ctrl_output_whitelist=ctrl_output_whitelist,
                ctrl_mo_ta_whitelist=ctrl_mo_ta_whitelist,
                params_frozen_hash=params_frozen_hash,
                config_hash=config_hash,
            )
        else:
            if budget_line == BUDGET_LINE_B1:
                self._kiem_cua_b1(
                    dataset=dataset,
                    direction=direction,
                    param_under_test=param_under_test,
                    param_value=param_value,
                )
            self._kiem_cua_thiet_ke(budget_line=budget_line, hypothesis_slot=hypothesis_slot)
            khadung = self.available(
                n_dang_ky=n_dang_ky, so_lenh_da_dong=so_lenh_da_dong
            )
            if khadung < contribution:
                raise BudgetExhaustedError(
                    f"Khả dụng ({khadung}) < contribution ({contribution}) — TỪ CHỐI khởi động"
                )
        trial_id = self._next_trial_id()
        # Lời khai CTRL phải nằm TRONG sổ, không chỉ sống trong lần gọi này:
        # audit sau đó (và người đọc sổ) phải tự đối chiếu lại được vì sao
        # một dòng được miễn kế toán, không phải tin rằng cửa ghi đã kiểm.
        khai_ctrl: dict[str, Any] = {}
        if budget_line == CTRL_BUDGET_LINE:
            if reproduces_trial_id is not None:
                khai_ctrl["reproduces_trial_id"] = reproduces_trial_id
            if ctrl_output_whitelist is not None:
                khai_ctrl["ctrl_output_whitelist"] = list(ctrl_output_whitelist)
            if ctrl_mo_ta_whitelist is not None:
                khai_ctrl["ctrl_mo_ta_whitelist"] = list(ctrl_mo_ta_whitelist)
        self._append(
            {
                "event": "RESERVE",
                "trial_id": trial_id,
                "tool_id": tool_id,
                "registered_at": _utcnow_iso(),
                "budget_line": budget_line,
                "hypothesis_slot": hypothesis_slot,
                "direction": direction,
                "dataset": dataset,
                "param_under_test": param_under_test,
                "param_value": param_value,
                "params_frozen_hash": params_frozen_hash,
                "config_hash": config_hash,
                "code_commit": code_commit,
                "provenance": dict(provenance),
                "contribution": contribution,
                **khai_ctrl,
            }
        )
        return trial_id

    def seal(self, trial_id: str, *, seal_path: str) -> None:
        """Bộ chạy TỰ gọi ngay khi chỉ số đầu tiên tồn tại trong bộ nhớ,
        TRƯỚC cả khi in/ghi kết quả (DR-014 §3). Từ đây, `refund()` cho
        trial này PHẢI raise `SealedTrialError`.
        """
        proj = self.get(trial_id)
        if proj.sealed:
            raise AlreadyFinalizedError(f"{trial_id} đã có con dấu, không đóng dấu lần hai")
        self._append(
            {
                "event": "SEAL",
                "trial_id": trial_id,
                "sealed_at": _utcnow_iso(),
                "seal_path": seal_path,
            }
        )

    def consume(
        self,
        trial_id: str,
        *,
        outcome: Mapping[str, Any],
        verdict: str,
        rejection_reason: str | None = None,
        retest_forbidden: bool = True,
    ) -> None:
        """Ghi outcome — ĐÚNG MỘT LẦN (spec dòng 3762: sửa dòng cũ = sổ
        mất hiệu lực; ở đây thể hiện bằng raise nếu gọi lần hai).

        Được phép gọi cả khi trial ĐÃ `seal()` (đúng luồng bình thường:
        seal trước, rồi mới ghi outcome thật) — chỉ chặn khi outcome đã
        được ghi rồi, hoặc trial đã REFUNDED.
        """
        proj = self.get(trial_id)
        if proj.refunded:
            raise AlreadyFinalizedError(f"{trial_id} đã REFUNDED, không thể consume")
        if proj.outcome_written:
            raise AlreadyFinalizedError(f"{trial_id} đã có outcome, không ghi lại lần hai")
        self._append(
            {
                "event": "CONSUME",
                "trial_id": trial_id,
                "executed_at": _utcnow_iso(),
                "outcome": dict(outcome),
                "verdict": verdict,
                "rejection_reason": rejection_reason,
                "retest_forbidden": retest_forbidden,
            }
        )

    def refund(self, trial_id: str, *, cause_machine: str) -> TrialState:
        """Hoàn trả đặt chỗ. `cause_machine` PHẢI do MÁY xác định (exit
        code / exception / guard-block) — không nhận lời khai người vận
        hành (DR-014 §3).

        Raise `SealedTrialError` nếu ĐÃ có con dấu (L-Z53) — không có
        đường phủ quyết.

        Đã hoàn trả đủ `REFUND_CAP_PER_HYPOTHESIS` (3) lần cho CÙNG một
        giả thuyết → CƯỠNG CHẾ CONSUMED thay vì hoàn trả lần này (DR-014
        §5: "Lần thứ 4 không có con dấu → vẫn CONSUMED"). Trả về trạng
        thái CUỐI CÙNG để caller biết chuyện gì vừa xảy ra.
        """
        proj = self.get(trial_id)
        if proj.sealed:
            raise SealedTrialError(f"{trial_id} đã có con dấu — không được hoàn trả (L-Z53)")
        if proj.outcome_written:
            raise AlreadyFinalizedError(f"{trial_id} đã có outcome (CONSUMED), không hoàn trả")
        if proj.refunded:
            raise AlreadyFinalizedError(f"{trial_id} đã REFUNDED trước đó")

        key = HypothesisKey(proj.hypothesis_slot, proj.param_under_test, proj.param_value)
        if self.refund_count(key) >= REFUND_CAP_PER_HYPOTHESIS:
            self._append(
                {
                    "event": "CONSUME",
                    "trial_id": trial_id,
                    "executed_at": _utcnow_iso(),
                    "outcome": {
                        "expectancy": None,
                        "sharpe": None,
                        "n_trades": None,
                        "max_single_loss_ratio": None,
                    },
                    "verdict": "INCONCLUSIVE",
                    "rejection_reason": (
                        f"cưỡng chế CONSUMED — đã chạm trần trả lại "
                        f"{REFUND_CAP_PER_HYPOTHESIS} lần cho cùng giả thuyết (DR-014 §5); "
                        f"nguyên nhân gốc lần này: {cause_machine}"
                    ),
                    "retest_forbidden": True,
                }
            )
            return TrialState.CONSUMED

        self._append(
            {
                "event": "REFUND",
                "trial_id": trial_id,
                "refunded_at": _utcnow_iso(),
                "refund_cause_machine": cause_machine,
            }
        )
        return TrialState.REFUNDED

    def mark_contaminated(self, trial_id: str, *, reason: str) -> None:
        """DR-014 §6 — nhiễm tham số tiêu gấp đôi. Trial PHẢI đã CONSUMED
        (kết quả đã bị nhìn, không thu hồi được) — chỉ thêm dấu vết audit,
        KHÔNG xoá hay đổi trạng thái ("KHÔNG được xoá lần chạy khỏi sổ
        với lý do 'không hợp lệ'", spec dòng 3557).
        """
        proj = self.get(trial_id)
        if proj.state is not TrialState.CONSUMED:
            raise LedgerError(
                f"chỉ đánh dấu nhiễm cho trial ĐÃ CONSUMED, {trial_id} đang ở "
                f"trạng thái {proj.state.value}"
            )
        self._append(
            {
                "event": "CONTAMINATE",
                "trial_id": trial_id,
                "contaminated_at": _utcnow_iso(),
                "reason": reason,
            }
        )
