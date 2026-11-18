USERS = {
    1: {"first_name": "Vũ Gia", "last_name": "Hưng", "email": "a@vnu.vn"},
    2: {"first_name": "Nguyễn Thị", "last_name": "Thanh Hiền", "email": "b@vnu.vn"}
}

def get_user(uid):
    return USERS.get(uid)

def add_user(first_name, last_name, email):
    new_id = max(USERS.keys(), default=0) + 1
    USERS[new_id] = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email
    }
    return new_id

