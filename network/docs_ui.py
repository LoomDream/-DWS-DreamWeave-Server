from __future__ import annotations

from html import escape
from pathlib import Path
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
    .markdown-body {{ padding: 14px; border-top: 1px solid var(--line); background: #fff; }}
    .markdown-body h1 {{ font-size: 22px; margin: 0 0 12px; }}
    .markdown-body h2 {{ font-size: 18px; margin: 18px 0 8px; }}
    .markdown-body h3 {{ font-size: 15px; margin: 14px 0 6px; }}
    .markdown-body p {{ margin: 0 0 10px; }}
    .markdown-body ul, .markdown-body ol {{ margin: 0 0 10px 22px; padding: 0; }}
    .markdown-body blockquote {{ margin: 0 0 10px; padding: 8px 12px; border-left: 3px solid var(--accent); background: var(--soft); color: var(--muted); }}
    .markdown-body table {{ margin: 8px 0 12px; }}
    .markdown-body pre {{ margin: 8px 0 12px; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; }}
    .topbar {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }}
    .langs {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .langs a {{ border: 1px solid var(--line); background: #fff; padding: 6px 10px; border-radius: 6px; color: var(--text); }}
    .langs a.active {{ border-color: var(--accent); background: var(--soft); color: var(--accent); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
    .muted {{ color: var(--muted); }}
    .doc-list {{ display: grid; gap: 10px; }}
    details.doc-item {{ border: 1px solid var(--line); border-radius: 8px; background: #fff; overflow: hidden; }}
    details.doc-item summary {{ cursor: pointer; padding: 12px; display: grid; grid-template-columns: minmax(180px, 1fr) minmax(180px, 1.4fr); gap: 10px; align-items: start; }}
    details.doc-item summary:hover {{ background: #f8fbff; }}
    .doc-title {{ font-weight: 700; }}
    .doc-desc {{ color: var(--muted); }}
    .doc-mode {{ padding: 10px 12px; border-top: 1px solid var(--line); background: #f8fbff; color: var(--muted); font-size: 12px; }}
    .doc-content {{ margin: 0; border-radius: 0; max-height: 520px; white-space: pre-wrap; }}
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
      <h2>{escape(text["markdown_title"])}</h2>
      <p>{escape(text["markdown_body"])}</p>
      {markdown_panel(text["markdown_docs"])}
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


def markdown_panel(rows: list[tuple[str, str, str]]) -> str:
    items = []
    for path, title, desc in rows:
        markdown = read_markdown(path)
        items.append(
        f"""<details class="doc-item">
  <summary>
    <span><code>{escape(path)}</code><br><span class="doc-title">{escape(title)}</span></span>
    <span class="doc-desc">{escape(desc)}</span>
  </summary>
  <div class="doc-mode">Rendered Markdown</div>
  <div class="markdown-body">{render_markdown(markdown)}</div>
  <div class="doc-mode">Markdown Source</div>
  <pre class="doc-content">{escape(markdown)}</pre>
</details>"""
        )
    return f'<div class="doc-list">{"".join(items)}</div>'


def read_markdown(relative_path: str) -> str:
    root = Path(__file__).resolve().parent.parent
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return "document path is outside repository root"
    if path.suffix.lower() != ".md":
        return "document is not a markdown file"
    if not path.exists():
        return "document does not exist"
    return path.read_text(encoding="utf-8")


def render_markdown(markdown: str) -> str:
    lines = markdown.splitlines()
    html: list[str] = []
    paragraph: list[str] = []
    list_mode: str | None = None
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            html.append(f"<p>{inline_markdown(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_mode
        if list_mode:
            html.append(f"</{list_mode}>")
            list_mode = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                html.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False
            else:
                flush_paragraph()
                close_list()
                in_code = True
                code_lines = []
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not stripped:
            flush_paragraph()
            close_list()
            continue
        if stripped.startswith("### "):
            flush_paragraph()
            close_list()
            html.append(f"<h3>{inline_markdown(stripped[4:])}</h3>")
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            close_list()
            html.append(f"<h2>{inline_markdown(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            flush_paragraph()
            close_list()
            html.append(f"<h1>{inline_markdown(stripped[2:])}</h1>")
            continue
        if stripped.startswith("> "):
            flush_paragraph()
            close_list()
            html.append(f"<blockquote>{inline_markdown(stripped[2:])}</blockquote>")
            continue
        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            if list_mode != "ul":
                close_list()
                html.append("<ul>")
                list_mode = "ul"
            html.append(f"<li>{inline_markdown(stripped[2:])}</li>")
            continue
        paragraph.append(stripped)

    if in_code:
        html.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")
    flush_paragraph()
    close_list()
    return "".join(html)


def inline_markdown(value: str) -> str:
    output: list[str] = []
    parts = value.split("`")
    for index, part in enumerate(parts):
        if index % 2:
            output.append(f"<code>{escape(part)}</code>")
        else:
            output.append(escape(part))
    return "".join(output)


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
        "markdown_title": "Markdown 文档说明",
        "markdown_body": "以下是仓库中维护的 Markdown 文档及其用途。中文为默认文档，英文、日文、俄文文档分别位于 docs/en-us、docs/ja-jp、docs/ru-ru，法律文档可通过 /api/legal/* 端点返回。点击条目可直接查看内容。",
        "links_title": "相关入口",
        "admin_link": "打开管理面板",
        "markdown_docs": [
            ("README.md", "项目说明", "中文默认入口，包含功能、启动、配置、API 概览、管理面板、剧情和音频说明。"),
            ("DEV.md", "开发说明", "中文开发文档，包含握手、签名、内容传输、管理 API、Cookie、状态端点和检查命令。"),
            ("CLIENT_DEV.md", "客户端开发文档", "面向 HTML/WebGL、手机和电脑客户端，说明 CORS、客户端元信息、签名、同步、剧情和性能建议。"),
            ("docs/en-us/README.md", "English README", "英文版项目说明，供英语开发者阅读。"),
            ("docs/en-us/DEV.md", "English Dev Notes", "英文版开发说明，覆盖协议、端点、内容传输和部署注意事项。"),
            ("docs/ja-jp/README.md", "日本語 README", "日文版项目说明，供日语开发者阅读。"),
            ("docs/ja-jp/DEV.md", "日本語 Dev Notes", "日文版开发说明，覆盖认证、CORS、端点和内容传输。"),
            ("docs/ru-ru/README.md", "Русский README", "俄文版项目说明，供俄语开发者阅读。"),
            ("docs/ru-ru/DEV.md", "Русский Dev Notes", "俄文版开发说明，覆盖认证、CORS、端点和内容传输。"),
            ("content/legal/terms.md", "用户协议", "默认中文用户协议，通过 GET /api/legal/terms 返回。"),
            ("content/legal/privacy.md", "隐私政策", "默认中文隐私政策，通过 GET /api/legal/privacy 返回。"),
            ("content/legal/eula.md", "最终用户许可协议", "默认中文 EULA，通过 GET /api/legal/eula 返回，覆盖许可证边界、私服和破译限制。"),
        ],
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
        "markdown_title": "Markdown Documents",
        "markdown_body": "These Markdown files are maintained in the repository. Chinese is the default documentation language. English, Japanese, and Russian documents live under docs/en-us, docs/ja-jp, and docs/ru-ru. Legal documents are also exposed through /api/legal/*. Click an item to read its content.",
        "links_title": "Links",
        "admin_link": "Open admin panel",
        "markdown_docs": [
            ("README.md", "Project README", "Default Chinese project entry covering features, startup, config, API overview, admin panel, story, and audio."),
            ("DEV.md", "Developer Notes", "Chinese developer guide covering handshake, signing, content transfer, admin APIs, cookies, status endpoint, and checks."),
            ("CLIENT_DEV.md", "Client Developer Guide", "Guide for HTML/WebGL, mobile, and desktop clients, covering CORS, client metadata, signing, sync, story, and performance notes."),
            ("docs/en-us/README.md", "English README", "English project overview for English-speaking developers."),
            ("docs/en-us/DEV.md", "English Dev Notes", "English developer notes covering protocol, endpoints, content transfer, and deployment notes."),
            ("docs/ja-jp/README.md", "Japanese README", "Japanese project overview for Japanese-speaking developers."),
            ("docs/ja-jp/DEV.md", "Japanese Dev Notes", "Japanese developer notes covering authentication, CORS, endpoints, and content transfer."),
            ("docs/ru-ru/README.md", "Russian README", "Russian project overview for Russian-speaking developers."),
            ("docs/ru-ru/DEV.md", "Russian Dev Notes", "Russian developer notes covering authentication, CORS, endpoints, and content transfer."),
            ("content/legal/terms.md", "Terms of Service", "Default Chinese terms document returned by GET /api/legal/terms."),
            ("content/legal/privacy.md", "Privacy Policy", "Default Chinese privacy document returned by GET /api/legal/privacy."),
            ("content/legal/eula.md", "EULA", "Default Chinese EULA returned by GET /api/legal/eula, covering license boundaries, private servers, and reverse-engineering restrictions."),
        ],
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
        "markdown_title": "Markdown ドキュメント",
        "markdown_body": "リポジトリで管理されている Markdown 文書です。既定は中国語、英語・日本語・ロシア語文書は docs/en-us、docs/ja-jp、docs/ru-ru にあります。法務文書は /api/legal/* からも取得できます。項目をクリックすると内容を読めます。",
        "links_title": "リンク",
        "admin_link": "管理パネルを開く",
        "markdown_docs": [
            ("README.md", "プロジェクト説明", "機能、起動、設定、API 概要、管理パネル、ストーリー、音声を含む既定の中国語入口です。"),
            ("DEV.md", "開発説明", "握手、署名、コンテンツ転送、管理 API、Cookie、状態 endpoint、検査コマンドを含む中国語開発文書です。"),
            ("CLIENT_DEV.md", "クライアント開発文書", "HTML/WebGL、モバイル、デスクトップクライアント向けに CORS、client metadata、署名、同期、ストーリー、性能を説明します。"),
            ("docs/en-us/README.md", "英語 README", "英語開発者向けのプロジェクト概要です。"),
            ("docs/en-us/DEV.md", "英語 Dev Notes", "プロトコル、endpoint、コンテンツ転送、デプロイ注意点を扱う英語開発文書です。"),
            ("docs/ja-jp/README.md", "日本語 README", "日本語開発者向けのプロジェクト概要です。"),
            ("docs/ja-jp/DEV.md", "日本語 Dev Notes", "認証、CORS、endpoint、コンテンツ転送を扱う日本語開発文書です。"),
            ("docs/ru-ru/README.md", "ロシア語 README", "ロシア語開発者向けのプロジェクト概要です。"),
            ("docs/ru-ru/DEV.md", "ロシア語 Dev Notes", "認証、CORS、endpoint、コンテンツ転送を扱うロシア語開発文書です。"),
            ("content/legal/terms.md", "利用規約", "GET /api/legal/terms で返される既定の中国語規約文書です。"),
            ("content/legal/privacy.md", "プライバシーポリシー", "GET /api/legal/privacy で返される既定の中国語プライバシー文書です。"),
            ("content/legal/eula.md", "EULA", "GET /api/legal/eula で返される既定の中国語 EULA です。ライセンス境界、私設サーバー、解析制限を扱います。"),
        ],
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
        "markdown_title": "Markdown документы",
        "markdown_body": "Ниже перечислены Markdown документы репозитория. Китайский язык используется по умолчанию. Английские, японские и русские документы находятся в docs/en-us, docs/ja-jp и docs/ru-ru. Юридические документы также доступны через /api/legal/*. Нажмите на элемент, чтобы прочитать содержимое.",
        "links_title": "Ссылки",
        "admin_link": "Открыть панель управления",
        "markdown_docs": [
            ("README.md", "Описание проекта", "Основной китайский документ с функциями, запуском, конфигурацией, обзором API, админ-панелью, сюжетом и аудио."),
            ("DEV.md", "Заметки разработчика", "Китайское руководство по handshake, подписи, передаче контента, admin API, Cookie, статусу и проверкам."),
            ("CLIENT_DEV.md", "Документ клиента", "Руководство для HTML/WebGL, мобильных и настольных клиентов: CORS, client metadata, подпись, синхронизация, сюжет и производительность."),
            ("docs/en-us/README.md", "English README", "Английский обзор проекта для разработчиков."),
            ("docs/en-us/DEV.md", "English Dev Notes", "Английские заметки по протоколу, endpoint, передаче контента и развертыванию."),
            ("docs/ja-jp/README.md", "Japanese README", "Японский обзор проекта для разработчиков."),
            ("docs/ja-jp/DEV.md", "Japanese Dev Notes", "Японские заметки по аутентификации, CORS, endpoint и передаче контента."),
            ("docs/ru-ru/README.md", "Russian README", "Русский обзор проекта для разработчиков."),
            ("docs/ru-ru/DEV.md", "Russian Dev Notes", "Русские заметки по аутентификации, CORS, endpoint и передаче контента."),
            ("content/legal/terms.md", "Пользовательское соглашение", "Китайский документ условий, возвращается через GET /api/legal/terms."),
            ("content/legal/privacy.md", "Политика приватности", "Китайский документ приватности, возвращается через GET /api/legal/privacy."),
            ("content/legal/eula.md", "EULA", "Китайская EULA, возвращается через GET /api/legal/eula; описывает границы лицензии, private servers и ограничения reverse engineering."),
        ],
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
