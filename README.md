# TaskVault

A full stack task manager with **user authentication, role-based access, and a REST API**. Users sign up, log in, and manage their own tasks; admins can manage all users.

Built with Flask, SQLite, JWT, and a dependency-free vanilla JavaScript frontend.

<!-- Add a screenshot here: ![TaskVault screenshot](docs/screenshot.png) -->

## Features

- **Authentication:** sign up and log in with JWT tokens (HS256, 2-hour expiry by default)
- **Secure passwords:** hashed with Werkzeug (scrypt), never stored in plain text
- **Task CRUD:** create, read, update, and delete tasks with a status (`todo`, `in_progress`, `done`) and a status filter
- **Data isolation:** every query is scoped to the logged-in user, so one user can never read or change another user's tasks
- **Admin role:** list users with task counts, promote or demote users, delete users (their tasks are removed automatically)
- **Input validation** on every endpoint, consistent JSON errors, and a request size limit
- **Tested:** 31 automated tests covering auth, ownership, admin permissions, and security edge cases
- **CI and Docker:** GitHub Actions runs the tests on every push, and a Dockerfile is included

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | SQLite (parameterized queries, foreign keys with cascade delete) |
| Auth | PyJWT, Werkzeug password hashing |
| Frontend | HTML, CSS, vanilla JavaScript (no build step) |
| Testing | `unittest` with Flask's test client |
| DevOps | GitHub Actions, Docker, Gunicorn |

## Project structure

```
taskvault/
├── app/
│   ├── __init__.py      # app factory, config, error handlers
│   ├── auth.py          # register, login, JWT, login_required / admin_required
│   ├── tasks.py         # task CRUD (scoped to the current user)
│   ├── admin.py         # admin-only user management
│   ├── db.py            # SQLite connection and schema
│   ├── utils.py         # JSON helpers
│   └── static/          # index.html, app.js, style.css
├── tests/               # unittest suite
├── manage.py            # CLI: create an admin user
├── run.py               # development entry point
├── Dockerfile
└── .github/workflows/ci.yml
```

## Run it locally (VS Code)

Requires Python 3.10 or newer.

```bash
# 1. Clone and open
git clone https://github.com/<your-username>/taskvault.git
cd taskvault
code .

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your secret key
cp .env.example .env             # Windows: copy .env.example .env
# then edit .env and set SECRET_KEY to a long random string

# 5. Start the app
python run.py
```

Open http://127.0.0.1:5000. The database file is created automatically in `instance/`.

Generate a good secret key with: `python -c "import secrets; print(secrets.token_hex(32))"`

### Create an admin account

New sign-ups are always regular users. Create the first admin from the command line (you will be prompted for a password):

```bash
python manage.py create-admin --email you@example.com --name "Your Name"
```

### Run the tests

```bash
python -m unittest discover -s tests -v
```

## API

All task and admin routes need the header `Authorization: Bearer <token>`.

| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/api/auth/register` | Create an account, returns a token | Public |
| POST | `/api/auth/login` | Log in, returns a token | Public |
| GET | `/api/auth/me` | Current user | Logged in |
| GET | `/api/tasks?status=` | List my tasks (optional filter) | Logged in |
| POST | `/api/tasks` | Create a task | Logged in |
| GET | `/api/tasks/<id>` | Get one of my tasks | Logged in |
| PATCH | `/api/tasks/<id>` | Update my task (partial update) | Logged in |
| DELETE | `/api/tasks/<id>` | Delete my task | Logged in |
| GET | `/api/admin/users` | List all users with task counts | Admin |
| PATCH | `/api/admin/users/<id>` | Change a user's role | Admin |
| DELETE | `/api/admin/users/<id>` | Delete a user and their tasks | Admin |
| GET | `/api/health` | Health check | Public |

Example:

```bash
curl -X POST http://127.0.0.1:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Ada","email":"ada@example.com","password":"correct-horse-battery"}'
```

## Docker

```bash
docker build -t taskvault .
docker run -p 8000:8000 -e SECRET_KEY=<long-random-string> -v taskvault-data:/data taskvault
```

Then open http://localhost:8000.

## Security notes

- Passwords are hashed; login errors never reveal whether an email exists
- JWTs are verified on every request and the user is re-loaded from the database, so deleting a user or changing a role takes effect immediately
- All SQL uses parameterized queries
- The frontend renders user content with `textContent`, so HTML in a task title is shown as text and never executed
- Secrets live in `.env` (git-ignored); only `.env.example` is committed

**Known limitations** (good next steps): the token is kept in `localStorage` (an httpOnly cookie would resist XSS better), there is no rate limiting on login, and SQLite suits a single small instance. For production, put it behind HTTPS and consider PostgreSQL.

## Roadmap

- [ ] Rate limiting on login and registration
- [ ] PostgreSQL support (for example Amazon RDS)
- [ ] Refresh tokens or httpOnly cookie sessions
- [ ] Password reset by email
- [ ] Deploy to AWS (EC2 or Elastic Beanstalk) with a CI/CD pipeline

## License

MIT, see [LICENSE](LICENSE).
