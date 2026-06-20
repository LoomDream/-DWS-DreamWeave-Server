from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    version: str
    motd: str
    environment: str
    region: str
    server_name: str


@dataclass(frozen=True)
class VersionConfig:
    minimum_client_version: str
    recommended_client_version: str
    protocol_version: str
    api_revision: str
    update_required: bool
    download_url: str
    release_notes_url: str


@dataclass(frozen=True)
class AdminConfig:
    enabled: bool
    panel_version: str
    token: str
    max_sql_rows: int


@dataclass(frozen=True)
class SecurityConfig:
    server_secret: str
    developer_secret: str
    session_token_ttl_seconds: int
    handshake_ttl_seconds: int


@dataclass(frozen=True)
class CookieConfig:
    secure: bool
    samesite: str
    domain: str
    handshake_cookie: str
    session_cookie: str


@dataclass(frozen=True)
class CorsConfig:
    enabled: bool
    allow_origins: tuple[str, ...]
    allow_origin_regex: str
    allow_credentials: bool
    allow_methods: tuple[str, ...]
    allow_headers: tuple[str, ...]
    expose_headers: tuple[str, ...]
    max_age: int


@dataclass(frozen=True)
class DatabaseConfig:
    path: Path


@dataclass(frozen=True)
class ContentConfig:
    story_file: Path
    story_dir: Path
    audio_dir: Path


@dataclass(frozen=True)
class LegalConfig:
    terms_file: Path
    privacy_file: Path
    eula_file: Path
    terms_dir: Path
    privacy_dir: Path
    eula_dir: Path
    default_language: str
    fallback_languages: tuple[str, ...]


@dataclass(frozen=True)
class StatusConfig:
    public_message: str
    maintenance: bool
    maintenance_message: str
    allow_registration: bool
    allow_login: bool
    allow_sync: bool
    allow_content_download: bool
    max_players: int
    status_components: tuple[str, ...]


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    version: VersionConfig
    admin: AdminConfig
    security: SecurityConfig
    cookies: CookieConfig
    cors: CorsConfig
    database: DatabaseConfig
    content: ContentConfig
    legal: LegalConfig
    status: StatusConfig


