from uuid import uuid4


def v1_create_order(body):
    return {"order_id": str(uuid4()), "account_id": body["account_id"]}


def v2_create_order(body):
    return {
        "order": {"order_id": str(uuid4()), "account_id": body["account_id"]},
        "status": "created",
    }
