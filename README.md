# drrew-template-backend

Backend for [`drrew_template`](https://github.com/andrehaliim/drrew_template), built with FastAPI. Provides a complete auth system (register, login, logout, token refresh with rotation, profile update, change password) meant to be a reusable starting point for new projects.

## ✨ Features

- **JWT auth** — access token + refresh token, with refresh token rotation
- **Stateful refresh tokens** — stored in the database (`refresh_tokens` table) with `jti`-based revocation, so logout / change-password can actually invalidate sessions
- **Password hashing** — Passlib + bcrypt
- **ORM** — SQLAlchemy with PostgreSQL
- **Validation** — Pydantic v2 schemas
- **CORS** enabled for local development

## 🧰 Requirements

- Python 3.11+
- Docker & Docker Compose (for PostgreSQL)
- [Postman](https://www.postman.com/) (recommended, for testing the API)
- [TablePlus](https://tableplus.com/) or any Postgres GUI (optional, for inspecting the database)

## 🚀 Installation

1. **Clone the repo**

   ```bash
   git clone https://github.com/andrehaliim/drrew-template-backend.git
   cd drrew-template-backend
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   ```

   Activate it:

   ```powershell
   # Windows (PowerShell)
   .\venv\Scripts\Activate.ps1
   ```

   ```bash
   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the `.env` file**

   Copy `.env.example` (if available) or create a new `.env` in the project root:

   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/drrew_template
   SECRET_KEY=your-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   REFRESH_TOKEN_EXPIRE_DAYS=7
   ```

   > Generate a strong `SECRET_KEY`, e.g. with `python -c "import secrets; print(secrets.token_hex(32))"`.

5. **Start PostgreSQL via Docker Compose**

   ```bash
   docker compose up -d
   ```

   Check it's running:

   ```bash
   docker ps
   ```

   > If you get a SQLAlchemy connection error on startup, this is almost always because the Postgres container isn't running yet — check `docker ps` first.

6. **Run the server**

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   Tables are created automatically on startup via `Base.metadata.create_all`.

7. **Open the interactive docs**

   ```
   http://localhost:8000/docs
   ```

## 📡 Endpoints

All auth endpoints are prefixed with `/auth`.

| Method | Endpoint                | Description                                                          | Auth required               |
| ------ | ------------------------ | --------------------------------------------------------------------- | ---------------------------- |
| POST   | `/auth/register`         | Create a new user                                                     | No                            |
| POST   | `/auth/login`            | Log in, returns access + refresh token                                | No                            |
| POST   | `/auth/refresh`          | Exchange a refresh token for a new token pair (rotates the old one)   | No                            |
| POST   | `/auth/logout`           | Revoke a refresh token                                                | No (refresh token in body)   |
| POST   | `/auth/change-password`  | Change password, revokes all active refresh tokens for the user       | Yes                           |
| GET    | `/auth/me`               | Get the current user's profile                                        | Yes                           |
| PATCH  | `/auth/me`               | Update the current user's profile                                     | Yes                           |

Protected endpoints expect `Authorization: Bearer <access_token>`.

## 🔑 Token Lifecycle Notes

- Access tokens are short-lived JWTs (default 30 minutes) and are **stateless** — they remain technically valid until they expire, even after logout.
- Refresh tokens are long-lived (default 7 days) and are **stateful** — each one is tracked in the database by its `jti` and can be revoked (on logout, on refresh, or on password change).
- This is a reasonable trade-off for a template: full access-token revocation would require a blocklist check on every request.

## 🗄️ Inspecting the Database

Use TablePlus (or any Postgres client) to connect with the credentials from your `.env`:

```
Host: localhost
Port: 5432
Database: drrew_template
User: postgres
Password: postgres
```

## 📁 Project Structure

```
app/
├── __init__.py
├── auth.py           # password hashing, JWT creation/verification
├── database.py       # SQLAlchemy engine & session
├── models.py         # User, RefreshToken
├── schemas.py        # Pydantic request/response schemas
└── routers/
    └── auth.py       # all /auth endpoints
main.py                # FastAPI app entrypoint
```