def load_config(path: str | Path = "config.toml") -> AppConfig:
    config_path = Path(path)
    base_dir = config_path.resolve().parent

    with config_path.open("rb") as config_file:
        raw = tomllib.load(config_file)

    server = raw.get("server", {})
    version = raw.get("version", {})
    admin = raw.get("admin", {})
    security = raw.get("security", {})
    cookies = raw.get("cookies", {})
    cors = raw.get("cors", {})
    database = raw.get("database", {})
    content = raw.get("content", {})
    legal = raw.get("legal", {})
    status = raw.get("status", {})

    environment = str(server.get("environment", "development"))
    server_secret = _env_or_config("DREAMWEAVE_SERVER_SECRET", security.get("server_secret", ""))
    developer_secret = _env_or_config("DREAMWEAVE_DEVELOPER_SECRET", security.get("developer_secret", ""))
    admin_token = _env_or_config("DREAMWEAVE_ADMIN_TOKEN", admin.get("token", ""))
    _validate_secrets(environment, server_secret, developer_secret, admin_token)

    return AppConfig(
        server=ServerConfig(
            host=str(server.get("host", "0.0.0.0")),
            port=int(server.get("port", 7777)),
            version=str(server.get("version", "0.1.2")),
            motd=str(server.get("motd", "")),
            environment=environment,
            region=str(server.get("region", "local")),
            server_name=str(server.get("server_name", "Dreamweave")),
        ),
        version=VersionConfig(
            minimum_client_version=str(version.get("minimum_client_version", "0.1.2")),
            recommended_client_version=str(version.get("recommended_client_version", "0.1.2")),
            protocol_version=str(version.get("protocol_version", "2026.06")),
            api_revision=str(version.get("api_revision", "3")),
            update_required=bool(version.get("update_required", False)),
            download_url=str(version.get("download_url", "")),
            release_notes_url=str(version.get("release_notes_url", "")),
        ),
        admin=AdminConfig(
            enabled=bool(admin.get("enabled", True)),
            panel_version=str(admin.get("panel_version", "0.1.2")),
            token=admin_token,
            max_sql_rows=int(admin.get("max_sql_rows", 200)),
        ),
        security=SecurityConfig(
            server_secret=server_secret,
            developer_secret=developer_secret,
            session_token_ttl_seconds=int(security.get("session_token_ttl_seconds", 86400)),
            handshake_ttl_seconds=int(security.get("handshake_ttl_seconds", 300)),
        ),
        cookies=CookieConfig(
            secure=bool(cookies.get("secure", False)),
            samesite=str(cookies.get("samesite", "lax")),
            domain=str(cookies.get("domain", "")),
            handshake_cookie=str(cookies.get("handshake_cookie", "dw_handshake")),
            session_cookie=str(cookies.get("session_cookie", "dw_session")),
        ),
        cors=CorsConfig(
            enabled=bool(cors.get("enabled", True)),
            allow_origins=tuple(
                str(origin)
                for origin in cors.get(
                    "allow_origins",
                    [
                        "http://localhost:3000",
                        "http://127.0.0.1:3000",
                        "http://localhost:5173",
                        "http://127.0.0.1:5173",
                        "http://localhost:7777",
                        "http://127.0.0.1:7777",
                    ],
                )
            ),
            allow_origin_regex=str(cors.get("allow_origin_regex", "")),
            allow_credentials=bool(cors.get("allow_credentials", True)),
            allow_methods=tuple(str(method) for method in cors.get("allow_methods", ["GET", "POST", "PUT", "OPTIONS"])),
            allow_headers=tuple(str(header) for header in cors.get("allow_headers", ["*"])),
            expose_headers=tuple(str(header) for header in cors.get("expose_headers", [])),
            max_age=int(cors.get("max_age", 600)),
        ),
        database=DatabaseConfig(
            path=_resolve_path(base_dir, str(database.get("path", "dreamweave.sqlite3"))),
        ),
        content=ContentConfig(
            story_file=_resolve_path(base_dir, str(content.get("story_file", "content/story.json"))),
            story_dir=_resolve_path(base_dir, str(content.get("story_dir", "story"))),
            audio_dir=_resolve_path(base_dir, str(content.get("audio_dir", "wav/story"))),
        ),
        legal=LegalConfig(
            terms_file=_resolve_path(base_dir, str(legal.get("terms_file", "content/legal/terms.md"))),
            privacy_file=_resolve_path(base_dir, str(legal.get("privacy_file", "content/legal/privacy.md"))),
            eula_file=_resolve_path(base_dir, str(legal.get("eula_file", "content/legal/eula.md"))),
            terms_dir=_resolve_path(base_dir, str(legal.get("terms_dir", "content/legal/terms"))),
            privacy_dir=_resolve_path(base_dir, str(legal.get("privacy_dir", "content/legal/privacy"))),
            eula_dir=_resolve_path(base_dir, str(legal.get("eula_dir", "content/legal/eula"))),
            default_language=str(legal.get("default_language", "zh-CN")),
            fallback_languages=tuple(str(lang) for lang in legal.get("fallback_languages", ["zh-CN", "en-US", "ja-JP", "ru-RU"])),
        ),
        status=StatusConfig(
            public_message=str(status.get("public_message", "")),
            maintenance=bool(status.get("maintenance", False)),
            maintenance_message=str(status.get("maintenance_message", "")),
            allow_registration=bool(status.get("allow_registration", True)),
            allow_login=bool(status.get("allow_login", True)),
            allow_sync=bool(status.get("allow_sync", True)),
            allow_content_download=bool(status.get("allow_content_download", True)),
            max_players=int(status.get("max_players", 0)),
            status_components=tuple(str(component) for component in status.get("status_components", [])),
        ),
    )


def _resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base_dir / path


def _env_or_config(env_name: str, config_value: object) -> str:
    env_value = os.getenv(env_name)
    if env_value is not None:
        return env_value
    return str(config_value)


def _validate_secrets(environment: str, server_secret: str, developer_secret: str, admin_token: str) -> None:
    if environment.lower() in {"development", "local", "dev"}:
        return

    sample_values = {
        "",
        "change-me-dreamweave-server-secret",
        "change-me-dreamweave-developer-secret",
        "change-me-dreamweave-admin-token",
    }
    if server_secret in sample_values or developer_secret in sample_values or admin_token in sample_values:
        raise ValueError(
            "DREAMWEAVE_SERVER_SECRET, DREAMWEAVE_DEVELOPER_SECRET, and DREAMWEAVE_ADMIN_TOKEN must be set "
            "to non-sample values outside development."
        )
