from flask import Flask
from flask.views import MethodView
from flask_smorest import Api, Blueprint
from marshmallow import Schema, fields
import uuid

# Khởi tạo Flask app và cấu hình Swagger UI
app = Flask(__name__)
app.config["API_TITLE"] = "Tasks API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config["OPENAPI_SWAGGER_UI_PATH"] = "/docs"
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
app.config["API_SPEC_OPTIONS"] = {
    "security": [{"bearerAuth": []}],
    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
    }
}

api = Api(app)

# --- KHAI BÁO SCHEMAS BẰNG MARSHMALLOW ---
class TaskSchema(Schema):
    id = fields.UUID(dump_only=True)
    title = fields.Str(required=True)
    status = fields.Str(dump_default="open")
    priority = fields.Str(dump_default="normal")
    dueDate = fields.Date()
    assigneeId = fields.UUID()

class CreateTaskInput(Schema):
    title = fields.Str(required=True)
    status = fields.Str(load_default="open")
    priority = fields.Str(load_default="normal")
    dueDate = fields.Date()
    assigneeId = fields.UUID()

class UpdateTaskInput(Schema):
    title = fields.Str()
    status = fields.Str()
    priority = fields.Str()
    dueDate = fields.Date()
    assigneeId = fields.UUID()

class TaskQuerySchema(Schema):
    limit = fields.Int(load_default=10)
    status = fields.Str()

# --- ĐỊNH NGHĨA BLUEPRINT VÀ ROUTES ---
bp = Blueprint("tasks", __name__, url_prefix="/v1/tasks", description="Quản lý task nội bộ")

# Mock database tạm thời lưu trong memory
tasks_db = {}

@bp.route("/")
class TaskCollection(MethodView):
    @bp.arguments(TaskQuerySchema, location="query")
    @bp.response(200, TaskSchema(many=True))
    def get(self, query_args):
        """Lấy danh sách Tasks"""
        return list(tasks_db.values())

    @bp.arguments(CreateTaskInput)
    @bp.response(201, TaskSchema)
    def post(self, new_task_data):
        """Tạo một Task mới"""
        task_id = uuid.uuid4()
        task = {"id": task_id, **new_task_data}
        tasks_db[task_id] = task
        return task

@bp.route("/<uuid:task_id>")
class TaskItem(MethodView):
    @bp.response(200, TaskSchema)
    def get(self, task_id):
        """Lấy thông tin Task theo ID"""
        if task_id not in tasks_db:
            abort(404, message="Task not found")
        return tasks_db[task_id]

    @bp.arguments(UpdateTaskInput)
    @bp.response(200, TaskSchema)
    def patch(self, update_data, task_id):
        """Cập nhật một phần Task"""
        if task_id not in tasks_db:
            abort(404, message="Task not found")
        tasks_db[task_id].update(update_data)
        return tasks_db[task_id]

    @bp.response(204)
    def delete(self, task_id):
        """Xóa một Task"""
        if task_id in tasks_db:
            del tasks_db[task_id]
        return ""

# Đăng ký Blueprint vào API
api.register_blueprint(bp)

if __name__ == "__main__":
    app.run(debug=True, port=5000)