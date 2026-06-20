# Dreamweave Server Dev Notes

## Runtime

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start the server:

```powershell
python main.py
```

The server reads `config.toml` for host, port, version, SQLite path, content path, and shared secrets.

Outside development/local environments, startup rejects empty or sample secrets. Secrets can be provided through environment variables:

```text
DREAMWEAVE_SERVER_SECRET
DREAMWEAVE_DEVELOPER_SECRET
DREAMWEAVE_ADMIN_TOKEN
```

## Admin Panel

Entry point:

```text
GET /admin
```

Admin APIs accept `X-Admin-Token`, `Authorization: Bearer <token>`, or the `dw_admin_token` cookie.

Available admin endpoints:

```text
POST /admin/api/auth
GET  /admin/api/meta
GET  /admin/api/endpoints
GET  /admin/api/logs
GET  /admin/api/story
POST /admin/api/story
GET  /admin/api/story/scenes
POST /admin/api/story/scenes
GET  /admin/api/story/scenes/{filename}
PUT  /admin/api/story/scenes/{filename}
GET  /admin/api/sql/tables
GET  /admin/api/sql/tables/{table}/schema
GET  /admin/api/sql/tables/{table}/rows
POST /admin/api/sql/query
```

`/admin/api/sql/query` defaults to read-only statements: `SELECT`, `WITH`, `PRAGMA`. Set `write=true` to run one write statement. Multi-statement SQL is rejected. Maximum returned rows are controlled by `admin.max_sql_rows` in `config.toml`.

The panel also includes endpoint details/testing, call logs, visual table/schema browsing, paginated table rows, and multi-scene story editing.

## Multi-Scene Story Files

Story directory:

```toml
[content]
story_file = "content/story.json"
story_dir = "story"
audio_dir = "wav/story"
seed_dir = "seed/map"
```

Files use this pattern:

```text
./story/<chapter>-<act>.json
```

Example JSON:

```json
{
  "meta": {
    "chapter": 1,
    "act": 1,
    "chapter_title": "Chapter One",
    "scene_title": "Scene One"
  },
  "characters": [],
  "backgrounds": [],
  "audio": [
    {
      "id": "intro_bgm",
      "kind": "bgm",
      "file": "chapter1_act1_bgm.wav",
      "url": "/api/content/audio/chapter1_act1_bgm.wav",
      "loop": true,
      "volume": 0.75
    }
  ],
  "dialogues": [],
  "tasks": []
}
```

When `story_dir` exists and contains scene JSON files, `POST /api/content/story` returns a collection. Otherwise it falls back to `story_file`.

## Story Audio

Story audio files live in:

```text
wav/story/
```

Story JSON references audio through the `audio` array:

```json
{
  "audio": [
    {
      "id": "luna_intro_voice",
      "kind": "voice",
      "file": "luna_intro_001.wav",
      "url": "/api/content/audio/luna_intro_001.wav",
      "dialogue_index": 0,
      "volume": 1.0
    }
  ]
}
```

Audio endpoints:

```text
GET /api/content/audio
GET /api/content/audio/{filename}
```

Both endpoints require normal `X-Dreamweave-*` request signing. The list endpoint returns available files. The stream endpoint returns `audio/wav`.

## Client Authentication

All `/api/*` routes require client authentication before request handling, except `/api/hello`, which is the handshake route used to create the authenticated session.

### 1. Start Handshake

Request:

```http
POST /api/hello
Content-Type: application/json

{
  "client": {
    "name": "DreamweaveClient",
    "version": "0.1.2",
    "platform": "windows",
    "build": "dev",
    "device": "desktop"
  }
}
```

Response payload:

```json
{
  "handshake_id": "...",
  "server_nonce": "...",
  "server_key": "...",
  "version": "0.1.2",
  "minimum_client_version": "0.1.2",
  "recommended_client_version": "0.1.2",
  "api_revision": "3",
  "protocol_version": "2026.06",
  "client_metadata_required": true,
  "motd": "Dreamweave alpha server"
}
```

The client verifies:

```text
server_key = MD5(server_secret + ":" + server_nonce)
```

### 2. Complete Handshake

The client creates `client_nonce` and sends:

```http
POST /api/hello
Content-Type: application/json

{
  "handshake_id": "...",
  "client_nonce": "...",
  "client_key": "...",
  "client": {
    "name": "DreamweaveClient",
    "version": "0.1.2",
    "platform": "windows",
    "build": "dev",
    "device": "desktop"
  }
}
```

`client_key` is:

```text
MD5(server_secret + ":" + server_nonce + ":" + client_nonce)
```

Both sides derive the session key:

```text
session_key = SHA256(server_secret + ":" + server_nonce + ":" + client_nonce)
```

### 3. Sign Every API Request

Every request after the handshake must include these headers:

```http
X-Dreamweave-Handshake: <handshake_id>
X-Dreamweave-Timestamp: <unix_seconds>
X-Dreamweave-Nonce: <unique_request_nonce>
X-Dreamweave-Client-Name: <client_name>
X-Dreamweave-Client-Version: <client_version>
X-Dreamweave-Client-Platform: <platform>
X-Dreamweave-Client-Build: <build_id>
X-Dreamweave-Client-Device: <device>
X-Dreamweave-Key: <request_key>
```

The timestamp must be within 300 seconds of server time. `X-Dreamweave-Nonce` can only be used once per handshake session.

`request_key` is:

```text
MD5(
  server_secret + ":" +
  session_key_hex + ":" +
  handshake_id + ":" +
  HTTP_METHOD + ":" +
  request_path + ":" +
  body_md5 + ":" +
  timestamp + ":" +
  request_nonce + ":" +
  client_metadata_md5
)
```

