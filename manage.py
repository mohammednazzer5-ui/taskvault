"""Command line helper.

Create (or promote) an admin account:
    python manage.py create-admin --email you@example.com --name "Your Name"
You will be prompted for the password so it never lands in shell history.
"""
import argparse
import getpass
import sys

from werkzeug.security import generate_password_hash

from app import create_app
from app.db import get_db


def create_admin(email, name, password):
    app = create_app()
    with app.app_context():
        db = get_db()
        email = email.strip().lower()
        existing = db.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (existing["id"],))
            print(f"Existing user {email} promoted to admin.")
        else:
            db.execute(
                "INSERT INTO users (name, email, password_hash, role) "
                "VALUES (?, ?, ?, 'admin')",
                (name, email, generate_password_hash(password)),
            )
            print(f"Admin {email} created.")
        db.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create-admin", help="create or promote an admin user")
    p.add_argument("--email", required=True)
    p.add_argument("--name", default="Admin")
    args = parser.parse_args()

    password = getpass.getpass("Password (min 8 characters): ")
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters.")
    create_admin(args.email, args.name, password)


if __name__ == "__main__":
    main()
