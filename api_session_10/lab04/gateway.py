from hashlib import md5

from flask import current_app, request

from handlers import v1_create_order, v2_create_order

V2_COHORTS = {"beta", "internal"}
V2_FORCE_ACCOUNTS = {"acct_42", "acct_99"}


def route_to_v2(body):
    cohort = request.headers.get("X-Cohort", "").strip().lower()
    if cohort in V2_COHORTS:
        return True

    account_id = body["account_id"]
    if account_id in V2_FORCE_ACCOUNTS:
        return True

    digest = md5(account_id.encode("utf-8"), usedforsecurity=False).hexdigest()
    bucket = int(digest, 16) % 100
    return bucket < current_app.config["V2_PERCENT"]


def dispatch(body):
    if route_to_v2(body):
        return "v2", v2_create_order(body)
    return "v1", v1_create_order(body)
