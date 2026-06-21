# Dreamweave Server

Dreamweave Server は Dreamweave 3D オンラインゲームのバックエンドです。FastAPI で HTTP API を公開し、SQLite にユーザー、セッション、プレイヤー状態、握手セッション、呼び出しログを保存します。

## 機能

- `/api/*` に統一された FastAPI HTTP API。
- `/api/hello` によるクライアント握手と相互認証。
- 署名付きリクエスト。`X-Dreamweave-Client-Name` と `X-Dreamweave-Client-Version` は必須です。
- `/api/content/story` による暗号化されたストーリー配信。
- `/api/content/audio` と `/api/content/audio/{filename}` による WAV 音声配信。
- `/api/model` は起動時に `model/` からスキャンしたモデル一覧を返します。
- `/api/version` と `/api/status` は JSON を返します。
- `/admin` は Token のみで入る管理パネルです。
- ユーザーデータは `uid`、`nickname`、`email` を含みます。互換性のため `username` と `display_name` も返されます。

## 起動

```powershell
pip install -r requirements.txt
python main.py
```

Windows:

```powershell
.\run.bat
```

Linux/macOS:

```sh
chmod +x ./run.sh
./run.sh
```

既定の URL:

```text
http://127.0.0.1:7777
```

## 主要入口

```text
GET /docs
GET /swagger
GET /admin
GET /api/version
GET /api/status
```

## 設定

主要設定は `config.toml` にあります。

```toml
[server]
version = "0.1.8"

[version]
minimum_client_version = "0.1.8"
recommended_client_version = "0.1.8"
protocol_version = "2026.06"
api_revision = "3"

[cors]
enabled = true
allow_credentials = true
allow_headers = ["*"]
```

Web クライアントの origin は `[cors].allow_origins` に追加してください。

## 認証ヘッダー

`/api/hello` 以外の `/api/*` には以下が必要です。

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

詳細は [DEV.md](DEV.md) と [CLIENT_DEV.md](../../CLIENT_DEV.md) を参照してください。

## ドキュメント

- 中国語: `README.md`, `DEV.md`, `CLIENT_DEV.md`
- 英語: `docs/en-us/README.md`, `docs/en-us/DEV.md`
- 日本語: `docs/ja-jp/README.md`, `docs/ja-jp/DEV.md`
- ロシア語: `docs/ru-ru/README.md`, `docs/ru-ru/DEV.md`
