# Lời mở đầu cho phiên IDEA sạch (tạo ngày {ngay})

## 1. Câu dán vào phiên sạch (chủ dự án copy nguyên văn)

```
Đây là phiên IDEA sạch. Đọc README.md trong thư mục này trước, rồi mọi file khác trong thư mục. Không mở bất kỳ
file nào ngoài thư mục này, và không chạy lệnh Docker hay lệnh nào đụng tới repo C:\Trading Tool_Smart DCA.

Việc 1: đề xuất 3–5 ý tưởng giao dịch có cơ chế khác hẳn Z-1…Z-5. Với mỗi ý tưởng, trả lời ba câu của bộ lọc: cơ chế
là gì, AI trả tiền cho mình và vì sao họ buộc phải trả, vì sao lợi thế chưa bị arbitrage hết. Ý tưởng nào không trả
lời được câu "ai trả tiền" thì tự loại, ghi rõ lý do. Nếu file tiêu chí của quý đòi tính toán kèm theo (vd độ mạnh
thống kê), làm luôn cho từng ý tưởng.

Việc 2: tôi chọn ý tưởng nào đáng nộp thì mới soạn đơn don-N.yaml theo mau-don-y-tuong.yaml.
Chưa soạn tờ chọn cho tới khi tôi dán lại kết quả nộp.
```

## 2. Dành cho chủ dự án — lệnh chạy (PowerShell riêng, KHÔNG chạy qua Claude)

Lệnh chỉ in dòng ✅ khi ghi được; báo cáo kiểm tra sổ sau dòng đó bị lọc bỏ. Bị từ chối thì in 🛑 kèm lý do (chỉ nói về
lỗi của đơn, dán lại được). Không nhận ra kết quả thì in một câu cảnh báo, không in lọt báo cáo.

**Nộp đơn** (đổi `don-1.yaml` thành tên file cần nộp; dán CẢ khối một lần):

```powershell
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$out = @(docker compose -f "C:\Trading Tool_Smart DCA\docker\docker-compose.yml" run --rm `
  -v "{thu_muc_windows}:/don:ro" `
  freqtrade entrypoints/trial_ledger_audit.py --nop-y-tuong /don/don-1.yaml 2>$null)
$ma = $LASTEXITCODE
if ($out.Count -gt 0 -and $out[0] -match 'IQ-\d{4}.*registry/idea_queue\.jsonl') { $out[0] } elseif ($ma -eq 96) { $out } else { "KHONG NHAN RA KET QUA (ma thoat $ma) - DUNG DAN gi cho phien sach, bao phien trong repo." }
```

**Chọn:** cùng khối trên, thay `--nop-y-tuong /don/don-1.yaml` bằng `--chon-y-tuong /don/to-chon.yaml`.

Dán lại cho phiên sạch **chỉ** phần lệnh in ra. Thấy dòng `❌` hay bảng mã kiểm tra (`L-Z…`, `TD-0…`) thì đừng dán: bộ lọc
đã hỏng, báo phiên trong repo.
