from os import environ

from flask import Flask, jsonify, request

from gateway import dispatch

app = Flask(__name__)
app.config["V2_PERCENT"] = int(environ.get("V2_PERCENT", "5"))
if not 0 <= app.config["V2_PERCENT"] <= 100:
    raise ValueError("V2_PERCENT must be between 0 and 100")


@app.post("/orders")
def create_order():
    body = request.get_json(silent=True)
    account_id = body.get("account_id") if isinstance(body, dict) else None
    if not isinstance(account_id, str) or not account_id.strip():
        return jsonify(error="account_id must be a non-empty string"), 400

    version, result = dispatch(body)
    response = jsonify(result)
    response.headers["X-Order-Handler"] = version
    return response, 201 if version == "v2" else 200


if __name__ == "__main__":
    app.run(port=5000)
