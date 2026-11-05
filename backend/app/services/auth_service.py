"""MySQL-backed local accounts and opaque cookie sessions."""

import hashlib
import hmac
import re
import secrets
import time
from contextlib import contextmanager
from typing import Iterator

import pymysql
from pymysql.cursors import DictCursor

from app.config import settings

SESSION_COOKIE = settings.session_cookie_name
SESSION_TTL_SECONDS = settings.session_ttl_seconds
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


@contextmanager
def _connection() -> Iterator[tuple[pymysql.Connection, DictCursor]]:
    connection = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        **(
            {
                "ssl_ca": str(settings.mysql_ssl_ca_path),
                "ssl_verify_cert": True,
                "ssl_verify_identity": True,
            }
            if settings.mysql_ssl_ca_path
            else {}
        ),
    )
    cursor = connection.cursor()
    try:
        yield connection, cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def initialize() -> None:
    with _connection() as (_, cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(32) NOT NULL PRIMARY KEY,
                username VARCHAR(32) NOT NULL UNIQUE,
                password_hash VARCHAR(128) NOT NULL,
                role ENUM('admin', 'user') NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at BIGINT NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash CHAR(64) NOT NULL PRIMARY KEY,
                user_id VARCHAR(32) NOT NULL,
                expires_at BIGINT NOT NULL,
                INDEX sessions_expiry_idx (expires_at),
                CONSTRAINT sessions_user_fk FOREIGN KEY (user_id)
                    REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )


def setup_required() -> bool:
    with _connection() as (_, cursor):
        cursor.execute("SELECT 1 FROM users LIMIT 1")
        return cursor.fetchone() is None


def password_recovery_enabled() -> bool:
    return settings.account_recovery_key is not None


def validate_credentials(username: str, password: str) -> None:
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Username must be 3-32 characters: letters, numbers, dot, dash, or underscore.")
    if len(password) < settings.min_password_length or len(password) > settings.max_password_length:
        raise ValueError(
            f"Password must be between {settings.min_password_length} and {settings.max_password_length} characters."
        )


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"{salt.hex()}:{digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        salt_hex, digest_hex = encoded.split(":", maxsplit=1)
        candidate = _hash_password(password, bytes.fromhex(salt_hex)).split(":", maxsplit=1)[1]
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False


def _public_user(row: dict) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
    }


def _insert_user(cursor: DictCursor, username: str, password: str, role: str) -> dict:
    validate_credentials(username, password)
    user_id = secrets.token_hex(16)
    cursor.execute(
        "INSERT INTO users (id, username, password_hash, role, created_at) VALUES (%s, %s, %s, %s, %s)",
        (user_id, username, _hash_password(password), role, int(time.time())),
    )
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    return _public_user(row)


def create_initial_admin(username: str, password: str) -> dict:
    with _connection() as (connection, cursor):
        connection.begin()
        cursor.execute("SELECT id FROM users LIMIT 1 FOR UPDATE")
        if cursor.fetchone() is not None:
            raise RuntimeError("Initial admin account has already been created.")
        return _insert_user(cursor, username, password, "admin")


def create_user(username: str, password: str, role: str = "user") -> dict:
    if role not in ("admin", "user"):
        raise ValueError("Role must be admin or user.")
    with _connection() as (_, cursor):
        return _insert_user(cursor, username, password, role)


def reset_password(username: str, recovery_key: str, new_password: str) -> bool:
    configured_key = settings.account_recovery_key
    if configured_key is None or not hmac.compare_digest(configured_key, recovery_key):
        return False

    validate_credentials(username, new_password)
    with _connection() as (_, cursor):
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        if row is None:
            return False

        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (_hash_password(new_password), row["id"]),
        )
        cursor.execute("DELETE FROM sessions WHERE user_id = %s", (row["id"],))
        return cursor.rowcount == 1


def list_users() -> list[dict]:
    with _connection() as (_, cursor):
        cursor.execute("SELECT * FROM users ORDER BY created_at, username")
        rows = cursor.fetchall()
        return [_public_user(row) for row in rows]


def set_user_active(user_id: str, is_active: bool) -> bool:
    with _connection() as (_, cursor):
        cursor.execute("UPDATE users SET is_active = %s WHERE id = %s", (int(is_active), user_id))
        if cursor.rowcount != 1:
            return False
        if not is_active:
            cursor.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
        return True


def login(username: str, password: str) -> tuple[dict, str] | None:
    with _connection() as (_, cursor):
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        if row is None or not row["is_active"] or not _verify_password(password, row["password_hash"]):
            return None

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        now = int(time.time())
        cursor.execute("DELETE FROM sessions WHERE expires_at <= %s", (now,))
        cursor.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
            (token_hash, row["id"], now + SESSION_TTL_SECONDS),
        )
        return _public_user(row), token


def get_session_user(token: str | None) -> dict | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()
    now = int(time.time())
    with _connection() as (_, cursor):
        cursor.execute("DELETE FROM sessions WHERE expires_at <= %s", (now,))
        cursor.execute(
            "SELECT users.* FROM sessions JOIN users ON users.id = sessions.user_id "
            "WHERE sessions.token_hash = %s AND sessions.expires_at > %s AND users.is_active = 1",
            (token_hash, now),
        )
        row = cursor.fetchone()
        return _public_user(row) if row else None


def logout(token: str | None) -> None:
    if not token:
        return
    token_hash = hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()
    with _connection() as (_, cursor):
        cursor.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))