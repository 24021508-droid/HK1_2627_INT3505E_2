# Practice 2: Header Versioning với Decorator `@api_version`

## 1. Mục tiêu
* Cùng một URL duy nhất: `GET /users/{id}` cho cả 3 phiên bản API (`1`, `2`, `2024-06-20`).
* Client lựa chọn phiên bản thông qua Request Header: `X-API-Version`.
* Server phản hồi kèm Response Header: `X-API-Version-Served` để debug và xác nhận phiên bản được phục vụ.

---

## 2. Bốn điểm kiến trúc cần nhớ
1. **Decorator parse `X-API-Version`**: Nếu client không truyền header, hệ thống tự động sử dụng version mặc định (`LATEST = "2"`).
2. **Trả `X-API-Version-Served` header**: Gắn phiên bản thực tế được phục vụ vào response header.
3. **Endpoint xử lý phân nhánh schema**: Dựa vào tham số `version` được decorator truyền vào để trả về dữ liệu tương ứng (`v1` trả `full_name`, `v2` trả `first_name` + `last_name`).
4. **Version không hợp lệ**: Trả về `400 Bad Request` (`{"error": "unsupported version"}`), dứt khoát không fallback về default.

---

## 3. Cài đặt và Khởi chạy

```bash
# Di chuyển vào thư mục lab02
cd lab02

# Kích hoạt virtualenv (nếu có)
.\.venv\Scripts\activate

# Cài đặt thư viện
pip install -r requirements.txt

# Khởi chạy server
python app.py
```
Server chạy mặc định tại: `http://127.0.0.1:5000`

---

## 4. Kiểm thử với cURL

### 4.1. Mặc định (không truyền header $\rightarrow$ fallback về LATEST "2")
```bash
curl -i http://127.0.0.1:5000/users/1
```
* **Status**: `200 OK`
* **Header**: `X-API-Version-Served: 2`
* **Response**: `{"id": 1, "first_name": "Văn", "last_name": "Nguyễn", "email": "a@vnu.vn"}`

### 4.2. Chỉ định rõ phiên bản v1 (`X-API-Version: 1`)
```bash
curl -i -H "X-API-Version: 1" http://127.0.0.1:5000/users/1
```
* **Status**: `200 OK`
* **Header**: `X-API-Version-Served: 1`
* **Response**: `{"id": 1, "full_name": "Văn Nguyễn"}`

### 4.3. Phiên bản dạng ngày tháng (`X-API-Version: 2024-06-20`)
```bash
curl -i -H "X-API-Version: 2024-06-20" http://127.0.0.1:5000/users/1
```
* **Status**: `200 OK`
* **Header**: `X-API-Version-Served: 2024-06-20`
* **Response**: `{"id": 1, "first_name": "Văn", "last_name": "Nguyễn", "email": "a@vnu.vn"}`

### 4.4. Phiên bản không hỗ trợ (`X-API-Version: 99`)
```bash
curl -i -H "X-API-Version: 99" http://127.0.0.1:5000/users/1
```
* **Status**: `400 Bad Request`
* **Response**: `{"error": "unsupported version"}`
