from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class ProblemError(Exception):
    def __init__(self, status, title, detail, type="about:blank"):
        self.status = status
        self.title = title
        self.detail = detail
        self.type = type
        super().__init__(detail)


def problem_response(status, title, detail, type="about:blank"):
    response = jsonify({
        "type": type,
        "title": title,
        "detail": detail,
        "status": status,
        "instance": request.path
    })

    response.status_code = status
    response.content_type = "application/problem+json"

    return response


@app.errorhandler(ProblemError)
def handle_problem_error(error):
    return problem_response(
        error.status,
        error.title,
        error.detail,
        error.type
    )


@app.errorhandler(HTTPException)
def handle_http_exception(error):
    return problem_response(
        error.code,
        error.name,
        error.description
    )


@app.errorhandler(Exception)
def handle_exception(error):
    logger.exception("Unhandled exception")

    return problem_response(
        500,
        "Internal Server Error",
        "An unexpected error occurred."
    )


@app.get("/test/400")
def test_400():
    raise ProblemError(
        400,
        "Bad Request",
        "The request is invalid."
    )


@app.get("/test/401")
def test_401():
    raise ProblemError(
        401,
        "Unauthorized",
        "Authentication is required."
    )


@app.get("/test/403")
def test_403():
    raise ProblemError(
        403,
        "Forbidden",
        "You do not have permission to access this resource."
    )


@app.get("/test/404")
def test_404():
    raise ProblemError(
        404,
        "Not Found",
        "The requested resource was not found."
    )


@app.get("/test/409")
def test_409():
    raise ProblemError(
        409,
        "Conflict",
        "The request conflicts with the current state of the resource."
    )


@app.get("/test/422")
def test_422():
    raise ProblemError(
        422,
        "Unprocessable Entity",
        "The request data is invalid."
    )


@app.get("/test/429")
def test_429():
    raise ProblemError(
        429,
        "Too Many Requests",
        "Too many requests. Please try again later."
    )


@app.get("/test/500")
def test_500():
    raise Exception("Database connection failed")


@app.get("/test/503")
def test_503():
    raise ProblemError(
        503,
        "Service Unavailable",
        "The service is temporarily unavailable."
    )


if __name__ == "__main__":
    app.run(debug=False)