# Dreamweave Server Dev Notes

## Клиентская аутентификация

Все `/api/*`, кроме `/api/hello`, проходят клиентскую аутентификацию до бизнес-логики.

### 1. Начать handshake

```http
POST /api/hello
Content-Type: application/json

{
  "client": {
    "name": "DreamweaveWeb",
    "version": "0.1.2",
    "platform": "web",
    "build": "dev",
    "device": "browser"
  }
}
```

Ответ содержит `handshake_id`, `server_nonce`, `server_key` и версию сервера.

```text
server_key = MD5(server_secret + ":" + server_nonce)
```

### 2. Завершить handshake

```json
{
  "handshake_id": "...",
  "client_nonce": "...",
  "client_key": "...",
  "client": {
    "name": "DreamweaveWeb",
    "version": "0.1.2",
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

### 3. Подписать API запрос

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

`client_metadata_md5` — MD5 строки из имени клиента, версии, платформы, build и устройства, соединенных переносом строки.

## CORS

Браузерный клиент использует CORS. Добавьте origin клиента в `[cors]` в `config.toml`.

```toml
[cors]
enabled = true
allow_origins = ["http://localhost:5173"]
allow_credentials = true
allow_headers = ["*"]
```

## Основные endpoint

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

## Данные пользователя

Данные пользователя содержат:

```json
{
  "uid": "player_001",
  "nickname": "Dreamer",
  "email": "player@example.com",
  "password_md5": "e10adc3949ba59abbe56e057f20f883e"
}
```

- `uid`: уникальный ID пользователя для входа, синхронизации и идентификации на сервере.
- `nickname`: отображаемое имя игрока.
- `email`: контактная почта для восстановления аккаунта, связи и служебных уведомлений.
- `password_md5`: 32-символьный lowercase MD5 от UTF-8 пароля, который клиент отправляет для регистрации и входа.

Регистрация использует `uid`, `nickname`, `email` и `password_md5`. Вход использует `uid` и `password_md5`. Сервер хранит серверный хэш от `password_md5`, а не plaintext пароль. Для совместимости также возвращаются `username` и `display_name`; старые клиенты с полем `password` конвертируются в MD5 credential и обновляются после успешного входа.

## Контент

Сюжет JSON:

```text
story/<chapter>-<act>.json
```

Аудио:

```text
wav/story/*.wav
```

После получения зашифрованного сюжета клиент должен расшифровать payload, проверить MD5 и подтвердить через `/api/content/ack`.
