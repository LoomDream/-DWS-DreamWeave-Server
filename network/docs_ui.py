from __future__ import annotations

from html import escape
from typing import Any

from .config import AppConfig


LANG_ORDER = ("zh-CN", "en-US", "ja-JP", "ru-RU")


def docs_page(config: AppConfig, lang: str | None) -> str:
    language = normalize_language(lang)
    text = DOCS.get(language, DOCS["zh-CN"])
    return f"""<!doctype html>
<html lang="{escape(language)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(text["title"])}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --text: #182033;
      --muted: #65708a;
      --line: #d8deea;
      --accent: #1769d2;
      --soft: #e9f2ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--text); font: 14px/1.55 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    header {{ padding: 28px 24px 20px; background: var(--panel); border-bottom: 1px solid var(--line); }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 20px 16px 48px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    h2 {{ margin: 0 0 12px; font-size: 18px; }}
    p {{ margin: 0 0 10px; }}
    a {{ color: var(--accent); text-decoration: none; }}
    code {{ background: var(--soft); border: 1px solid #d7e7ff; border-radius: 4px; padding: 1px 5px; }}
    pre {{ overflow: auto; background: #101828; color: #f8fafc; border-radius: 8px; padding: 12px; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; }}
    .topbar {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }}
    .langs {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .langs a {{ border: 1px solid var(--line); background: #fff; padding: 6px 10px; border-radius: 6px; color: var(--text); }}
    .langs a.active {{ border-color: var(--accent); background: var(--soft); color: var(--accent); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
    .muted {{ color: var(--muted); }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #eef2f8; }}
    section {{ margin-top: 16px; }}
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div>
        <h1>{escape(text["title"])}</h1>
        <p class="muted">{escape(text["subtitle"])}</p>
      </div>
      <nav class="langs">{language_links(language)}</nav>
    </div>
  </header>
  <main>
    <section class="grid">
      {info_card(text["server"], config.server.version)}
      {info_card(text["api_revision"], config.version.api_revision)}
      {info_card(text["protocol"], config.version.protocol_version)}
      {info_card(text["admin"], "/admin")}
      {info_card("Swagger", "/swagger")}
      {info_card("OpenAPI JSON", "/openapi.json")}
    </section>
    <section class="card">
      <h2>{escape(text["auth_title"])}</h2>
      <p>{escape(text["auth_body"])}</p>
      <pre>X-Dreamweave-Handshake: &lt;handshake_id&gt;
X-Dreamweave-Timestamp: &lt;unix_seconds&gt;
X-Dreamweave-Nonce: &lt;unique_request_nonce&gt;
X-Dreamweave-Client-Name: &lt;client_name&gt;
X-Dreamweave-Client-Version: &lt;client_version&gt;
X-Dreamweave-Client-Platform: &lt;platform&gt;
X-Dreamweave-Client-Build: &lt;build_id&gt;
X-Dreamweave-Client-Device: &lt;device&gt;
X-Dreamweave-Key: &lt;request_key&gt;</pre>
    </section>
    <section class="card">
      <h2>{escape(text["api_title"])}</h2>
      {endpoint_table(text["endpoints"])}
    </section>
    <section class="card">
      <h2>{escape(text["content_title"])}</h2>
      <p>{escape(text["content_body"])}</p>
      <pre>story/
  1-1.json
wav/story/
  chapter1_act1_bgm.wav
  luna_intro_001.wav</pre>
    </section>
    <section class="card">
      <h2>{escape(text["links_title"])}</h2>
      <p><a href="/admin">{escape(text["admin_link"])}</a></p>
      <p><a href="/swagger">Swagger UI</a></p>
      <p><a href="/redoc">ReDoc</a></p>
    </section>
  </main>
</body>
</html>"""


def language_links(active: str) -> str:
    names = {"zh-CN": "中文", "en-US": "English", "ja-JP": "日本語", "ru-RU": "Русский"}
    return "".join(
        f'<a class="{"active" if lang == active else ""}" href="/docs?lang={lang}">{escape(names[lang])}</a>'
        for lang in LANG_ORDER
    )


