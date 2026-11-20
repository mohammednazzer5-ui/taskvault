import datetime
import re
import sqlite3
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .utils import error, json_body

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def public_user(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
    }


def make_token(user_id):
    now = datetime.datetime.now(datetime.timezone.utc)
    hours = current_app.config["TOKEN_HOURS"]
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + datetime.timedelta(hours=hours),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def _token_from_request():
    parts = request.headers.get("Authorization", "").split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def login_required(view):
    """Require a valid JWT. The user is re-loaded from the database on every
    request, so deleted users and role changes take effect immediately."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        token = _token_from_request()
        if not token:
            return error("Authentication required", 401)
        try:
            payload = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            user_id = int(payload["sub"])
        except jwt.ExpiredSignatureError:
            return error("Token expired, please log in again", 401)
        except (jwt.InvalidTokenError, KeyError, ValueError):
            return error("Invalid token", 401)

        user = get_db().execute(
            "SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if user is None:
            return error("User no longer exists", 401)
        g.user = user
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["role"] != "admin":
            return error("Admin access required", 403)
        return view(*args, **kwargs)

    return wrapped


@bp.post("/register")
def register():
    data = json_body()
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not 1 <= len(name) <= 80:
        return error("Name is required (max 80 characters)", 400)
    if not EMAIL_RE.match(email) or len(email) > 254:
        return error("A valid email is required", 400)
    if not 8 <= len(password) <= 128:
        return error("Password must be 8 to 128 characters", 400)

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error("An account with this email already exists", 409)

    user = db.execute(
        "SELECT id, name, email, role FROM users WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify({"token": make_token(user["id"]), "user": public_user(user)}), 201


@bp.post("/login")
def login():
    data = json_body()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    user = get_db().execute(
        "SELECT id, name, email, role, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    # Same message for unknown email and wrong password (no account enumeration)
    if user is None or not check_password_hash(user["password_hash"], password):
        return error("Invalid email or password", 401)

    return jsonify({"token": make_token(user["id"]), "user": public_user(user)})


@bp.get("/me")
@login_required
def me():
    return jsonify({"user": public_user(g.user)})
