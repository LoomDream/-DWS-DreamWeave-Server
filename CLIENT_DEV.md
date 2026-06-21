# Dreamweave 客户端开发文档

版本：0.1.8

本文档面向 Dreamweave 游戏客户端开发者，默认客户端目标为手机和电脑均可运行的 WebGL/HTML 客户端，也适用于 Unity、Godot、原生 OpenGL 客户端接入同一套 HTTP API。

## 1. 推荐客户端形态

推荐优先实现：

```text
HTML + JavaScript + WebGL
Three.js 或 Babylon.js
```

原因：

- 手机浏览器和桌面浏览器都可运行。
- 不需要分别维护 Windows、Android、iOS 安装包。
- 可直接调用 FastAPI 暴露的 `/api/*` 接口。
- WebGL 底层模型接近 OpenGL ES，适合中等性能目标。

后续如需要原生客户端，也可以使用 Unity、Godot、Unreal 或 C++ OpenGL。协议层保持一致。

## 2. 服务器基础信息

默认开发地址：

```text
http://127.0.0.1:7777
```

常用入口：

```text
GET /docs
GET /swagger
GET /api/version
GET /api/status
POST /api/hello
```

版本要求：

```text
server_version = 0.1.8
minimum_client_version = 0.1.8
recommended_client_version = 0.1.8
api_revision = 3
```

客户端启动时应先请求 `/api/version` 或完成 `/api/hello`，检查自身版本是否低于 `minimum_client_version`。

## 3. CORS

服务器已支持 CORS，配置位于 `config.toml`：

```toml
[cors]
enabled = true
allow_origins = [
  "http://localhost:3000",
  "http://127.0.0.1:3000",
  "http://localhost:5173",
  "http://127.0.0.1:5173",
  "http://localhost:7776",
  "http://127.0.0.1:7776",
  "http://localhost:7777",
  "http://127.0.0.1:7777",
]
allow_origin_regex = "^https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?$"
allow_credentials = true
allow_methods = ["GET", "POST", "PUT", "OPTIONS"]
allow_headers = ["*"]
```

开发环境默认允许 `localhost` 和 `127.0.0.1` 的任意端口，因此 `http://127.0.0.1:7776` 可以请求 `http://127.0.0.1:7777`。生产环境不要随意使用 `"*"` 或宽泛 regex，尤其是在 `allow_credentials = true` 时。

浏览器请求建议：

```js
fetch(url, {
  method: "POST",
  credentials: "include",
  headers,
  body: JSON.stringify(payload),
});
```

`credentials: "include"` 用于携带服务器写入的 `dw_handshake` 和 `dw_session` Cookie。

## 4. 客户端元信息

0.1.8 起，客户端请求必须带客户端元信息。

`POST /api/hello` 请求体必须包含：

```json
{
  "client": {
    "name": "DreamweaveWeb",
    "version": "0.1.8",
    "platform": "web",
    "build": "dev",
    "device": "browser"
  }
}
```

除 `/api/hello` 外，所有 `/api/*` 请求必须带请求头：

```http
X-Dreamweave-Client-Name: DreamweaveWeb
X-Dreamweave-Client-Version: 0.1.8
X-Dreamweave-Client-Platform: web
X-Dreamweave-Client-Build: dev
X-Dreamweave-Client-Device: browser
```

必填：

- `X-Dreamweave-Client-Name`
- `X-Dreamweave-Client-Version`

可选但推荐：

- `X-Dreamweave-Client-Platform`
- `X-Dreamweave-Client-Build`
- `X-Dreamweave-Client-Device`

这些字段会参与请求签名。客户端发送的元信息必须和生成签名时使用的元信息一致。

## 5. 握手流程

### 5.1 创建握手

```http
POST /api/hello
Content-Type: application/json
```

请求体：

```json
{
  "client": {
    "name": "DreamweaveWeb",
    "version": "0.1.8",
    "platform": "web",
    "build": "dev",
    "device": "browser"
  }
}
```

返回：

```json
{
  "ok": true,
  "payload": {
    "handshake_id": "...",
    "server_nonce": "...",
    "server_key": "...",
    "version": "0.1.8",
    "minimum_client_version": "0.1.8",
    "recommended_client_version": "0.1.8",
    "api_revision": "3",
    "protocol_version": "2026.06",
    "client_metadata_required": true
  }
}
```

客户端校验：

```text
server_key = MD5(server_secret + ":" + server_nonce)
```

### 5.2 完成握手

客户端生成 `client_nonce`，计算：

```text
client_key = MD5(server_secret + ":" + server_nonce + ":" + client_nonce)
```

请求：

```json
{
  "handshake_id": "...",
  "client_nonce": "...",
  "client_key": "...",
  "client": {
    "name": "DreamweaveWeb",
    "version": "0.1.8",
    "platform": "web",
    "build": "dev",
    "device": "browser"
  }
}
```

