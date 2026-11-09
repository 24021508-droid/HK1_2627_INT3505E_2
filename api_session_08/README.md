# Lab 01 - Backend Service với Flask

Bài tập xây dựng RESTful API quản lý Product và Order sử dụng Flask, SQLAlchemy 2.x, Marshmallow và SQLite.

## Cài đặt môi trường

Cài các thư viện cần thiết:
```bash
pip install -r requirements.txt
```

## Chạy ứng dụng

Chạy server dev:
```bash
python app.py
```
Server chạy tại: `http://127.0.0.1:5000`

Hoặc chạy bằng Docker:
```bash
docker compose up --build
```

## Chạy kiểm thử

Chạy file test thủ công (in kết quả console):
```bash
python test_api.py
```

Chạy pytest (test eager loading, chống N+1 query):
```bash
pytest test_lab.py -v
```

## Danh sách API

### Health check
- `GET /healthz`: Liveness probe (kiểm tra tiến trình sống).
- `GET /ready`: Readiness probe (kiểm tra kết nối database).

### Products
- `GET /api/v1/products`: Lấy danh sách sản phẩm (có query `?page=1&size=20`).
- `GET /api/v1/products/<id>`: Lấy chi tiết sản phẩm.
- `POST /api/v1/products`: Tạo mới sản phẩm (báo lỗi 409 nếu trùng sku).
- `POST /api/v1/products/<id>/reserve`: Đặt trước sản phẩm và trừ tồn kho (báo lỗi 409 nếu hết hàng).
- `PATCH /api/v1/products/<id>`: Cập nhật một phần thông tin.
- `DELETE /api/v1/products/<id>`: Soft delete (đánh dấu `archived=True`).

### Orders
- `POST /api/v1/orders`: Tạo đơn hàng gồm nhiều sản phẩm, tự động tính tổng tiền và trừ tồn kho.
- `GET /api/v1/orders`: Lấy danh sách đơn hàng (sử dụng `selectinload` để eager load tránh N+1 query).
