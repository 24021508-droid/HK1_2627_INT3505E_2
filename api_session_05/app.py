import base64
import json
from datetime import datetime
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, func, and_, or_, tuple_
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)


class BookAuthor(db.Model):
    __tablename__ = "book_authors"
    book_id: Mapped[int] = mapped_column(db.ForeignKey("books.id"), primary_key=True)
    author_id: Mapped[int] = mapped_column(db.ForeignKey("authors.id"), primary_key=True)
    role: Mapped[str] = mapped_column(db.String(50), default="author")


class Category(db.Model):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    slug: Mapped[str] = mapped_column(db.String(100), unique=True, nullable=False)
    books: Mapped[list["Book"]] = relationship("Book", back_populates="category")


class Author(db.Model):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    bio: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    books: Mapped[list["Book"]] = relationship("Book", secondary="book_authors", back_populates="authors")


class Book(db.Model):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(db.String(200), nullable=False)
    isbn: Mapped[str] = mapped_column(db.String(20), unique=True, nullable=False)
    price_vnd: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    stock: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    genre: Mapped[str] = mapped_column(db.String(100), nullable=False, default="General")
    category_id: Mapped[int | None] = mapped_column(db.ForeignKey("categories.id"), nullable=True)

    category: Mapped[Category | None] = relationship("Category", back_populates="books")
    authors: Mapped[list[Author]] = relationship("Author", secondary="book_authors", back_populates="books")

    def to_dict(self):
        return {
            "id": f"book_{self.id}",
            "numeric_id": self.id,
            "title": self.title,
            "isbn": self.isbn,
            "price_vnd": self.price_vnd,
            "stock": self.stock,
            "genre": self.genre,
            "category": self.category.name if self.category else None,
            "authors": [a.name for a in self.authors]
        }


SORT_WHITELIST = {
    "id": Book.id,
    "title": Book.title,
    "price": Book.price_vnd,
    "price_vnd": Book.price_vnd,
    "stock": Book.stock,
    "genre": Book.genre,
}

def encode_cursor(data: dict) -> str:
    raw = json.dumps(data, ensure_ascii=False)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")

def decode_cursor(raw: str) -> dict:
    pad = "=" * (-len(raw) % 4)
    decoded = base64.urlsafe_b64decode((raw + pad).encode("utf-8")).decode("utf-8")
    return json.loads(decoded)

def parse_sort_multi(sort_raw: str):
    if not sort_raw:
        sort_raw = "-id"

    parts = [p.strip() for p in sort_raw.split(",") if p.strip()]
    if not parts:
        parts = ["-id"]

    parsed_keys = []
    order_by_clauses = []
    normalized_parts = []
    has_id = False

    for part in parts:
        desc = part.startswith("-")
        key = part.lstrip("-")
        if key not in SORT_WHITELIST:
            return None, None, None, f"Invalid sort key '{key}'. Allowed keys: {', '.join(sorted(SORT_WHITELIST.keys()))}"
        col = SORT_WHITELIST[key]
        parsed_keys.append((key, col, desc))
        order_by_clauses.append(col.desc() if desc else col.asc())
        normalized_parts.append(f"-{key}" if desc else key)
        if key == "id":
            has_id = True

    if not has_id:
        default_id_desc = parsed_keys[0][2]
        parsed_keys.append(("id", Book.id, default_id_desc))
        order_by_clauses.append(Book.id.desc() if default_id_desc else Book.id.asc())

    normalized_sort_str = ",".join(normalized_parts)
    return parsed_keys, order_by_clauses, normalized_sort_str, None


