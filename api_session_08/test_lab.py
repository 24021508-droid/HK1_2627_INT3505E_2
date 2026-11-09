import pytest
from sqlalchemy import event
from app import app, db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


# 1. Test POST Order: Tạo đơn hàng, kiểm tra tính đúng tổng tiền và trừ kho
def test_create_order(client):
    # Tạo sẵn 2 sản phẩm
    p1 = client.post("/api/v1/products", json={
        "sku": "P-01", "name": "Bàn phím cơ", "price_cents": 500000, "qty_in_stock": 10
    }).get_json()

    p2 = client.post("/api/v1/products", json={
        "sku": "P-02", "name": "Chuột Gaming", "price_cents": 300000, "qty_in_stock": 5
    }).get_json()

    # Mua 2 bàn phím + 1 chuột
    res = client.post("/api/v1/orders", json={
        "customer_email": "sv@university.edu.vn",
        "items": [
            {"product_id": p1["id"], "qty": 2},
            {"product_id": p2["id"], "qty": 1}
        ]
    })
    assert res.status_code == 201
    data = res.get_json()

    # Kiểm tra tổng tiền: 500.000 * 2 + 300.000 * 1 = 1.300.000
    assert data["total_cents"] == 1300000
    assert len(data["items"]) == 2

    # Kiểm tra tồn kho của từng sản phẩm đã bị trừ
    p1_after = client.get(f"/api/v1/products/{p1['id']}").get_json()
    p2_after = client.get(f"/api/v1/products/{p2['id']}").get_json()
    assert p1_after["qty_in_stock"] == 8
    assert p2_after["qty_in_stock"] == 4


# 2. Test GET Order có eager loading & đếm số truy vấn để phát hiện bẫy N+1
def test_get_orders_eager_loading_detect_n_plus_one(client):
    # Tạo 1 sản phẩm
    p = client.post("/api/v1/products", json={
        "sku": "PROD-TEST", "name": "Món hàng test", "price_cents": 100000, "qty_in_stock": 100
    }).get_json()

    # Tạo 5 đơn hàng khác nhau
    for i in range(5):
        client.post("/api/v1/orders", json={
            "customer_email": f"khach_{i}@gmail.com",
            "items": [{"product_id": p["id"], "qty": 1}]
        })

    # Đếm số lần phát sinh câu lệnh SQL tới database
    query_count = 0

    def query_counter(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count
        query_count += 1

    event.listen(db.engine, "before_cursor_execute", query_counter)
    try:
        res = client.get("/api/v1/orders")
        assert res.status_code == 200
        orders = res.get_json()
        assert len(orders) == 5

        # Nếu có EAGER LOADING (selectinload):
        # Truy vấn chỉ tốn: 1 query lấy Orders + 1 query lấy OrderItems + 1 query lấy Products.
        # Nếu bị lỗi N+1: Số truy vấn sẽ tăng vọt thành >= 1 + 5 + 5 = 11 queries!
        assert query_count <= 3, f"Bị dính lỗi N+1 query! Đã thực hiện tới {query_count} queries."
    finally:
        event.remove(db.engine, "before_cursor_execute", query_counter)


# 3. Test Health Checks (/healthz + /ready)
def test_health_checks(client):
    res_liveness = client.get("/healthz")
    assert res_liveness.status_code == 200
    assert res_liveness.get_json() == {"status": "ok"}

    res_readiness = client.get("/ready")
    assert res_readiness.status_code == 200
    assert res_readiness.get_json()["status"] == "ok"

