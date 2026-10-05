from flask import Flask, jsonify, request

app = Flask(__name__)

posts = [
    {"id": 1, "title": "Hello API", "content": "My first post"},
    {"id": 2, "title": "Flask", "content": "Learning Flask REST API"}
]


# GET /api/v1/posts
@app.get("/api/v1/posts")
def get_posts():
    return jsonify(posts)


# POST /api/v1/posts
@app.post("/api/v1/posts")
def create_post():
    data = request.get_json()

    post = {
        "id": len(posts) + 1,
        "title": data["title"],
        "content": data["content"]
    }

    posts.append(post)
    return jsonify(post), 201


# GET /api/v1/posts/<post_id>
@app.get("/api/v1/posts/<int:post_id>")
def get_post(post_id):
    post = next((p for p in posts if p["id"] == post_id), None)

    if post is None:
        return jsonify({"error": "Post not found"}), 404

    return jsonify(post)


if __name__ == "__main__":
    app.run(debug=True)