def info_card(title: str, value: str) -> str:
    escaped_value = escape(str(value))
    if str(value).startswith("/"):
        escaped_value = f'<a href="{escaped_value}">{escaped_value}</a>'
    return f'<div class="card"><div class="muted">{escape(title)}</div><strong>{escaped_value}</strong></div>'


def endpoint_table(rows: list[tuple[str, str, str]]) -> str:
    body = "".join(
        f"<tr><td><code>{escape(method)}</code></td><td><code>{escape(path)}</code></td><td>{escape(desc)}</td></tr>"
        for method, path, desc in rows
    )
    return f"<table><thead><tr><th>Method</th><th>Path</th><th>Description</th></tr></thead><tbody>{body}</tbody></table>"


def normalize_language(value: str | None) -> str:
    aliases = {
        "zh": "zh-CN",
        "zh-cn": "zh-CN",
        "cn": "zh-CN",
        "en": "en-US",
        "en-us": "en-US",
        "ja": "ja-JP",
        "ja-jp": "ja-JP",
        "jp": "ja-JP",
        "ru": "ru-RU",
        "ru-ru": "ru-RU",
    }
    if not value:
        return "zh-CN"
    return aliases.get(value.strip().lower(), "zh-CN")


BASE_ENDPOINTS = [
    ("POST", "/api/hello"),
    ("GET", "/api/version"),
    ("GET", "/api/status"),
    ("GET", "/api/legal/terms?lang=zh-CN"),
    ("GET", "/api/legal/privacy?lang=zh-CN"),
    ("GET", "/api/legal/eula?lang=zh-CN"),
    ("POST", "/api/register"),
    ("POST", "/api/login"),
    ("POST", "/api/sync/get"),
    ("POST", "/api/sync/update"),
    ("POST", "/api/content/story"),
    ("GET", "/api/content/audio"),
    ("GET", "/api/content/audio/{filename}"),
    ("POST", "/api/content/ack"),
]


def endpoint_rows(descriptions: list[str]) -> list[tuple[str, str, str]]:
    return [(method, path, descriptions[index]) for index, (method, path) in enumerate(BASE_ENDPOINTS)]


