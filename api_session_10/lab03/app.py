from datetime import datetime, timezone

from flask import Flask, jsonify

from sunset import deprecate_at

app = Flask(__name__)
V1_SUNSET = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


@app.get("/api/v1/users/<int:uid>")
@deprecate_at(V1_SUNSET, replacement="/api/v2/users")
def get_v1(uid):
    return {"id": uid, "full_name": "Nguyễn Văn A"}


@app.get("/api/v2/users")
def list_v2():
    return jsonify([{"id": 1, "first_name": "Văn A", "last_name": "Nguyễn"}])


if __name__ == "__main__":
    app.run(port=5000)
