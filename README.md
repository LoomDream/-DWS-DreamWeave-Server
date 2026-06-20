# Dreamweave Server

Dreamweave 织梦 3D 联机游戏服务端。当前版本基于 FastAPI 暴露 HTTP API，使用 SQLite 保存用户、会话、玩家状态和调用日志，并提供客户端鉴权、请求签名、剧情内容加密传输、状态查询和 Token 管理面板。

英文文档位于 [docs/en-us](docs/en-us)。

## 功能

- FastAPI HTTP API，业务接口统一位于 `/api/*`。
- SQLite 存储用户、登录会话、玩家状态、握手会话、请求 nonce 和调用日志。
- `/api/hello` 建立客户端握手，除握手外的 `/api/*` 请求都需要 `X-Dreamweave-*` 签名。
- `/api/content/story` 返回加密剧情包，带 MD5 完整性校验和开发者密钥 proof。
- `/api/version` 和 `/api/status` 返回 JSON，内容由 `config.toml` 配置。
- `/api/content/audio` 和 `/api/content/audio/{filename}` 提供剧情音频列表和 WAV 流式传输。
- `/admin` 提供 Token 管理面板，无需用户名密码。
- 管理面板支持调用日志、端点说明、端点测试、可视化 SQL、表结构/数据查看、多剧情文件管理。

## 快速启动

要求：

- Python 3.11+
- pip

安装依赖：

```powershell
pip install -r requirements.txt
```

启动：

```powershell
python main.py
```

Windows 一键脚本：

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

常用入口：

```text
本地化文档:   http://127.0.0.1:7777/docs
Swagger UI:   http://127.0.0.1:7777/swagger
管理面板:     http://127.0.0.1:7777/admin
```

`/docs` 默认中文，可使用 `?lang=en-US`、`?lang=ja-JP`、`?lang=ru-RU` 切换英文、日文、俄文。FastAPI 原生 Swagger UI 保留在 `/swagger`。

## 配置

核心配置在 `config.toml`。

```toml
[server]
host = "0.0.0.0"
port = 7777
version = "0.1.1"
environment = "development"

[admin]
enabled = true
panel_version = "0.1.1"
token = "change-me-dreamweave-admin-token"
max_sql_rows = 200

[security]
server_secret = "change-me-dreamweave-server-secret"
developer_secret = "change-me-dreamweave-developer-secret"

[content]
story_file = "content/story.json"
story_dir = "story"
audio_dir = "wav/story"
```

非 `development/local/dev` 环境会拒绝空密钥和示例密钥。也可以用环境变量覆盖：

```text
DREAMWEAVE_SERVER_SECRET
DREAMWEAVE_DEVELOPER_SECRET
DREAMWEAVE_ADMIN_TOKEN
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
GET  /api/legal/eula
POST /api/register
POST /api/login
POST /api/sync/get
POST /api/sync/update
POST /api/content/story
GET  /api/content/audio
GET  /api/content/audio/{filename}
POST /api/content/ack
```

鉴权请求头：

```http
X-Dreamweave-Handshake: <handshake_id>
X-Dreamweave-Timestamp: <unix_seconds>
X-Dreamweave-Nonce: <unique_request_nonce>
X-Dreamweave-Client-Name: <client_name>
X-Dreamweave-Client-Version: <client_version>
X-Dreamweave-Client-Platform: <windows|android|ios|web>
X-Dreamweave-Client-Build: <build_id>
X-Dreamweave-Key: <request_key>
```

`X-Dreamweave-Client-Name` 和 `X-Dreamweave-Client-Version` 为必填。平台、构建号和设备信息为可选，但会参与请求签名；客户端生成 `X-Dreamweave-Key` 时必须把客户端元信息 MD5 追加到原有签名材料末尾。

完整签名流程见 [DEV.md](DEV.md)。

## 管理面板

入口：

```text
GET /admin
```

管理 API 支持三种 Token 传递方式：

- `X-Admin-Token`
- `Authorization: Bearer <token>`
- `dw_admin_token` Cookie

管理能力：

- 概览：面板版本、API revision、服务器版本、协议版本、数据库路径、剧情目录。
- 端点测试：查看每个端点的鉴权方式和说明，并从浏览器直接发起测试请求。
- 调用日志：查看 `/api/*` 和 `/admin/api/*` 调用记录。
- 剧情管理：创建、查看、编辑 `./story/<第几章>-<第几幕>.json`。
- SQL 管理：查看 SQLite 表、字段、索引、外键、分页数据。
- SQL 执行器：默认只读查询；选择写入时允许单条写语句。

## 多剧情文件

剧情目录：

```text
./story/
```

文件命名：

```text
<第几章>-<第几幕>.json
```

示例：

```text
story/1-1.json
story/1-2.json
story/2-1.json
```

每个 JSON 顶部需要 `meta` 元信息：

```json
{
  "meta": {
    "chapter": 1,
    "act": 1,
    "chapter_title": "第一章：织梦初醒",
    "scene_title": "第一幕：空港回声"
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

当 `story/` 目录存在并包含剧情文件时，`POST /api/content/story` 会返回剧情集合；否则回退到旧的 `content/story.json`。

## 剧情音频

音频文件目录：

```text
wav/story/
```

支持 `.wav` 文件。文件名只能使用字母、数字、下划线、点和短横线，例如：

```text
wav/story/chapter1_act1_bgm.wav
wav/story/luna_intro_001.wav
```

音频 API：

```text
GET /api/content/audio
GET /api/content/audio/{filename}
```

这两个端点位于 `/api/*` 下，因此同样需要正常的 `X-Dreamweave-*` 客户端鉴权签名。列表接口返回文件名、大小、更新时间、URL 和 content type；文件接口以 `audio/wav` 流式返回 WAV 文件。

## 项目结构

```text
.
|-- main.py
|-- config.toml
|-- run.bat
|-- run.sh
|-- admin_ui/
|   `-- index.html
|-- content/
|   |-- story.json
|   `-- legal/
|-- story/
|   `-- 1-1.json
|-- network/
|   |-- admin.py
|   |-- api.py
|   |-- config.py
|   |-- content.py
|   |-- crypto.py
|   `-- db.py
`-- docs/
    `-- en-us/
```

## 开发检查

```powershell
$files = @('main.py') + (Get-ChildItem .\network -Filter *.py | ForEach-Object { $_.FullName })
python -m py_compile @files
```
