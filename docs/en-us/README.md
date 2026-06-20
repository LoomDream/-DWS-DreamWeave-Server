# Dreamweave Server

Dreamweave Server is the backend for the Dreamweave 3D online game. The current version exposes HTTP APIs with FastAPI, stores user data and player state in SQLite, and provides client handshake authentication, request signing, encrypted story-content transfer, and server version/status endpoints.

## Features

- FastAPI HTTP API with unified `/api/*` routes.
- SQLite user database with registration, login, session tokens, and player-state sync.
- Client handshake authentication through `/api/hello`.
- All business API requests must include `X-Dreamweave-*` signature headers.
- Request signatures cover HTTP method, path, body MD5, timestamp, nonce, and session key.
- Story JSON transfer includes MD5 integrity checks and developer-secret proof.
- Story payloads are encrypted at the application layer, independent of HTTPS.

## Requirements

- Python 3.11+
- pip

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Quick Start

Edit `config.toml` before running the server, especially:

```toml
[security]
server_secret = "change-me-dreamweave-server-secret"
developer_secret = "change-me-dreamweave-developer-secret"
handshake_ttl_seconds = 300
```

Start the server:

```powershell
python main.py
```

Or use the one-click run scripts:

```powershell
.\run.bat
```

Linux/macOS:

```sh
chmod +x ./run.sh
./run.sh
```

Default address:

```text
http://127.0.0.1:7777
```

FastAPI docs are available while the server is running:

```text
http://127.0.0.1:7777/docs
```

## Project Layout

```text
.
|-- main.py              # Server entrypoint
|-- config.toml          # Runtime config
|-- DEV.md               # Chinese protocol and development notes
|-- requirements.txt     # Python dependencies
|-- content/
|   `-- story.json       # Story/dialogue/task content
|-- docs/
|   `-- en-us/           # English docs
`-- network/
    |-- api.py           # FastAPI routes and request authentication
    |-- config.py        # TOML config loading
    |-- content.py       # Story package loading/encryption
    |-- crypto.py        # MD5 proof, session key, payload encryption helpers
    `-- db.py            # SQLite user/session/player-state storage
```

## API Overview

Public handshake route:

```text
POST /api/hello
```

Authenticated routes:

```text
GET  /api/version
GET  /api/status
GET  /api/legal/terms
GET  /api/legal/privacy
POST /api/register
POST /api/login
POST /api/sync/get
POST /api/sync/update
POST /api/content/story
POST /api/content/ack
```

All authenticated routes require:

```http
X-Dreamweave-Handshake: <handshake_id>
X-Dreamweave-Timestamp: <unix_seconds>
X-Dreamweave-Nonce: <unique_request_nonce>
X-Dreamweave-Key: <request_key>
```

See `docs/en-us/DEV.md` for the full handshake flow and request-signing formula.

`GET /api/status` returns non-sensitive server health information such as server version, uptime, database availability, story file availability, and active handshake counts.

`GET /api/legal/terms` and `GET /api/legal/privacy` return the terms of service and privacy policy as Markdown content.

`GET /api/version` and `GET /api/status` are controlled by `config.toml`, and every API response is JSON.

## Version And Status Config

`[version]` controls `/api/version`:

```toml
[version]
minimum_client_version = "0.1.0"
recommended_client_version = "0.1.0"
protocol_version = "2026.06"
api_revision = "1"
update_required = false
download_url = ""
release_notes_url = ""
```

`[status]` controls `/api/status` and selected feature switches:

```toml
[status]
public_message = "Dreamweave server is online."
maintenance = false
maintenance_message = ""
allow_registration = true
allow_login = true
allow_sync = true
allow_content_download = true
max_players = 100
status_components = ["api", "database", "content", "auth"]
```

## Cookies

The server writes and prefers these cookies:

- `dw_handshake`: handshake id used to identify the client handshake session.
- `dw_session`: login session token used to identify the logged-in user.

Handshake lookup prefers the `X-Dreamweave-Handshake` header and falls back to the cookie. Login-token lookup prefers the `dw_session` cookie and falls back to the request body's `token` field.

Cookie behavior is configurable in `config.toml`:

```toml
[cookies]
secure = false
samesite = "lax"
domain = ""
handshake_cookie = "dw_handshake"
session_cookie = "dw_session"
```

## Database

The server creates the SQLite database automatically at the path configured in `config.toml`:

```toml
[database]
path = "dreamweave.sqlite3"
```

Current tables:

- `users`
- `sessions`
- `player_state`
- `handshakes`
- `handshake_nonces`

## Content

Story, dialogue, and task data currently live in:

```text
content/story.json
```

`POST /api/content/story` returns an encrypted package with:

- `md5`: content integrity hash
- `server_key`: developer-secret proof
- `payload`: encrypted base64 story JSON

The client verifies the package and confirms through `POST /api/content/ack`.

## Development Notes

Run syntax checks:

```powershell
$files = @('main.py') + (Get-ChildItem .\network -Filter *.py | ForEach-Object { $_.FullName })
python -m py_compile @files
```

The current content encryption is a lightweight development implementation based on a SHA-256-derived XOR stream. Before public testing or release, replace it with an authenticated cipher such as AES-GCM or ChaCha20-Poly1305.
