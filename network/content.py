from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .crypto import developer_proof, encrypt_json_payload, md5_hex


class ContentStore:
    def __init__(self, story_file: Path, developer_secret: str) -> None:
        self.story_file = story_file
        self.developer_secret = developer_secret

    def load_story(self) -> dict[str, Any]:
        with self.story_file.open("r", encoding="utf-8") as story_data:
            return json.load(story_data)

    def encrypted_story_package(self, session_key: bytes) -> dict[str, Any]:
        story = self.load_story()
        raw = json.dumps(story, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        content_md5 = md5_hex(raw)
        return {
            "kind": "story_json",
            "encoding": "base64",
            "encryption": "xor-sha256-session-key",
            "md5": content_md5,
            "server_key": developer_proof(self.developer_secret, session_key, content_md5),
            "payload": encrypt_json_payload(raw, session_key),
        }