双方派生会话密钥：

```text
session_key = SHA256(server_secret + ":" + server_nonce + ":" + client_nonce)
```

后续请求使用 `session_key_hex` 参与签名。

## 6. 业务请求签名

除 `/api/hello` 外，所有 `/api/*` 请求都需要签名。

请求头：

```http
X-Dreamweave-Handshake: <handshake_id>
X-Dreamweave-Timestamp: <unix_seconds>
X-Dreamweave-Nonce: <unique_request_nonce>
X-Dreamweave-Client-Name: DreamweaveWeb
X-Dreamweave-Client-Version: 0.1.8
X-Dreamweave-Client-Platform: web
X-Dreamweave-Client-Build: dev
X-Dreamweave-Client-Device: browser
X-Dreamweave-Key: <request_key>
```

`timestamp` 必须在服务端时间前后 300 秒内。`nonce` 在同一个握手会话中只能使用一次。

签名公式：

```text
request_key = MD5(
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

`body_md5` 是原始请求体 bytes 的 MD5。GET 空 body 使用：

```text
d41d8cd98f00b204e9800998ecf8427e
```

`client_metadata_md5` 是以下五个字段按顺序用换行符连接后的 MD5：

```text
client_name + "\n" +
client_version + "\n" +
client_platform + "\n" +
client_build + "\n" +
client_device
```

## 7. JavaScript 示例

```js
const SERVER = "http://127.0.0.1:7777";
const CLIENT = {
  name: "DreamweaveWeb",
  version: "0.1.8",
  platform: "web",
  build: "dev",
  device: navigator.userAgent.slice(0, 80),
};

async function md5Hex(textOrBytes) {
  // 浏览器 Web Crypto 不提供 MD5。这里应替换为经过审计的 MD5 实现。
  // 入参必须按 UTF-8 字符串或原始 bytes 计算，返回小写 hex。
  throw new Error("md5Hex implementation required");
}

async function sha256Bytes(textOrBytes) {
  const bytes = typeof textOrBytes === "string"
    ? new TextEncoder().encode(textOrBytes)
    : textOrBytes;
  return new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
}

function hex(bytes) {
  return [...bytes].map(b => b.toString(16).padStart(2, "0")).join("");
}

function nonce() {
  return crypto.getRandomValues(new Uint8Array(16));
}

async function startHandshake(serverSecret) {
  const first = await fetch(`${SERVER}/api/hello`, {
    method: "POST",
    credentials: "include",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({client: CLIENT}),
  }).then(r => r.json());

  const payload = first.payload;
  const expectedServerKey = await md5Hex(`${serverSecret}:${payload.server_nonce}`);
  if (payload.server_key !== expectedServerKey) throw new Error("server key mismatch");

  const clientNonce = hex(nonce());
  const clientKey = await md5Hex(`${serverSecret}:${payload.server_nonce}:${clientNonce}`);

  await fetch(`${SERVER}/api/hello`, {
    method: "POST",
    credentials: "include",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      handshake_id: payload.handshake_id,
      client_nonce: clientNonce,
      client_key: clientKey,
      client: CLIENT,
    }),
  }).then(r => r.json());

  const sessionKey = await sha256Bytes(`${serverSecret}:${payload.server_nonce}:${clientNonce}`);
  return {handshakeId: payload.handshake_id, sessionKeyHex: hex(sessionKey)};
}

