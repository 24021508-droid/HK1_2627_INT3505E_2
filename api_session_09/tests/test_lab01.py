"""LAB 1 — 4 tests + 1 bonus test."""
import pytest
from jsonschema import validate, ValidationError
from tools import get_book_schema


def test_get_books_empty(client):
    """A. GET /books khi CSDL rỗng trả về mảng rỗng (không phải null)."""
    response = client.get("/books")
    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0
    assert data is not None


def test_get_book_not_found(client):
    """B. GET /books/<id> với id không tồn tại trả về 404 + JSON chứa 'code': 'NOT_FOUND'."""
    response = client.get("/books/999999")
    assert response.status_code == 404

    data = response.get_json()
    assert data.get("code") == "NOT_FOUND"


def test_post_book_missing_title(client):
    """C. POST /books thiếu title trả về 400 + trong errors có field 'title'."""
    payload = {"author": "Nguyen Van A"}
    response = client.post("/books", json=payload)

    assert response.status_code == 400

    data = response.get_json()
    assert "errors" in data
    error_fields = [e.get("field") for e in data["errors"]]
    assert "title" in error_fields


def test_delete_then_get(client):
    """D. Xoá rồi GET cùng id — phải trả về 404."""
    post_res = client.post(
        "/books", json={"title": "Test Book", "author": "Test Author"}
    )
    assert post_res.status_code == 201
    book_id = post_res.get_json().get("id")

    del_res = client.delete(f"/books/{book_id}")
    assert del_res.status_code in (200, 204)

    get_res = client.get(f"/books/{book_id}")
    assert get_res.status_code == 404


def test_response_extra_field_blocked(client, sample_book):
    """Bước 2, Bonus: test_response_extra_field_blocked dùng jsonschema — chứng minh backend không lộ password_hash."""
    response = client.get(f"/books/{sample_book}")
    assert response.status_code == 200
    book_data = response.get_json()

    # Chứng minh backend không chứa password_hash
    assert "password_hash" not in book_data

    schema = get_book_schema()

    # Response gốc hợp lệ theo schema
    validate(instance=book_data, schema=schema)

    # Thêm field lạ password_hash vào bản copy để giả lập trường hợp bị rò rỉ field
    tampered_data = dict(book_data)
    tampered_data["password_hash"] = "pbkdf2:sha256:fake_hash_123"

    # Schema có additionalProperties: false nên validate phải raise ValidationError
    with pytest.raises(ValidationError):
        validate(instance=tampered_data, schema=schema)
