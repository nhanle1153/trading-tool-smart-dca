"""H3-D — Walk-forward orchestrator (D3, Khối 14).

🔴 WFO của Tool D KHÔNG khớp lại tham số. `N3` cấm vĩnh viễn `hyperopt`
và mọi `*Parameter` của Freqtrade; `N4` buộc tham số chỉ đến từ
`config/tool_d_config.yaml`. Cửa sổ train ở đây dùng để **XẾP HẠNG các
arm ablation** (Z0…Z3b, §D0.9), cửa sổ test kiểm **thứ hạng đó có giữ
được sang đoạn sau không** — đúng nghĩa "sinh cặp IS/OOS cho CSCV"
(spec dòng 4326).

Hệ quả phải nhớ khi đọc kết quả: đơn vị phân tích là *thứ hạng giữa các
arm*, không phải *giá trị tuyệt đối của một arm*. Xem
`docs/decisions/DR-D3-01-so-do-fold.md`.
"""
