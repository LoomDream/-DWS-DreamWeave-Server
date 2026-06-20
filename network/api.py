from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .admin import AdminPanel
from .config import AppConfig
from .content import ContentStore
from .docs_ui import docs_page
from .crypto import (
    client_proof,
    constant_time_equal,
    developer_proof,
    make_session_key,
    md5_hex,
    new_nonce,
    request_proof,
    server_proof,
)
from .db import Database


class HelloRequest(BaseModel):
    handshake_id: str | None = None
    client_nonce: str | None = None
    client_key: str | None = None


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=256)
    display_name: str | None = Field(default=None, max_length=32)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenRequest(BaseModel):
    token: str | None = None


class SyncUpdateRequest(TokenRequest):
    state: dict[str, Any]


class StoryRequest(BaseModel):
    pass


class ContentAckRequest(BaseModel):
    md5: str
    client_key: str


class DreamweaveApi:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.database = Database(config.database.path, config.security.session_token_ttl_seconds)
        self.content = ContentStore(
            config.content.story_file,
            config.content.story_dir,
            config.content.audio_dir,
            config.security.developer_secret,
        )
        self.started_at = int(time.time())

    def app(self) -> FastAPI:
        app = FastAPI(
            title="Dreamweave Server",
            version=self.config.server.version,
            docs_url="/swagger",
            redoc_url="/redoc",
        )

        @app.on_event("startup")
        def startup() -> None:
            self.database.initialize()

        @app.middleware("http")
        async def client_auth_middleware(request: Request, call_next: Any) -> Any:
            started = time.perf_counter()
            if not self.needs_client_auth(request):
                response = await call_next(request)
                self.record_call(request, response.status_code, started)
                return response

            try:
                await self.authenticate_request(request)
            except HTTPException as exc:
                response = JSONResponse(
                    status_code=exc.status_code,
                    content={"ok": False, "route": request.url.path.removeprefix("/"), "error": {"message": exc.detail}},
                )
                self.record_call(request, response.status_code, started)
                return response
            response = await call_next(request)
            self.record_call(request, response.status_code, started)
            return response

        @app.get("/docs", include_in_schema=False)
        def localized_docs(lang: str | None = None) -> Response:
            return Response(content=docs_page(self.config, lang), media_type="text/html; charset=utf-8")

        @app.get("/api/version")
        def version() -> dict[str, Any]:
            return self.ok(
                "api/version",
                {
                    "server_version": self.config.server.version,
                    "minimum_client_version": self.config.version.minimum_client_version,
                    "recommended_client_version": self.config.version.recommended_client_version,
                    "protocol_version": self.config.version.protocol_version,
                    "api_revision": self.config.version.api_revision,
                    "update_required": self.config.version.update_required,
                    "download_url": self.config.version.download_url,
                    "release_notes_url": self.config.version.release_notes_url,
                    "server_name": self.config.server.server_name,
                    "environment": self.config.server.environment,
                    "region": self.config.server.region,
                    "motd": self.config.server.motd,
                },
            )

        @app.get("/api/status")
        def status() -> dict[str, Any]:
            self.cleanup_handshakes()
            handshake_counts = self.database.count_handshakes()
            authenticated_handshakes = handshake_counts["authenticated"]
            database_ok = self.check_database()
            story_scene_count = len(self.content.list_story_scenes()) if self.config.content.story_dir.exists() else 0
            story_exists = self.config.content.story_file.exists()
            story_content_ok = story_exists or story_scene_count > 0
            legal_terms_exists = self.config.legal.terms_file.exists()
            legal_privacy_exists = self.config.legal.privacy_file.exists()
            degraded = not database_ok or not story_content_ok or not legal_terms_exists or not legal_privacy_exists
            return self.ok(
                "api/status",
                {
                    "status": "maintenance" if self.config.status.maintenance else "degraded" if degraded else "ok",
                    "public_message": self.config.status.public_message,
                    "maintenance": self.config.status.maintenance,
                    "maintenance_message": self.config.status.maintenance_message,
                    "server_version": self.config.server.version,
                    "protocol_version": self.config.version.protocol_version,
                    "api_revision": self.config.version.api_revision,
                    "server_name": self.config.server.server_name,
                    "environment": self.config.server.environment,
                    "region": self.config.server.region,
                    "server_time": int(time.time()),
                    "uptime_seconds": max(0, int(time.time()) - self.started_at),
                    "features": {
                        "registration": self.config.status.allow_registration,
                        "login": self.config.status.allow_login,
                        "sync": self.config.status.allow_sync,
                        "content_download": self.config.status.allow_content_download,
                    },
                    "capacity": {
                        "max_players": self.config.status.max_players,
                    },
                    "configured_components": list(self.config.status.status_components),
                    "components": {
                        "api": {"ok": True},
                        "auth": {"ok": True, "active_handshakes": authenticated_handshakes},
                        "database": {"ok": database_ok},
                        "content": {"ok": story_content_ok, "scene_count": story_scene_count},
                        "legal": {"ok": legal_terms_exists and legal_privacy_exists},
                    },
                    "database": {
                        "ok": database_ok,
                        "path": str(self.config.database.path),
                    },
                    "content": {
                        "story_file_exists": story_exists,
                        "story_file": str(self.config.content.story_file),
                        "story_dir": str(self.config.content.story_dir),
                        "story_scene_count": story_scene_count,
                        "audio_dir": str(self.config.content.audio_dir),
                        "story_audio_count": len(self.content.list_story_audio())
                    },
                    "legal": {
                        "terms_file_exists": legal_terms_exists,
                        "privacy_file_exists": legal_privacy_exists,
                    },
                    "handshakes": {
                        "total": handshake_counts["total"],
                        "authenticated": authenticated_handshakes,
                    },
                },
            )

        @app.get("/api/legal/terms")
        def legal_terms(lang: str | None = None) -> dict[str, Any]:
            return self.legal_document("api/legal/terms", "terms", lang)

        @app.get("/api/legal/privacy")
        def legal_privacy(lang: str | None = None) -> dict[str, Any]:
            return self.legal_document("api/legal/privacy", "privacy", lang)

        @app.post("/api/hello")
        def hello(request: HelloRequest, response: Response) -> dict[str, Any]:
            self.cleanup_handshakes()
            if request.handshake_id is None:
                handshake_id = new_nonce()
                server_nonce = new_nonce()
                self.database.create_handshake(
                    handshake_id,
                    server_nonce,
                    self.config.security.handshake_ttl_seconds,
                )
                self.set_cookie(
                    response,
                    self.config.cookies.handshake_cookie,
                    handshake_id,
                    max_age=self.config.security.handshake_ttl_seconds,
                    httponly=False,
                )
                return self.ok(
                    "api/hello",
                    {
                        "handshake_id": handshake_id,
                        "server_nonce": server_nonce,
                        "server_key": server_proof(self.config.security.server_secret, server_nonce),
                        "version": self.config.server.version,
                        "motd": self.config.server.motd,
                    },
                )

            session = self.require_handshake(request.handshake_id)
            if not request.client_nonce or not request.client_key:
                raise HTTPException(status_code=400, detail="client_nonce and client_key are required")

            expected = client_proof(
                self.config.security.server_secret,
                session["server_nonce"],
                request.client_nonce,
            )
            if not constant_time_equal(request.client_key, expected):
                raise HTTPException(status_code=401, detail="client key check failed")

            session_key = make_session_key(
                self.config.security.server_secret,
                session["server_nonce"],
                request.client_nonce,
            )
            self.database.authenticate_handshake(request.handshake_id, request.client_nonce, session_key)
            self.set_cookie(
                response,
                self.config.cookies.handshake_cookie,
                request.handshake_id,
                max_age=self.config.security.handshake_ttl_seconds,
                httponly=False,
            )
            return self.ok(
                "api/hello",
                {
                    "handshake_id": request.handshake_id,
                    "authenticated": True,
                    "encryption": "xor-sha256-session-key",
                },
            )

        @app.post("/api/register")
        def register(request: RegisterRequest) -> dict[str, Any]:
            if not self.config.status.allow_registration:
                raise HTTPException(status_code=503, detail="registration is disabled")
            try:
                user = self.database.register_user(request.username, request.password, request.display_name)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            return self.ok("api/register", {"user": user})

        @app.post("/api/login")
        def login(request: LoginRequest, response: Response) -> dict[str, Any]:
            if not self.config.status.allow_login:
                raise HTTPException(status_code=503, detail="login is disabled")
            result = self.database.login_user(request.username, request.password)
            if result is None:
                raise HTTPException(status_code=401, detail="username or password is invalid")
            self.set_cookie(
                response,
                self.config.cookies.session_cookie,
                str(result["token"]),
                max_age=self.config.security.session_token_ttl_seconds,
                httponly=True,
            )
            return self.ok("api/login", result)

        @app.post("/api/sync/get")
        def sync_get(request: TokenRequest, http_request: Request) -> dict[str, Any]:
            if not self.config.status.allow_sync:
                raise HTTPException(status_code=503, detail="sync is disabled")
            user = self.require_user(self.request_token(http_request, request.token))
            state = self.database.get_player_state(int(user["id"]))
            return self.ok("api/sync/get", {"state": state})

        @app.post("/api/sync/update")
        def sync_update(request: SyncUpdateRequest, http_request: Request) -> dict[str, Any]:
            if not self.config.status.allow_sync:
                raise HTTPException(status_code=503, detail="sync is disabled")
            user = self.require_user(self.request_token(http_request, request.token))
            state = self.database.update_player_state(int(user["id"]), request.state)
            return self.ok("api/sync/update", {"state": state})

        @app.post("/api/content/story")
        def content_story(request: StoryRequest, http_request: Request) -> dict[str, Any]:
            if not self.config.status.allow_content_download:
                raise HTTPException(status_code=503, detail="content download is disabled")
            session = self.authenticated_session(http_request)
            package = self.content.encrypted_story_package(session["session_key"])
            return self.ok("api/content/story", package)

        @app.get("/api/content/audio")
        def content_audio_list() -> dict[str, Any]:
            if not self.config.status.allow_content_download:
                raise HTTPException(status_code=503, detail="content download is disabled")
            return self.ok(
                "api/content/audio",
                {
                    "audio_dir": str(self.config.content.audio_dir),
                    "files": self.content.list_story_audio(),
                },
            )

        @app.get("/api/content/audio/{filename}")
        def content_audio_stream(filename: str) -> FileResponse:
            if not self.config.status.allow_content_download:
                raise HTTPException(status_code=503, detail="content download is disabled")
            try:
                path = self.content.audio_path(filename)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if not path.exists():
                raise HTTPException(status_code=404, detail="audio file does not exist")
            return FileResponse(path, media_type="audio/wav", filename=path.name)

        @app.post("/api/content/ack")
        def content_ack(request: ContentAckRequest, http_request: Request) -> dict[str, Any]:
            session = self.authenticated_session(http_request)
            expected = developer_proof(self.config.security.developer_secret, session["session_key"], request.md5)
            if not constant_time_equal(request.client_key, expected):
                raise HTTPException(status_code=401, detail="developer key check failed")
            return self.ok("api/content/ack", {"verified": True})

        app.include_router(AdminPanel(self.config, self.database, self.content).router())
        return app

    def require_user(self, token: str) -> dict[str, Any]:
        user = self.database.get_user_by_token(token)
        if user is None:
            raise HTTPException(status_code=401, detail="token is invalid or expired")
        return user

    def request_token(self, request: Request, fallback_token: str | None = None) -> str:
        token = request.cookies.get(self.config.cookies.session_cookie) or fallback_token
        if not token:
            raise HTTPException(status_code=401, detail="login token is required")
        return token

    def require_handshake(self, handshake_id: str) -> dict[str, Any]:
        session = self.database.get_handshake(handshake_id)
        if session is None:
            raise HTTPException(status_code=404, detail="handshake does not exist or expired")
        return session

    def require_authenticated_handshake(self, handshake_id: str) -> dict[str, Any]:
        session = self.require_handshake(handshake_id)
        if session["session_key"] is None:
            raise HTTPException(status_code=401, detail="handshake is not authenticated")
        return session

    def authenticated_session(self, request: Request) -> dict[str, Any]:
        session = getattr(request.state, "handshake_session", None)
        if session is None or session["session_key"] is None:
            raise HTTPException(status_code=401, detail="client authentication is required")
        return session

    def needs_client_auth(self, request: Request) -> bool:
        path = request.url.path
        if not path.startswith("/api/"):
            return False
        return path != "/api/hello"

    async def authenticate_request(self, request: Request) -> None:
        header_handshake_id = request.headers.get("X-Dreamweave-Handshake")
        cookie_handshake_id = request.cookies.get(self.config.cookies.handshake_cookie)
        handshake_id = header_handshake_id or cookie_handshake_id
        timestamp = request.headers.get("X-Dreamweave-Timestamp")
        nonce = request.headers.get("X-Dreamweave-Nonce")
        client_key = request.headers.get("X-Dreamweave-Key")
        if not handshake_id or not timestamp or not nonce or not client_key:
            raise HTTPException(status_code=401, detail="missing client authentication headers")

        session = self.require_authenticated_handshake(handshake_id)
        now = int(time.time())
        try:
            request_time = int(timestamp)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="timestamp must be an integer") from exc
        if abs(now - request_time) > 300:
            raise HTTPException(status_code=401, detail="timestamp is outside the allowed window")

        if not self.database.reserve_handshake_nonce(handshake_id, nonce):
            raise HTTPException(status_code=401, detail="request nonce has already been used")

        body = await request.body()
        expected = request_proof(
            self.config.security.server_secret,
            session["session_key"],
            handshake_id,
            request.method,
            request.url.path,
            md5_hex(body),
            timestamp,
            nonce,
        )
        if not constant_time_equal(client_key, expected):
            raise HTTPException(status_code=401, detail="client request key check failed")

        request.state.handshake_id = handshake_id
        request.state.handshake_session = session

    def cleanup_handshakes(self) -> None:
        self.database.cleanup_handshakes()

    def record_call(self, request: Request, status_code: int, started: float) -> None:
        path = request.url.path
        if path == "/admin/api/logs":
            return
        if not (path.startswith("/api/") or path.startswith("/admin/api/")):
            return
        client_host = request.client.host if request.client else ""
        user_agent = request.headers.get("user-agent", "")
        try:
            self.database.record_call_log(
                route=path,
                method=request.method,
                status_code=status_code,
                ok=200 <= status_code < 400,
                duration_ms=(time.perf_counter() - started) * 1000,
                client_host=client_host,
                user_agent=user_agent,
            )
        except Exception:
            pass

    def check_database(self) -> bool:
        try:
            with self.database.connection() as conn:
                conn.execute("SELECT 1").fetchone()
        except Exception:
            return False
        return True

    def legal_document(self, route: str, kind: str, lang: str | None) -> dict[str, Any]:
        path, language = self.resolve_legal_document(kind, lang)
        if not path.exists():
            raise HTTPException(status_code=404, detail="legal document does not exist")
        text = path.read_text(encoding="utf-8")
        return self.ok(
            route,
            {
                "format": "markdown",
                "language": language,
                "available_languages": list(self.config.legal.fallback_languages),
                "path": str(path),
                "updated_at": int(path.stat().st_mtime),
                "content": text,
            },
        )

    def resolve_legal_document(self, kind: str, lang: str | None) -> tuple[Any, str]:
        directory = self.config.legal.terms_dir if kind == "terms" else self.config.legal.privacy_dir
        legacy_path = self.config.legal.terms_file if kind == "terms" else self.config.legal.privacy_file
        requested = normalize_language(lang or self.config.legal.default_language)
        candidates = [requested]
        candidates.extend(normalize_language(item) for item in self.config.legal.fallback_languages)
        for language in dict.fromkeys(candidates):
            path = directory / f"{language}.md"
            if path.exists():
                return path, language
        return legacy_path, self.config.legal.default_language

    def set_cookie(self, response: Response, key: str, value: str, max_age: int, httponly: bool) -> None:
        response.set_cookie(
            key=key,
            value=value,
            max_age=max_age,
            httponly=httponly,
            secure=self.config.cookies.secure,
            samesite=self.config.cookies.samesite,
            domain=self.config.cookies.domain or None,
        )

    @staticmethod
    def ok(route: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "route": route, "payload": payload}

def create_app(config: AppConfig) -> FastAPI:
    return DreamweaveApi(config).app()


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
