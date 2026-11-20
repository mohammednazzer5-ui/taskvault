from flask import Blueprint, g, jsonify, request

from .auth import login_required
from .db import get_db
from .utils import error, json_body

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")

VALID_STATUS = ("todo", "in_progress", "done")
COLUMNS = "id, title, description, status, created_at, updated_at"


def task_dict(row):
    return {key: row[key] for key in row.keys()}


def validate(data, partial=False):
    """Validate task fields. Returns (clean_dict, error_message)."""
    clean = {}

    if "title" in data or not partial:
        title = str(data.get("title", "")).strip()
        if not 1 <= len(title) <= 120:
            return None, "Title is required (max 120 characters)"
        clean["title"] = title

    if "description" in data:
        description = str(data["description"]).strip()
        if len(description) > 2000:
            return None, "Description must be 2000 characters or fewer"
        clean["description"] = description

    if "status" in data:
        if data["status"] not in VALID_STATUS:
            return None, "Status must be one of: " + ", ".join(VALID_STATUS)
        clean["status"] = data["status"]

    return clean, None


def get_owned_task(task_id):
    """Fetch a task only if it belongs to the logged-in user."""
    return get_db().execute(
        f"SELECT {COLUMNS} FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, g.user["id"]),
    ).fetchone()


@bp.get("")
@login_required
def list_tasks():
    status = request.args.get("status")
    sql = f"SELECT {COLUMNS} FROM tasks WHERE user_id = ?"
    params = [g.user["id"]]
    if status:
        if status not in VALID_STATUS:
            return error("Invalid status filter", 400)
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY id DESC"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify({"tasks": [task_dict(r) for r in rows]})


@bp.post("")
@login_required
def create_task():
    clean, problem = validate(json_body())
    if problem:
        return error(problem, 400)

    db = get_db()
    cur = db.execute(
        "INSERT INTO tasks (user_id, title, description, status) VALUES (?, ?, ?, ?)",
        (
            g.user["id"],
            clean["title"],
            clean.get("description", ""),
            clean.get("status", "todo"),
        ),
    )
    db.commit()
    return jsonify({"task": task_dict(get_owned_task(cur.lastrowid))}), 201


@bp.get("/<int:task_id>")
@login_required
def get_task(task_id):
    task = get_owned_task(task_id)
    if task is None:
        return error("Task not found", 404)
    return jsonify({"task": task_dict(task)})


@bp.route("/<int:task_id>", methods=["PUT", "PATCH"])
@login_required
def update_task(task_id):
    if get_owned_task(task_id) is None:
        return error("Task not found", 404)

    clean, problem = validate(json_body(), partial=True)
    if problem:
        return error(problem, 400)
    if not clean:
        return error("Nothing to update", 400)

    # Column names come from the validate() whitelist above, never from user input.
    assignments = ", ".join(f"{col} = ?" for col in clean)
    db = get_db()
    db.execute(
        f"UPDATE tasks SET {assignments}, updated_at = CURRENT_TIMESTAMP "
        "WHERE id = ? AND user_id = ?",
        (*clean.values(), task_id, g.user["id"]),
    )
    db.commit()
    return jsonify({"task": task_dict(get_owned_task(task_id))})


@bp.delete("/<int:task_id>")
@login_required
def delete_task(task_id):
    if get_owned_task(task_id) is None:
        return error("Task not found", 404)
    db = get_db()
    db.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, g.user["id"])
    )
    db.commit()
    return "", 204
