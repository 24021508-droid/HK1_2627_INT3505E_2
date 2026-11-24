from flask import Blueprint
from .users_data import get_user

bp = Blueprint("v1", __name__, url_prefix="/users")

@bp.after_request
def add_sunset_header(response):
    # RFC 8594: Sunset Header báo hiệu thời điểm API v1 sẽ ngừng hoạt động
    response.headers["Sunset"] = "Wed, 01 Jul 2026 00:00:00 GMT"
    response.headers["Link"] = '</api/v2/users>; rel="successor-version"'
    response.headers["Deprecation"] = "true"
    return response

@bp.route("/<int:uid>")
def get(uid):
    u = get_user(uid)
    if not u:
        return {"error": "nf"}, 404
    return {
        "id": uid,
        "full_name": f"{u['first_name']} {u['last_name']}",
        "email": u["email"]
    }

