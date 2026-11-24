# Lab 04 — Blue-Green routing

`POST /orders` chọn handler theo thứ tự sau.

1. Header `X-Cohort` là `beta` hoặc `internal` thì gọi v2.
2. Tài khoản `acct_42` hoặc `acct_99` thì gọi v2.
3. Với các tài khoản còn lại, lấy MD5 của `account_id` rồi chia lấy dư cho 100.
   Bucket nhỏ hơn `V2_PERCENT` thì gọi v2, các bucket còn lại gọi v1.
   Cùng một tài khoản luôn có cùng bucket.

Phản hồi có header `X-Order-Handler` để kiểm tra handler đã chạy.
V1 trả `200 OK`, v2 trả `201 Created`. Hai handler tạo dữ liệu đơn hàng
mẫu trong phản hồi. Request thiếu `account_id` hợp lệ nhận `400 Bad Request`.

## Chạy trên PowerShell

Từ thư mục `lab04`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Từ terminal khác, thử cohort, allow-list và hai bucket ở hai phía của ngưỡng 5%.

```powershell
$headers = @{ 'X-Cohort' = 'beta' }
Invoke-WebRequest http://127.0.0.1:5000/orders -Method Post -ContentType 'application/json' -Headers $headers -Body '{"account_id":"ordinary"}'
foreach ($accountId in 'acct_42', 'acct_189', 'acct_21') {
    $body = @{ account_id = $accountId } | ConvertTo-Json -Compress
    Invoke-WebRequest http://127.0.0.1:5000/orders -Method Post -ContentType 'application/json' -Body $body
}
```

Kết quả dự kiến theo thứ tự là v2, v2, v2 và v1.

## Rollout

Mặc định là 5%. Dừng server rồi chạy lại với `$env:V2_PERCENT = '100'` để
chuyển toàn bộ request hợp lệ sang v2. Đặt về `'5'` để quay lại mức thử
nghiệm, hoặc `'0'` để chỉ giữ v2 cho cohort và allow-list. Giữ v1 trong
30 ngày sau khi rollout 100% ổn định, sau đó archive theo yêu cầu bài lab.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```
