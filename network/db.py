from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .crypto import hash_password, make_token, verify_password


class Database:
    def __init__(self, path: Path, token_ttl_seconds: int) -> None:
        self.path = path
        self.token_ttl_seconds = token_ttl_seconds

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    last_login_at INTEGER
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS player_state (
                    user_id INTEGER PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS handshakes (
                    handshake_id TEXT PRIMARY KEY,
                    server_nonce TEXT NOT NULL,
                    client_nonce TEXT,
                    session_key_hex TEXT,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS handshake_nonces (
                    handshake_id TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY (handshake_id, nonce),
                    FOREIGN KEY (handshake_id) REFERENCES handshakes(handshake_id) ON DELETE CASCADE
                );
                """
            )

    def register_user(self, username: str, password: str, display_name: str | None = None) -> dict[str, Any]:
        now = int(time.time())
        safe_display_name = display_name or username
        with self.connection() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO users (username, password_hash, display_name, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, hash_password(password), safe_display_name, now),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("username already exists") from exc

            user_id = int(cursor.lastrowid)
            conn.execute(
                """
                INSERT INTO player_state (user_id, payload, updated_at)
                VALUES (?, ?, ?)
                """,
                (user_id, json.dumps(default_player_state(), separators=(",", ":")), now),
            )

        return {"id": user_id, "username": username, "display_name": safe_display_name}

    def login_user(self, username: str, password: str) -> dict[str, Any] | None:
        now = int(time.time())
        with self.connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if user is None or not verify_password(password, str(user["password_hash"])):
                return None

            token = make_token()
            expires_at = now + self.token_ttl_seconds
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, int(user["id"]), now, expires_at),
            )
            conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, int(user["id"])))

        return {
            "token": token,
            "expires_at": expires_at,
            "user": {
                "id": int(user["id"]),
                "username": str(user["username"]),
                "display_name": str(user["display_name"]),
            },
        }

    def get_user_by_token(self, token: str) -> dict[str, Any] | None:
        now = int(time.time())
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT users.id, users.username, users.display_name
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = ? AND sessions.expires_at > ?
                """,
                (token, now),
            ).fetchone()
        if row is None:
            return None
        return {"id": int(row["id"]), "username": str(row["username"]), "display_name": str(row["display_name"])}

    def get_player_state(self, user_id: int) -> dict[str, Any]:
        with self.connection() as conn:
            row = conn.execute("SELECT payload, updated_at FROM player_state WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            return default_player_state()

        payload = json.loads(str(row["payload"]))
        payload["updated_at"] = int(row["updated_at"])
        return payload

    def update_player_state(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        now = int(time.time())
        clean_payload = sanitize_player_state(payload)
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO player_state (user_id, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
                """,
                (user_id, json.dumps(clean_payload, separators=(",", ":")), now),
            )
        clean_payload["updated_at"] = now
        return clean_payload

    def create_handshake(self, handshake_id: str, server_nonce: str, ttl_seconds: int) -> None:
        now = int(time.time())
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO handshakes (handshake_id, server_nonce, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (handshake_id, server_nonce, now, now + ttl_seconds),
            )

    def authenticate_handshake(self, handshake_id: str, client_nonce: str, session_key: bytes) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE handshakes
                SET client_nonce = ?, session_key_hex = ?
                WHERE handshake_id = ? AND expires_at > ?
                """,
                (client_nonce, session_key.hex(), handshake_id, int(time.time())),
            )

    def get_handshake(self, handshake_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT handshake_id, server_nonce, client_nonce, session_key_hex, created_at, expires_at
                FROM handshakes
                WHERE handshake_id = ? AND expires_at > ?
                """,
                (handshake_id, int(time.time())),
            ).fetchone()
        if row is None:
            return None
        session_key_hex = row["session_key_hex"]
        return {
            "handshake_id": str(row["handshake_id"]),
            "server_nonce": str(row["server_nonce"]),
            "client_nonce": str(row["client_nonce"]) if row["client_nonce"] is not None else None,
            "session_key": bytes.fromhex(str(session_key_hex)) if session_key_hex else None,
            "created_at": int(row["created_at"]),
            "expires_at": int(row["expires_at"]),
        }

    def count_handshakes(self) -> dict[str, int]:
        now = int(time.time())
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN session_key_hex IS NOT NULL THEN 1 ELSE 0 END) AS authenticated
                FROM handshakes
                WHERE expires_at > ?
                """,
                (now,),
            ).fetchone()
        return {
            "total": int(row["total"] or 0),
            "authenticated": int(row["authenticated"] or 0),
        }

    def reserve_handshake_nonce(self, handshake_id: str, nonce: str) -> bool:
        try:
            with self.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO handshake_nonces (handshake_id, nonce, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (handshake_id, nonce, int(time.time())),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def cleanup_handshakes(self) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM handshakes WHERE expires_at <= ?", (int(time.time()),))


def default_player_state() -> dict[str, Any]:
    return {
        "position": {"x": 0.0, "y": 1.0, "z": 0.0},
        "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
        "inventory": [],
        "active_tasks": ["task_find_anchor"],
        "completed_tasks": [],
        "stats": {"level": 1, "xp": 0},
    }


def sanitize_player_state(payload: dict[str, Any]) -> dict[str, Any]:
    state = default_player_state()
    if isinstance(payload.get("position"), dict):
        state["position"] = _vector3(payload["position"])
    if isinstance(payload.get("rotation"), dict):
        state["rotation"] = _vector3(payload["rotation"])
    if isinstance(payload.get("inventory"), list):
        state["inventory"] = [str(item) for item in payload["inventory"][:128]]
    if isinstance(payload.get("active_tasks"), list):
        state["active_tasks"] = [str(task) for task in payload["active_tasks"][:64]]
    if isinstance(payload.get("completed_tasks"), list):
        state["completed_tasks"] = [str(task) for task in payload["completed_tasks"][:256]]
    if isinstance(payload.get("stats"), dict):
        stats = payload["stats"]
        state["stats"] = {
            "level": max(1, int(stats.get("level", 1))),
            "xp": max(0, int(stats.get("xp", 0))),
        }
    return state


def _vector3(value: dict[str, Any]) -> dict[str, float]:
    return {
        "x": float(value.get("x", 0.0)),
        "y": float(value.get("y", 0.0)),
        "z": float(value.get("z", 0.0)),
    }
