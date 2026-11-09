from app import app, db

client = app.test_client()

with app.app_context():
    db.create_all()

# 1. POST create product
res = client.post("/api/v1/products", json={
    "sku": "BANPHIM-01",
    "name": "Bàn phím cơ DareU",
    "description": "Bàn phím không dây",
    "price_cents": 850000,
    "qty_in_stock": 10
})
print("Create product:", res.status_code, res.get_json())
prod_id = res.get_json().get("id")

# 2. POST duplicate SKU (409)
res = client.post("/api/v1/products", json={
    "sku": "BANPHIM-01",
    "name": "Trùng SKU",
    "price_cents": 500000
})
print("Duplicate SKU (409):", res.status_code, res.get_json())

# 3. GET product list
res = client.get("/api/v1/products?page=1&size=20")
print("List products:", res.status_code, res.get_json())

# 4. GET product by id
res = client.get(f"/api/v1/products/{prod_id}")
print("Get product:", res.status_code, res.get_json())

# 5. POST reserve product
res = client.post(f"/api/v1/products/{prod_id}/reserve", json={"qty": 3})
print("Reserve 3 items:", res.status_code, res.get_json())

# 6. PATCH update product
res = client.patch(f"/api/v1/products/{prod_id}", json={"price_cents": 900000})
print("Patch product:", res.status_code, res.get_json())

# 7. POST create order
res = client.post("/api/v1/orders", json={
    "customer_email": "user@example.com",
    "items": [{"product_id": prod_id, "qty": 2}]
})
print("Create order:", res.status_code, res.get_json())

# 8. GET orders
res = client.get("/api/v1/orders")
print("List orders:", res.status_code, res.get_json())

# 9. Health checks
print("Healthz:", client.get("/healthz").get_json())
print("Ready:", client.get("/ready").get_json())

# 10. DELETE product (soft delete)
res = client.delete(f"/api/v1/products/{prod_id}")
print("Delete product:", res.status_code)

res = client.get(f"/api/v1/products/{prod_id}")
print("Get after delete (404):", res.status_code, res.get_json())
