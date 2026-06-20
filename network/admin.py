from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .config import AppConfig
from .content import ContentStore
from .crypto import constant_time_equal, md5_hex
from .db import Database


class AdminAuthRequest(BaseModel):
    token: str


class LegacyStorySaveRequest(BaseModel):
    content: dict[str, Any]


class StoryCreateRequest(BaseModel):
    chapter: int = Field(ge=1)
    act: int = Field(ge=1)
    chapter_title: str = Field(default="", max_length=120)
    scene_title: str = Field(default="", max_length=120)


class StorySceneSaveRequest(BaseModel):
    content: dict[str, Any]


class SqlQueryRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=20000)
    write: bool = False


class AdminPanel:
    def __init__(self, config: AppConfig, database: Database, content: ContentStore) -> None:
        self.config = config
        self.database = database
        self.content = content
        self.ui_path = Path(__file__).resolve().parent.parent / "admin_ui" / "index.html"

    def router(self) -> APIRouter:
        router = APIRouter(include_in_schema=False)

        @router.get("/admin", response_class=HTMLResponse)
        def admin_page() -> str:
            if not self.config.admin.enabled:
                raise HTTPException(status_code=404, detail="admin panel is disabled")
            return self.ui_path.read_text(encoding="utf-8")

        @router.post("/admin/api/auth")
        def auth(request: AdminAuthRequest) -> dict[str, Any]:
            self.require_token_value(request.token)
            return {"ok": True, "payload": self.panel_meta()}

        @router.get("/admin/api/meta")
        def meta(_: None = Depends(self.require_admin)) -> dict[str, Any]:
            return {"ok": True, "payload": self.panel_meta()}

        @router.get("/admin/api/endpoints")
        def endpoints(lang: str = "zh-CN", _: None = Depends(self.require_admin)) -> dict[str, Any]:
            language = normalize_language(lang)
            return {"ok": True, "payload": {"language": language, "endpoints": self.endpoints(language)}}

        @router.get("/admin/api/logs")
        def logs(limit: int = 100, _: None = Depends(self.require_admin)) -> dict[str, Any]:
            return {"ok": True, "payload": {"logs": self.database.list_call_logs(limit)}}

        @router.get("/admin/api/story")
        def story(_: None = Depends(self.require_admin)) -> dict[str, Any]:
            content = self.content.load_story()
            raw = json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            return {
                "ok": True,
                "payload": {
                    "path": str(self.config.content.story_file),
                    "story_dir": str(self.config.content.story_dir),
                    "md5": md5_hex(raw),
                    "content": content,
                },
            }

        @router.post("/admin/api/story")
        def save_story(request: LegacyStorySaveRequest, _: None = Depends(self.require_admin)) -> dict[str, Any]:
            self.config.content.story_file.parent.mkdir(parents=True, exist_ok=True)
            self.config.content.story_file.write_text(
                json.dumps(request.content, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return {"ok": True, "payload": {"saved": True, "path": str(self.config.content.story_file)}}

        @router.get("/admin/api/story/scenes")
        def story_scenes(_: None = Depends(self.require_admin)) -> dict[str, Any]:
            return {
                "ok": True,
                "payload": {
                    "story_dir": str(self.config.content.story_dir),
                    "scenes": self.content.list_story_scenes(),
                },
            }

        @router.post("/admin/api/story/scenes")
        def create_story_scene(request: StoryCreateRequest, _: None = Depends(self.require_admin)) -> dict[str, Any]:
            try:
                scene = self.content.create_story_scene(
                    request.chapter,
                    request.act,
                    request.chapter_title or f"Chapter {request.chapter}",
                    request.scene_title or f"Scene {request.act}",
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return {"ok": True, "payload": scene}

        @router.get("/admin/api/story/scenes/{filename}")
        def read_story_scene(filename: str, _: None = Depends(self.require_admin)) -> dict[str, Any]:
            try:
                content = self.content.read_story_scene(filename)
                path = self.content.story_path(filename)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            raw = json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            return {
                "ok": True,
                "payload": {
                    "file": path.name,
                    "path": str(path),
                    "md5": md5_hex(raw),
                    "content": content,
                },
            }

        @router.put("/admin/api/story/scenes/{filename}")
        def save_story_scene(filename: str, request: StorySceneSaveRequest, _: None = Depends(self.require_admin)) -> dict[str, Any]:
            try:
                scene = self.content.save_story_scene(filename, request.content)
            except (OSError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return {"ok": True, "payload": scene}

        @router.get("/admin/api/sql/tables")
        def tables(_: None = Depends(self.require_admin)) -> dict[str, Any]:
            return {"ok": True, "payload": {"tables": self.database.list_tables()}}

        @router.get("/admin/api/sql/tables/{table}/schema")
        def table_schema(table: str, _: None = Depends(self.require_admin)) -> dict[str, Any]:
            try:
                return {"ok": True, "payload": self.database.table_schema(table)}
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        @router.get("/admin/api/sql/tables/{table}/rows")
        def table_rows(table: str, limit: int = 100, offset: int = 0, _: None = Depends(self.require_admin)) -> dict[str, Any]:
            try:
                return {"ok": True, "payload": self.database.table_rows(table, limit, offset)}
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        @router.post("/admin/api/sql/query")
        def sql_query(request: SqlQueryRequest, _: None = Depends(self.require_admin)) -> dict[str, Any]:
            try:
                if request.write:
                    result = self.database.execute_admin_sql(request.sql, self.config.admin.max_sql_rows)
                else:
                    result = self.database.query_readonly(request.sql, self.config.admin.max_sql_rows)
            except (ValueError, sqlite3.Error) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return {"ok": True, "payload": result}

        return router

    def require_admin(self, request: Request) -> None:
        if not self.config.admin.enabled:
            raise HTTPException(status_code=404, detail="admin panel is disabled")
        token = request.headers.get("X-Admin-Token") or request.cookies.get("dw_admin_token")
        if not token:
            auth = request.headers.get("Authorization", "")
            if auth.lower().startswith("bearer "):
                token = auth[7:]
        self.require_token_value(token)

    def require_token_value(self, token: str | None) -> None:
        if not token or not constant_time_equal(token, self.config.admin.token):
            raise HTTPException(status_code=401, detail="invalid admin token")

    def panel_meta(self) -> dict[str, Any]:
        return {
            "panel_version": self.config.admin.panel_version,
            "api_version": self.config.version.api_revision,
            "server_version": self.config.server.version,
            "protocol_version": self.config.version.protocol_version,
            "environment": self.config.server.environment,
            "region": self.config.server.region,
            "server_name": self.config.server.server_name,
            "database": str(self.config.database.path),
            "story_dir": str(self.config.content.story_dir),
        }

    @staticmethod
    def endpoints(lang: str = "zh-CN") -> list[dict[str, Any]]:
        descriptions = endpoint_descriptions(normalize_language(lang))
        return [
            endpoint("GET", "/api/version", "client", descriptions["api_version"]),
            endpoint("GET", "/api/status", "client", descriptions["api_status"]),
            endpoint("POST", "/api/hello", "public/client handshake", descriptions["api_hello"]),
            endpoint("POST", "/api/register", "client", descriptions["api_register"]),
            endpoint("POST", "/api/login", "client", descriptions["api_login"]),
            endpoint("POST", "/api/sync/get", "client+session", descriptions["api_sync_get"]),
            endpoint("POST", "/api/sync/update", "client+session", descriptions["api_sync_update"]),
            endpoint("POST", "/api/content/story", "client", descriptions["api_content_story"]),
            endpoint("GET", "/api/content/audio", "client", descriptions["api_content_audio"]),
            endpoint("GET", "/api/content/audio/{filename}", "client", descriptions["api_content_audio_file"]),
            endpoint("POST", "/api/content/ack", "client", descriptions["api_content_ack"]),
            endpoint("GET", "/api/legal/terms", "client", descriptions["api_terms"]),
            endpoint("GET", "/api/legal/privacy", "client", descriptions["api_privacy"]),
            endpoint("GET", "/admin", "public page", descriptions["admin_page"]),
            endpoint("POST", "/admin/api/auth", "admin token", descriptions["admin_auth"]),
            endpoint("GET", "/admin/api/meta", "admin token", descriptions["admin_meta"]),
            endpoint("GET", "/admin/api/endpoints", "admin token", descriptions["admin_endpoints"]),
            endpoint("GET", "/admin/api/logs", "admin token", descriptions["admin_logs"]),
            endpoint("GET", "/admin/api/story", "admin token", descriptions["admin_story_get"]),
            endpoint("POST", "/admin/api/story", "admin token", descriptions["admin_story_post"]),
            endpoint("GET", "/admin/api/story/scenes", "admin token", descriptions["admin_scenes"]),
            endpoint("POST", "/admin/api/story/scenes", "admin token", descriptions["admin_scenes_post"]),
            endpoint("GET", "/admin/api/story/scenes/{filename}", "admin token", descriptions["admin_scene_get"]),
            endpoint("PUT", "/admin/api/story/scenes/{filename}", "admin token", descriptions["admin_scene_put"]),
            endpoint("GET", "/admin/api/sql/tables", "admin token", descriptions["admin_sql_tables"]),
            endpoint("GET", "/admin/api/sql/tables/{table}/schema", "admin token", descriptions["admin_sql_schema"]),
            endpoint("GET", "/admin/api/sql/tables/{table}/rows", "admin token", descriptions["admin_sql_rows"]),
            endpoint("POST", "/admin/api/sql/query", "admin token", descriptions["admin_sql_query"]),
        ]


def endpoint(method: str, path: str, auth: str, description: str) -> dict[str, Any]:
    return {
        "method": method,
        "path": path,
        "auth": auth,
        "description": description,
    }


def normalize_language(value: str) -> str:
    aliases = {
        "zh": "zh-CN",
        "zh-cn": "zh-CN",
        "cn": "zh-CN",
        "en": "en-US",
        "en-us": "en-US",
        "ja": "ja-JP",
        "ja-jp": "ja-JP",
        "jp": "ja-JP",
        "ru": "ru-RU",
        "ru-ru": "ru-RU",
    }
    return aliases.get(value.strip().lower(), value.strip() or "zh-CN")


def endpoint_descriptions(lang: str) -> dict[str, str]:
    zh = {
        "api_version": "Returns server version, protocol version, API revision, and update metadata.",
        "api_status": "Returns server health, component status, database status, and content path status.",
        "api_hello": "Creates a handshake or completes mutual client authentication with client proof.",
        "api_register": "Registers a user and initializes player state.",
        "api_login": "Logs in a user, returns a session token, and writes the session cookie.",
        "api_sync_get": "Reads player sync state.",
        "api_sync_update": "Updates player position, rotation, inventory, tasks, and base stats.",
        "api_content_story": "Returns the encrypted story collection and developer proof.",
        "api_content_audio": "Lists story audio files under wav/story.",
        "api_content_audio_file": "Streams one WAV story audio file from wav/story.",
        "api_content_ack": "Accepts client MD5 proof for story content confirmation.",
        "api_terms": "Returns Terms of Service Markdown; supports the lang parameter.",
        "api_privacy": "Returns Privacy Policy Markdown; supports the lang parameter.",
        "admin_page": "Admin panel page.",
        "admin_auth": "Validates the admin token.",
        "admin_meta": "Returns panel, API, server, and protocol versions.",
        "admin_endpoints": "Returns available endpoints and descriptions; supports the lang parameter.",
        "admin_logs": "Shows API and admin API call logs.",
        "admin_story_get": "Compatibility endpoint for current story collection or legacy story file.",
        "admin_story_post": "Compatibility endpoint for saving the legacy story file.",
        "admin_scenes": "Lists multi-scene story files under ./story.",
        "admin_scenes_post": "Creates ./story/<chapter>-<act>.json.",
        "admin_scene_get": "Reads a selected story JSON file.",
        "admin_scene_put": "Saves a selected story JSON file.",
        "admin_sql_tables": "Lists SQLite tables.",
        "admin_sql_schema": "Shows table columns, indexes, foreign keys, and row count.",
        "admin_sql_rows": "Shows paginated table rows.",
        "admin_sql_query": "Runs SQL. Read-only by default; write=true allows one write statement.",
    }
    # Endpoint descriptions currently use English as a stable fallback for all languages.
    # The admin UI shell remains Chinese-first and can request localized endpoint data later.
    return zh
