from datetime import datetime
from typing import Optional, List
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, validate
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///products.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# --- Models ---

class Product(db.Model):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(2000))
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    qty_in_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="product")


class Order(db.Model):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")


# --- Schemas ---

class ProductIn(Schema):
    sku = fields.Str(required=True, validate=validate.Length(min=3, max=32))
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(load_default=None)
    price_cents = fields.Int(required=True, validate=validate.Range(min=0))
    qty_in_stock = fields.Int(load_default=0, validate=validate.Range(min=0))


class ProductPatch(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(allow_none=True)
    price_cents = fields.Int(validate=validate.Range(min=0))
    qty_in_stock = fields.Int(validate=validate.Range(min=0))


class ReserveIn(Schema):
    qty = fields.Int(required=True, validate=validate.Range(min=1))


class ProductOut(Schema):
    id = fields.Int()
    sku = fields.Str()
    name = fields.Str()
    description = fields.Str()
    price_cents = fields.Int()
    qty_in_stock = fields.Int()
    archived = fields.Bool()


class OrderItemIn(Schema):
    product_id = fields.Int(required=True)
    qty = fields.Int(required=True, validate=validate.Range(min=1))


class OrderCreateIn(Schema):
    customer_email = fields.Email(required=True)
    items = fields.List(fields.Nested(OrderItemIn), required=True, validate=validate.Length(min=1))


class OrderItemOut(Schema):
    id = fields.Int()
    product_id = fields.Int()
    qty = fields.Int()
    price_cents = fields.Int()
    product = fields.Nested(ProductOut)


class OrderOut(Schema):
    id = fields.Int()
    customer_email = fields.Str()
    total_cents = fields.Int()
    created_at = fields.DateTime()
    items = fields.List(fields.Nested(OrderItemOut))


# --- Home & Health checks ---

@app.get("/")
def index():
    return jsonify({
        "message": "Product & Order API Service is running!",
        "endpoints": {
            "healthz": "/healthz",
            "ready": "/ready",
            "products": "/api/v1/products",
            "orders": "/api/v1/orders"
        }
    }), 200


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


@app.get("/ready")
def ready():
    checks = {}
    try:
        db.session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "err"

    ok = all(v == "ok" for v in checks.values())
    return jsonify({"status": "ok" if ok else "degraded", "checks": checks}), 200 if ok else 503


# --- Products endpoints ---

@app.get("/api/v1/products")
def list_products():
    page = max(1, int(request.args.get("page", 1)))
    size = min(100, max(1, int(request.args.get("size", 20))))

    query = db.select(Product).where(Product.archived.is_(False))
    total = db.session.scalar(
        db.select(db.func.count()).select_from(Product).where(Product.archived.is_(False))
    )
    rows = db.session.execute(
        query.order_by(Product.id).offset((page - 1) * size).limit(size)
    ).scalars().all()

    return jsonify({
        "items": [ProductOut().dump(p) for p in rows],
        "page": page,
        "size": size,
        "total": total,
    }), 200


@app.get("/api/v1/products/<int:id>")
def get_product(id):
    p = db.session.get(Product, id)
    if p is None or p.archived:
        return jsonify({"error": "not_found", "detail": f"Product {id} not found"}), 404
    return jsonify(ProductOut().dump(p)), 200


@app.post("/api/v1/products")
def create_product():
    if not request.is_json:
        return jsonify({"error": "bad_request", "detail": "Missing JSON body"}), 400

    errors = ProductIn().validate(request.json)
    if errors:
        return jsonify({"error": "validation_error", "detail": errors}), 422

    body = ProductIn().load(request.json)
    p = Product(**body)
    db.session.add(p)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "conflict", "detail": "sku already exists"}), 409

    return jsonify(ProductOut().dump(p)), 201


@app.post("/api/v1/products/<int:id>/reserve")
def reserve_product(id):
    p = db.session.get(Product, id)
    if p is None or p.archived:
        return jsonify({"error": "not_found", "detail": f"Product {id} not found"}), 404

    errors = ReserveIn().validate(request.json)
    if errors:
        return jsonify({"error": "validation_error", "detail": errors}), 422

    qty = ReserveIn().load(request.json)["qty"]
    if p.qty_in_stock < qty:
        return jsonify({"error": "out_of_stock", "detail": f"only {p.qty_in_stock} left"}), 409

    p.qty_in_stock -= qty
    db.session.commit()
    return jsonify(ProductOut().dump(p)), 200


@app.patch("/api/v1/products/<int:id>")
def patch_product(id):
    p = db.session.get(Product, id)
    if p is None or p.archived:
        return jsonify({"error": "not_found", "detail": f"Product {id} not found"}), 404

    errors = ProductPatch().validate(request.json)
    if errors:
        return jsonify({"error": "validation_error", "detail": errors}), 422

    body = ProductPatch().load(request.json, partial=True)
    for key, value in body.items():
        setattr(p, key, value)
    db.session.commit()
    return jsonify(ProductOut().dump(p)), 200


@app.delete("/api/v1/products/<int:id>")
def delete_product(id):
    p = db.session.get(Product, id)
    if p is None or p.archived:
        return jsonify({"error": "not_found", "detail": f"Product {id} not found"}), 404

    # Soft delete
    p.archived = True
    db.session.commit()
    return "", 204


# --- Orders endpoints ---

@app.post("/api/v1/orders")
def create_order():
    if not request.is_json:
        return jsonify({"error": "bad_request", "detail": "Missing JSON body"}), 400

    errors = OrderCreateIn().validate(request.json)
    if errors:
        return jsonify({"error": "validation_error", "detail": errors}), 422

    data = OrderCreateIn().load(request.json)
    customer_email = data["customer_email"]
    items_to_buy = data["items"]

    total_cents = 0
    order_items_list = []

    for item_req in items_to_buy:
        prod_id = item_req["product_id"]
        qty = item_req["qty"]

        product = db.session.get(Product, prod_id)
        if product is None or product.archived:
            return jsonify({"error": "not_found", "detail": f"Product {prod_id} not found"}), 404

        if product.qty_in_stock < qty:
            return jsonify({
                "error": "out_of_stock",
                "detail": f"Product '{product.name}' only has {product.qty_in_stock} in stock"
            }), 409

        product.qty_in_stock -= qty
        total_cents += product.price_cents * qty

        order_items_list.append(OrderItem(
            product_id=prod_id,
            qty=qty,
            price_cents=product.price_cents
        ))

    order = Order(
        customer_email=customer_email,
        total_cents=total_cents,
        items=order_items_list
    )
    db.session.add(order)
    db.session.commit()

    return jsonify(OrderOut().dump(order)), 201


@app.get("/api/v1/orders")
def list_orders():
    # Eager load items and products to prevent N+1 query
    stmt = db.select(Order).options(selectinload(Order.items).selectinload(OrderItem.product))
    orders = db.session.execute(stmt).scalars().all()
    return jsonify([OrderOut().dump(o) for o in orders]), 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
