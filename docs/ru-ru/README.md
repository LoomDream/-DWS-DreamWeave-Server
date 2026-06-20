# Dreamweave Server

Dreamweave Server — серверная часть 3D онлайн-игры Dreamweave. Сервер использует FastAPI для HTTP API и SQLite для пользователей, сессий, состояния игрока, handshake-сессий и журналов вызовов.

## Возможности

- Единые HTTP API в `/api/*`.
- Handshake и взаимная аутентификация через `/api/hello`.
- Подписанные запросы. `X-Dreamweave-Client-Name` и `X-Dreamweave-Client-Version` обязательны.
- Зашифрованная передача сюжета через `/api/content/story`.
- Список и потоковая передача WAV через `/api/content/audio`.
- `/api/version` и `/api/status` возвращают JSON.
- `/admin` — панель управления по Admin Token.
- Данные пользователя содержат `uid`, `nickname` и `email`; устаревшие поля `username` и `display_name` также возвращаются для совместимости.

## Запуск

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

Адрес по умолчанию:

```text
http://127.0.0.1:7777
```

## Основные входы

```text
GET /docs
GET /swagger
GET /admin
GET /api/version
GET /api/status
```

## Конфигурация

Основные параметры находятся в `config.toml`.

```toml
[server]
version = "0.1.5"

[version]
minimum_client_version = "0.1.5"
recommended_client_version = "0.1.5"
protocol_version = "2026.06"
api_revision = "3"

[cors]
enabled = true
allow_credentials = true
allow_headers = ["*"]
```

Добавьте origin веб-клиента в `[cors].allow_origins`.

## Заголовки аутентификации

Все `/api/*`, кроме `/api/hello`, требуют:

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

Подробнее см. [DEV.md](DEV.md) и [CLIENT_DEV.md](../../CLIENT_DEV.md).

## Документы

- Китайский: `README.md`, `DEV.md`, `CLIENT_DEV.md`
- Английский: `docs/en-us/README.md`, `docs/en-us/DEV.md`
- Японский: `docs/ja-jp/README.md`, `docs/ja-jp/DEV.md`
- Русский: `docs/ru-ru/README.md`, `docs/ru-ru/DEV.md`
