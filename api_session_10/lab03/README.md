# Lab 03 — Sunset middleware

`@deprecate_at` đặt thời điểm ngừng phục vụ cho một route Flask. Route v1
trả dữ liệu bình thường trước 23:59:59 UTC ngày 31/12/2026 và trả JSON
`410 Gone` từ đúng thời điểm đó. Mỗi request v1 ghi log `deprecated_call`
kèm đường dẫn và địa chỉ IP. Cả hai phản hồi đều gửi `Sunset`,
`Deprecation: true` và `Link` trỏ đến `/api/v2/users`.

Header `Sunset` dùng định dạng HTTP-date theo [RFC 8594](https://www.rfc-editor.org/rfc/rfc8594.html).

## Chạy trên PowerShell

Từ thư mục `lab03`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Gửi request từ terminal khác:

```powershell
curl.exe -i http://127.0.0.1:5000/api/v1/users/1
curl.exe -i http://127.0.0.1:5000/api/v2/users
```

## Kiểm thử

Test dùng Flask test client và giả lập thời gian để kiểm tra trước, đúng
và sau thời điểm sunset. Test cũng kiểm tra log cảnh báo và route v2.

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```
