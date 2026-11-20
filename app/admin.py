from flask import Blueprint, g, jsonify

from .auth import admin_required
from .db import get_db
from .utils import error, json_body

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.get("/users")
@admin_required
def list_users():
    rows = get_db().execute(
        """
        SELECT u.id, u.name, u.email, u.role, u.created_at,
               COUNT(t.id) AS task_count
        FROM users u
        LEFT JOIN tasks t ON t.user_id = u.id
        GROUP BY u.id
        ORDER BY u.id
        """
    ).fetchall()
    return jsonify({"users": [{k: r[k] for k in r.keys()} for r in rows]})


@bp.patch("/users/<int:user_id>")
@admin_required
def change_role(user_id):
    role = json_body().get("role")
    if role not in ("user", "admin"):
        return error("Role must be 'user' or 'admin'", 400)
    if user_id == g.user["id"]:
        return error("You cannot change your own role", 400)

    db = get_db()
    cur = db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    db.commit()
    if cur.rowcount == 0:
        return error("User not found", 404)
    return jsonify({"id": user_id, "role": role})


@bp.delete("/users/<int:user_id>")
@admin_required
def delete_user(user_id):
    if user_id == g.user["id"]:
        return error("You cannot delete your own account here", 400)

    db = get_db()
    cur = db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()  # tasks are removed automatically (ON DELETE CASCADE)
    if cur.rowcount == 0:
        return error("User not found", 404)
    return "", 204
