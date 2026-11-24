# URI Path Versioning: User API v1 $\rightarrow$ v2 với Flask Blueprint

Dự án mẫu minh họa kỹ thuật **URI Path Versioning** trong RESTful API sử dụng Flask Blueprint để hỗ trợ nhiều phiên bản API song song (`/api/v1` và `/api/v2`), giải quyết bài toán thay đổi cấu trúc dữ liệu trả về (*breaking change*) mà không làm gián đoạn các client đang dùng phiên bản cũ.

---

## 1. Mục tiêu và Schema

* **Version 1 (`/api/v1/users/<id>`)**:
  * Giữ nguyên schema cũ.
  * Trả về thông tin gộp họ và tên qua trường `full_name`.
  * Response mẫu:
    ```json
    {
      "id": 1,
      "full_name": "Vũ Gia Hưng",
      "email": "a@vnu.vn"
    }
    ```

* **Version 2 (`/api/v2/users/<id>`)**:
  * Đổi mới schema (Breaking Change).
  * Tách họ và tên thành 2 trường riêng biệt: `first_name` và `last_name`.
  * Response mẫu:
    ```json
    {
      "id": 1,
      "first_name": "Vũ",
      "last_name": "Gia Hưng",
      "email": "a@vnu.vn"
    }
    ```

---

## 2. Cấu trúc thư mục

```text
api_session_10/
├── app.py                  # Khởi tạo Flask app và đăng ký Blueprint theo version
├── blueprints/
│   ├── __init__.py
│   ├── users_data.py       # Dữ liệu dùng chung (single source of truth)
│   ├── v1.py               # Route logic cho API v1 (full_name)
│   └── v2.py               # Route logic cho API v2 (first_name + last_name)
├── requirements.txt        # Danh sách thư viện phụ thuộc
├── .gitignore
└── README.md
```

---

## 3. Cài đặt và Chạy

### Yêu cầu tiên quyết
* Python 3.10+

### Bước 1: Tạo và kích hoạt môi trường ảo (tùy chọn)
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Bước 2: Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### Bước 3: Khởi động server
```bash
python app.py
```
Server mặc định chạy tại: `http://127.0.0.1:5000`

---

## 4. Kiểm thử với cURL

### 4.1. Lấy thông tin user phiên bản v1
```bash
curl http://127.0.0.1:5000/api/v1/users/1
```

### 4.2. Lấy thông tin user phiên bản v2
```bash
curl http://127.0.0.1:5000/api/v2/users/1
```

### 4.3. Trường hợp user không tồn tại (HTTP 404)
```bash
curl http://127.0.0.1:5000/api/v1/users/999
# Response: {"error": "nf"}
```

---

## 5. Các tính năng mở rộng

### 5.1. Thêm POST `/users` cho Version 2
Tạo mới một user với dữ liệu đầu vào chuẩn schema v2 (`first_name`, `last_name`, `email`):

```bash
curl -X POST http://127.0.0.1:5000/api/v2/users \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Lê", "last_name": "Hải Nam", "email": "c@vnu.vn"}'
```
* Response (`201 Created`):
```json
{
  "id": 3,
  "first_name": "Lê",
  "last_name": "Hải Nam",
  "email": "c@vnu.vn"
}
```

### 5.2. Header `Sunset` cảnh báo ngưng hoạt động API v1 (RFC 8594)
Mọi request tới `v1` đều tự động đính kèm response header cảnh báo thời điểm tắt v1 và link chuyển tiếp sang v2:

```bash
curl -i http://127.0.0.1:5000/api/v1/users/1
```
* Header phản hồi:
```http
HTTP/1.1 200 OK
Sunset: Wed, 01 Jul 2026 00:00:00 GMT
Link: </api/v2/users>; rel="successor-version"
Deprecation: true
Content-Type: application/json
```

### 5.3. OpenAPI 3.0 Spec & Swagger UI
* **OpenAPI 3.0 Spec**: `http://127.0.0.1:5000/openapi.yaml` (hoặc file [openapi.yaml](openapi.yaml))
* **Swagger UI tương tác**: Mở trình duyệt và truy cập `http://127.0.0.1:5000/docs` để xem tài liệu API và test trực tiếp các endpoint v1, v2.

