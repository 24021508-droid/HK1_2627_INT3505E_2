import base64
import json
from flask import Flask, jsonify, request

app = Flask(__name__)

# Giả lập database đơn hàng
ORDERS = [
    {"id": 1, "customer_id": 101, "status": "paid", "total": 150.0, "created_at": "2026-10-01T10:00:00Z"},
    {"id": 2, "customer_id": 102, "status": "pending", "total": 200.5, "created_at": "2026-10-01T11:00:00Z"},
    {"id": 3, "customer_id": 101, "status": "paid", "total": 50.0, "created_at": "2026-10-01T12:00:00Z"},
    {"id": 4, "customer_id": 103, "status": "shipped", "total": 300.0, "created_at": "2026-10-01T13:00:00Z"},
    {"id": 5, "customer_id": 102, "status": "paid", "total": 120.0, "created_at": "2026-10-01T14:00:00Z"},
    {"id": 6, "customer_id": 101, "status": "cancelled", "total": 80.0, "created_at": "2026-10-01T15:00:00Z"},
    {"id": 7, "customer_id": 104, "status": "paid", "total": 450.0, "created_at": "2026-10-01T16:00:00Z"},
]

def encode_cursor(last_id: int) -> str:
    payload = json.dumps({"last_id": last_id})
    return base64.b64encode(payload.encode('utf-8')).decode('utf-8')

def decode_cursor(cursor_str: str) -> int:
    try:
        decoded_bytes = base64.b64decode(cursor_str.encode('utf-8'))
        data = json.loads(decoded_bytes.decode('utf-8'))
        if not isinstance(data, dict) or "last_id" not in data:
            raise ValueError()
        return data["last_id"]
    except Exception:
        raise ValueError("Invalid cursor format")

def bad_request_error(detail_msg: str):
    res = jsonify({
        "type": "https://api.shop.example/errors/bad-request",
        "title": "Bad Request",
        "status": 400,
        "detail": detail_msg,
        "instance": request.path
    })
    res.status_code = 400
    res.mimetype = "application/problem+json"
    return res

@app.get("/orders")
def get_orders():
    # 1. Cursor Decoding & Limit
    cursor_param = request.args.get('cursor')
    last_id = None
    if cursor_param:
        try:
            last_id = decode_cursor(cursor_param)
        except ValueError:
            return bad_request_error("The provided pagination cursor is invalid or corrupted.")

    limit_param = request.args.get('limit', '10')
    try:
        limit = int(limit_param)
        if limit <= 0:
            raise ValueError()
    except ValueError:
        return bad_request_error("Query parameter 'limit' must be a positive integer.")

    results = list(ORDERS)

    # 2. Filtering (status, customer_id)
    status_filter = request.args.get('status')
    if status_filter:
        results = [o for o in results if o['status'] == status_filter]

    customer_id_filter = request.args.get('customer_id')
    if customer_id_filter:
        try:
            cid = int(customer_id_filter)
            results = [o for o in results if o['customer_id'] == cid]
        except ValueError:
            return bad_request_error("Query parameter 'customer_id' must be an integer.")

    # 3. Sorting (mặc định theo id tăng dần, hỗ trợ '-' để giảm dần)
    sort_param = request.args.get('sort', 'id')
    reverse = False
    if sort_param.startswith('-'):
        reverse = True
        sort_field = sort_param[1:]
    else:
        sort_field = sort_param

    if results and sort_field in results[0]:
        results = sorted(results, key=lambda x: x.get(sort_field), reverse=reverse)

    # Lọc danh sách dựa trên Cursor
    if last_id is not None:
        start_index = 0
        for idx, item in enumerate(results):
            if item['id'] == last_id:
                start_index = idx + 1
                break
        results = results[start_index:]

    # Cắt lấy số bản ghi theo limit
    paginated_data = results[:limit]

    # Tính toán next_cursor
    next_cursor = None
    if len(paginated_data) < len(results) and len(paginated_data) > 0:
        next_cursor = encode_cursor(paginated_data[-1]['id'])

    # 4. Sparse Fieldsets (fields)
    fields_param = request.args.get('fields')
    if fields_param:
        fields = [f.strip() for f in fields_param.split(',')]
        paginated_data = [
            {k: v for k, v in item.items() if k in fields}
            for item in paginated_data
        ]

    return jsonify({
        "data": paginated_data,
        "pagination": {
            "limit": limit,
            "next_cursor": next_cursor
        }
    })

if __name__ == "__main__":
    app.run(port=5000, debug=True)