`X-Dreamweave-Client-Name` and `X-Dreamweave-Client-Version` are required. `Platform`, `Build`, and `Device` are optional. `client_metadata_md5` is the MD5 of these five fields joined with newline characters in this order:

```text
client_name + "\n" +
client_version + "\n" +
client_platform + "\n" +
client_build + "\n" +
client_device
```

`body_md5` is the MD5 of the exact raw request body bytes. For a GET request with no body, use the MD5 of empty bytes:

```text
d41d8cd98f00b204e9800998ecf8427e
```

## Endpoints

Authenticated endpoints:

```text
GET  /api/version
GET  /api/status
GET  /api/legal/terms
GET  /api/legal/privacy
GET  /api/legal/eula
POST /api/register
POST /api/login
POST /api/sync/get
POST /api/sync/update
POST /api/content/story
POST /api/content/ack
GET  /api/seed/{map_id}
```

## User Data

User data contains:

```json
{
  "uid": "player_001",
  "nickname": "Dreamer",
  "email": "player@example.com",
  "password_md5": "e10adc3949ba59abbe56e057f20f883e"
}
```

- `uid`: unique user ID used for login, sync, and server-side identity.
- `nickname`: player display name.
- `email`: contact email for account recovery, contact, or operational notices.
- `password_md5`: 32-character lowercase MD5 of the UTF-8 password, sent by the client for registration and login matching.

Registration uses `uid`, `nickname`, `email`, and `password_md5`. Login uses `uid` and `password_md5`. The server stores a server-side hash of `password_md5`, not the plaintext password. Legacy fields `username` and `display_name` are still returned for compatibility; legacy clients that send `password` are converted to the MD5 credential and upgraded after a successful login.

Handshake endpoint:

```text
POST /api/hello
```

## Status Endpoint

`GET /api/status` returns non-sensitive server status as JSON:

```json
{
  "status": "ok",
  "public_message": "Dreamweave server is online.",
  "maintenance": false,
  "maintenance_message": "",
  "server_version": "0.1.2",
  "protocol_version": "2026.06",
  "api_revision": "3",
  "server_name": "Dreamweave Alpha",
  "environment": "development",
  "region": "local",
  "server_time": 1234567890,
  "uptime_seconds": 12,
  "features": {
    "registration": true,
    "login": true,
    "sync": true,
    "content_download": true
  },
  "capacity": {
    "max_players": 100
  },
  "database": {
    "ok": true,
    "path": "..."
  },
  "content": {
    "story_file_exists": true,
    "story_file": "..."
  },
  "handshakes": {
    "total": 1,
    "authenticated": 1
  }
}
```

This endpoint still requires normal `X-Dreamweave-*` request signing.

`GET /api/version` also returns JSON and is controlled by `[version]` in `config.toml`. `[status]` controls `/api/status` output as well as registration, login, sync, and content-download feature switches.

## Legal Endpoints

These endpoints return Markdown legal documents, including the EULA:

```text
GET /api/legal/terms
GET /api/legal/privacy
GET /api/legal/eula
```

Response payload:

```json
{
  "format": "markdown",
  "path": "...",
  "updated_at": 1234567890,
  "content": "..."
}
```

The file paths are configured through `[legal]` in `config.toml`:

```toml
terms_file = "content/legal/terms.md"
privacy_file = "content/legal/privacy.md"
eula_file = "content/legal/eula.md"
terms_dir = "content/legal/terms"
privacy_dir = "content/legal/privacy"
eula_dir = "content/legal/eula"
```

## Cookie Storage

The server writes these cookies:

- `dw_handshake`: handshake id. It is written when a handshake is created and completed. Later requests prefer this cookie.
- `dw_session`: login session token. It is written after successful login. Later user sync requests prefer this cookie.

Lookup priority:

- Handshake session: `X-Dreamweave-Handshake` header first, then `dw_handshake` cookie.
- Login token: `dw_session` cookie first, then request body `token`.

The request signature must still use the correct `handshake_id`. If the client sends the handshake through a cookie, the signature formula must use that same value.

Handshake sessions and used request nonces are persisted to SQLite, so authentication no longer depends only on Python process memory.

Cookie behavior is configurable in `config.toml`:

```toml
[cookies]
secure = false
samesite = "lax"
domain = ""
handshake_cookie = "dw_handshake"
session_cookie = "dw_session"
```

## Content Transfer

`POST /api/content/story` returns an encrypted story package:

```json
{
  "kind": "story_json",
  "encoding": "base64",
  "encryption": "xor-sha256-session-key",
  "md5": "...",
  "server_key": "...",
  "payload": "..."
}
```

`server_key` is:

```text
MD5(developer_secret + ":" + content_md5 + ":" + session_key_hex)
```

After decrypting and verifying the payload MD5, the client confirms with:

```http
POST /api/content/ack
```

## Map Seeds

Map seed files live in:

```text
seed/map/
```

File names start from `1.txt`:

```text
seed/map/1.txt
seed/map/2.txt
```

Clients request a seed through:

```http
GET /api/seed/{map_id}
```

The endpoint reads `seed/map/<map_id>.txt` and returns JSON with `seed`, `md5`, `updated_at`, and `algorithm = "perlin-terrain"`. `map_id` starts from 1. This endpoint requires normal `X-Dreamweave-*` request signing.

Body:

```json
{
  "md5": "<content_md5>",
  "client_key": "<same developer proof formula>"
}
```

The request itself still needs the normal `X-Dreamweave-*` authentication headers.

## Notes

The current content encryption is a standard-library development layer using a SHA-256-derived XOR stream. It keeps the protocol independent of HTTPS during early development. Before public testing, replace it with an authenticated cipher such as AES-GCM or ChaCha20-Poly1305.
