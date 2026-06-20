from __future__ import annotations

import json
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


class StorySaveRequest(BaseModel):
    content: dict[str, Any]


class SqlQueryRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=5000)


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
        def endpoints(_: None = Depends(self.require_admin)) -> dict[str, Any]:
            return {"ok": True, "payload": {"endpoints": self.endpoints()}}

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
                    "md5": md5_hex(raw),
                    "content": content,
                },
            }

        @router.post("/admin/api/story")
        def save_story(request: StorySaveRequest, _: None = Depends(self.require_admin)) -> dict[str, Any]:
            self.config.content.story_file.parent.mkdir(parents=True, exist_ok=True)
            self.config.content.story_file.write_text(
                json.dumps(request.content, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return {"ok": True, "payload": {"saved": True, "path": str(self.config.content.story_file)}}

        @router.get("/admin/api/sql/tables")
        def tables(_: None = Depends(self.require_admin)) -> dict[str, Any]:
            return {"ok": True, "payload": {"tables": self.database.list_tables()}}

        @router.post("/admin/api/sql/query")
        def sql_query(request: SqlQueryRequest, _: None = Depends(self.require_admin)) -> dict[str, Any]:
            try:
                result = self.database.query_readonly(request.sql, self.config.admin.max_sql_rows)
            except ValueError as exc:
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
        }

    @staticmethod
    def endpoints() -> list[dict[str, str]]:
        return [
            {"method": "GET", "path": "/api/version", "auth": "client"},
            {"method": "GET", "path": "/api/status", "auth": "client"},
            {"method": "POST", "path": "/api/hello", "auth": "public"},
            {"method": "POST", "path": "/api/register", "auth": "client"},
            {"method": "POST", "path": "/api/login", "auth": "client"},
            {"method": "POST", "path": "/api/sync/get", "auth": "client+session"},
            {"method": "POST", "path": "/api/sync/update", "auth": "client+session"},
            {"method": "POST", "path": "/api/content/story", "auth": "client"},
            {"method": "POST", "path": "/api/content/ack", "auth": "client"},
            {"method": "GET", "path": "/api/legal/terms", "auth": "client"},
            {"method": "GET", "path": "/api/legal/privacy", "auth": "client"},
            {"method": "GET", "path": "/admin", "auth": "public page"},
            {"method": "POST", "path": "/admin/api/auth", "auth": "admin token"},
            {"method": "GET", "path": "/admin/api/meta", "auth": "admin token"},
            {"method": "GET", "path": "/admin/api/endpoints", "auth": "admin token"},
            {"method": "GET", "path": "/admin/api/logs", "auth": "admin token"},
            {"method": "GET", "path": "/admin/api/story", "auth": "admin token"},
            {"method": "POST", "path": "/admin/api/story", "auth": "admin token"},
            {"method": "GET", "path": "/admin/api/sql/tables", "auth": "admin token"},
            {"method": "POST", "path": "/admin/api/sql/query", "auth": "admin token"},
        ]