async function signedFetch(auth, method, path, body, serverSecret) {
  const rawBody = body === undefined ? "" : JSON.stringify(body);
  const timestamp = String(Math.floor(Date.now() / 1000));
  const requestNonce = hex(nonce());
  const bodyMd5 = await md5Hex(new TextEncoder().encode(rawBody));
  const metadataMd5 = await md5Hex([
    CLIENT.name,
    CLIENT.version,
    CLIENT.platform || "",
    CLIENT.build || "",
    CLIENT.device || "",
  ].join("\n"));

  const requestKey = await md5Hex([
    serverSecret,
    auth.sessionKeyHex,
    auth.handshakeId,
    method.toUpperCase(),
    path,
    bodyMd5,
    timestamp,
    requestNonce,
    metadataMd5,
  ].join(":"));

  const response = await fetch(`${SERVER}${path}`, {
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Dreamweave-Handshake": auth.handshakeId,
      "X-Dreamweave-Timestamp": timestamp,
      "X-Dreamweave-Nonce": requestNonce,
      "X-Dreamweave-Client-Name": CLIENT.name,
      "X-Dreamweave-Client-Version": CLIENT.version,
      "X-Dreamweave-Client-Platform": CLIENT.platform || "",
      "X-Dreamweave-Client-Build": CLIENT.build || "",
      "X-Dreamweave-Client-Device": CLIENT.device || "",
      "X-Dreamweave-Key": requestKey,
    },
    body: method === "GET" ? undefined : rawBody,
  });
  return response.json();
}
```

说明：浏览器 Web Crypto 标准不提供 MD5。正式 Web 客户端可以使用经过审计的小型 MD5 实现，或等待服务端协议升级到 SHA-256/HMAC。

## 8. 登录和同步

注册：

```http
POST /api/register
```

请求体：

```json
{
  "uid": "player_001",
  "nickname": "织梦者",
  "email": "player@example.com",
  "password_md5": "e10adc3949ba59abbe56e057f20f883e"
}
```

用户数据包含：

- `uid`：用户唯一 ID，用于登录和服务器内部识别。
- `nickname`：玩家显示昵称。
- `email`：联系邮箱，用于账号联系、找回或运营通知。
- `password_md5`：客户端对 UTF-8 密码原文计算出的 32 位小写 MD5，用于注册和登录匹配。

兼容字段 `username` 和 `display_name` 仍会返回，但新客户端应优先使用 `uid` 和 `nickname`。

密码处理规则：

```text
password_md5 = MD5(UTF-8 password)
```

业务请求本身仍要按握手后的 `X-Dreamweave-Key` 规则签名。服务端不会保存明文密码，会保存 `password_md5` 的服务端哈希用于后续匹配。旧客户端传 `password` 时仍可兼容，但新客户端必须传 `password_md5`。

登录：

```http
POST /api/login
```

请求体：

```json
{
  "uid": "player_001",
  "password_md5": "e10adc3949ba59abbe56e057f20f883e"
}
```

登录成功后服务端返回 session token，并写入 `dw_session` Cookie。后续同步可以优先依赖 Cookie，也可以在请求体中带 `token`。

读取状态：

```http
POST /api/sync/get
```

更新状态：

```http
POST /api/sync/update
```

建议同步频率：

```text
移动端：5-10 次/秒
桌面端：10-20 次/秒
```

当前 HTTP 同步适合早期验证。实时多人移动建议后续新增 WebSocket，例如 `/ws/game`。

## 9. 剧情和音频

剧情：

```http
POST /api/content/story
```

音频列表：

```http
GET /api/content/audio
```

音频流：

```http
GET /api/content/audio/{filename}
```

剧情包会使用会话密钥做应用层加密，并带 MD5 与开发者 proof。客户端解密并校验成功后，通过：

```http
POST /api/content/ack
```

回传确认。

地图种子：

```http
GET /api/seed/{map_id}
```

服务端会读取 `seed/map/<map_id>.txt`，其中 `map_id` 从 1 开始。返回 payload 中的 `seed` 字段用于客户端 Perlin 地形生成；`md5` 可用于缓存校验。该端点同样需要握手后的签名请求头。

模型清单：

```http
GET /api/model
```

服务端启动时扫描 `model/` 目录，并缓存模型文件清单。返回 payload 中的 `files` 数组包含 `name`、`relative_path`、`extension`、`bytes`、`updated_at`。客户端可用 `bytes` 和 `updated_at` 做资源缓存判断。新增或替换模型后需要重启服务刷新清单。

下载指定模型：

```http
POST /api/down
Content-Type: application/json

{
  "model": "characters/hero.glb"
}
```

`model` 字段使用 `/api/model` 返回的 `relative_path`。响应是模型文件流，客户端按文件扩展名或响应 `Content-Type` 加载。

## 10. 客户端性能建议

手机和电脑共用 WebGL 客户端时，建议：

- 低多边形模型优先。
- 单张贴图控制在 512 或 1024。
- 手机端关闭高质量阴影、屏幕空间后处理和大量粒子。
- 同屏玩家数量先限制到 20-50。
- 大地图分块加载，剧情和音频按章节懒加载。
- 服务端只同步位置、旋转、动作、状态和少量任务数据。
- 客户端预测移动，服务端状态用于校正。

## 11. 常见错误

`422`：

- `/api/hello` 缺少 `client`。
- 请求体字段类型不符合 Pydantic 校验。

`401 missing client metadata headers`：

- 业务请求缺少 `X-Dreamweave-Client-Name` 或 `X-Dreamweave-Client-Version`。

`401 client request key check failed`：

- 签名公式错误。
- `client_metadata_md5` 和实际请求头不一致。
- path 使用了完整 URL，而不是 `/api/...` 路径。
- body MD5 不是原始请求体 bytes 的 MD5。

`401 request nonce has already been used`：

- 同一个握手会话里重复使用了 nonce。

`401 timestamp is outside the allowed window`：

- 客户端系统时间和服务器差距超过 300 秒。
