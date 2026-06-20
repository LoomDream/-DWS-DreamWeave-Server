# Dreamweave Server

Dreamweave 织梦 3D 联机游戏服务端。当前版本基于 FastAPI 暴露 HTTP API，使用 SQLite 保存用户和玩家状态，并提供客户端握手鉴权、请求签名、剧情内容加密传输、服务器版本查询和状态查看。

英文文档位于 [docs/en-us](docs/en-us)。

## 功能

- 使用 FastAPI 暴露 HTTP API，路由统一为 `/api/*`。
- 使用 SQLite 保存用户、登录会话和玩家状态。
- 通过 `/api/hello` 建立客户端握手会话。
- 所有业务 API 请求都必须携带 `X-Dreamweave-*` 签名请求头。
- 请求签名覆盖 HTTP method、path、body MD5、timestamp、nonce 和 session key。
- 剧情 JSON 传输包含 MD5 完整性校验和开发者密钥 proof。
- 剧情 payload 使用应用层加密传输，不依赖 HTTPS 才能工作。

## 环境要求

- Python 3.11+
- pip

安装依赖：

```powershell
pip install -r requirements.txt
```

## 快速启动

启动前请先修改 `config.toml`，尤其是密钥配置：

```toml
[security]
server_secret = "change-me-dreamweave-server-secret"
developer_secret = "change-me-dreamweave-developer-secret"
handshake_ttl_seconds = 300
```

非 development/local 环境会拒绝空密钥或示例密钥。也可以通过环境变量覆盖：

```powershell
$env:DREAMWEAVE_SERVER_SECRET = "..."
$env:DREAMWEAVE_DEVELOPER_SECRET = "..."
```

启动服务：

```powershell
python main.py
```

也可以使用一键运行脚本：

```powershell
.\run.bat
```

Linux/macOS：

```sh
chmod +x ./run.sh
./run.sh
```

默认地址：

```text
http://127.0.0.1:7777
```

服务运行后可以打开 FastAPI 文档：

```text
http://127.0.0.1:7777/docs
```

## 项目结构

```text
.
|-- main.py              # 服务入口
|-- config.toml          # 运行配置
|-- DEV.md               # 中文协议和开发说明
|-- requirements.txt     # Python 依赖
|-- content/
|   `-- story.json       # 剧情、对话、任务内容
|-- docs/
|   `-- en-us/           # 英文文档
`-- network/
    |-- api.py           # FastAPI 路由和请求鉴权
    |-- config.py        # TOML 配置加载
    |-- content.py       # 剧情包加载和加密
    |-- crypto.py        # MD5 proof、会话密钥、payload 加密工具
    `-- db.py            # SQLite 用户、会话、玩家状态存储
```

## API 概览

公开握手端点：

```text
POST /api/hello
```

需要客户端鉴权的端点：

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

所有鉴权端点都必须携带：

```http
X-Dreamweave-Handshake: <handshake_id>
X-Dreamweave-Timestamp: <unix_seconds>
X-Dreamweave-Nonce: <unique_request_nonce>
X-Dreamweave-Key: <request_key>
```

完整握手流程和签名公式见 [DEV.md](DEV.md)。

`GET /api/status` 会返回非敏感服务状态，例如服务版本、运行时长、数据库可用性、剧情文件可用性和当前握手会话数量。

`GET /api/legal/terms` 和 `GET /api/legal/privacy` 会返回 Markdown 格式的用户协议和隐私政策。

`GET /api/version` 和 `GET /api/status` 的返回内容都由 `config.toml` 控制，并且所有接口返回值都是 JSON。

## 版本和状态配置

`config.toml` 中的 `[version]` 控制 `/api/version`：

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

`[status]` 控制 `/api/status` 以及部分功能开关：

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

## Cookie

服务端会写入并优先读取以下 Cookie：

- `dw_handshake`：握手 id，用于后续请求优先识别客户端握手会话。
- `dw_session`：登录 session token，用于后续同步请求优先识别登录用户。

握手 id 读取优先级为 `X-Dreamweave-Handshake` 请求头优先，Cookie 回退。登录 token 读取优先级为 `dw_session` Cookie 优先，请求体 `token` 回退。

Cookie 行为可通过 `config.toml` 配置：

```toml
[cookies]
secure = false
samesite = "lax"
domain = ""
handshake_cookie = "dw_handshake"
session_cookie = "dw_session"
```

## 数据库

服务会根据 `config.toml` 自动创建 SQLite 数据库：

```toml
[database]
path = "dreamweave.sqlite3"
```

当前表：

- `users`
- `sessions`
- `player_state`
- `handshakes`
- `handshake_nonces`

## 内容数据

剧情、对话和任务数据当前存放在：

```text
content/story.json
```

`POST /api/content/story` 会返回加密内容包：

- `md5`：内容完整性哈希
- `server_key`：开发者密钥 proof
- `payload`：base64 编码的加密剧情 JSON

客户端校验并解密后，通过 `POST /api/content/ack` 确认。

## 开发说明

运行语法检查：

```powershell
$files = @('main.py') + (Get-ChildItem .\network -Filter *.py | ForEach-Object { $_.FullName })
python -m py_compile @files
```

当前内容加密是基于 SHA-256 派生 XOR 流的开发期实现。公开测试或正式上线前，建议替换为 AES-GCM 或 ChaCha20-Poly1305 这类带认证的加密算法。
