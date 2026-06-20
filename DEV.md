# Dreamweave Server 开发说明

英文版文档位于 [docs/en-us/DEV.md](docs/en-us/DEV.md)。

## 运行

安装依赖：

```powershell
pip install -r requirements.txt
```

启动服务：

```powershell
python main.py
```

服务会读取 `config.toml` 中的 host、port、版本号、SQLite 路径、内容路径和共享密钥。

非 development/local 环境会拒绝空密钥或示例密钥。密钥可通过环境变量覆盖：

```text
DREAMWEAVE_SERVER_SECRET
DREAMWEAVE_DEVELOPER_SECRET
DREAMWEAVE_ADMIN_TOKEN
```

## 管理面板

入口：

```text
GET /admin
```

管理 API 使用 `X-Admin-Token`、`Authorization: Bearer <token>` 或 `dw_admin_token` Cookie 鉴权。

可用管理端点：

```text
POST /admin/api/auth
GET  /admin/api/meta
GET  /admin/api/endpoints
GET  /admin/api/logs
GET  /admin/api/story
POST /admin/api/story
GET  /admin/api/sql/tables
POST /admin/api/sql/query
```

`/admin/api/sql/query` 仅允许只读语句：`SELECT`、`WITH`、`PRAGMA`。最大返回行数由 `config.toml` 的 `admin.max_sql_rows` 控制。

## 客户端鉴权

除了 `/api/hello` 之外，所有 `/api/*` 路由都会在进入业务逻辑前进行客户端鉴权。

### 1. 发起握手

请求：

```http
POST /api/hello
Content-Type: application/json

{}
```

响应 payload：

```json
{
  "handshake_id": "...",
  "server_nonce": "...",
  "server_key": "...",
  "version": "0.1.0",
  "motd": "Dreamweave alpha server"
}
```

客户端校验：

```text
server_key = MD5(server_secret + ":" + server_nonce)
```

### 2. 完成握手

客户端生成 `client_nonce`，然后发送：

```http
POST /api/hello
Content-Type: application/json

{
  "handshake_id": "...",
  "client_nonce": "...",
  "client_key": "..."
}
```

`client_key` 计算方式：

```text
MD5(server_secret + ":" + server_nonce + ":" + client_nonce)
```

双端派生会话密钥：

```text
session_key = SHA256(server_secret + ":" + server_nonce + ":" + client_nonce)
```

### 3. 签名每个业务请求

握手完成后，每个业务请求都必须携带：

```http
X-Dreamweave-Handshake: <handshake_id>
X-Dreamweave-Timestamp: <unix_seconds>
X-Dreamweave-Nonce: <unique_request_nonce>
X-Dreamweave-Key: <request_key>
```

`X-Dreamweave-Timestamp` 必须在服务端时间前后 300 秒内。`X-Dreamweave-Nonce` 在同一个握手会话中只能使用一次。

`request_key` 计算方式：

```text
MD5(
  server_secret + ":" +
  session_key_hex + ":" +
  handshake_id + ":" +
  HTTP_METHOD + ":" +
  request_path + ":" +
  body_md5 + ":" +
  timestamp + ":" +
  request_nonce
)
```

`body_md5` 是原始请求体字节的 MD5。没有 body 的 GET 请求使用空字节 MD5：

```text
d41d8cd98f00b204e9800998ecf8427e
```

## 端点

公开握手端点：

```text
POST /api/hello
```

需要鉴权的端点：

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

## 状态端点

`GET /api/status` 返回 JSON 格式的非敏感服务状态：

```json
{
  "status": "ok",
  "public_message": "Dreamweave server is online.",
  "maintenance": false,
  "maintenance_message": "",
  "server_version": "0.1.0",
  "protocol_version": "2026.06",
  "api_revision": "1",
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

该端点同样需要正常的 `X-Dreamweave-*` 请求签名。

`GET /api/version` 也返回 JSON，并由 `config.toml` 的 `[version]` 配置控制。`[status]` 配置会同时控制 `/api/status` 返回内容，以及注册、登录、同步和内容下载开关。

## 法律文本端点

以下端点返回 Markdown 格式的法律文本：

```text
GET /api/legal/terms
GET /api/legal/privacy
```

返回 payload：

```json
{
  "format": "markdown",
  "path": "...",
  "updated_at": 1234567890,
  "content": "..."
}
```

法律文本文件路径由 `config.toml` 的 `[legal]` 配置指定。

## Cookie 存储

服务端会写入以下 Cookie：

- `dw_handshake`：握手 id。创建握手和完成握手时都会写入，后续请求优先从 Cookie 读取该值。
- `dw_session`：登录 session token。登录成功后写入，后续用户数据同步优先从 Cookie 读取该值。

读取优先级：

- 握手会话：`X-Dreamweave-Handshake` 请求头优先，其次 `dw_handshake` Cookie。
- 登录 token：`dw_session` Cookie 优先，其次请求体里的 `token` 字段。

注意：请求签名仍然必须包含正确的 `handshake_id`。如果客户端使用 Cookie 传递握手 id，签名公式里的 `handshake_id` 也必须使用同一个值。

握手会话和已使用的请求 nonce 会持久化到 SQLite，避免服务重启或多进程部署时只依赖 Python 进程内存。

Cookie 行为可通过 `config.toml` 配置：

```toml
[cookies]
secure = false
samesite = "lax"
domain = ""
handshake_cookie = "dw_handshake"
session_cookie = "dw_session"
```

## 内容传输

`POST /api/content/story` 返回加密剧情包：

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

`server_key` 计算方式：

```text
MD5(developer_secret + ":" + content_md5 + ":" + session_key_hex)
```

客户端解密并校验 payload MD5 后，通过以下端点确认：

```http
POST /api/content/ack
```

请求 body：

```json
{
  "md5": "<content_md5>",
  "client_key": "<same developer proof formula>"
}
```

该请求本身仍然需要正常的 `X-Dreamweave-*` 请求签名。

## 注意

当前内容加密是标准库开发期实现，使用 SHA-256 派生 XOR 流，让协议在早期开发阶段不依赖 HTTPS。公开测试前，建议替换为 AES-GCM 或 ChaCha20-Poly1305 这类带认证的加密算法。
