import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_get_books_empty(client):
    """Ensure GET /books returns an empty list when DB has no records."""
    response = client.get("/books")
    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0
    assert data is not None


def test_get_book_not_found(client):
    """Ensure GET /books/<id> returns 404 with NOT_FOUND error code for invalid IDs."""
    response = client.get("/books/999999")
    assert response.status_code == 404

    data = response.get_json()
    assert data.get("code") == "NOT_FOUND"


def test_post_book_missing_title(client):
    """Ensure POST /books missing title field returns 400 with title validation error."""
    payload = {"author": "Nguyen Van A"}
    response = client.post("/books", json=payload)

    assert response.status_code == 400

    data = response.get_json()
    assert "errors" in data
    assert "title" in data["errors"]


def test_delete_then_get(client):
    """Ensure a deleted book resource returns 404 on subsequent GET requests."""
    # Seed test record
    post_res = client.post(
        "/books", json={"title": "Test Book", "author": "Test Author"}
    )
    book_id = post_res.get_json().get("id")

    # Delete resource
    del_res = client.delete(f"/books/{book_id}")
    assert del_res.status_code in (200, 204)

    # Verify resource non-existence
    get_res = client.get(f"/books/{book_id}")
    assert get_res.status_code == 404