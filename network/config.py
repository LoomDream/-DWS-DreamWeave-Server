from __future__ import annotations

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
class DatabaseConfig:
    path: Path


@dataclass(frozen=True)
class ContentConfig:
    story_file: Path


@dataclass(frozen=True)
class LegalConfig:
    terms_file: Path
    privacy_file: Path


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
    security: SecurityConfig
    cookies: CookieConfig
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
    security = raw.get("security", {})
    cookies = raw.get("cookies", {})
    database = raw.get("database", {})
    content = raw.get("content", {})
    legal = raw.get("legal", {})
    status = raw.get("status", {})

    return AppConfig(
        server=ServerConfig(
            host=str(server.get("host", "0.0.0.0")),
            port=int(server.get("port", 7777)),
            version=str(server.get("version", "0.1.0")),
            motd=str(server.get("motd", "")),
            environment=str(server.get("environment", "development")),
            region=str(server.get("region", "local")),
            server_name=str(server.get("server_name", "Dreamweave")),
        ),
        version=VersionConfig(
            minimum_client_version=str(version.get("minimum_client_version", "0.1.0")),
            recommended_client_version=str(version.get("recommended_client_version", "0.1.0")),
            protocol_version=str(version.get("protocol_version", "2026.06")),
            api_revision=str(version.get("api_revision", "1")),
            update_required=bool(version.get("update_required", False)),
            download_url=str(version.get("download_url", "")),
            release_notes_url=str(version.get("release_notes_url", "")),
        ),
        security=SecurityConfig(
            server_secret=str(security.get("server_secret", "")),
            developer_secret=str(security.get("developer_secret", "")),
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
        database=DatabaseConfig(
            path=_resolve_path(base_dir, str(database.get("path", "dreamweave.sqlite3"))),
        ),
        content=ContentConfig(
            story_file=_resolve_path(base_dir, str(content.get("story_file", "content/story.json"))),
        ),
        legal=LegalConfig(
            terms_file=_resolve_path(base_dir, str(legal.get("terms_file", "content/legal/terms.md"))),
            privacy_file=_resolve_path(base_dir, str(legal.get("privacy_file", "content/legal/privacy.md"))),
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
