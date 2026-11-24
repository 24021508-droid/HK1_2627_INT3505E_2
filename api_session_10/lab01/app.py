import os
from flask import Flask, send_file, render_template_string
from blueprints.v1 import bp as v1_bp
from blueprints.v2 import bp as v2_bp

app = Flask(__name__)

app.register_blueprint(v1_bp, url_prefix=f"/api/v1{v1_bp.url_prefix or ''}")
app.register_blueprint(v2_bp, url_prefix=f"/api/v2{v2_bp.url_prefix or ''}")

# Phục vụ OpenAPI Specification file
@app.route("/openapi.yaml")
def openapi_spec():
    yaml_path = os.path.join(os.path.dirname(__file__), "openapi.yaml")
    return send_file(yaml_path, mimetype="text/yaml")

# Giao diện Swagger UI trực quan
@app.route("/docs")
def swagger_ui():
    template = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>User API - Swagger Documentation</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({
      url: '/openapi.yaml',
      dom_id: '#swagger-ui'
    });
  </script>
</body>
</html>"""
    return render_template_string(template)

if __name__ == "__main__":
    app.run(debug=True, port=5000)