def apply_cursor_condition(query, cursor_token: str, normalized_sort: str, parsed_keys):
    if not cursor_token:
        return query, None, 200

    try:
        payload = decode_cursor(cursor_token)
    except Exception:
        return None, "invalid_cursor", 400

    if payload.get("s") != normalized_sort:
        return None, "sort_chg", 400

    values = payload.get("v")
    if not isinstance(values, list) or len(values) != len(parsed_keys):
        return None, "invalid_cursor_values", 400

    clauses = []
    for i in range(len(parsed_keys)):
        prefix_eq = []
        for j in range(i):
            _, col_j, _ = parsed_keys[j]
            prefix_eq.append(col_j == values[j])

        _, col_i, desc_i = parsed_keys[i]
        cmp_expr = (col_i < values[i]) if desc_i else (col_i > values[i])

        if prefix_eq:
            clauses.append(and_(*prefix_eq, cmp_expr))
        else:
            clauses.append(cmp_expr)

    query = query.filter(or_(*clauses))
    return query, None, 200


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bookstore.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    @app.route("/")
    def index():
        return jsonify({
            "message": "Bookstore API",
            "endpoints": {
                "list_books": "/api/v1/books"
            }
        })

    @app.route("/api/v1/books", methods=["GET"])
    @app.route("/books", methods=["GET"])
    def list_books():
        genre_filter = request.args.get("genre", type=str)
        sort_raw = request.args.get("sort", "-id")
        limit = min(request.args.get("limit", 20, type=int), 100)
        if limit <= 0:
            limit = 20

        raw_strategy = request.args.get("strategy")
        if raw_strategy:
            strategy = raw_strategy.lower()
            if strategy not in ("offset", "cursor"):
                return jsonify({"error": "invalid_strategy", "message": "Strategy must be 'offset' or 'cursor'"}), 400
        else:
            if "offset" in request.args and "cursor" not in request.args:
                strategy = "offset"
            else:
                strategy = "cursor"

        parsed_keys, order_by_clauses, normalized_sort, sort_err = parse_sort_multi(sort_raw)
        if sort_err:
            return jsonify({"error": "bad_sort", "message": sort_err}), 400

        q = select(Book)
        if genre_filter:
            q = q.filter(Book.genre.ilike(f"%{genre_filter.strip()}%"))

        if strategy == "offset":
            offset = request.args.get("offset", 0, type=int)
            if offset < 0:
                offset = 0

            total_q = select(func.count(Book.id))
            if genre_filter:
                total_q = total_q.filter(Book.genre.ilike(f"%{genre_filter.strip()}%"))
            total = db.session.scalar(total_q) or 0

            paged_query = q.order_by(*order_by_clauses).offset(offset).limit(limit)
            items = db.session.scalars(paged_query).all()

            has_next = (offset + limit) < total

            return jsonify({
                "data": [b.to_dict() for b in items],
                "pagination": {
                    "strategy": "offset",
                    "offset": offset,
                    "limit": limit,
                    "total": total,
                    "has_next": has_next
                }
            })

        else:
            cursor_token = request.args.get("cursor")
            q, cursor_err, status_code = apply_cursor_condition(q, cursor_token, normalized_sort, parsed_keys)
            if cursor_err:
                return jsonify({
                    "error": cursor_err,
                    "message": "Sort criteria changed or cursor invalid" if cursor_err == "sort_chg" else "Invalid cursor provided"
                }), status_code

            paged_query = q.order_by(*order_by_clauses).limit(limit + 1)
            rows = db.session.scalars(paged_query).all()

            has_more = len(rows) > limit
            items = rows[:limit]

            next_cursor = None
            if items and has_more:
                last_item = items[-1]
                values = []
                for _, col_attr, _ in parsed_keys:
                    val = getattr(last_item, col_attr.key)
                    values.append(val)
                next_cursor = encode_cursor({
                    "s": normalized_sort,
                    "v": values
                })

            return jsonify({
                "data": [b.to_dict() for b in items],
                "pagination": {
                    "strategy": "cursor",
                    "limit": limit,
                    "next_cursor": next_cursor,
                    "has_more": has_more
                }
            })

    @app.route("/api/v1/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        book = db.session.get(Book, book_id)
        if not book:
            return jsonify({"error": "not_found", "message": f"Book with id {book_id} not found"}), 404
        return jsonify(book.to_dict())

    @app.route("/api/v1/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True) or {}
        if not data.get("title") or not data.get("isbn"):
            return jsonify({"error": "bad_request", "message": "title and isbn are required"}), 400

        book = Book(
            title=data["title"],
            isbn=data["isbn"],
            price_vnd=data.get("price_vnd", data.get("price", 0)),
            stock=data.get("stock", 0),
            genre=data.get("genre", "General")
        )
        db.session.add(book)
        db.session.commit()
        return jsonify(book.to_dict()), 201

    return app


def seed_data(app):
    with app.app_context():
        db.create_all()
        if db.session.scalar(select(func.count(Book.id))) == 0:
            c_tech = Category(name="Technology", slug="technology")
            c_lit = Category(name="Literature", slug="literature")
            c_sci = Category(name="Science", slug="science")
            db.session.add_all([c_tech, c_lit, c_sci])
            db.session.flush()

            a1 = Author(name="Robert C. Martin", bio="Uncle Bob")
            a2 = Author(name="Martin Fowler", bio="Refactoring guru")
            a3 = Author(name="Andrew Hunt", bio="Pragmatic Programmer")
            db.session.add_all([a1, a2, a3])
            db.session.flush()

            sample_books = [
                ("Clean Code", "9780132350884", 450000, 15, "Technology", c_tech, [a1]),
                ("Clean Architecture", "9780134494166", 520000, 12, "Technology", c_tech, [a1]),
                ("The Pragmatic Programmer", "9780135957059", 480000, 20, "Technology", c_tech, [a3]),
                ("Refactoring", "9780201485677", 490000, 8, "Technology", c_tech, [a2]),
                ("Design Patterns (GoF)", "9780201633610", 550000, 10, "Technology", c_tech, [a1, a2]),
                ("Domain-Driven Design", "9780321125217", 530000, 7, "Technology", c_tech, [a2]),
                ("Introduction to Algorithms", "9780262033848", 680000, 25, "Science", c_sci, []),
                ("Artificial Intelligence: Modern Approach", "9780136042594", 750000, 5, "Science", c_sci, []),
                ("Structure and Interpretation of Computer Programs", "9780262510875", 420000, 9, "Technology", c_tech, []),
                ("Designing Data-Intensive Applications", "9781449373320", 590000, 30, "Technology", c_tech, []),
                ("War and Peace", "9780199232765", 210000, 18, "Literature", c_lit, []),
                ("Crime and Punishment", "9780140449136", 190000, 22, "Literature", c_lit, []),
                ("1984", "9780451524935", 150000, 50, "Literature", c_lit, []),
                ("Brave New World", "9780060850524", 160000, 40, "Literature", c_lit, []),
                ("The Great Gatsby", "9780743273565", 140000, 35, "Literature", c_lit, []),
                ("To Kill a Mockingbird", "9780061120084", 175000, 28, "Literature", c_lit, []),
                ("A Brief History of Time", "9780553380163", 260000, 14, "Science", c_sci, []),
                ("The Selfish Gene", "9780199291151", 280000, 11, "Science", c_sci, []),
                ("Cosmos", "9780345539434", 310000, 16, "Science", c_sci, []),
                ("Sapiens: A Brief History of Humankind", "9780062316097", 320000, 45, "Science", c_sci, []),
                ("Python Crash Course", "9781593279288", 390000, 30, "Technology", c_tech, []),
                ("Fluent Python", "9781491946008", 490000, 17, "Technology", c_tech, []),
            ]

            for title, isbn, price, stock, genre, cat, authors in sample_books:
                b = Book(
                    title=title,
                    isbn=isbn,
                    price_vnd=price,
                    stock=stock,
                    genre=genre,
                    category=cat,
                    authors=authors
                )
                db.session.add(b)

            db.session.commit()


app = create_app()

if __name__ == "__main__":
    seed_data(app)
    app.run(host="0.0.0.0", port=5000, debug=True)
