# Dreamweave Server 开发说明

英文版文档位于 [docs/en-us/DEV.md](docs/en-us/DEV.md)。

## 运行

```powershell
pip install -r requirements.txt
python main.py
```

也可以使用：

```powershell
.\run.bat
```

Linux/macOS：

```sh
./run.sh
```

服务读取 `config.toml` 中的 host、port、版本号、SQLite 路径、内容路径、管理 Token 和共享密钥。

文档入口：

```text
GET /docs
GET /docs?lang=en-US
GET /docs?lang=ja-JP
GET /docs?lang=ru-RU
GET /swagger
```

`/docs` 是项目本地化文档页，默认中文。`/swagger` 是 FastAPI 原生 Swagger UI。

非 `development/local/dev` 环境必须设置非示例密钥：

```text
DREAMWEAVE_SERVER_SECRET
DREAMWEAVE_DEVELOPER_SECRET
DREAMWEAVE_ADMIN_TOKEN
```

## 客户端鉴权

除 `/api/hello` 外，所有 `/api/*` 路由都会在进入业务逻辑前进行客户端鉴权。

### 1. 创建握手

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

返回 payload：

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

客户端校验：

```text
server_key = MD5(server_secret + ":" + server_nonce)
```

### 2. 完成握手

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

`client_key`：

```text
MD5(server_secret + ":" + server_nonce + ":" + client_nonce)
```

双端派生会话密钥：

```text
session_key = SHA256(server_secret + ":" + server_nonce + ":" + client_nonce)
```

### 3. 签名业务请求

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

`X-Dreamweave-Timestamp` 必须在服务端时间前后 300 秒内。`X-Dreamweave-Nonce` 在同一个握手会话中只能使用一次。

`request_key`：

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

`X-Dreamweave-Client-Name` 和 `X-Dreamweave-Client-Version` 必填；`Platform`、`Build`、`Device` 可选。`client_metadata_md5` 是以下五个字段按顺序用换行符连接后的 MD5：

```text
client_name + "\n" +
client_version + "\n" +
client_platform + "\n" +
client_build + "\n" +
client_device
```

GET 空 body 的 MD5：

```text
d41d8cd98f00b204e9800998ecf8427e
```

## 业务端点

```text
POST /api/hello
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
GET  /api/content/audio
GET  /api/content/audio/{filename}
POST /api/content/ack
GET  /api/seed/{map_id}
```

## 用户数据

用户数据至少包含：

```json
{
  "uid": "player_001",
  "nickname": "织梦者",
  "email": "player@example.com",
  "password_md5": "e10adc3949ba59abbe56e057f20f883e"
}
```

- `uid`：用户唯一 ID，用于登录、同步和服务端识别。
- `nickname`：玩家显示昵称。
- `email`：联系邮箱，用于账号联系、找回或运营通知。
- `password_md5`：客户端对 UTF-8 密码原文计算出的 32 位小写 MD5，用于注册和登录匹配。

注册使用 `uid`、`nickname`、`email`、`password_md5`。登录使用 `uid` 和 `password_md5`。服务端会保存 `password_md5` 的服务端哈希，不保存明文密码。兼容字段 `username` 与 `display_name` 仍会返回给旧客户端；旧客户端传 `password` 时，服务端会转换为 MD5 凭据并在成功登录后升级存储。

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

`server_key`：

```text
MD5(developer_secret + ":" + content_md5 + ":" + session_key_hex)
```

客户端解密并校验 MD5 后，通过 `/api/content/ack` 回传同样的开发者 proof。

## 多剧情管理

剧情目录由 `config.toml` 指定：

```toml
[content]
story_file = "content/story.json"
story_dir = "story"
audio_dir = "wav/story"
```

管理面板和管理 API 会使用：

```text
./story/<第几章>-<第几幕>.json
```

文件名示例：

```text
story/1-1.json
story/1-2.json
story/2-1.json
```

剧情 JSON 基本结构：