DOCS: dict[str, dict[str, Any]] = {
    "zh-CN": {
        "title": "Dreamweave Server 文档",
        "subtitle": "默认中文文档。英文、日文、俄文可通过右上角切换。",
        "server": "服务器版本",
        "api_revision": "API 修订",
        "protocol": "协议版本",
        "admin": "管理面板",
        "auth_title": "客户端鉴权",
        "auth_body": "除 /api/hello 外，/api/* 请求都需要握手后的签名请求头，并必须携带客户端名称和版本号。客户端元信息 MD5 会参与 X-Dreamweave-Key 计算。",
        "api_title": "常用端点",
        "content_title": "剧情和音频",
        "content_body": "剧情 JSON 位于 story/<章节>-<幕>.json，剧情音频位于 wav/story，并通过 /api/content/audio 流式传输。",
        "links_title": "相关入口",
        "admin_link": "打开管理面板",
        "endpoints": endpoint_rows([
            "创建或完成客户端握手。",
            "返回版本、协议和更新信息。",
            "返回服务器状态和组件健康。",
            "返回用户协议 Markdown，支持 lang 参数。",
            "返回隐私政策 Markdown，支持 lang 参数。",
            "返回最终用户许可协议 Markdown，支持 lang 参数。",
            "注册用户。",
            "登录用户并返回 session token。",
            "读取玩家同步状态。",
            "更新玩家同步状态。",
            "返回加密剧情集合。",
            "列出剧情音频文件。",
            "流式返回 WAV 音频。",
            "确认剧情内容 MD5 proof。",
        ]),
    },
    "en-US": {
        "title": "Dreamweave Server Docs",
        "subtitle": "Chinese is the default. English, Japanese, and Russian are available here.",
        "server": "Server Version",
        "api_revision": "API Revision",
        "protocol": "Protocol Version",
        "admin": "Admin Panel",
        "auth_title": "Client Authentication",
        "auth_body": "All /api/* requests except /api/hello require signed headers after the handshake, plus client name and version metadata. The client-metadata MD5 is included in X-Dreamweave-Key.",
        "api_title": "Common Endpoints",
        "content_title": "Story And Audio",
        "content_body": "Story JSON lives in story/<chapter>-<act>.json. Story audio lives in wav/story and is streamed through /api/content/audio.",
        "links_title": "Links",
        "admin_link": "Open admin panel",
        "endpoints": endpoint_rows([
            "Create or complete the client handshake.",
            "Return version, protocol, and update metadata.",
            "Return server and component health.",
            "Return Terms Markdown; supports lang.",
            "Return Privacy Markdown; supports lang.",
            "Return EULA Markdown; supports lang.",
            "Register a user.",
            "Log in and return a session token.",
            "Read player sync state.",
            "Update player sync state.",
            "Return encrypted story collection.",
            "List story audio files.",
            "Stream a WAV audio file.",
            "Confirm story content MD5 proof.",
        ]),
    },
    "ja-JP": {
        "title": "Dreamweave Server ドキュメント",
        "subtitle": "既定は中国語です。英語、日本語、ロシア語も利用できます。",
        "server": "サーバー版",
        "api_revision": "API リビジョン",
        "protocol": "プロトコル版",
        "admin": "管理パネル",
        "auth_title": "クライアント認証",
        "auth_body": "/api/hello 以外の /api/* は、ハンドシェイク後の署名ヘッダーとクライアント名・バージョンが必要です。client metadata MD5 は X-Dreamweave-Key に含まれます。",
        "api_title": "主要エンドポイント",
        "content_title": "ストーリーと音声",
        "content_body": "ストーリー JSON は story/<chapter>-<act>.json、音声は wav/story に置き、/api/content/audio でストリームします。",
        "links_title": "リンク",
        "admin_link": "管理パネルを開く",
        "endpoints": endpoint_rows([
            "クライアント handshake を作成または完了します。",
            "版、プロトコル、更新情報を返します。",
            "サーバーとコンポーネント状態を返します。",
            "利用規約 Markdown を返します。lang 対応。",
            "プライバシー Markdown を返します。lang 対応。",
            "EULA Markdown を返します。lang 対応。",
            "ユーザー登録。",
            "ログインして session token を返します。",
            "プレイヤー同期状態を読みます。",
            "プレイヤー同期状態を更新します。",
            "暗号化されたストーリー集合を返します。",
            "ストーリー音声ファイルを列挙します。",
            "WAV 音声をストリームします。",
            "ストーリー MD5 proof を確認します。",
        ]),
    },
    "ru-RU": {
        "title": "Документация Dreamweave Server",
        "subtitle": "Китайский язык используется по умолчанию. Также доступны английский, японский и русский.",
        "server": "Версия сервера",
        "api_revision": "API Revision",
        "protocol": "Версия протокола",
        "admin": "Панель управления",
        "auth_title": "Клиентская аутентификация",
        "auth_body": "Все /api/* запросы, кроме /api/hello, требуют подписанных заголовков после handshake, а также имя и версию клиента. MD5 client metadata входит в X-Dreamweave-Key.",
        "api_title": "Основные endpoint",
        "content_title": "Сюжет и аудио",
        "content_body": "Сюжет JSON находится в story/<chapter>-<act>.json. Аудио находится в wav/story и передается через /api/content/audio.",
        "links_title": "Ссылки",
        "admin_link": "Открыть панель управления",
        "endpoints": endpoint_rows([
            "Создает или завершает client handshake.",
            "Возвращает версии и данные обновления.",
            "Возвращает состояние сервера и компонентов.",
            "Возвращает Markdown соглашения; поддерживает lang.",
            "Возвращает Markdown политики; поддерживает lang.",
            "Возвращает Markdown EULA; поддерживает lang.",
            "Регистрирует пользователя.",
            "Выполняет вход и возвращает session token.",
            "Читает состояние синхронизации игрока.",
            "Обновляет состояние синхронизации игрока.",
            "Возвращает зашифрованный набор сюжета.",
            "Показывает аудиофайлы сюжета.",
            "Передает WAV аудио потоком.",
            "Подтверждает MD5 proof контента.",
        ]),
    },
}
