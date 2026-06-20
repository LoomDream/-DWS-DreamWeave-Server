# Dreamweave Server 開発メモ

## クライアント認証

`/api/hello` 以外の `/api/*` は、処理前にクライアント認証を行います。

### 1. 握手開始

```http
POST /api/hello
Content-Type: application/json

{
  "client": {
    "name": "DreamweaveWeb",
    "version": "0.1.5",
    "platform": "web",
    "build": "dev",
    "device": "browser"
  }
}
```

レスポンスには `handshake_id`、`server_nonce`、`server_key`、バージョン情報が含まれます。

```text
server_key = MD5(server_secret + ":" + server_nonce)
```

### 2. 握手完了

```json
{
  "handshake_id": "...",
  "client_nonce": "...",
  "client_key": "...",
  "client": {
    "name": "DreamweaveWeb",
    "version": "0.1.5",
    "platform": "web",
    "build": "dev",
    "device": "browser"
  }
}
```

```text
client_key = MD5(server_secret + ":" + server_nonce + ":" + client_nonce)
session_key = SHA256(server_secret + ":" + server_nonce + ":" + client_nonce)
```

### 3. API リクエスト署名

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

`client_metadata_md5` は、クライアント名、バージョン、プラットフォーム、ビルド、デバイスを改行で連結した文字列の MD5 です。

## CORS

ブラウザクライアントは CORS を使用します。`config.toml` の `[cors]` に origin を追加してください。

```toml
[cors]
enabled = true
allow_origins = ["http://localhost:5173"]
allow_credentials = true
allow_headers = ["*"]
```

## 主要 endpoint

```text
GET  /api/version
GET  /api/status
POST /api/register
POST /api/login
POST /api/sync/get
POST /api/sync/update
POST /api/content/story
GET  /api/content/audio
GET  /api/content/audio/{filename}
POST /api/content/ack
```

## ユーザーデータ

ユーザーデータは以下を含みます。

```json
{
  "uid": "player_001",
  "nickname": "Dreamer",
  "email": "player@example.com",
  "password_md5": "e10adc3949ba59abbe56e057f20f883e"
}
```

- `uid`: ログイン、同期、サーバー側識別に使う一意のユーザー ID。
- `nickname`: プレイヤー表示名。
- `email`: アカウント連絡、復旧、運用通知に使う連絡メール。
- `password_md5`: UTF-8 パスワード原文の 32 文字小文字 MD5。登録とログインの照合に使います。

登録には `uid`、`nickname`、`email`、`password_md5` を使います。ログインには `uid` と `password_md5` を使います。サーバーは明文パスワードではなく `password_md5` のサーバー側ハッシュを保存します。互換性のため `username` と `display_name` も返されます。旧クライアントが `password` を送る場合は MD5 資格情報に変換し、ログイン成功後に保存形式を更新します。

## コンテンツ

ストーリー JSON:

```text
story/<chapter>-<act>.json
```

音声:

```text
wav/story/*.wav
```

暗号化ストーリーを受信したクライアントは、復号、MD5 検証、`/api/content/ack` による確認を行います。
