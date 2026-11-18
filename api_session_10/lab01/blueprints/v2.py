from flask import Blueprint, request
from .users_data import get_user, add_user

bp = Blueprint("v2", __name__, url_prefix="/users")

@bp.route("/<int:uid>")
def get(uid):
    u = get_user(uid)
    if not u:
        return {"error": "nf"}, 404
    return {
        "id": uid,
        "first_name": u["first_name"],
        "last_name": u["last_name"],
        "email": u["email"]
    }

@bp.route("", methods=["POST"])
def create():
    data = request.get_json(silent=True) or {}
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    email = data.get("email", "").strip()

    if not first_name or not last_name or not email:
        return {
            "error": "validation_error",
            "message": "Các trường 'first_name', 'last_name', 'email' không được để trống"
        }, 400

    new_id = add_user(first_name, last_name, email)
    return {
        "id": new_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email
    }, 201