```json
{
  "meta": {
    "chapter": 1,
    "act": 1,
    "chapter_title": "第一章：织梦初醒",
    "scene_title": "第一幕：空港回声"
  },
  "characters": [
    {"id": "guide_luna", "name": "露娜", "role": "引导者"}
  ],
  "backgrounds": [
    {"id": "sky_dock", "name": "悬空港", "asset": "bg/sky_dock"}
  ],
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
  "dialogues": [
    {"speaker": "guide_luna", "text": "同步完成。", "emotion": "calm"}
  ],
  "tasks": [
    {"id": "task_find_anchor", "title": "寻找梦境锚点", "description": "...", "next": []}
  ]
}
```

当 `story_dir` 存在并包含 JSON 文件时，客户端剧情下载接口返回剧情集合；否则回退到旧单文件 `story_file`。

## 剧情音频

音频目录：

```text
wav/story/
```

音频文件使用 `.wav`。剧情 JSON 中通过 `audio` 数组引用文件，并提供客户端可直接请求的 URL。

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

音频 API：

```text
GET /api/content/audio
GET /api/content/audio/{filename}
```

两个端点都需要正常的 `X-Dreamweave-*` 请求签名。`/api/content/audio` 返回可用音频列表；`/api/content/audio/{filename}` 以 `audio/wav` 流式返回文件。

## 地图种子

地图种子文件位于：

```text
./seed/map/
```

文件名从 1 开始递增：

```text
seed/map/1.txt
seed/map/2.txt
seed/map/3.txt
```

每个文件只保存一个种子码文本。客户端通过：

```http
GET /api/seed/{map_id}
```

获取用于 Perlin 地形生成的种子码。`map_id` 必须从 1 开始；服务端读取 `seed/map/<map_id>.txt`，返回 JSON，其中包含 `seed`、`md5`、`updated_at` 和 `algorithm = "perlin-terrain"`。该端点同样需要正常的 `X-Dreamweave-*` 请求签名。

## 管理面板

入口：

```text
GET /admin
```

管理 API 鉴权方式：

```http
X-Admin-Token: <admin_token>
Authorization: Bearer <admin_token>
Cookie: dw_admin_token=<admin_token>
```

管理端点：

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

`/admin/api/sql/query` 默认只允许：

```text
SELECT
WITH
PRAGMA
```

请求体设置 `write=true` 时允许执行单条写 SQL。仍然禁止多语句输入。

## 法律文档

服务端提供 Markdown 格式法律文档：

```text
GET /api/legal/terms
GET /api/legal/privacy
GET /api/legal/eula
```

`/api/legal/eula` 用于返回最终用户许可协议（EULA），内容覆盖许可证边界、反私服、反破解和反逆向等条款。

路径由 `config.toml` 的 `[legal]` 配置：

```toml
terms_file = "content/legal/terms.md"
privacy_file = "content/legal/privacy.md"
eula_file = "content/legal/eula.md"
terms_dir = "content/legal/terms"
privacy_dir = "content/legal/privacy"
eula_dir = "content/legal/eula"
```

## Cookie

服务端会写入并优先读取：

- `dw_handshake`：握手 id。
- `dw_session`：登录 session token。
- `dw_admin_token`：管理面板 Token。

握手读取优先级：`X-Dreamweave-Handshake` 请求头优先，其次 `dw_handshake` Cookie。

登录 token 读取优先级：`dw_session` Cookie 优先，其次请求体 `token` 字段。

## 状态端点

`GET /api/status` 返回 JSON：

```json
{
  "status": "ok",
  "public_message": "Dreamweave server is online.",
  "maintenance": false,
  "server_version": "0.1.2",
  "protocol_version": "2026.06",
  "api_revision": "3",
  "database": {"ok": true, "path": "..."},
  "content": {"story_file_exists": true, "story_file": "..."},
  "handshakes": {"total": 1, "authenticated": 1}
}
```

该端点同样需要正常的 `X-Dreamweave-*` 签名。

## 检查

```powershell
$files = @('main.py') + (Get-ChildItem .\network -Filter *.py | ForEach-Object { $_.FullName })
python -m py_compile @files
```
