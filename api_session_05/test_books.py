import pytest
from app import create_app, db, Book

@pytest.fixture
def client():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
    })
    with app.app_context():
        db.create_all()
        books = [
            Book(title="Book A", isbn="ISBN001", price_vnd=100000, stock=10, genre="Tech"),
            Book(title="Book B", isbn="ISBN002", price_vnd=300000, stock=5, genre="Tech"),
            Book(title="Book C", isbn="ISBN003", price_vnd=200000, stock=12, genre="Science"),
            Book(title="Book D", isbn="ISBN004", price_vnd=300000, stock=8, genre="Science"),
            Book(title="Book E", isbn="ISBN005", price_vnd=150000, stock=20, genre="Literature"),
            Book(title="Book F", isbn="ISBN006", price_vnd=200000, stock=15, genre="Literature"),
            Book(title="Book G", isbn="ISBN007", price_vnd=400000, stock=2, genre="Tech"),
            Book(title="Book H", isbn="ISBN008", price_vnd=100000, stock=30, genre="Tech"),
            Book(title="Book I", isbn="ISBN009", price_vnd=250000, stock=7, genre="Literature"),
            Book(title="Book J", isbn="ISBN010", price_vnd=350000, stock=14, genre="Science"),
        ]
        db.session.add_all(books)
        db.session.commit()

        yield app.test_client()

        db.session.remove()
        db.drop_all()


def test_offset_pagination(client):
    res = client.get("/api/v1/books?strategy=offset&limit=4&offset=0")
    assert res.status_code == 200
    json_data = res.get_json()
    assert len(json_data["data"]) == 4
    assert json_data["pagination"]["offset"] == 0
    assert json_data["pagination"]["limit"] == 4
    assert json_data["pagination"]["total"] == 10
    assert json_data["pagination"]["has_next"] is True

    res2 = client.get("/api/v1/books?strategy=offset&limit=4&offset=8")
    assert res2.status_code == 200
    json_data2 = res2.get_json()
    assert len(json_data2["data"]) == 2
    assert json_data2["pagination"]["has_next"] is False


def test_cursor_pagination(client):
    res = client.get("/api/v1/books?strategy=cursor&limit=4&sort=id")
    assert res.status_code == 200
    json_data = res.get_json()
    assert len(json_data["data"]) == 4
    assert json_data["pagination"]["has_more"] is True
    next_cursor = json_data["pagination"]["next_cursor"]
    assert next_cursor is not None

    res2 = client.get(f"/api/v1/books?strategy=cursor&limit=4&sort=id&cursor={next_cursor}")
    assert res2.status_code == 200
    json_data2 = res2.get_json()
    assert len(json_data2["data"]) == 4
    next_cursor2 = json_data2["pagination"]["next_cursor"]

    res3 = client.get(f"/api/v1/books?strategy=cursor&limit=4&sort=id&cursor={next_cursor2}")
    assert res3.status_code == 200
    json_data3 = res3.get_json()
    assert len(json_data3["data"]) == 2
    assert json_data3["pagination"]["has_more"] is False
    assert json_data3["pagination"]["next_cursor"] is None


def test_filter_genre(client):
    res = client.get("/api/v1/books?strategy=offset&genre=Science")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert len(data) == 3
    for b in data:
        assert b["genre"] == "Science"


def test_multi_key_sort(client):
    res = client.get("/api/v1/books?strategy=offset&sort=-price,title&limit=10")
    assert res.status_code == 200
    data = res.get_json()["data"]
    prices = [b["price_vnd"] for b in data]
    for i in range(len(prices) - 1):
        assert prices[i] >= prices[i + 1]

    items_300k = [b["title"] for b in data if b["price_vnd"] == 300000]
    assert items_300k == ["Book B", "Book D"]


def test_cursor_with_multi_key_sort(client):
    res1 = client.get("/api/v1/books?strategy=cursor&sort=-price,title&limit=3")
    assert res1.status_code == 200
    data1 = res1.get_json()
    cursor1 = data1["pagination"]["next_cursor"]
    assert cursor1 is not None

    res2 = client.get(f"/api/v1/books?strategy=cursor&sort=-price,title&limit=3&cursor={cursor1}")
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert len(data2["data"]) == 3

    ids1 = {b["id"] for b in data1["data"]}
    ids2 = {b["id"] for b in data2["data"]}
    assert len(ids1.intersection(ids2)) == 0


def test_invalid_sort_key_rejected(client):
    res = client.get("/api/v1/books?sort=malicious_column")
    assert res.status_code == 400
    assert res.get_json()["error"] == "bad_sort"


def test_cursor_sort_changed_rejected(client):
    res = client.get("/api/v1/books?strategy=cursor&sort=-price&limit=2")
    cursor = res.get_json()["pagination"]["next_cursor"]

    res2 = client.get(f"/api/v1/books?strategy=cursor&sort=title&cursor={cursor}")
    assert res2.status_code == 400
    assert res2.get_json()["error"] == "sort_chg"
